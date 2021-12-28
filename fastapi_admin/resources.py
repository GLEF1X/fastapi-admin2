import dataclasses
from typing import Any, List, Optional, Type, Union, Iterable, Mapping

from pydantic import BaseModel, validator
from sqlalchemy import inspect, Column, Boolean, DateTime, Date, Enum, JSON, String, Integer
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.sql import Select
from sqlalchemy.util import ImmutableProperties
from starlette.datastructures import FormData
from starlette.requests import Request
from tortoise import ForeignKeyFieldInstance, ManyToManyFieldInstance

from fastapi_admin.enums import HTTPMethod
from fastapi_admin.exceptions import NoSuchFieldFound
from fastapi_admin.services.i18n.context import gettext as _
from fastapi_admin.widgets import Widget, displays, inputs
from fastapi_admin.widgets.filters import Filter, Search


class Resource:
    """
    Base Resource
    """

    label: str
    icon: str = ""


class Link(Resource):
    url: str
    target: str = "_self"


class Field:
    name: str
    label: str
    display: displays.Display
    input: inputs.Input

    def __init__(
            self,
            name: str,
            label: Optional[str] = None,
            display: Optional[displays.Display] = None,
            input_: Optional[Widget] = None,
    ):
        self.name = name
        self.label = label or name.title()
        if not display:
            display = displays.Display()
        display.context.update(label=self.label)
        self.display = display
        if not input_:
            input_ = inputs.Input()
        input_.context.update(label=self.label, name=name)
        self.input = input_


class ComputeField(Field):
    async def get_value(self, request: Request, obj: Mapping):
        return obj.get(self.name)


class Action(BaseModel):
    icon: str
    label: str
    name: str
    method: HTTPMethod = HTTPMethod.POST
    ajax: bool = True

    @validator("ajax")
    def ajax_validate(cls, v: bool, values: dict, **kwargs):
        if not v and values["method"] != HTTPMethod.GET:
            raise ValueError("ajax is False only available when method is Method.GET")


class ToolbarAction(Action):
    class_: Optional[str]


