from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from urllib.parse import urlencode

from jinja2 import pass_context
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from fastapi_admin2 import VERSION
from fastapi_admin2.constants import BASE_DIR


def create_jinja2_templates(
        template_directory: Optional[Path] = None,
        *template_options: Callable[[Jinja2Templates], Jinja2Templates]
) -> Jinja2Templates:
    if template_directory is None:
        template_directory = BASE_DIR / "templates"
    templates = Jinja2Templates(directory=str(template_directory))
    templates.env.globals["VERSION"] = VERSION
    templates.env.globals["NOW_YEAR"] = date.today().year
    templates.env.add_extension("jinja2.ext.i18n")
    templates.env.add_extension("jinja2.ext.autoescape")

    for option in template_options:
        templates = option(templates)

    @pass_context
    def current_page_with_params(context: Dict[str, Any], params: Dict[str, Any]) -> str:
        request = context["request"]  # type: Request
        full_path = request.scope["raw_path"].decode()
        query_params = dict(request.query_params)
        for k, v in params.items():
            query_params[k] = v
        return full_path + "?" + urlencode(query_params)

    templates.env.filters["current_page_with_params"] = current_page_with_params

    return templates
