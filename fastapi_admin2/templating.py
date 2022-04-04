import functools
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from jinja2 import pass_context, Environment, FileSystemLoader, select_autoescape, FileSystemBytecodeCache
from starlette.background import BackgroundTask
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from fastapi_admin2.default_settings import BASE_DIR


class JinjaTemplates:

    def __init__(self, directory: Optional[Path] = None):
        self._directory = directory
        if self._directory is None:
            self._directory = BASE_DIR / "templates"
        self.env = self._create_env()

    async def create_html_response(
            self,
            template_name: str,
            context: Optional[Dict[str, Any]] = None,
            status_code: int = 200,
            headers: Optional[Dict[str, Any]] = None,
            media_type: Optional[str] = None,
            background: Optional[BackgroundTask] = None
    ) -> HTMLResponse:
        if headers is None:
            headers = {}

        content = await self._render_content(supplement_template_name(template_name), context)
        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                **headers
            },
            media_type=media_type,
            background=background,
        )

    async def _render_content(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        if context is None:
            context = {}
        template = self.env.get_template(template_name)
        return await template.render_async(context)

    def _create_env(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(self._directory),
            autoescape=select_autoescape(["html", "xml"]),
            bytecode_cache=FileSystemBytecodeCache(),
            enable_async=True
        )

        env.globals["url_for"] = url_for
        env.globals["NOW_YEAR"] = date.today().year

        env.filters["current_page_with_params"] = current_page_with_params

        return env


@pass_context
def current_page_with_params(context: Dict[str, Any], params: Dict[str, Any]) -> str:
    request = context["request"]  # type: Request
    full_path = request.scope["raw_path"].decode()
    query_params = dict(request.query_params)
    for k, v in params.items():
        query_params[k] = v
    return full_path + "?" + urlencode(query_params)


@pass_context
def url_for(context: Dict[str, Any], name: str, **path_params: Any) -> str:
    request: Request = context["request"]
    return request.url_for(name, **path_params)


async def add_render_function_to_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    templates: JinjaTemplates = request.app.templates
    request.state.create_html_response = templates.create_html_response

    async def render_jinja_template(template_name, context):
        template = templates.env.get_template(supplement_template_name(template_name))
        return await template.render_async(context)

    request.state.render_jinja = render_jinja_template
    return await call_next(request)


@functools.lru_cache(1200)
def supplement_template_name(name: str) -> str:
    if not name.endswith(".html"):
        return name + ".html"
    return name
