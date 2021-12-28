from typing import List

from fastapi import Depends, Form
from starlette.requests import Request

from fastapi_admin.database.models.abstract import Admin
from fastapi_admin.database.repository.admin import UserRepositoryProto
from fastapi_admin.depends import get_current_admin, get_resources
from fastapi_admin.providers.security.dependencies import UserRepositoryDependencyMarker
from fastapi_admin.providers.security.impl import SecurityProvider


class LoginProvider(SecurityProvider):
    async def renew_password(
            self,
            request: Request,
            old_password: str = Form(...),
            new_password: str = Form(...),
            re_new_password: str = Form(...),
            admin: Admin = Depends(get_current_admin),
            resources: List[dict] = Depends(get_resources),
            user_repository: UserRepositoryProto = Depends(UserRepositoryDependencyMarker)
    ):
        return await self.logout(request)
