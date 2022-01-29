from typing import List, Dict, Any

from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_404_NOT_FOUND

from examples.sqlalchemy.orm_models import Config
from fastapi_admin2.depends import get_resources
from fastapi_admin2.backends.sqla.markers import AsyncSessionDependencyMarker
from fastapi_admin2.template import templates

admin_panel_main_router = APIRouter(include_in_schema=False)


@admin_panel_main_router.get("/")
async def home(
        request: Request,
        resources: List[Dict[str, Any]] = Depends(get_resources),
):
    return templates.TemplateResponse(
        "dashboard.html",
        context={
            "request": request,
            "resources": resources,
            "resource_label": "Административная панель",
            "page_pre_title": "overview",
            "page_title": "Административная панель",
        },
    )


@admin_panel_main_router.put("/config/switch_status/{config_id}")
async def switch_config_status(request: Request, config_id: int,
                               session: AsyncSession = Depends(AsyncSessionDependencyMarker)):
    async with session.begin():
        config = await session.get(Config, config_id)
        if not config:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)
        config.status = config.status.switch_status()
        await session.merge(config)
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)
