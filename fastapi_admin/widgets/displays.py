import json
from datetime import datetime
from typing import Optional, Any, Callable

from starlette.requests import Request

from fastapi_admin import constants
from fastapi_admin.widgets import Widget


class Display(Widget):
    """
    Parent class for all display widgets
    """


class DatetimeDisplay(Display):
    def __init__(self, format_: str = constants.DATETIME_FORMAT):
        super().__init__()
        self.format_ = format_

    async def render(self, request: Request, value: datetime) -> str:
        return await super(DatetimeDisplay, self).render(
            request, value.strftime(self.format_) if value else None
        )


class DateDisplay(DatetimeDisplay):
    def __init__(self, format_: str = constants.DATE_FORMAT):
        super().__init__(format_)


class InputOnly(Display):
    """
    Only input without showing in display
    """


class Boolean(Display):
    template = "widgets/displays/boolean.html"


class Image(Display):
    template = "widgets/displays/image.html"

    def __init__(self, width: Optional[str] = None, height: Optional[str] = None):
        super().__init__(width=width, height=height)


class Json(Display):
    template = "widgets/displays/json.html"

    def __init__(self, dumper: Callable[..., Any] = json.dumps, **context):
        super().__init__(**context)
        self._dumper = dumper

    async def render(self, request: Request, value: dict):
        return await super(Json, self).render(request, self._dumper(value))


class EnumDisplay(Display):
    template = ""
