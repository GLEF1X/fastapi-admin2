from typing import List, Union, Optional, Sequence, Any, Type

from sqlalchemy import Column, inspect, Boolean, DateTime, Date, String, Integer, Enum, JSON
from sqlalchemy.orm import DeclarativeMeta
from starlette.datastructures import FormData
from starlette.requests import Request

from fastapi_admin2.backends.sqla.field_converters import (
    BooleanColumnToFieldConverter,
    DatetimeColumnToFieldConverter,
    DateColumnToFieldConverter,
    EnumColumnToFieldConverter,
    JSONColumnToFieldConverter,
    StringColumnToFieldConverter,
    IntegerColumnToFieldConverter
)
from fastapi_admin2.backends.sqla.filters import Search
from fastapi_admin2.resources import AbstractModelResource
from fastapi_admin2.resources.field import Field, ComputedField
from fastapi_admin2.resources.model import Q
from fastapi_admin2.widgets import inputs, displays


class Model(AbstractModelResource):
    _default_filter = Search

    def __init__(self):
        super().__init__()
        self._fields = self._scaffold_fields(inspect(self.model).columns.items())
        self._converters = {
            Boolean: BooleanColumnToFieldConverter(),
            DateTime: DatetimeColumnToFieldConverter(),
            Date: DateColumnToFieldConverter(),
            String: StringColumnToFieldConverter(),
            Integer: IntegerColumnToFieldConverter(),
            Enum: EnumColumnToFieldConverter(),
            JSON: JSONColumnToFieldConverter()
        }
        self._converters.update(self.converters)

    async def enrich_select_with_filters(self, request: Request, model: Any, query: Q) -> Q:
        parsed_query_params = await self.parse_query_params(request)
        where_conditions = []
        for filter_ in self._normalized_filters:
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

    async def resolve_form_data(self, data: FormData):
        for field in self.input_fields:
            field_input = field.input
            if field_input.internationalized.get("disabled") or isinstance(field_input, inputs.DisplayOnly):
                continue

            input_name: Optional[str] = field_input.internationalized.get("name")
            if not isinstance(field_input, inputs.BaseManyToManyInput):
                continue

            v = await field_input.parse(data.getlist(input_name))

    def _scaffold_model_fields_for_display(self) -> List[Field]:
        sqlalchemy_model_columns: Sequence[Column] = inspect(self.model).columns.items()
        fields: List[Field] = []

        for field in self._scaffold_fields(sqlalchemy_model_columns):
            if isinstance(field, str):
                field = self._create_field_by_field_name(field)
            if isinstance(field.display, displays.InputOnly):
                continue
            fields.append(field)

        return self._shift_primary_keys_to_beginning(fields)

    def _shift_primary_keys_to_beginning(self, fields: List[Field]) -> List[Field]:
        pk_columns: Sequence[Column] = inspect(self.model).primary_key
        pk_columns_names = [c.name for c in pk_columns]
        for index, field in enumerate(fields):
            if field.name not in pk_columns_names:
                continue
            primary_key_not_at_the_beginning = index != 0
            if primary_key_not_at_the_beginning:
                fields.remove(field)
                fields.insert(0, field)
        return fields

    def _scaffold_fields(
            self,
            sqlalchemy_model_columns: Sequence[Column] = ()
    ) -> Sequence[Union[str, Field, ComputedField]]:
        field_iterator = self.fields
        if not field_iterator:
            field_iterator = [
                self._create_field_by_field_name(column.name)
                for column in sqlalchemy_model_columns
            ]
        return field_iterator

    def _get_column_by_name(self, name: str) -> Any:
        return self.model.__dict__.get(name)

    def _convert_column_for_which_no_converter_found(self, column: Column, field_name: str) -> Field:
        placeholder = column.description or ""
        return Field(
            display=displays.Display(),
            input_=inputs.Input(
                placeholder=placeholder, null=column.nullable, default=column.default
            ),
            name=field_name,
            label=field_name.title()
        )
