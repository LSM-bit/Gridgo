"""
地图加载服务

从 MySQL 加载地图模板（maps, map_tiles, map_station_rent, map_utility_rent, map_cards），
缓存到 Redis，供游戏引擎初始化时使用。
"""

import json
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.map import Map, MapCard, MapStationRent, MapTile, MapUtilityRent


# Redis 缓存 TTL（1 小时）
MAP_CACHE_TTL = 3600


class MapService:
    """地图加载服务"""

    @staticmethod
    async def load_map_template(db: AsyncSession, map_id: str) -> dict:
        """
        加载地图模板，优先从 Redis 缓存读取，未命中则从 MySQL 加载并缓存。

        Returns:
            包含地图所有配置的字典:
            {
                "info": {...},
                "tiles": [...],
                "station_rent": {...},
                "utility_multiplier": {...},
                "cards": [...]
            }
        """
        redis = await get_redis()

        # 1. 尝试从 Redis 缓存读取
        cache_key = f"map:{map_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. 从 MySQL 加载
        # 地图基本信息
        result = await db.execute(select(Map).where(Map.id == map_id, Map.is_active.is_(True)))
        map_obj = result.scalars().first()
        if not map_obj:
            raise ValueError(f"地图不存在或未启用: {map_id}")

        # 地块配置
        result = await db.execute(
            select(MapTile).where(MapTile.map_id == map_id).order_by(MapTile.position)
        )
        tiles = result.scalars().all()

        # 车站租金
        result = await db.execute(
            select(MapStationRent).where(MapStationRent.map_id == map_id).order_by(MapStationRent.owned_count)
        )
        station_rents = result.scalars().all()

        # 设施租金
        result = await db.execute(
            select(MapUtilityRent).where(MapUtilityRent.map_id == map_id).order_by(MapUtilityRent.owned_count)
        )
        utility_rents = result.scalars().all()

        # 卡片
        result = await db.execute(select(MapCard).where(MapCard.map_id == map_id))
        cards = result.scalars().all()

        # 3. 组装数据
        template = {
            "info": {
                "id": map_obj.id,
                "name": map_obj.name,
                "description": map_obj.description,
                "tile_count": map_obj.tile_count,
                "start_bonus": map_obj.start_bonus,
                "jail_bail": map_obj.jail_bail,
                "max_build_level": map_obj.max_build_level,
            },
            "tiles": [
                {
                    "position": t.position,
                    "name": t.name,
                    "tile_type": t.tile_type,
                    "tile_group": t.tile_group,
                    "group_color": t.group_color,
                    "price": t.price,
                    "build_cost": t.build_cost,
                    "rent_0": t.rent_0,
                    "rent_1": t.rent_1,
                    "rent_2": t.rent_2,
                    "rent_3": t.rent_3,
                    "rent_4": t.rent_4,
                    "rent_5": t.rent_5,
                    "tax_amount": t.tax_amount,
                    "tax_is_percent": t.tax_is_percent,
                }
                for t in tiles
            ],
            "station_rent": {sr.owned_count: sr.rent for sr in station_rents},
            "utility_multiplier": {ur.owned_count: ur.dice_multiplier for ur in utility_rents},
            "cards": [
                {
                    "card_type": c.card_type,
                    "card_id": c.card_id,
                    "name": c.name,
                    "effect_type": c.effect_type,
                    "effect_value": c.effect_value,
                    "description": c.description,
                }
                for c in cards
            ],
        }

        # 4. 缓存到 Redis
        await redis.set(cache_key, json.dumps(template, ensure_ascii=False), ex=MAP_CACHE_TTL)

        return template

    @staticmethod
    async def get_card_by_id(db: AsyncSession, map_id: str, card_type: str, card_id: str) -> dict | None:
        """获取指定卡片信息"""
        template = await MapService.load_map_template(db, map_id)
        for card in template["cards"]:
            if card["card_type"] == card_type and card["card_id"] == card_id:
                return card
        return None

    @staticmethod
    async def shuffle_decks(template: dict) -> tuple[list[str], list[str]]:
        """根据地图模板洗牌，返回 (chance_deck, fate_deck)"""
        chance_cards = [c["card_id"] for c in template["cards"] if c["card_type"] == "CHANCE"]
        fate_cards = [c["card_id"] for c in template["cards"] if c["card_type"] == "FATE"]
        random.shuffle(chance_cards)
        random.shuffle(fate_cards)
        return chance_cards, fate_cards
