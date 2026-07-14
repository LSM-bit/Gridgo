"""
地图数据库模型
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Map(Base):
    """地图表 — 存储地图模板基本信息"""

    __tablename__ = "maps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="地图ID（如 classic, city, island）")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="地图显示名称")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="地图描述")
    tile_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=40, comment="地块总数")
    start_bonus: Mapped[int] = mapped_column(nullable=False, default=200, comment="经过起点奖励金额")
    jail_bail: Mapped[int] = mapped_column(nullable=False, default=50, comment="保释金金额")
    max_build_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5, comment="最大建筑等级（0=空地, 5=酒店）")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class MapTile(Base):
    """地块配置表 — 存储地图中每个位置的地块详情"""

    __tablename__ = "map_tiles"
    __table_args__ = (
        UniqueConstraint("map_id", "position", name="uq_map_tile_position"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    map_id: Mapped[str] = mapped_column(String(32), ForeignKey("maps.id"), nullable=False, comment="所属地图")
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="地块在棋盘上的位置（0-39）")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="地块名称（如'朝阳路'）")
    tile_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="地块类型：START / PROPERTY / STATION / UTILITY / CHANCE / FATE / TAX / JAIL / PARKING / GO_TO_JAIL",
    )
    tile_group: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="地产分组：brown / light_blue / pink / orange / red / yellow / green / blue（仅PROPERTY类型）",
    )
    group_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="分组颜色（前端渲染用，与tile_group一一对应）",
    )
    price: Mapped[int | None] = mapped_column(nullable=True, comment="购买价格（仅PROPERTY / STATION / UTILITY）")
    build_cost: Mapped[int | None] = mapped_column(nullable=True, comment="每级建筑升级费用（仅PROPERTY）")
    rent_0: Mapped[int | None] = mapped_column(nullable=True, comment="空地租金（建筑等级=0）")
    rent_1: Mapped[int | None] = mapped_column(nullable=True, comment="1栋房屋租金")
    rent_2: Mapped[int | None] = mapped_column(nullable=True, comment="2栋房屋租金")
    rent_3: Mapped[int | None] = mapped_column(nullable=True, comment="3栋房屋租金")
    rent_4: Mapped[int | None] = mapped_column(nullable=True, comment="4栋房屋租金")
    rent_5: Mapped[int | None] = mapped_column(nullable=True, comment="酒店租金")
    tax_amount: Mapped[int | None] = mapped_column(nullable=True, comment="税收金额（仅TAX类型）")
    tax_is_percent: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True, comment="税收是否为百分比")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="图标标识（前端渲染用）")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="地块描述/提示文字")


class MapStationRent(Base):
    """车站租金阶梯表 — 拥有N座车站时的租金"""

    __tablename__ = "map_station_rent"
    __table_args__ = (
        UniqueConstraint("map_id", "owned_count", name="uq_map_station_rent"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    map_id: Mapped[str] = mapped_column(String(32), ForeignKey("maps.id"), nullable=False, comment="所属地图")
    owned_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="拥有车站数量（1-4）")
    rent: Mapped[int] = mapped_column(nullable=False, comment="对应租金")


class MapUtilityRent(Base):
    """公共设施租金规则表 — 拥有N座设施时的骰子倍率"""

    __tablename__ = "map_utility_rent"
    __table_args__ = (
        UniqueConstraint("map_id", "owned_count", name="uq_map_utility_rent"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    map_id: Mapped[str] = mapped_column(String(32), ForeignKey("maps.id"), nullable=False, comment="所属地图")
    owned_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="拥有设施数量（1-2）")
    dice_multiplier: Mapped[int] = mapped_column(nullable=False, comment="骰子倍率（1座=×4, 2座=×10）")


class MapCard(Base):
    """卡片配置表 — 机会卡/命运卡效果"""

    __tablename__ = "map_cards"
    __table_args__ = (
        UniqueConstraint("map_id", "card_type", "card_id", name="uq_map_card"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    map_id: Mapped[str] = mapped_column(String(32), ForeignKey("maps.id"), nullable=False, comment="所属地图")
    card_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="卡片类型：CHANCE / FATE")
    card_id: Mapped[str] = mapped_column(String(10), nullable=False, comment="卡片编号（如C01, F05）")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="卡片名称")
    effect_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="效果类型：move_to_position / move_forward / move_backward / move_to_nearest_station / "
                "gain_money / lose_money / pay_per_house / gain_from_all / go_to_jail / get_out_of_jail",
    )
    effect_value: Mapped[int | None] = mapped_column(nullable=True, comment="效果数值（金额、步数等）")
    description: Mapped[str] = mapped_column(String(200), nullable=False, comment="卡片描述文字")
