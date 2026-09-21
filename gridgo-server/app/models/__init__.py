"""数据库模型包"""

from app.models.friend import Friendship
from app.models.game_record import GamePlayer, GameRecord
from app.models.map import Map, MapCard, MapStationRent, MapTile, MapUtilityRent
from app.models.room import Room, RoomPlayerRow
from app.models.stats import GameTurnLog, UserStats
from app.models.user import User

__all__ = [
    "User",
    "Map", "MapTile", "MapStationRent", "MapUtilityRent", "MapCard",
    "GameRecord", "GamePlayer",
    # docs/PROJECT.md 6.2 声明的其余表
    "Room", "RoomPlayerRow", "UserStats", "GameTurnLog", "Friendship",
]