class Model(Resource):
    model: Type[Any]
    fields: List[Union[str, Field, ComputeField]] = []
    page_size: int = 10
    page_pre_title: Optional[str] = None
    page_title: Optional[str] = None
    filters: List[Union[str, Filter]] = []

    async def get_toolbar_actions(self, request: Request) -> List[ToolbarAction]:
        return [
            ToolbarAction(
                label=_("create"),
                icon="fas fa-plus",
                name="create",
                method=HTTPMethod.GET,
                ajax=False,
                class_="btn-dark",
            )
        ]

    async def row_attributes(self, request: Request, obj: Mapping) -> dict:
        return {}

    async def column_attributes(self, request: Request, field: Field) -> dict:
        return {}

    async def cell_attributes(self, request: Request, obj: Mapping, field: Field) -> dict:
        return {}

    async def get_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=_("update"), icon="ti ti-edit", name="update", method=HTTPMethod.GET, ajax=False
            ),
            Action(label=_("delete"), icon="ti ti-trash", name="delete", method=HTTPMethod.DELETE),
        ]

    async def get_bulk_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=_("delete_selected"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE,
            ),
        ]

    @classmethod
    async def get_inputs(cls, request: Request, obj: Optional[Any] = None):
        ret = []
        for field in cls.get_fields(is_display=False):
            input_ = field.input
            if isinstance(input_, inputs.DisplayOnly):
                continue
            if isinstance(input_, inputs.File):
                cls.enctype = "multipart/form-data"
            name = input_.context.get("name")
            ret.append(await input_.render(request, getattr(obj, name, None)))
        return ret

    @classmethod
    async def resolve_query_params(cls, request: Request, values: dict, expr: Select):
        ret = {}
        for f in cls.filters:
            if isinstance(f, str):
                f = Search(name=f, label=f.title())
            name = f.context.get("name")
            v = values.get(name)
            if v is not None and v != "":
                ret[name] = await f.parse_value(request, v)
                expr = await f.apply_filter(request, v, expr)
        return ret, expr

    @classmethod
    async def resolve_data(cls, request: Request, data: FormData):
        ret = {}
        m2m_ret = {}
        for field in cls.get_fields(is_display=False):
            input_ = field.input
            if input_.context.get("disabled") or isinstance(input_, inputs.DisplayOnly):
                continue
            name = input_.context.get("name")
            if isinstance(input_, inputs.ManyToMany):
                v = data.getlist(name)
                value = await input_.parse_value(request, v)
                m2m_ret[name] = await input_.model.filter(pk__in=value)
            else:
                v = data.get(name)
                value = await input_.parse_value(request, v)
                if value is None:
                    continue
                ret[name] = value
        return ret, m2m_ret

    @classmethod
    async def get_filters(cls, request: Request, values: Optional[dict] = None):
        if not values:
            values = {}
        ret = []
        for f in cls.filters:
            if isinstance(f, str):
                f = Search(name=f, label=f.title())
            name = f.context.get("name")
            value = values.get(name)
            ret.append(await f.render(request, value))
        return ret

    @classmethod
    def _get_fields_attr(cls, attr: str, display: bool = True):
        ret = []
        for field in cls.get_fields():
            if display and isinstance(field.display, displays.InputOnly):
                continue
            ret.append(getattr(field, attr))
        return ret or cls.model._meta.db_fields

    @classmethod
    def get_fields_name(cls, display: bool = True):
        return cls._get_fields_attr("name", display)

    @classmethod
    def _get_display_input_field(cls, field_name: str) -> Field:
        column: Optional[Column] = cls.model.__dict__.get(field_name)
        if not column:
            raise NoSuchFieldFound(f"Can't found field '{field_name}' in model {cls.model}")
        label = field_name
        is_nullable = column.nullable
        placeholder = column.description or ""
        display, input_ = displays.Display(), inputs.Input(
            placeholder=placeholder, null=is_nullable, default=column.default
        )
        if column.primary_key:
            display, input_ = displays.Display(), inputs.DisplayOnly()
        elif isinstance(column.type, Boolean):
            display, input_ = displays.Boolean(), inputs.Switch(null=is_nullable, default=column.default)
        elif isinstance(column.type, DateTime):
            if column.auto_now or column.auto_now_add:
                input_ = inputs.DisplayOnly()
            else:
                input_ = inputs.DateTime(null=is_nullable, default=column.default)
            display, input_ = displays.DatetimeDisplay(), input_
        elif isinstance(column.type, Date):
            display, input_ = displays.DateDisplay(), inputs.Date(null=is_nullable, default=column.default)
        elif isinstance(column.type, Enum):
            display, input_ = displays.Display(), inputs.Enum(
                column.type.__class__, null=is_nullable, default=column.default
            )
        elif isinstance(column.type, JSON):
            display, input_ = displays.Json(), inputs.Json(null=is_nullable)
        elif isinstance(column.type, String):
            display, input_ = displays.Display(), inputs.TextArea(
                placeholder=placeholder, null=is_nullable, default=column.default
            )
        elif isinstance(column.type, Integer):
            display, input_ = displays.Display(), inputs.Number(
                placeholder=placeholder, null=is_nullable, default=column.default
            )
        elif isinstance(column.type, ForeignKeyFieldInstance):
            display, input_ = displays.Display(), inputs.ForeignKey(
                column.related_model, null=is_nullable, default=column.default
            )
            field_name = column.source_field
        elif isinstance(column.type, ManyToManyFieldInstance):
            display, input_ = displays.InputOnly(), inputs.ManyToMany(column.related_model)
        return Field(name=field_name, label=label.title(), display=display, input_=input_)

    @classmethod
    def get_fields(cls, is_display: bool = True) -> List[Column[Any]]:
        ret: List[Column[Any]] = []
        primary_key_column: Column[Any] = inspect(cls.model).primary_key[0]
        model_columns: ImmutableProperties = inspect(cls.model).column_attrs  # type: ignore  # noqa
        for column in model_columns:  # include fields attr
            if isinstance(column, str):
                if column == primary_key_column:
                    continue
                column = cls._get_display_input_field(column)
            if isinstance(column, ComputeField) and not is_display:
                continue
            elif isinstance(column, Field):
                if column.name == primary_key_column:
                    continue
                if (is_display and isinstance(column.display, displays.InputOnly)) or (
                        not is_display and isinstance(column.input, inputs.DisplayOnly)
                ):
                    continue
            # if (
            #         column.name in cls.model._meta.fetch_fields
            #         and column.name not in cls.model._meta.fk_fields | cls.model._meta.m2m_fields
            # ):
            #     continue
            ret.append(column)
        ret.insert(0, cls._get_display_input_field(primary_key_column.name ))
        return ret

    @classmethod
    def get_fields_label(cls, display: bool = True):
        return cls._get_fields_attr("label", display)

    @classmethod
    def get_m2m_field(cls):
        ret = []
        for field in cls.fields or cls.model._meta.fields:
            if isinstance(field, Field):
                field = field.name
            if field in cls.model._meta.m2m_fields:
                ret.append(field)
        return ret


class Dropdown(Resource):
    resources: List[Type[Resource]]


@dataclasses.dataclass(frozen=True)
class ModelValues:
    ret: List[List[Any]]  # TODO rename to human-readable
    row_attributes: Iterable[dict]
    column_attributes: Iterable[dict]
    cell_attributes: Iterable[Iterable[dict]]


async def render_model_fields(
        request: Request,
        model: "Model",
        fields: List["Field"],
        values: List[Mapping[str, Any]],
        display: bool = True,
) -> ModelValues:
    """
    render values with template render
    :params model:
    :params request:
    :params fields:
    :params values:
    :params display:
    :params request:
    :params model:
    :return:
    """
    ret = []
    cell_attributes: List[List[dict]] = []
    row_attributes: List[dict] = []
    column_attributes: List[dict] = []
    for field in fields:
        column_attributes.append(await model.column_attributes(request, field))
    for value in values:
        row_attributes.append(await model.row_attributes(request, value))
        item = []
        cell_item = []
        for field in fields:
            if isinstance(field, ComputeField):
                v = await field.get_value(request, value)
            else:
                v = value.get(field.name)
            cell_item.append(await model.cell_attributes(request, value, field))
            if display:
                item.append(await field.display.render(request, v))
            else:
                item.append(await field.input.render(request, v))
        ret.append(item)
        cell_attributes.append(cell_item)
    return ModelValues(ret, row_attributes, column_attributes, cell_attributes)
