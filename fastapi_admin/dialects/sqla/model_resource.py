from typing import List, Union, Optional, Sequence, Iterable, Any

from sqlalchemy import Column, inspect, Boolean, DateTime, Date, Enum, JSON, String, Integer
from starlette.datastructures import FormData
from starlette.requests import Request

from fastapi_admin.dialects.sqla.filters import Search
from fastapi_admin.exceptions import FieldNotFoundError
from fastapi_admin.resources import AbstractModelResource
from fastapi_admin.resources.field import Field, ComputeField
from fastapi_admin.resources.model import Q
from fastapi_admin.widgets import inputs, displays


class Model(AbstractModelResource):
    _default_filter = Search

    @classmethod
    async def enrich_select_with_filters(cls, request: Request, model: Any, query: Q) -> Q:
        parsed_query_params = await cls.parse_query_params(request)
        where_conditions = []
        for filter_ in cls._normalize_filters():
            if not parsed_query_params.get(filter_.name):
                continue
            generated_filter = await filter_.generate_public_filter(parsed_query_params[filter_.name])
            where_conditions.append(
                generated_filter.operator(
                    model.__dict__[generated_filter.name],
                    generated_filter.value
                )
            )
        return query.where(*where_conditions)

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
        column_type = column.type

        display, input_ = displays.Display(), inputs.Input(
            placeholder=placeholder, null=is_nullable, default=column.default
        )
        if column.primary_key:
            display, input_ = displays.Display(), inputs.DisplayOnly()
        # elif column.foreign_keys:
        #     display, input_ = displays.Display(), inputs.ForeignKey(to_column=column, null=is_nullable)
        elif isinstance(column_type, Boolean):
            display, input_ = displays.Boolean(), inputs.Switch(null=is_nullable, default=column.default)
        elif isinstance(column_type, DateTime):
            if column.default or column.server_default:
                input_ = inputs.DisplayOnly()
            else:
                input_ = inputs.DateTime(null=is_nullable, default=column.server_default)
            display, input_ = displays.DatetimeDisplay(), input_
        elif isinstance(column_type, Date):
            display, input_ = displays.DateDisplay(), inputs.Date(null=is_nullable, default=column.default)
        elif isinstance(column_type, Enum):
            display, input_ = displays.Display(), inputs.Enum(
                column_type.__class__, null=is_nullable, default=column.default
            )
        elif isinstance(column_type, JSON):
            display, input_ = displays.Json(), inputs.Json(null=is_nullable)
        elif isinstance(column_type, String):
            display, input_ = displays.Display(), inputs.TextArea(
                placeholder=placeholder, null=is_nullable, default=column.default
            )
        elif isinstance(column_type, Integer):
            display, input_ = displays.Display(), inputs.Number(
                placeholder=placeholder, null=is_nullable, default=column.default
            )
        return Field(name=field_name, label=label.title(), display=display, input_=input_)

    @classmethod
    async def resolve_form_data(cls, data: FormData):
        for field in cls.get_model_fields_for_input():
            field_input = field.input
            if field_input.context.get("disabled") or isinstance(field_input, inputs.DisplayOnly):
                continue

            input_name: Optional[str] = field_input.context.get("name")
            if not isinstance(field_input, inputs.BaseManyToManyInput):
                continue

            v = await field_input.parse_value(data.getlist(input_name))

