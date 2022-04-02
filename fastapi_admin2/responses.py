from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response, HTMLResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_500_INTERNAL_SERVER_ERROR


def redirect(request: Request, view: str, **params) -> Response:
    return RedirectResponse(
        url=request.app.admin_path + request.app.url_path_for(view, **params),
        status_code=HTTP_303_SEE_OTHER,
    )


async def server_error_exception(
        request: Request,
        exc: HTTPException,
) -> HTMLResponse:
    return await request.state.create_html_response(
        "errors/500.html",
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        context={"request": request},
    )


async def not_found(
        request: Request,
        exc: HTTPException,
) -> HTMLResponse:
    return await request.state.create_html_response(
        "errors/404.html", status_code=exc.status_code, context={"request": request}
    )


async def forbidden(
        request: Request,
        exc: HTTPException,
) -> HTMLResponse:
    return await request.state.create_html_response(
        "errors/403.html", status_code=exc.status_code, context={"request": request}
    )


async def unauthorized(
        request: Request,
        exc: HTTPException,
) -> HTMLResponse:
    return await request.state.create_html_response(
        "errors/401.html", status_code=exc.status_code, context={"request": request}
    )
