"""
插入 classic 地图初始数据种子

使用方法：
    cd gridgo-server
    python -m scripts.seed_classic_map
"""

import asyncio
import sys

# 修复 Windows 终端中文显示
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.core.database import async_session
from app.models.map import Map, MapCard, MapStationRent, MapTile, MapUtilityRent


# ─── maps ────────────────────────────────────────────────
MAP_DATA = {
    "id": "classic",
    "name": "经典地图",
    "description": "GridGo 经典大富翁地图，40 格环形棋盘",
    "tile_count": 40,
    "start_bonus": 200,
    "jail_bail": 50,
    "max_build_level": 5,
    "is_active": True,
}

# ─── map_tiles ───────────────────────────────────────────
# (position, name, tile_type, tile_group, price, rent_0, rent_1, rent_2, rent_3, rent_4, rent_5, build_cost)
TILES_RAW: list[tuple] = [
    (0, "起点", "START", None, None, None, None, None, None, None, None, None),
    (1, "朝阳路", "PROPERTY", "brown", 60, 4, 20, 60, 180, 320, 450, 50),
    (2, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (3, "朝阳大道", "PROPERTY", "brown", 60, 4, 20, 60, 180, 320, 450, 50),
    (4, "所得税", "TAX", None, None, None, None, None, None, None, None, None),
    (5, "北京站", "STATION", None, 200, None, None, None, None, None, None, None),
    (6, "长安街", "PROPERTY", "light_blue", 100, 6, 30, 90, 270, 400, 550, 50),
    (7, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (8, "南京路", "PROPERTY", "light_blue", 100, 6, 30, 90, 270, 400, 550, 50),
    (9, "淮海路", "PROPERTY", "light_blue", 120, 8, 40, 100, 300, 450, 600, 50),
    (10, "监狱", "JAIL", None, None, None, None, None, None, None, None, None),
    (11, "王府井", "PROPERTY", "pink", 140, 10, 50, 150, 450, 625, 750, 100),
    (12, "电力公司", "UTILITY", None, 150, None, None, None, None, None, None, None),
    (13, "西单", "PROPERTY", "pink", 140, 10, 50, 150, 450, 625, 750, 100),
    (14, "东单", "PROPERTY", "pink", 160, 12, 60, 180, 500, 700, 900, 100),
    (15, "上海站", "STATION", None, 200, None, None, None, None, None, None, None),
    (16, "春熙路", "PROPERTY", "orange", 180, 14, 70, 200, 550, 750, 950, 100),
    (17, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (18, "步行街", "PROPERTY", "orange", 180, 14, 70, 200, 550, 750, 950, 100),
    (19, "中山路", "PROPERTY", "orange", 200, 16, 80, 220, 600, 800, 1000, 100),
    (20, "免费停车", "PARKING", None, None, None, None, None, None, None, None, None),
    (21, "解放路", "PROPERTY", "red", 220, 18, 90, 250, 700, 875, 1050, 150),
    (22, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (23, "人民路", "PROPERTY", "red", 220, 18, 90, 250, 700, 875, 1050, 150),
    (24, "建设路", "PROPERTY", "red", 240, 20, 100, 300, 750, 925, 1100, 150),
    (25, "广州站", "STATION", None, 200, None, None, None, None, None, None, None),
    (26, "天河路", "PROPERTY", "yellow", 260, 22, 110, 330, 800, 975, 1150, 150),
    (27, "珠江路", "PROPERTY", "yellow", 260, 22, 110, 330, 800, 975, 1150, 150),
    (28, "自来水公司", "UTILITY", None, 150, None, None, None, None, None, None, None),
    (29, "体育西路", "PROPERTY", "yellow", 280, 24, 120, 360, 850, 1025, 1200, 150),
    (30, "去监狱", "GO_TO_JAIL", None, None, None, None, None, None, None, None, None),
    (31, "科技园", "PROPERTY", "green", 300, 26, 130, 390, 900, 1100, 1275, 200),
    (32, "软件大道", "PROPERTY", "green", 300, 26, 130, 390, 900, 1100, 1275, 200),
    (33, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (34, "金融街", "PROPERTY", "green", 320, 28, 150, 450, 1000, 1200, 1400, 200),
    (35, "深圳站", "STATION", None, 200, None, None, None, None, None, None, None),
    (36, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (37, "滨海大道", "PROPERTY", "blue", 350, 35, 175, 500, 1100, 1300, 1500, 200),
    (38, "奢侈品税", "TAX", None, None, None, None, None, None, None, None, None),
    (39, "前海路", "PROPERTY", "blue", 400, 50, 200, 600, 1400, 1700, 2000, 200),
]

# tile_group → group_color 映射
GROUP_COLORS = {
    "brown": "#8B4513",
    "light_blue": "#87CEEB",
    "pink": "#FF69B4",
    "orange": "#FFA500",
    "red": "#FF0000",
    "yellow": "#FFD700",
    "green": "#008000",
    "blue": "#0000CD",
}

# TAX 类型特殊字段
TAX_SPECIAL: dict[int, dict] = {
    4: {"tax_amount": 200, "tax_is_percent": False, "description": "所得税，支付 200"},
    38: {"tax_amount": 100, "tax_is_percent": False, "description": "奢侈品税，支付 100"},
}

# ─── map_station_rent ────────────────────────────────────
STATION_RENT = [
    (1, 25),
    (2, 50),
    (3, 75),
    (4, 100),
]

# ─── map_utility_rent ────────────────────────────────────
UTILITY_RENT = [
    (1, 4),
    (2, 10),
]

# ─── map_cards ───────────────────────────────────────────
# (card_type, card_id, name, effect_type, effect_value, description)
CARDS_RAW: list[tuple] = [
    ("CHANCE", "C01", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
    ("CHANCE", "C02", "前进至最近的车站", "move_to_nearest_station", None, "移动到下一车站，需付双倍租金"),
    ("CHANCE", "C03", "前进三格", "move_forward", 3, "向前移动 3 格"),
    ("CHANCE", "C04", "银行分红", "gain_money", 150, "从银行获得 150"),
    ("CHANCE", "C05", "修理费", "pay_per_house", 25, "每栋房屋支付 25，每家酒店支付 100"),
    ("CHANCE", "C06", "出狱卡", "get_out_of_jail", None, "获得免罪卡，可随时使用出狱"),
    ("CHANCE", "C07", "后退一格", "move_backward", 1, "向后移动 1 格"),
    ("CHANCE", "C08", "前进至朝阳路", "move_to_position", 1, "移动到朝阳路"),
    ("CHANCE", "C09", "被罚款", "lose_money", 40, "支付 40"),
    ("CHANCE", "C10", "前进至监狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F01", "银行利息", "gain_money", 100, "从银行获得 100"),
    ("FATE", "F02", "医疗费用", "lose_money", 50, "支付 50"),
    ("FATE", "F03", "生日快乐", "gain_from_all", 20, "每位其他玩家向你支付 20"),
    ("FATE", "F04", "遗产继承", "gain_money", 200, "从银行获得 200"),
    ("FATE", "F05", "出狱卡", "get_out_of_jail", None, "获得免罪卡"),
    ("FATE", "F06", "入狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F07", "补缴税款", "pay_per_house", 40, "每栋房屋支付 40，每家酒店支付 115"),
    ("FATE", "F08", "彩票中奖", "gain_money", 500, "从银行获得 500"),
    ("FATE", "F09", "咨询费", "lose_money", 25, "支付 25"),
    ("FATE", "F10", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
]


async def seed() -> None:
    """插入 classic 地图初始数据"""
    async with async_session() as session:
        # 检查是否已存在
        existing = await session.execute(select(Map).where(Map.id == "classic"))
        if existing.scalar_one_or_none():
            print("⚠️ classic 地图已存在，跳过种子数据插入")
            return

        # 1. 插入 maps
        map_obj = Map(**MAP_DATA)
        session.add(map_obj)

        # 2. 插入 map_tiles
        for t in TILES_RAW:
            pos, name, tile_type, tile_group, price, r0, r1, r2, r3, r4, r5, build_cost = t
            extra = TAX_SPECIAL.get(pos, {})
            tile = MapTile(
                map_id="classic",
                position=pos,
                name=name,
                tile_type=tile_type,
                tile_group=tile_group,
                group_color=GROUP_COLORS.get(tile_group) if tile_group else None,
                price=price,
                build_cost=build_cost,
                rent_0=r0,
                rent_1=r1,
                rent_2=r2,
                rent_3=r3,
                rent_4=r4,
                rent_5=r5,
                **extra,
            )
            session.add(tile)

        # 3. 插入 map_station_rent
        for owned, rent in STATION_RENT:
            session.add(MapStationRent(map_id="classic", owned_count=owned, rent=rent))

        # 4. 插入 map_utility_rent
        for owned, mult in UTILITY_RENT:
            session.add(MapUtilityRent(map_id="classic", owned_count=owned, dice_multiplier=mult))

        # 5. 插入 map_cards
        for c in CARDS_RAW:
            card_type, card_id, name, effect_type, effect_value, desc = c
            session.add(MapCard(
                map_id="classic",
                card_type=card_type,
                card_id=card_id,
                name=name,
                effect_type=effect_type,
                effect_value=effect_value,
                description=desc,
            ))

        await session.commit()
        print("✅ classic 地图种子数据插入完成")
        print(f"   - maps: 1 条")
        print(f"   - map_tiles: {len(TILES_RAW)} 条")
        print(f"   - map_station_rent: {len(STATION_RENT)} 条")
        print(f"   - map_utility_rent: {len(UTILITY_RENT)} 条")
        print(f"   - map_cards: {len(CARDS_RAW)} 条")


if __name__ == "__main__":
    asyncio.run(seed())
