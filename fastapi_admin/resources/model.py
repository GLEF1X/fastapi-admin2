from typing import Type, Any, List, Union, Optional, Sequence, Iterable

from sqlalchemy import inspect, Column, Boolean, DateTime, Date, Enum, JSON, String, Integer
from sqlalchemy.sql import Select
from starlette.datastructures import FormData
from starlette.requests import Request

from fastapi_admin.enums import HTTPMethod
from fastapi_admin.exceptions import FieldNotFoundError
from fastapi_admin.i18n import gettext as _
from fastapi_admin.resources.action import ToolbarAction, Action
from fastapi_admin.resources.base import Resource
from fastapi_admin.resources.field import Field, ComputeField
from fastapi_admin.widgets import inputs, displays
from fastapi_admin.widgets.filters import Filter, Search


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

    async def row_attributes(self, request: Request, obj: Any) -> dict:
        return {}

    async def column_attributes(self, request: Request, field: Field) -> dict:
        return {}

    async def cell_attributes(self, request: Request, obj: Any, field: Field) -> dict:
        return {}

    async def get_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=_("update"),
                icon="ti ti-edit",
                name="update",
                method=HTTPMethod.GET,
                ajax=False
            ),
            Action(
                label=_("delete"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE
            ),
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
    async def render_inputs(cls, request: Request, obj: Optional[Any] = None) -> List[str]:
        rendered_inputs = []
        for field in cls.get_model_fields_for_input():
            input_ = field.input
            if isinstance(input_, inputs.DisplayOnly):
                continue
            if isinstance(input_, inputs.File):
                cls.enctype = "multipart/form-data"
            name = input_.context.get("name")
            rendered_inputs.append(await input_.render(request, getattr(obj, name, None)))
        return rendered_inputs

    @classmethod
    async def parse_query_params(cls, request: Request) -> dict:
        params = {}
        query_params = request.query_params
        for filter_ in cls._normalize_filters():
            name = filter_.context.get("name")
            try:
                matched_filter_value = query_params[name]
                if matched_filter_value == "":
                    raise KeyError
            except KeyError:
                continue
            params[name] = await filter_.parse_value(request, matched_filter_value)
        return params

    @classmethod
    async def enrich_select_with_filters(cls, request: Request, model: Any,
                                         select_statement: Select) -> Select:
        parsed_query_params = await cls.parse_query_params(request)
        for filter_ in cls._normalize_filters():
            filter_name = filter_.context["name"]
            if not parsed_query_params.get(filter_name):
                continue
            select_statement = await filter_.apply_filter(request, model, parsed_query_params[filter_name],
                                                          select_statement)
        return select_statement

    @classmethod
    def _normalize_filters(cls) -> List[Filter]:
        normalized_filters: List[Filter] = []
        for filter_ in cls.filters:
            if isinstance(filter_, str):
                filter_ = Search(name=filter_, label=filter_.title())
            normalized_filters.append(filter_)
        return normalized_filters

    @classmethod
    async def render_filters(cls, request: Request, values: Optional[dict] = None) -> List[str]:
        if not values:
            values = {}
        rendered_filters: List[str] = []
        for filter_ in cls.filters:
            filter_is_column_name = isinstance(filter_, str)
            if filter_is_column_name:
                filter_ = Search(name=filter_, label=filter_.title())
            name = filter_.context.get("name")
            value = values.get(name)
            rendered_filters.append(await filter_.render(request, value))
        return rendered_filters

    @classmethod
    async def resolve_data(cls, request: Request, data: FormData):
        ret = {}
        m2m_ret = {}
        for field in cls.get_model_fields_for_input():
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
    def get_field_names(cls, display: bool = True) -> List[str]:
        return cls._get_fields_attr("name", display)

    @classmethod
    def get_model_fields_for_input(cls) -> List[Field]:
        display_fields = cls.get_model_fields_for_display()
        return [
            field for field in display_fields
            if not isinstance(field, ComputeField) and not isinstance(field.display, inputs.DisplayOnly)
        ]

    @classmethod
    def get_model_fields_for_display(cls) -> List[Field]:
        sqlalchemy_model_columns: Sequence[Column] = inspect(cls.model).columns.items()
        field_iterator = cls._create_field_iterator(sqlalchemy_model_columns)

        fields: List[Field] = []

        for field in field_iterator:
            if isinstance(field, str):
                field = cls._create_field_by_field_name(field)
            if isinstance(field.display, displays.InputOnly):
                continue
            fields.append(field)

        return cls._shift_primary_keys_to_beginning(fields)

    @classmethod
    def _shift_primary_keys_to_beginning(cls, fields: List[Field]):
        pk_columns: Sequence[Column] = inspect(cls.model).primary_key
        pk_columns_names = [c.name for c in pk_columns]
        for index, field in enumerate(fields):
            if field.name not in pk_columns_names:
                continue
            primary_key_not_at_the_beginning = index != 0
            if primary_key_not_at_the_beginning:
                fields.remove(field)
                fields.insert(0, field)
        return fields

    @classmethod
    def _create_field_iterator(
            cls,
            sqlalchemy_model_columns: Sequence[Column] = ()
    ) -> Iterable[Union[str, Field, ComputeField]]:
        field_iterator = cls.fields
        if not field_iterator:
            field_iterator = [
                cls._create_field_by_field_name(column.name)
                for column in sqlalchemy_model_columns
            ]
        return field_iterator

    @classmethod
    def _create_field_by_field_name(cls, field_name: str) -> Field:
        """
        Create field if you have passed on string to fields
        and rely only on built-in recognition of field type

        for instance:
        >>> class MyModelResource(Model):
        >>>     model = SomeModel
        >>>     fields = ["id", "json_column", "some_column"]

        In this case, fields would be transformed to appropriate field inputs and displays automaticly

        :param field_name:
        :return:
        """
        column: Optional[Column] = cls.model.__dict__.get(field_name)
        if not column:
            raise FieldNotFoundError(f"Can't found field '{field_name}' in model {cls.model}")
        label = field_name
        is_nullable = column.nullable
        placeholder = column.description or ""
        display, input_ = displays.Display(), inputs.Input(
            placeholder=placeholder, null=is_nullable, default=column.default
        )
        if column.primary_key:
            display, input_ = displays.Display(), inputs.DisplayOnly()
        elif column.foreign_keys:
            display, input_ = displays.Display(), inputs.ForeignKey(to_column=column, null=is_nullable)
        elif isinstance(column.type, Boolean):
            display, input_ = displays.Boolean(), inputs.Switch(null=is_nullable, default=column.default)
        elif isinstance(column.type, DateTime):
            if column.default or column.server_default:
                input_ = inputs.DisplayOnly()
            else:
                input_ = inputs.DateTime(null=is_nullable, default=column.server_default)
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
        return Field(name=field_name, label=label.title(), display=display, input_=input_)

    @classmethod
    def get_field_labels(cls, display: bool = True) -> List[str]:
        return cls._get_fields_attr("label", display)

    @classmethod
    def _get_fields_attr(cls, attr: str, display: bool = True) -> List[Any]:
        some_field_attribute_values = []
        for field in cls.get_model_fields_for_display():
            if display and isinstance(field.display, displays.InputOnly):
                continue
            some_field_attribute_values.append(getattr(field, attr))
        return some_field_attribute_values
