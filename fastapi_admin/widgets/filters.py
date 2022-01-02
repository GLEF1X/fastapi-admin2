import abc
import operator
from enum import Enum as EnumCLS
from typing import Any, List, Optional, Tuple, Type, Callable

import pendulum
from sqlalchemy import between, Column
from sqlalchemy.sql import Select as SqalchemySelect, ClauseElement
from sqlalchemy.sql.operators import is_
from starlette.requests import Request

from fastapi_admin import constants
from fastapi_admin.i18n.context import lazy_gettext as _
from fastapi_admin.widgets.inputs import Input


def between_comparator_for_date_range(
        column: Column,
        date_range: Tuple[pendulum.DateTime, pendulum.DateTime]
):
    lower_bound = date_range[0]
    upper_bound = date_range[1]
    return between(column, lower_bound, upper_bound)


class Filter(Input):
    def __init__(self, name: str, label: str, placeholder: str = "", null: bool = True,
                 **context):
        """
        Parent class for all filters
        :param name: model field name
        :param label:
        """
        super().__init__(name=name, label=label, placeholder=placeholder, null=null, **context)

    async def apply_filter(self, request: Request, model: Any, value: Any, expression: SqalchemySelect):
        value = await self.parse_value(request, value)
        return expression.where(
            self.context["comparator"](model.__dict__[self.context["name"]], value)
        )


class Search(Filter):
    template = "widgets/filters/search.html"

    def __init__(
            self,
            name: str,
            label: str,
            comparator: Callable[[Any, Any], ClauseElement] = operator.eq,
            placeholder: str = "",
            null: bool = True,
    ):
        super().__init__(name, label, placeholder, null, comparator=comparator)


class Date(Filter):
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
            placeholder=placeholder,
            comparator=between_comparator_for_date_range
        )
        self.context.update(date=True)

    async def parse_value(self, request: Request, value: Optional[str]):
        if value:
            ranges = value.split(" - ")
            return pendulum.parse(ranges[0]), pendulum.parse(ranges[1])

    async def render(self, request: Request, value: Tuple[pendulum.DateTime, pendulum.DateTime]):
        format_ = self.context.get("format")
        if value is not None:
            value = value[0].format(format_) + " - " + value[1].format(format_)
        return await super().render(request, value)


class DatetimeRange(Date):
    template = "widgets/filters/datetime.html"

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


class Select(Filter):
    template = "widgets/filters/select.html"

    def __init__(self, name: str, label: str, null: bool = True):
        super().__init__(name, label, null=null, comparator=operator.eq)

    @abc.abstractmethod
    async def get_options(self):
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """

    async def render(self, request: Request, value: Any):
        options = await self.get_options()
        self.context.update(options=options)
        return await super(Select, self).render(request, value)


class Enum(Select):
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

    async def parse_value(self, request: Request, value: Any):
        return self.enum(self.enum_type(value))

    async def get_options(self):
        options = [(v.name, v.value) for v in self.enum]
        if self.context.get("null"):
            options = [("", "")] + options
        return options


class ForeignKey(Select):
    def __init__(self, model: Type[Any], name: str, label: str, null: bool = True):
        super().__init__(name=name, label=label, null=null)
        self.model = model

    async def get_options(self):
        ret = await self.get_models()
        options = [
            (
                str(x),
                x.pk,
            )
            for x in ret
        ]
        if self.context.get("null"):
            options = [("", "")] + options
        return options

    async def get_models(self):
        return await self.model.all()

    async def render(self, request: Request, value: Any):
        if value is not None:
            value = int(value)
        return await super().render(request, value)


class DistinctColumn(Select):
    def __init__(self, model: Type[Any], name: str, label: str, null: bool = True):
        super().__init__(name=name, label=label, null=null)
        self.model = model
        self.name = name

    async def get_options(self):
        ret = await self.get_values()
        options = [
            (
                str(x[0]),
                str(x[0]),
            )
            for x in ret
        ]
        if self.context.get("null"):
            options = [("", "")] + options
        return options

    async def get_values(self):
        return await self.model.all().distinct().values_list(self.name)


class Boolean(Select):

    async def get_options(self) -> List[Tuple[str, str]]:
        """Return list of possible values to select from."""
        options = [
            (_("TRUE"), "true"),
            (_("FALSE"), "false"),
        ]
        if self.context.get("null"):
            options.insert(0, ("", ""))

        return options

    async def apply_filter(self, request: Request, model: Any, value: Any, expression: SqalchemySelect):
        return expression.where(is_(model.__dict__[self.context["name"]], bool(value)))
