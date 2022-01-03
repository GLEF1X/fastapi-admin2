from typing import List

from fastapi import Depends, Form
from starlette.requests import Request

from fastapi_admin.database.models.abstract_admin import AbstractAdmin
from fastapi_admin.database.repository.admin import AdminRepositoryProto
from fastapi_admin.depends import get_current_admin, get_resources
from fastapi_admin.providers.security.dependencies import AdminRepositoryDependencyMarker
from fastapi_admin.providers.security.impl import SecurityProvider


class LoginProvider(SecurityProvider):
    async def renew_password(
            self,
            request: Request,
            old_password: str = Form(...),
            new_password: str = Form(...),
            re_new_password: str = Form(...),
            admin: AbstractAdmin = Depends(get_current_admin),
            resources: List[dict] = Depends(get_resources),
            user_repository: AdminRepositoryProto = Depends(AdminRepositoryDependencyMarker)
    ):
        return await self.logout(request)
