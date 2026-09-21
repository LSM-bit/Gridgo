"""Alembic 迁移链单测（docs/PROJECT.md 6.2）

覆盖：迁移链单头、新迁移挂在 a1b2c3d4e5f6 之后、且创建 rooms / room_players /
user_stats / game_turn_logs / friendships 五张表。
纯文件解析，不连接数据库。
"""

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

SERVER_ROOT = Path(__file__).resolve().parents[2]
NEW_REVISION = "b7c1d9e4a2f8"
# 最新 head：雪花 UID 列类型修复迁移（game_players.user_id / game_records.winner_id -> bigint）
LATEST_REVISION = "c8e2f4a91b73"
EXPECTED_TABLES = {
    "rooms",
    "room_players",
    "user_stats",
    "game_turn_logs",
    "friendships",
}


def _script() -> ScriptDirectory:
    cfg = Config(str(SERVER_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER_ROOT / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_single_head():
    heads = _script().get_heads()
    assert len(heads) == 1, f"迁移链存在多头: {heads}"
    assert heads[0] == LATEST_REVISION


def test_new_revision_chained_after_previous_head():
    rev = _script().get_revision(NEW_REVISION)
    assert rev is not None
    assert rev.down_revision == "a1b2c3d4e5f6"


def test_new_migration_creates_expected_tables():
    path = SERVER_ROOT / "alembic" / "versions" / f"{NEW_REVISION}_create_rooms_stats_friends_tables.py"
    assert path.exists(), f"缺少迁移脚本: {path}"
    source = path.read_text(encoding="utf-8")
    created = set(re.findall(r"op\.create_table\(\s*['\"]([a-z_]+)['\"]", source))
    assert EXPECTED_TABLES <= created, f"缺失建表: {EXPECTED_TABLES - created}"
    dropped = set(re.findall(r"op\.drop_table\(\s*['\"]([a-z_]+)['\"]", source))
    assert EXPECTED_TABLES <= dropped, f"downgrade 未完整回滚: {EXPECTED_TABLES - dropped}"


def test_latest_revision_chained_after_new_revision():
    """最新迁移（user 引用列扩宽为 bigint）挂在 b7c1d9e4a2f8 之后"""
    rev = _script().get_revision(LATEST_REVISION)
    assert rev is not None
    assert rev.down_revision == NEW_REVISION
