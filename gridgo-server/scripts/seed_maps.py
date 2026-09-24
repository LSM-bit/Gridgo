"""
插入地图初始数据种子（classic / city / island）

背景：前端地图下拉提供「经典地图 / 城市风云 / 海岛探险」三种选项，
而历史种子脚本只写入了 classic，导致选择 city / island 创建的房间
在开局阶段必然失败（地图不存在）。本脚本统一补种三套 40 格地图。

使用方法：
    cd gridgo-server
    python -m scripts.seed_maps              # 缺哪张补哪张（已存在的跳过）
    python -m scripts.seed_maps --force      # 删除并重建全部三张地图数据
    python -m scripts.seed_maps --map city   # 只处理指定地图（可重复传参）

结构约束（与游戏引擎/前端棋盘强绑定，不可随意改动）：
    - 每张地图 40 格，position 0-39
    - position 0 = START，10 = JAIL，20 = PARKING，30 = GO_TO_JAIL（引擎硬编码监狱位置为 10）
    - 4 座 STATION、2 座 UTILITY、22 块 PROPERTY、6 格卡牌（3 CHANCE + 3 FATE）、2 格 TAX
"""

import argparse
import asyncio
import sys

# 修复 Windows 终端中文显示
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import delete, select

from app.core.database import async_session
from app.models.map import Map, MapCard, MapStationRent, MapTile, MapUtilityRent

# tile_group → group_color（前端棋盘分组配色，三张地图保持一致）
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

# 车站租金阶梯 / 设施骰子倍率（三张地图通用）
STATION_RENT = [
    (1, 25),
    (2, 50),
    (3, 75),
    (4, 100),
]

UTILITY_RENT = [
    (1, 4),
    (2, 10),
]

# ══════════════════════════════════════════════════════════
# classic 经典地图（与 scripts/seed_classic_map.py 完全一致，保证向后兼容）
# ══════════════════════════════════════════════════════════

CLASSIC_INFO = {
    "id": "classic",
    "name": "经典地图",
    "description": "GridGo 经典大富翁地图，40 格环形棋盘",
    "tile_count": 40,
    "start_bonus": 200,
    "jail_bail": 50,
    "max_build_level": 5,
    "is_active": True,
}

