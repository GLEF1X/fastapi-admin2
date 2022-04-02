import abc
from dataclasses import dataclass
from enum import Enum as EnumCLS
from typing import Any, List, Optional, Tuple, Type, Generic, TypeVar

import pendulum
from starlette.requests import Request

from fastapi_admin2 import constants
from fastapi_admin2.widgets.inputs import Input

T = TypeVar("T")
Q = TypeVar("Q")


@dataclass()
class DateRange:
    start: pendulum.DateTime
    end: pendulum.DateTime

    def to_string(self, date_format: str) -> str:
        return f"{self.start.format(date_format)} - {self.end.format(date_format)}"


class AbstractFilter(Input, abc.ABC, Generic[T]):

    def __init__(self, name: str, label: str, placeholder: str = "", null: bool = True,
                 **context: Any) -> None:
        """
        Parent class for all filters
        :param name: model field name
        :param label:
        """
        super().__init__(name=name, label=label, placeholder=placeholder, null=null, **context)

    @abc.abstractmethod
    def utilize(self, query: Q, value: T) -> Q:
        pass

    def validate(self, value: T) -> None:
        pass

    def parse(self, value: T) -> T:
        return value


class BaseSearchFilter(AbstractFilter, abc.ABC):
    template_name = "widgets/filters/search.html"


class BaseDateRangeFilter(AbstractFilter[str], abc.ABC):
    def __init__(
            self,
            name: str,
            label: str,
            format_: str = constants.DATE_FORMAT_MOMENT,
            null: bool = True,
            placeholder: str = ""
    ):
        super().__init__(
            name=name,
            label=label,
            format=format_,
            null=null,
            placeholder=placeholder
        )
        self.context.update(date=True)

    async def parse(self, value: str) -> DateRange:
        date_range = value.split(" - ")
        return DateRange(start=pendulum.parse(date_range[0]), end=pendulum.parse(date_range[1]))

    async def render(self, request: Request, value: DateRange) -> str:
        format_ = self.context.get("format")
        return await super().render(request, value.to_string(date_format=format_))


class BaseDatetimeRangeFilter(BaseDateRangeFilter, abc.ABC):
    template_name = "widgets/filters/datetime.html"

    def __init__(
            self,
            name: str,
            label: str,
            format_: str = constants.DATETIME_FORMAT_MOMENT,
            null: bool = True,
            placeholder: str = "",
    ):
        super().__init__(name, label, null=null, format_=format_, placeholder=placeholder, )
        self.context.update(date=False)


class BaseSelectFilter(AbstractFilter):
    template_name = "widgets/filters/select.html"

    def __init__(self, name: str, label: str, null: bool = True):
        super().__init__(name, label, null=null)

    @abc.abstractmethod
    async def get_options(self, request: Request):
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """

    async def render(self, request: Request, value: Any):
        options = await self.get_options(request)
        self.context.update(options=options)
        return await super().render(request, value)


class BaseEnumFilter(BaseSelectFilter, abc.ABC):
    def __init__(
            self,
            enum: Type[EnumCLS],
            name: str,
            label: str,
            enum_type: Type = int,
            null: bool = True,
    ):
        super().__init__(name=name, label=label, null=null)
        self.enum = enum
        self.enum_type = enum_type

    async def parse(self, value: Any):
        return self.enum(self.enum_type(value))

    async def get_options(self, request: Request):
        options = [(v.name, v.value) for v in self.enum]
        if self.context.get("null"):
            options = [("", "")] + options
        return options


class BaseBooleanFilter(BaseSelectFilter, abc.ABC):

    async def get_options(self, request: Request) -> List[Tuple[str, str]]:
        """Return list of possible values to select from."""
        options = [
            (request.state.t("TRUE"), "true"),
            (request.state.t("FALSE"), "false"),
        ]
        if self.context.get("null"):
            options.insert(0, ("", ""))

        return options
