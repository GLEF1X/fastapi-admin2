from typing import Callable, Awaitable

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from fastapi_admin2.utils.templating import JinjaTemplates, supplement_template_name


def create_template_middleware(templates: JinjaTemplates) -> Callable[
    [Request, RequestResponseEndpoint], Awaitable[Response]
]:
    async def add_render_function_to_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.create_html_response = templates.create_html_response

        async def render_jinja_template(template_name, context):
            template = templates.env.get_template(supplement_template_name(template_name))
            return await template.render_async(context)

        request.state.render_jinja = render_jinja_template
        return await call_next(request)

    return add_render_function_to_request
