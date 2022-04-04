import abc
from dataclasses import dataclass
from enum import Enum as EnumCLS
from typing import Any, List, Tuple, Type, TypeVar, ClassVar, Sequence

import pendulum
from starlette.requests import Request

from fastapi_admin2.default_settings import DATE_FORMAT_MOMENT
from fastapi_admin2.widgets.exceptions import FilterValidationError

Q = TypeVar("Q")


@dataclass
class DateRangeDTO:
    start: pendulum.DateTime
    end: pendulum.DateTime

    def to_string(self, date_format: str) -> str:
        return f"{self.start.format(date_format)} - {self.end.format(date_format)}"


class AbstractFilter(abc.ABC):
    template_name: ClassVar[str] = ""

    def __init__(
            self,
            name: str,
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        self.name = name
        self._placeholder = placeholder
        self._null = null
        self._ctx = additional_context

    async def render(self, request: Request) -> str:
        current_filter_value = request.query_params.get(self.name)
        if current_filter_value is None:
            current_filter_value = ""
        if not self.template_name:
            return current_filter_value

        return await request.state.render_jinja(
            self.template_name,
            context=dict(
                current_locale=request.state.current_locale,
                name=self.name,
                placeholder=self._placeholder,
                null=self._null,
                value=current_filter_value,
                **self._ctx
            )
        )

    def apply(self, query: Q, value: Any) -> Q:
        try:
            self.validate(value)
        except FilterValidationError:
            return query

        return self._apply_to_sql_query(query, self.clean(value))

    @abc.abstractmethod
    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        pass

    def validate(self, value: Any) -> None:
        """
        Validates input value

        :param value:
        :raises:
            FilterValidationError if validation is not succeed
        """
        if not value:
            raise FilterValidationError(
                f"{self.__class__.__qualname__} filter's validation has been failed"
            )

    def clean(self, value: Any) -> Any:
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
            null: bool = True,
            **additional_context: Any
    ):
        super().__init__(name, placeholder, null, **additional_context)
        self._ctx.update(date=True)
        self._date_format = date_format

    def clean(self, value: Any) -> Any:
        value = super().clean(value)
        date_range = value.split(" - ")
        return DateRangeDTO(start=pendulum.parse(date_range[0]), end=pendulum.parse(date_range[1]))


class BaseDateTimeRangeFilter(BaseDateRangeFilter, abc.ABC):

    def __init__(
            self,
            name: str,
            date_format: str = DATE_FORMAT_MOMENT,
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ):
        super().__init__(name, date_format, placeholder, null, **additional_context)
        self._ctx.update(date=False)


class BaseSelectFilter(AbstractFilter, abc.ABC):
    template_name: ClassVar[str] = "widgets/filters/select.html"

    async def render(self, request: Request) -> str:
        options = await self.get_options(request)
        self._ctx.update(options=options)
        return await super().render(request)

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
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(placeholder=placeholder, name=name, null=null, **additional_context)
        self._enum = enum
        self._enum_type = enum_type

    async def clean(self, value: Any) -> EnumCLS:
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
            (request.state.gettext("TRUE"), "true"),
            (request.state.gettext("FALSE"), "false"),
        ]
        if self._null:
            options.insert(0, ("", ""))

        return options
