from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


async def theme_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    dark_mode_toggled = request.query_params.get('theme') == 'dark'
    light_theme_toggled = request.query_params.get('theme') == 'light'
    response = await call_next(request)

    if dark_mode_toggled:
        response.set_cookie('dark_mode', 'yes', path=request.app.admin_path)
    elif light_theme_toggled:
        response.delete_cookie('dark_mode', path=request.app.admin_path)

    return response
