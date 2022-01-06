from typing import Type, Any, Dict

from fastapi_admin.dialects.tortoise.models import AbstractAdminModel
from fastapi_admin.providers.security.dependencies import AdminDaoProto


class TortoiseAdminDao(AdminDaoProto):

    def __init__(self, admin_model: Type[AbstractAdminModel]):
        self._admin_model = admin_model

    async def get_one_admin_by_filters(self, **filters: Any) -> AbstractAdminModel:
        return await self._admin_model.filter(**filters).first()

    async def is_exists_at_least_one_admin(self, **filters: Any) -> bool:
        return await self._admin_model.filter(**filters).exists()

    async def add_admin(self, **values: Any) -> None:
        await self._admin_model.create(**values)

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None:
        await self._admin_model.filter(**filters).update(**values)
