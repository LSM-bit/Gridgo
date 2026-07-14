"""add actions and settlement_amount to game records

Revision ID: a1b2c3d4e5f6
Revises: 36c5dd26aae6
Create Date: 2026-07-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '36c5dd26aae6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add actions column to game_records and settlement_amount to game_players."""
    # game_records: 添加压缩编码的操作序列字段
    op.add_column('game_records', sa.Column('actions', sa.Text(), nullable=True, comment='压缩编码的操作序列'))

    # game_players: 添加结算金额字段
    op.add_column('game_players', sa.Column('settlement_amount', sa.Integer(), nullable=False, server_default='0', comment='结算金额（正=盈利，负=亏损）'))


def downgrade() -> None:
    """Remove actions and settlement_amount columns."""
    op.drop_column('game_players', 'settlement_amount')
    op.drop_column('game_records', 'actions')