# (position, name, tile_type, tile_group, price, rent_0, rent_1, rent_2, rent_3, rent_4, rent_5, build_cost)
CLASSIC_TILES: list[tuple] = [
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

CLASSIC_TAX = {
    4: {"tax_amount": 200, "tax_is_percent": False, "description": "所得税，支付 200"},
    38: {"tax_amount": 100, "tax_is_percent": False, "description": "奢侈品税，支付 100"},
}

# (card_type, card_id, name, effect_type, effect_value, description)
CLASSIC_CARDS: list[tuple] = [
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

# ══════════════════════════════════════════════════════════
# city 城市风云（都市地标主题，物价整体略高于经典地图）
# ══════════════════════════════════════════════════════════

CITY_INFO = {
    "id": "city",
    "name": "城市风云",
    "description": "城市地标主题地图，起步价更高、中后期租金增长更快，适合快节奏对局",
    "tile_count": 40,
    "start_bonus": 250,
    "jail_bail": 80,
    "max_build_level": 5,
    "is_active": True,
}

CITY_TILES: list[tuple] = [
    (0, "起点", "START", None, None, None, None, None, None, None, None, None),
    (1, "中关村", "PROPERTY", "brown", 80, 6, 30, 90, 270, 400, 550, 50),
    (2, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (3, "五道口", "PROPERTY", "brown", 80, 6, 30, 90, 270, 400, 550, 50),
    (4, "城市维护费", "TAX", None, None, None, None, None, None, None, None, None),
    (5, "北京南站", "STATION", None, 220, None, None, None, None, None, None, None),
    (6, "陆家嘴", "PROPERTY", "light_blue", 120, 10, 50, 150, 450, 625, 750, 50),
    (7, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (8, "外滩", "PROPERTY", "light_blue", 120, 10, 50, 150, 450, 625, 750, 50),
    (9, "南京西路", "PROPERTY", "light_blue", 140, 12, 60, 180, 500, 700, 900, 50),
    (10, "监狱", "JAIL", None, None, None, None, None, None, None, None, None),
    (11, "珠江新城", "PROPERTY", "pink", 160, 14, 70, 200, 550, 750, 950, 100),
    (12, "城市电网", "UTILITY", None, 180, None, None, None, None, None, None, None),
    (13, "天河CBD", "PROPERTY", "pink", 160, 14, 70, 200, 550, 750, 950, 100),
    (14, "深圳湾", "PROPERTY", "pink", 180, 16, 80, 220, 600, 800, 1000, 100),
    (15, "虹桥枢纽", "STATION", None, 220, None, None, None, None, None, None, None),
    (16, "光谷", "PROPERTY", "orange", 200, 18, 90, 250, 700, 875, 1050, 100),
    (17, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (18, "楚河汉街", "PROPERTY", "orange", 200, 18, 90, 250, 700, 875, 1050, 100),
    (19, "江汉路", "PROPERTY", "orange", 220, 20, 100, 300, 750, 925, 1100, 100),
    (20, "免费停车", "PARKING", None, None, None, None, None, None, None, None, None),
    (21, "西湖", "PROPERTY", "red", 240, 22, 110, 330, 800, 975, 1150, 150),
    (22, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (23, "钱江新城", "PROPERTY", "red", 240, 22, 110, 330, 800, 975, 1150, 150),
    (24, "武林广场", "PROPERTY", "red", 260, 24, 120, 360, 850, 1025, 1200, 150),
    (25, "广州南站", "STATION", None, 220, None, None, None, None, None, None, None),
    (26, "天府广场", "PROPERTY", "yellow", 280, 26, 130, 390, 900, 1100, 1275, 150),
    (27, "锦里", "PROPERTY", "yellow", 280, 26, 130, 390, 900, 1100, 1275, 150),
    (28, "城市水厂", "UTILITY", None, 180, None, None, None, None, None, None, None),
    (29, "太古里", "PROPERTY", "yellow", 300, 28, 150, 450, 1000, 1200, 1400, 150),
    (30, "去监狱", "GO_TO_JAIL", None, None, None, None, None, None, None, None, None),
    (31, "金融城", "PROPERTY", "green", 320, 30, 150, 450, 1000, 1200, 1400, 200),
    (32, "天府大道", "PROPERTY", "green", 320, 30, 150, 450, 1000, 1200, 1400, 200),
    (33, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (34, "环球中心", "PROPERTY", "green", 350, 35, 175, 500, 1100, 1300, 1500, 200),
    (35, "宝安机场", "STATION", None, 220, None, None, None, None, None, None, None),
    (36, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (37, "中央公园", "PROPERTY", "blue", 380, 40, 180, 550, 1200, 1400, 1600, 200),
    (38, "豪宅税", "TAX", None, None, None, None, None, None, None, None, None),
    (39, "城市之光", "PROPERTY", "blue", 420, 50, 220, 650, 1500, 1800, 2100, 200),
]

CITY_TAX = {
    4: {"tax_amount": 200, "tax_is_percent": False, "description": "城市维护费，支付 200"},
    38: {"tax_amount": 100, "tax_is_percent": False, "description": "豪宅税，支付 100"},
}

CITY_CARDS: list[tuple] = [
    ("CHANCE", "C01", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
    ("CHANCE", "C02", "前进至最近的车站", "move_to_nearest_station", None, "移动到下一车站，需付双倍租金"),
    ("CHANCE", "C03", "地铁提速三站", "move_forward", 3, "向前移动 3 格"),
    ("CHANCE", "C04", "写字楼分红", "gain_money", 150, "从银行获得 150"),
    ("CHANCE", "C05", "物业维修费", "pay_per_house", 30, "每栋房屋支付 30，每家酒店支付 120"),
    ("CHANCE", "C06", "出入证", "get_out_of_jail", None, "获得免罪卡，可随时使用出狱"),
    ("CHANCE", "C07", "错过地铁", "move_backward", 1, "向后移动 1 格"),
    ("CHANCE", "C08", "前进至中关村", "move_to_position", 1, "移动到中关村"),
    ("CHANCE", "C09", "违章罚款", "lose_money", 40, "支付 40"),
    ("CHANCE", "C10", "前进至监狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F01", "银行利息", "gain_money", 100, "从银行获得 100"),
    ("FATE", "F02", "医疗费用", "lose_money", 50, "支付 50"),
    ("FATE", "F03", "生日快乐", "gain_from_all", 20, "每位其他玩家向你支付 20"),
    ("FATE", "F04", "遗产继承", "gain_money", 200, "从银行获得 200"),
    ("FATE", "F05", "出狱卡", "get_out_of_jail", None, "获得免罪卡"),
    ("FATE", "F06", "入狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F07", "补缴税款", "pay_per_house", 40, "每栋房屋支付 40，每家酒店支付 115"),
    ("FATE", "F08", "项目中标", "gain_money", 500, "从银行获得 500"),
    ("FATE", "F09", "咨询费", "lose_money", 25, "支付 25"),
    ("FATE", "F10", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
]

# ══════════════════════════════════════════════════════════
# island 海岛探险（海岛主题，前期便宜、后期高租金，节奏反差更大）
# ══════════════════════════════════════════════════════════

ISLAND_INFO = {
    "id": "island",
    "name": "海岛探险",
    "description": "环岛探险主题地图，前期地价低廉、末期高租金，过路费波动更大",
    "tile_count": 40,
    "start_bonus": 200,
    "jail_bail": 50,
    "max_build_level": 5,
    "is_active": True,
}

ISLAND_TILES: list[tuple] = [
    (0, "起点", "START", None, None, None, None, None, None, None, None, None),
    (1, "椰林小径", "PROPERTY", "brown", 60, 4, 20, 60, 180, 320, 450, 50),
    (2, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (3, "贝壳沙滩", "PROPERTY", "brown", 60, 4, 20, 60, 180, 320, 450, 50),
    (4, "登岛税", "TAX", None, None, None, None, None, None, None, None, None),
    (5, "北岸渡口", "STATION", None, 200, None, None, None, None, None, None, None),
    (6, "珊瑚礁", "PROPERTY", "light_blue", 100, 6, 30, 90, 270, 400, 550, 50),
    (7, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (8, "浅水湾", "PROPERTY", "light_blue", 100, 6, 30, 90, 270, 400, 550, 50),
    (9, "渔人码头", "PROPERTY", "light_blue", 120, 8, 40, 100, 300, 450, 600, 50),
    (10, "监狱", "JAIL", None, None, None, None, None, None, None, None, None),
    (11, "灯塔岬", "PROPERTY", "pink", 140, 10, 50, 150, 450, 625, 750, 100),
    (12, "海岛发电站", "UTILITY", None, 150, None, None, None, None, None, None, None),
    (13, "红树林", "PROPERTY", "pink", 140, 10, 50, 150, 450, 625, 750, 100),
    (14, "潮汐湾", "PROPERTY", "pink", 160, 12, 60, 180, 500, 700, 900, 100),
    (15, "东岸港口", "STATION", None, 200, None, None, None, None, None, None, None),
    (16, "丛林营地", "PROPERTY", "orange", 180, 14, 70, 200, 550, 750, 950, 100),
    (17, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (18, "火山口", "PROPERTY", "orange", 180, 14, 70, 200, 550, 750, 950, 100),
    (19, "火山温泉", "PROPERTY", "orange", 200, 16, 80, 220, 600, 800, 1000, 100),
    (20, "免费停车", "PARKING", None, None, None, None, None, None, None, None, None),
    (21, "黑沙滩", "PROPERTY", "red", 220, 18, 90, 250, 700, 875, 1050, 150),
    (22, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (23, "珊瑚宫殿", "PROPERTY", "red", 220, 18, 90, 250, 700, 875, 1050, 150),
    (24, "海盗湾", "PROPERTY", "red", 240, 20, 100, 300, 750, 925, 1100, 150),
    (25, "灯塔码头", "STATION", None, 200, None, None, None, None, None, None, None),
    (26, "深蓝海峡", "PROPERTY", "yellow", 260, 22, 110, 330, 800, 975, 1150, 150),
    (27, "海豚湾", "PROPERTY", "yellow", 260, 22, 110, 330, 800, 975, 1150, 150),
    (28, "海水淡化厂", "UTILITY", None, 150, None, None, None, None, None, None, None),
    (29, "珍珠渔场", "PROPERTY", "yellow", 280, 24, 120, 360, 850, 1025, 1200, 150),
    (30, "去监狱", "GO_TO_JAIL", None, None, None, None, None, None, None, None, None),
    (31, "秘境森林", "PROPERTY", "green", 300, 26, 130, 390, 900, 1100, 1275, 200),
    (32, "远古遗迹", "PROPERTY", "green", 300, 26, 130, 390, 900, 1100, 1275, 200),
    (33, "命运卡", "FATE", None, None, None, None, None, None, None, None, None),
    (34, "失落神庙", "PROPERTY", "green", 320, 28, 150, 450, 1000, 1200, 1400, 200),
    (35, "深海港", "STATION", None, 200, None, None, None, None, None, None, None),
    (36, "机会卡", "CHANCE", None, None, None, None, None, None, None, None, None),
    (37, "海神神殿", "PROPERTY", "blue", 350, 35, 175, 500, 1100, 1300, 1500, 200),
    (38, "遗迹保护费", "TAX", None, None, None, None, None, None, None, None, None),
    (39, "世界尽头", "PROPERTY", "blue", 400, 50, 200, 600, 1400, 1700, 2000, 200),
]

ISLAND_TAX = {
    4: {"tax_amount": 200, "tax_is_percent": False, "description": "登岛税，支付 200"},
    38: {"tax_amount": 100, "tax_is_percent": False, "description": "遗迹保护费，支付 100"},
}

ISLAND_CARDS: list[tuple] = [
    ("CHANCE", "C01", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
    ("CHANCE", "C02", "前进至最近的车站", "move_to_nearest_station", None, "移动到下一车站，需付双倍租金"),
    ("CHANCE", "C03", "顺风三格", "move_forward", 3, "向前移动 3 格"),
    ("CHANCE", "C04", "渔获丰收", "gain_money", 150, "从银行获得 150"),
    ("CHANCE", "C05", "船只维修费", "pay_per_house", 25, "每栋房屋支付 25，每家酒店支付 100"),
    ("CHANCE", "C06", "离岛通行证", "get_out_of_jail", None, "获得免罪卡，可随时使用出狱"),
    ("CHANCE", "C07", "退潮搁浅", "move_backward", 1, "向后移动 1 格"),
    ("CHANCE", "C08", "前进至椰林小径", "move_to_position", 1, "移动到椰林小径"),
    ("CHANCE", "C09", "违规捕捞罚款", "lose_money", 40, "支付 40"),
    ("CHANCE", "C10", "前进至监狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F01", "银行利息", "gain_money", 100, "从银行获得 100"),
    ("FATE", "F02", "医疗费用", "lose_money", 50, "支付 50"),
    ("FATE", "F03", "生日快乐", "gain_from_all", 20, "每位其他玩家向你支付 20"),
    ("FATE", "F04", "发现宝藏", "gain_money", 200, "从银行获得 200"),
    ("FATE", "F05", "出狱卡", "get_out_of_jail", None, "获得免罪卡"),
    ("FATE", "F06", "入狱", "go_to_jail", None, "直接进入监狱"),
    ("FATE", "F07", "补缴税款", "pay_per_house", 40, "每栋房屋支付 40，每家酒店支付 115"),
    ("FATE", "F08", "打捞沉船", "gain_money", 500, "从银行获得 500"),
    ("FATE", "F09", "向导费", "lose_money", 25, "支付 25"),
    ("FATE", "F10", "前进至起点", "move_to_position", 0, "移动到起点，获得过路费"),
]

# ─── 三张地图汇总 ─────────────────────────────────────────

MAP_BUNDLES: dict[str, dict] = {
    "classic": {"info": CLASSIC_INFO, "tiles": CLASSIC_TILES, "tax": CLASSIC_TAX, "cards": CLASSIC_CARDS},
    "city": {"info": CITY_INFO, "tiles": CITY_TILES, "tax": CITY_TAX, "cards": CITY_CARDS},
    "island": {"info": ISLAND_INFO, "tiles": ISLAND_TILES, "tax": ISLAND_TAX, "cards": ISLAND_CARDS},
}

# 结构契约：位置 → 地块类型（引擎硬编码监狱位置 10，三张地图必须一致）
EXPECTED_SKELETON = {pos: tile[2] for pos, tile in enumerate(CLASSIC_TILES)}


def _validate(bundle: dict) -> None:
    """写入前自检地图结构，避免把坏数据种进库"""
    tiles = bundle["tiles"]
    info = bundle["info"]
    assert len(tiles) == 40, f"{info['id']}: 地块数必须为 40，实际 {len(tiles)}"
    positions = [t[0] for t in tiles]
    assert positions == list(range(40)), f"{info['id']}: position 必须为 0-39 连续"
    for pos, tile in enumerate(tiles):
        assert tile[2] == EXPECTED_SKELETON[pos], (
            f"{info['id']}: position {pos} 类型应为 {EXPECTED_SKELETON[pos]}，实际 {tile[2]}"
        )
        if tile[3]:
            assert tile[3] in GROUP_COLORS, f"{info['id']}: 未知分组 {tile[3]}"
    card_ids = [(c[0], c[1]) for c in bundle["cards"]]
    assert len(card_ids) == len(set(card_ids)), f"{info['id']}: 卡片编号重复"
    for c in bundle["cards"]:
        if c[3] == "move_to_position":
            assert 0 <= c[4] < 40, f"{info['id']}: 卡片 {c[1]} 目标位置越界"


async def _seed_one(session, map_id: str, bundle: dict, force: bool) -> str:
    """写入单张地图，返回执行结果描述"""
    info = bundle["info"]
    result = await session.execute(select(Map).where(Map.id == map_id))
    existing = result.scalars().first()

    if existing and not force:
        tile_count = len(
            (await session.execute(select(MapTile.id).where(MapTile.map_id == map_id))).scalars().all()
        )
        if tile_count == info["tile_count"]:
            return f"跳过 {map_id}：已存在且地块完整（{tile_count} 格）"
        return f"跳过 {map_id}：已存在但地块不完整（{tile_count}/{info['tile_count']}），如需修复请加 --force"

    if existing:
        # --force：先清理该地图的旧数据（仅限本地图，逐表按 map_id 删除）
        await session.execute(delete(MapTile).where(MapTile.map_id == map_id))
        await session.execute(delete(MapStationRent).where(MapStationRent.map_id == map_id))
        await session.execute(delete(MapUtilityRent).where(MapUtilityRent.map_id == map_id))
        await session.execute(delete(MapCard).where(MapCard.map_id == map_id))
        await session.delete(existing)
        await session.flush()

    session.add(Map(**info))

    for t in bundle["tiles"]:
        pos, name, tile_type, tile_group, price, r0, r1, r2, r3, r4, r5, build_cost = t
        session.add(
            MapTile(
                map_id=map_id,
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
                **bundle["tax"].get(pos, {}),
            )
        )

    for owned, rent in STATION_RENT:
        session.add(MapStationRent(map_id=map_id, owned_count=owned, rent=rent))

    for owned, mult in UTILITY_RENT:
        session.add(MapUtilityRent(map_id=map_id, owned_count=owned, dice_multiplier=mult))

    for c in bundle["cards"]:
        card_type, card_id, name, effect_type, effect_value, desc = c
        session.add(
            MapCard(
                map_id=map_id,
                card_type=card_type,
                card_id=card_id,
                name=name,
                effect_type=effect_type,
                effect_value=effect_value,
                description=desc,
            )
        )

    return (
        f"写入 {map_id}（{info['name']}）：maps 1 / map_tiles {len(bundle['tiles'])} / "
        f"map_station_rent {len(STATION_RENT)} / map_utility_rent {len(UTILITY_RENT)} / "
        f"map_cards {len(bundle['cards'])}"
    )


async def seed(map_ids: list[str], force: bool) -> None:
    for map_id in map_ids:
        _validate(MAP_BUNDLES[map_id])

    async with async_session() as session:
        lines = []
        for map_id in map_ids:
            lines.append(await _seed_one(session, map_id, MAP_BUNDLES[map_id], force))
        await session.commit()

    print("✅ 地图种子数据处理完成")
    for line in lines:
        print(f"   - {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GridGo 地图种子（classic / city / island）")
    parser.add_argument(
        "--map",
        dest="maps",
        action="append",
        choices=sorted(MAP_BUNDLES.keys()),
        help="仅处理指定地图，可重复传参；默认处理全部三张",
    )
    parser.add_argument("--force", action="store_true", help="删除并重建目标地图数据")
    args = parser.parse_args()
    asyncio.run(seed(args.maps or sorted(MAP_BUNDLES.keys()), args.force))


if __name__ == "__main__":
    main()
