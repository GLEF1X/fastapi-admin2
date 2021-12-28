from aioredis import Redis

from fastapi_admin.database.repository.admin import UserRepositoryProto
from fastapi_admin.utils.depends import Marker


class UserRepositoryDependencyMarker(Marker[UserRepositoryProto]):
    pass


class RedisClientDependencyMarker(Marker[Redis]):
    pass
