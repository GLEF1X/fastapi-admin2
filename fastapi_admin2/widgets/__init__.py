from typing import Any

from starlette.requests import Request


class Widget:
    template: str = ""

    def __init__(self, **context):
        """
        All context will pass to template render if template is not empty.

        :param context:
        """
        self.context = context

    async def render(self, request: Request, value: Any) -> str:
        if value is None:
            value = ""
        if not self.template:
            return value
        return request.app.templates.get_template(self.template).render(
            value=value,
            current_locale=request.state.current_locale,
            **self.context
        )
