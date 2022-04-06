import functools
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import pass_context, Environment, FileSystemLoader, select_autoescape, FileSystemBytecodeCache
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse

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

        return env


@pass_context
def url_for(context: Dict[str, Any], name: str, **path_params: Any) -> str:
    request: Request = context["request"]
    return request.url_for(name, **path_params)


@functools.lru_cache(1200)
def supplement_template_name(name: str) -> str:
    if not name.endswith(".html"):
        return name + ".html"
    return name
