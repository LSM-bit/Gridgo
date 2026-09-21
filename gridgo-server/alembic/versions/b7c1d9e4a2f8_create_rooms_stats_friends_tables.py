"""create rooms / room_players / user_stats / game_turn_logs / friendships

补齐 docs/PROJECT.md 6.2 声明但此前无迁移的表：
  - rooms / room_players：Redis 运行时房间状态的写穿透镜像（含 rooms.password_hash）
  - user_stats：结算累计统计，排行榜（GET /leaderboard）数据源
  - game_turn_logs：逐回合操作日志
  - friendships：好友关系（申请 + 关系共用一张表）

Revision ID: b7c1d9e4a2f8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-20 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d9e4a2f8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create rooms / room_players / user_stats / game_turn_logs / friendships."""
    # ─── rooms：房间持久化镜像 ───
    op.create_table(
        'rooms',
        sa.Column('id', sa.String(length=32), nullable=False, comment='房间 ID'),
        sa.Column('room_code', sa.String(length=8), nullable=False, comment='6 位房间代码'),
        sa.Column('name', sa.String(length=50), nullable=False, server_default='GridGo 房间', comment='房间名称'),
        sa.Column('host_id', sa.BigInteger(), nullable=False, comment='房主 user_id'),
        sa.Column('password_hash', sa.String(length=255), nullable=True, comment='房间密码哈希（无密码为 NULL）'),
        sa.Column('max_players', sa.SmallInteger(), nullable=False, server_default='8', comment='最大玩家数'),
        sa.Column('map_id', sa.String(length=32), nullable=False, server_default='classic', comment='地图 ID'),
        sa.Column('ai_count', sa.SmallInteger(), nullable=False, server_default='0', comment='AI 数量'),
        sa.Column('ai_difficulty', sa.String(length=10), nullable=False, server_default='easy', comment='AI 难度'),
        sa.Column('status', sa.SmallInteger(), nullable=False, server_default='0', comment='0=等待 1=游戏中 2=已结束'),
        sa.Column('config', sa.JSON(), nullable=True, comment='房间配置快照'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_code'),
    )
    op.create_index('ix_rooms_status', 'rooms', ['status'], unique=False)

    # ─── room_players：房间玩家 / AI / 观战者镜像 ───
    op.create_table(
        'room_players',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('room_id', sa.String(length=32), nullable=False, comment='房间 ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='玩家 user_id（AI 为负数）'),
        sa.Column('nickname', sa.String(length=50), nullable=False, server_default='', comment='显示昵称'),
        sa.Column('is_host', sa.Boolean(), nullable=False, server_default=sa.false(), comment='是否房主'),
        sa.Column('is_ready', sa.Boolean(), nullable=False, server_default=sa.false(), comment='是否已准备'),
        sa.Column('is_ai', sa.Boolean(), nullable=False, server_default=sa.false(), comment='是否 AI'),
        sa.Column('ai_difficulty', sa.String(length=10), nullable=True, comment='AI 难度'),
        sa.Column('is_spectator', sa.Boolean(), nullable=False, server_default=sa.false(), comment='是否观战者'),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='加入时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_id', 'user_id', name='uq_room_players_room_user'),
    )
    op.create_index('ix_room_players_room_id', 'room_players', ['room_id'], unique=False)

    # ─── user_stats：结算统计（排行榜数据源） ───
    op.create_table(
        'user_stats',
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户 ID'),
        sa.Column('total_games', sa.Integer(), nullable=False, server_default='0', comment='总局数'),
        sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0', comment='总胜场'),
        sa.Column('total_bankruptcies', sa.Integer(), nullable=False, server_default='0', comment='破产次数'),
        sa.Column('total_rent_collected', sa.BigInteger(), nullable=False, server_default='0', comment='累计收取租金'),
        sa.Column('total_rent_paid', sa.BigInteger(), nullable=False, server_default='0', comment='累计支付租金'),
        sa.Column('best_rank', sa.SmallInteger(), nullable=True, comment='历史最佳排名'),
        sa.Column('win_streak', sa.Integer(), nullable=False, server_default='0', comment='当前连胜'),
        sa.Column('best_win_streak', sa.Integer(), nullable=False, server_default='0', comment='历史最高连胜'),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0', comment='积分（排行榜排序依据）'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('user_id'),
    )

    # ─── game_turn_logs：逐回合操作日志 ───
    op.create_table(
        'game_turn_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.BigInteger(), nullable=False, comment='对局记录 ID（game_records.id）'),
        sa.Column('turn_number', sa.Integer(), nullable=False, server_default='0', comment='回合数'),
        sa.Column('player_id', sa.BigInteger(), nullable=False, comment='操作玩家 user_id（AI 为负数）'),
        sa.Column('action_type', sa.String(length=50), nullable=False, comment='操作类型'),
        sa.Column('action_data', sa.JSON(), nullable=True, comment='操作详情'),
        sa.Column('dice_values', sa.String(length=10), nullable=True, comment='骰子点数，如 3,5'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='记录时间'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_game_turn_logs_game_id', 'game_turn_logs', ['game_id'], unique=False)

    # ─── friendships：好友关系（申请 + 关系共用） ───
    op.create_table(
        'friendships',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='发起方 user_id'),
        sa.Column('friend_id', sa.BigInteger(), nullable=False, comment='接收方 user_id'),
        sa.Column('status', sa.SmallInteger(), nullable=False, server_default='0', comment='0=待确认 1=已接受 2=已拒绝'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='申请时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'friend_id', name='uq_friendships_user_friend'),
    )
    op.create_index('ix_friendships_friend_id', 'friendships', ['friend_id'], unique=False)


def downgrade() -> None:
    """Drop friendships / game_turn_logs / user_stats / room_players / rooms."""
    op.drop_index('ix_friendships_friend_id', table_name='friendships')
    op.drop_table('friendships')

    op.drop_index('ix_game_turn_logs_game_id', table_name='game_turn_logs')
    op.drop_table('game_turn_logs')

    op.drop_table('user_stats')

    op.drop_index('ix_room_players_room_id', table_name='room_players')
    op.drop_table('room_players')

    op.drop_index('ix_rooms_status', table_name='rooms')
    op.drop_table('rooms')
