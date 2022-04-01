from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from jinja2 import pass_context, Environment, FileSystemLoader, select_autoescape, FileSystemBytecodeCache
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse

from fastapi_admin2 import VERSION
from fastapi_admin2.constants import BASE_DIR


class JinjaTemplates:

    def __init__(self, directory: Optional[Path] = None):
        self._directory = directory
        if self._directory is None:
            self._directory = BASE_DIR / "templates"
        self._env = self._create_env()

    async def create_html_response(
            self,
            template_name: str,
            context: Optional[Dict[str, Any]] = None,
            status_code: int = 200,
            headers: Optional[Dict[str, Any]] = None,
            media_type: Optional[str] = None,
            background: Optional[BackgroundTask] = None
    ) -> HTMLResponse:
        template = self._env.get_template(template_name)
        if context is None:
            context = {}

        content = await template.render_async(context)
        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    def _create_env(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(self._directory),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=True,
            bytecode_cache=FileSystemBytecodeCache()
        )

        @pass_context
        def url_for(context: Dict[str, Any], name: str, **path_params: Any) -> str:
            request = context["request"]
            return request.url_for(name, **path_params)

        env.globals["url_for"] = url_for
        env.globals["VERSION"] = VERSION
        env.globals["NOW_YEAR"] = date.today().year
        env.add_extension("jinja2.ext.i18n")

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
