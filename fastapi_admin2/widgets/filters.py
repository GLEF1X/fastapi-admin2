import abc
from dataclasses import dataclass
from enum import Enum as EnumCLS
from typing import Any, List, Tuple, Type, TypeVar, Dict, ClassVar, Sequence, Optional

import pendulum
from starlette.requests import Request

from fastapi_admin2.constants import DATE_FORMAT_MOMENT
from fastapi_admin2.widgets.exceptions import FilterInputValidationError

Q = TypeVar("Q")


@dataclass
class DateRange:
    start: pendulum.DateTime
    end: pendulum.DateTime

    def to_string(self, date_format: str) -> str:
        return f"{self.start.format(date_format)} - {self.end.format(date_format)}"


class AbstractFilter(abc.ABC):
    template_name = ""

    def __init__(
            self,
            name: str,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        self.name = name
        self._placeholder = placeholder
        self._help_text = help_text
        self._null = null
        self._ctx = additional_context

    async def render(self, request: Request, value: Any) -> str:
        if value is None:
            value = ""
        if not self.template_name:
            return value

        return await request.state.render_jinja(
            self.template_name,
            context=dict(
                value=self.clean(value),
                current_locale=request.state.current_locale,
                name=request.state.t(self.name),
                placeholder=request.state.t(self._placeholder),
                help_text=self._help_text,
                null=self._null,
                **self._ctx
            )
        )

    @abc.abstractmethod
    def apply_to_sql_query(self, query: Q, value: Any) -> Q:
        pass

    def clean(self, value: Any) -> Any:
        """
        Validates and clean input value
        """
        if value is None and self._null is False:
            raise FilterInputValidationError(
                f"{self.__class__.__qualname__} filter's validation has been failed"
            )

        return value


class BaseSearchFilter(AbstractFilter, abc.ABC):
    template_name = "widgets/filters/search.html"


class BaseDateRangeFilter(AbstractFilter, abc.ABC):
    template_name = "widgets/filters/datetime.html"

    def __init__(
            self,
            name: str,
            date_format: str = DATE_FORMAT_MOMENT,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ):
        super().__init__(name, placeholder, help_text, null, **additional_context)
        self._ctx.update(date=True)
        self._date_format = date_format

    def clean(self, value: Any) -> Any:
        value = super().clean(value)

        if not value:
            return ""

        date_range = value.split(" - ")
        date_range = DateRange(start=pendulum.parse(date_range[0]), end=pendulum.parse(date_range[1]))
        return date_range.to_string(date_format=self._date_format)


class BaseDateTimeRangeFilter(BaseDateRangeFilter, abc.ABC):

    def __init__(
            self,
            name: str,
            date_format: str = DATE_FORMAT_MOMENT,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ):
        super().__init__(name, date_format, placeholder, help_text, null, **additional_context)
        self._ctx.update(date=False)


class BaseSelectFilter(AbstractFilter, abc.ABC):
    template_name: ClassVar[str] = "widgets/filters/select.html"

    async def render(self, request: Request, value: Any) -> str:
        options = await self.get_options(request)
        self._ctx.update(options=options)
        return await super().render(request, value)

    @abc.abstractmethod
    async def get_options(self, request: Request) -> Sequence[Tuple[str, Any]]:
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """


class BaseEnumFilter(BaseSelectFilter, abc.ABC):

    def __init__(
            self,
            enum: Type[EnumCLS],
            name: str,
            enum_type: Type[Any] = int,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(placeholder=placeholder, name=name, additional_context=additional_context, null=null,
                         help_text=help_text)
        self._enum = enum
        self._enum_type = enum_type

    async def parse_input(self, value: Any):
        return self._enum(self._enum_type(value))

    async def get_options(self, request: Request):
        options = [(v.name, v.value) for v in self._enum]
        if self._ctx.get("null"):
            options = [("", "")] + options
        return options


class BaseBooleanFilter(BaseSelectFilter, abc.ABC):

    async def get_options(self, request: Request) -> List[Tuple[str, str]]:
        """Return list of possible values to select from."""
        options = [
            (request.state.t("TRUE"), "true"),
            (request.state.t("FALSE"), "false"),
        ]
        if self._null:
            options.insert(0, ("", ""))

        return options
