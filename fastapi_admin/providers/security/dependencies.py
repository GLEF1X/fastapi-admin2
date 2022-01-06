from typing import Protocol, Any, Dict

from fastapi_admin.base.entities import AbstractAdmin
from fastapi_admin.exceptions import DatabaseError
from fastapi_admin.utils.depends import DependencyMarker


class AdminDaoProto(Protocol):

    async def get_one_admin_by_filters(self, **filters: Any) -> AbstractAdmin: ...

    async def is_exists_at_least_one_admin(self, **filters: Any) -> bool: ...

    async def add_admin(self, **values: Any) -> None: ...

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None: ...


class EntityNotFound(DatabaseError):
    pass


class AdminDaoDependencyMarker(DependencyMarker[AdminDaoProto]):
    pass
