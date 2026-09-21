"""
雪花算法（Snowflake）ID 生成器 —— 标准 64 位整数版本

位分配（共 64 bit，符号位留空，保证结果 ∈ [0, 2^63 - 1]，可存入 BIGINT）：
    ┌─────── 64 bit ─────────────────────────────────────────────┐
    │ 1 bit │ 41 bit 时间戳(毫秒) │ 10 bit 节点 │ 12 bit 序列 │
    └───────┴─────────────────────┴─────────────┴─────────────┘

说明：
  - 最高符号位固定为 0，因此生成的 ID 恒为正整数，
    最大值为 2^63 - 1 = 9_223_372_036_854_775_807，可直接存入 PostgreSQL BIGINT。
  - 时间戳以「毫秒」为单位，相对自定义纪元 EPOCH（默认 2026-01-01 UTC）计算，
    41 bit 毫秒约可支撑 69 年。
  - 10 bit 节点 ID 支持 0-1023 共 1024 个实例；12 bit 序列表示同一毫秒内最多
    4096 个 ID，单节点容量约 409.6 万 ID/秒；序列耗尽时自旋等待下一毫秒。
  - 采用单调递增的时间戳 + 线程锁，保证单进程内 ID 严格递增且不重复。

用法：
    from app.utils.snowflake import generate_user_id

    new_id = generate_user_id()
"""

from __future__ import annotations

import threading
import time

# ─── 位分配常量 ───
TIMESTAMP_BITS = 41
WORKER_BITS = 10
SEQUENCE_BITS = 12

# 最大值（掩码）
MAX_ID = (1 << 63) - 1  # 2^63 - 1，可直接存入 BIGINT
MAX_TIMESTAMP = (1 << TIMESTAMP_BITS) - 1  # 2^41 - 1
MAX_WORKER_ID = (1 << WORKER_BITS) - 1  # 1023
MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1  # 4095

# 自定义纪元：2026-01-01T00:00:00Z（毫秒级 Unix 时间戳）
DEFAULT_EPOCH_MS = 1_767_225_600_000

# 位偏移（符号位恒为 0，不参与运算）
WORKER_SHIFT = SEQUENCE_BITS  # 12
TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_BITS  # 22


class SnowflakeGenerator:
    """64 位雪花 ID 生成器（线程安全）"""

    def __init__(
        self,
        worker_id: int = 0,
        epoch_ms: int = DEFAULT_EPOCH_MS,
    ) -> None:
        if not 0 <= worker_id <= MAX_WORKER_ID:
            raise ValueError(f"worker_id 必须在 0-{MAX_WORKER_ID} 之间")
        if epoch_ms < 0:
            raise ValueError("epoch_ms 必须为非负整数")
        self._worker_id = worker_id
        self._epoch = epoch_ms
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    # ─── 属性 ───
    @property
    def worker_id(self) -> int:
        return self._worker_id

    @property
    def epoch_ms(self) -> int:
        return self._epoch

    @property
    def last_timestamp(self) -> int:
        return self._last_timestamp

    # ─── 内部方法 ───
    def _now(self) -> int:
        """当前相对纪元的毫秒级时间戳"""
        return int(time.time() * 1000) - self._epoch

    def next_id(self) -> int:
        """生成下一个 64 位 ID（恒 <= MAX_ID）"""
        with self._lock:
            timestamp = self._now()

            # 时钟回拨保护：回拨时自旋等待，追平后继续；追不平则报错
            if timestamp < self._last_timestamp:
                for _ in range(5):
                    time.sleep(0.002)
                    timestamp = self._now()
                    if timestamp >= self._last_timestamp:
                        break
                if timestamp < self._last_timestamp:
                    raise RuntimeError("检测到时钟回拨，无法生成雪花 ID")

            if timestamp == self._last_timestamp:
                # 同一毫秒内：递增序列
                self._sequence = (self._sequence + 1) & MAX_SEQUENCE
                if self._sequence == 0:
                    # 本毫秒 4096 个序列已耗尽，等待下一毫秒
                    while timestamp <= self._last_timestamp:
                        time.sleep(0.0002)
                        timestamp = self._now()
            else:
                self._sequence = 0

            self._last_timestamp = timestamp

            new_id = (
                ((timestamp & MAX_TIMESTAMP) << TIMESTAMP_SHIFT)
                | (self._worker_id << WORKER_SHIFT)
                | self._sequence
            )
            assert new_id <= MAX_ID, "生成的 ID 超出 64 位范围"
            return new_id


# ─── 全局单例 ───
_generator: SnowflakeGenerator | None = None
_generator_lock = threading.Lock()


def get_generator() -> SnowflakeGenerator:
    """获取全局雪花生成器（首次调用时按配置初始化）"""
    global _generator
    if _generator is None:
        with _generator_lock:
            if _generator is None:
                from app.core.config import settings

                _generator = SnowflakeGenerator(
                    worker_id=getattr(settings, "SNOWFLAKE_WORKER_ID", 0)
                )
    return _generator


def generate_user_id() -> int:
    """生成一个用户 ID（64 位雪花 ID，<= 2^63 - 1，可直接存入 BIGINT）"""
    return get_generator().next_id()


def is_valid_snowflake_id(value: int) -> bool:
    """校验 value 是否为合法的 64 位雪花 ID（正整数且不超过 2^63 - 1）"""
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value <= MAX_ID
