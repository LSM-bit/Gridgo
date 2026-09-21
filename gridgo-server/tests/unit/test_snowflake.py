"""雪花 ID 生成器单测（标准 64 位 Snowflake，users.id 非自增）

覆盖：位分配常量、ID 落在 0 < id <= 2^63 - 1（可存 BIGINT）、单线程严格递增、
多线程并发生成不重复、ID 结构可按位还原（时间戳/节点/序列）、worker_id 越界拒绝。
纯计算，不连接数据库。
"""

import threading

import pytest

from app.utils.snowflake import (
    MAX_ID,
    MAX_SEQUENCE,
    MAX_TIMESTAMP,
    MAX_WORKER_ID,
    SEQUENCE_BITS,
    TIMESTAMP_BITS,
    WORKER_BITS,
    SnowflakeGenerator,
    generate_user_id,
    is_valid_snowflake_id,
)


def test_bit_allocation_is_standard_64bit():
    assert (TIMESTAMP_BITS, WORKER_BITS, SEQUENCE_BITS) == (41, 10, 12)
    assert TIMESTAMP_BITS + WORKER_BITS + SEQUENCE_BITS == 63  # 符号位留空
    assert MAX_ID == (1 << 63) - 1
    assert MAX_ID == 9_223_372_036_854_775_807
    assert MAX_WORKER_ID == 1023
    assert MAX_SEQUENCE == 4095


def test_generated_id_within_bigint_range():
    for _ in range(500):
        value = generate_user_id()
        assert isinstance(value, int)
        assert 0 < value <= MAX_ID
        assert value < 2**63


def test_generated_ids_strictly_increasing():
    gen = SnowflakeGenerator(worker_id=1)
    ids = [gen.next_id() for _ in range(300)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_concurrent_generation_unique():
    gen = SnowflakeGenerator(worker_id=7)
    results: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        batch = [gen.next_id() for _ in range(200)]
        with lock:
            results.extend(batch)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 1000
    assert len(set(results)) == 1000


def test_id_structure_is_decodable():
    worker_id = 513
    gen = SnowflakeGenerator(worker_id=worker_id)
    value = gen.next_id()

    sequence = value & MAX_SEQUENCE
    decoded_worker = (value >> SEQUENCE_BITS) & MAX_WORKER_ID
    timestamp = (value >> (SEQUENCE_BITS + WORKER_BITS)) & MAX_TIMESTAMP

    assert decoded_worker == worker_id
    assert 0 <= sequence <= MAX_SEQUENCE
    assert timestamp == gen.last_timestamp


def test_worker_id_out_of_range_rejected():
    for bad in (-1, MAX_WORKER_ID + 1):
        with pytest.raises(ValueError):
            SnowflakeGenerator(worker_id=bad)


def test_is_valid_snowflake_id():
    assert is_valid_snowflake_id(1)
    assert is_valid_snowflake_id(MAX_ID)
    assert not is_valid_snowflake_id(0)
    assert not is_valid_snowflake_id(-1)
    assert not is_valid_snowflake_id(MAX_ID + 1)
    assert not is_valid_snowflake_id("1")  # type: ignore[arg-type]
