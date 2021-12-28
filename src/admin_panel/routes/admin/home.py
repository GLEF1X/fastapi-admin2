from fastapi import Depends, HTTPException, APIRouter
from fastapi_admin.depends import get_resources
from fastapi_admin.template import templates
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_404_NOT_FOUND

from src.infrastructure.impl.orm.models import Config

admin_panel_main_router = APIRouter(tags=["админка"])


@admin_panel_main_router.get("/")
async def home(
        request: Request,
        resources=Depends(get_resources),
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
async def switch_config_status(request: Request, config_id: int):
    config = await Config.get_or_none(pk=config_id)
    if not config:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    config.status = not config.status
    await config.save(update_fields=["status"])
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)
