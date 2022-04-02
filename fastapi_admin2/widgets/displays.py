import json
from datetime import datetime
from typing import Optional, Any, Callable

from starlette.requests import Request

from fastapi_admin2 import constants
from fastapi_admin2.widgets import Widget


class Display(Widget):
    """
    Parent class for all display widgets
    """


class DatetimeDisplay(Display):
    def __init__(self, format_: str = constants.DATETIME_FORMAT):
        super().__init__()
        self.format_ = format_

    async def render(self, request: Request, value: datetime) -> str:
        timestamp = value
        if value is not None:
            timestamp = value.strftime(self.format_)

        return await super(DatetimeDisplay, self).render(request, timestamp)


class DateDisplay(DatetimeDisplay):
    def __init__(self, format_: str = constants.DATE_FORMAT):
        super().__init__(format_)


class InputOnly(Display):
    """
    Only input without showing in display
    """


class Boolean(Display):
    template_name = "widgets/displays/boolean.html"


class Image(Display):
    template_name = "widgets/displays/image.html"

    def __init__(self, width: Optional[str] = None, height: Optional[str] = None):
        super().__init__(width=width, height=height)


class Json(Display):
    template_name = "widgets/displays/json.html"

    def __init__(self, dumper: Callable[..., Any] = json.dumps, **context):
        super().__init__(**context)
        self._dumper = dumper

    async def render(self, request: Request, value: dict):
        return await super(Json, self).render(request, self._dumper(value))


class EnumDisplay(Display):
    template_name = ""
