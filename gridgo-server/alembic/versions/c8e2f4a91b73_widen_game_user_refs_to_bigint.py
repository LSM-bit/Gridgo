"""widen game_players.user_id and game_records.winner_id to bigint

Revision ID: c8e2f4a91b73
Revises: b7c1d9e4a2f8
Create Date: 2026-09-21 00:00:00.000000

修复雪花 UID（64 位）与 int4 列不兼容问题：
users.id 已升级为 bigint，但对局记录相关表的用户列仍为 integer，
导致按 user_id 查询 / 写入 game_players、game_records.winner_id 时溢出。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2f4a91b73'
down_revision: Union[str, Sequence[str], None] = 'b7c1d9e4a2f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: widen user reference columns to bigint."""
    op.alter_column(
        'game_players', 'user_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using='user_id::bigint',
    )
    op.alter_column(
        'game_records', 'winner_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using='winner_id::bigint',
    )


def downgrade() -> None:
    """Downgrade schema: revert columns to integer."""
    op.alter_column(
        'game_records', 'winner_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        'game_players', 'user_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
