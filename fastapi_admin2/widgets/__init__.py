from typing import Any

from starlette.requests import Request
from starlette.templating import Jinja2Templates

from fastapi_admin2.i18n.context import get_i18n
from fastapi_admin2.template import templates as t


class Widget:
    templates: Jinja2Templates = t
    template: str = ""

    def __init__(self, **context):
        """
        All context will pass to template render if template is not empty.

        :param context:
        """
        self.context = context

    async def render(self, value: Any) -> str:
        if value is None:
            value = ""
        if not self.template:
            return value
        return self.templates.get_template(self.template).render(
            value=value,
            current_locale=get_i18n().current_locale,
            **self.context
        )
