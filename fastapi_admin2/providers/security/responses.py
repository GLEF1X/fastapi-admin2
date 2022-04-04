from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED


def to_init_page(request: Request) -> RedirectResponse:
    return RedirectResponse(
        url=request.app.admin_path + "/init",
        status_code=HTTP_303_SEE_OTHER
    )


def to_login_page(request: Request) -> RedirectResponse:
    return RedirectResponse(
        request.app.admin_path + "/login",
        status_code=HTTP_303_SEE_OTHER
    )


async def unauthorized(template_name: str, request: Request) -> RedirectResponse:
    return await request.state.create_html_response(
        template_name,
        status_code=HTTP_401_UNAUTHORIZED,
        context={"request": request, "error": request.state.t("login_failed")},
    )
