from typing import Any, Callable

from starlette.requests import Request


class Widget:
    template_name = ""
    gettext: Callable[[str], str] = lambda x: x

    def __init__(self, **context: Any):
        """
        All context will pass to template render if template is not empty.

        :param context:
        """
        self.context = context

    async def render(self, request: Request, value: Any) -> str:
        self.gettext = request.state.t
        if value is None:
            value = ""
        if not self.template_name:
            return value
        return await request.state.render_jinja(
            self.template_name,
            context=dict(
                value=value,
                current_locale=request.state.current_locale,
                **self.context
            )
        )
