import warnings
from typing import List, Union, Sequence, Any

from sqlalchemy import Column, inspect
from sqlalchemy.orm import ColumnProperty, RelationshipProperty
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
from fastapi_admin2.backends.sqla.toolings import filter_foreign_columns, get_primary_key
from fastapi_admin2.ui.resources import AbstractModelView
from fastapi_admin2.ui.resources.column import Field, ComputedField
from fastapi_admin2.ui.resources.model import Q
from fastapi_admin2.ui.widgets import inputs, displays


class ModelView(AbstractModelView):
    _default_filter = Search

    column_display_all_relations: bool = True
    auto_select_related: bool = True

    def __init__(self):
        self._fields = self._scaffold_fields()
        self._columns = self._scaffold_columns()
        self._auto_joins = self._scaffold_auto_joins()

        self._converters = [
            BooleanColumnToFieldConverter(),
            DatetimeColumnToFieldConverter(),
            DateColumnToFieldConverter(),
            StringColumnToFieldConverter(),
            IntegerColumnToFieldConverter(),
            EnumColumnToFieldConverter(),
            JSONColumnToFieldConverter()
        ]
        if self.converters is not None:
            self._converters.extend(self.converters)

        super().__init__()

    async def enrich_select_with_filters(self, request: Request, model: Any, query: Q) -> Q:
        query_params = {k: v for k, v in request.query_params.items() if v}
        for filter_ in self._normalized_filters:
            query = filter_.apply(query, query_params.get(filter_.name))
        return query

    async def resolve_form_data(self, data: FormData):
        pass

    def _create_field(self, field_name: str) -> Field:
        column_or_relationship_property: Union[ColumnProperty, RelationshipProperty] = inspect(
            self.model
        ).attrs[field_name]

        for converter in self._converters:
            if not converter.is_suitable(column_or_relationship_property):
                continue
            return converter.convert(column_or_relationship_property, field_name)

        raise ValueError(f"No suitable converter found for {field_name}")

    def _scaffold_columns(self) -> List[ColumnProperty]:
        """
            Return a list of columns from the model.
        """
        columns: List[ColumnProperty] = []

        for p in self._get_model_columns():
            if hasattr(p, 'direction'):
                if self.column_display_all_relations or p.direction.name == 'MANYTOONE':
                    columns.append(p.key)
            elif hasattr(p, 'columns'):
                if len(p.columns) > 1:
                    filtered = filter_foreign_columns(self.model.__table__, p.columns)

                    if len(filtered) == 0:
                        continue
                    elif len(filtered) > 1:
                        warnings.warn('Can not convert multiple-column properties (%s.%s)' % (self.model, p.key))
                        continue

                    column = filtered[0]
                else:
                    column = p.columns[0]

                if column.foreign_keys:
                    continue

                if not self.show_pk and column.primary_key:
                    continue

                columns.append(p.key)

        return columns

    def _scaffold_pk(self):
        return get_primary_key(self.model)

    def _scaffold_auto_joins(self) -> List[RelationshipProperty]:
        """
            Return a list of joined tables by going through the
            displayed columns.
        """
        if not self.auto_select_related:
            return []

        relations = set()

        for p in self._get_model_columns():
            if hasattr(p, 'direction'):
                # Check if it is pointing to same model
                if p.mapper.class_ == self.model:
                    continue

                # Check if it is pointing to a differnet bind
                source_bind = getattr(self.model, '__bind_key__', None)
                target_bind = getattr(p.mapper.class_, '__bind_key__', None)
                if source_bind != target_bind:
                    continue

                if p.direction.name in ['MANYTOONE', 'MANYTOMANY']:
                    relations.add(p.key)

        joined = []

        for prop, name in self._columns:
            if prop in relations:
                joined.append(getattr(self.model, prop))

        return joined

    def _scaffold_model_fields_for_display(self) -> List[Field]:
        fields: List[Field] = []

        for field in self._scaffold_fields():
            if isinstance(field, str):
                field = self._create_field(field)
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

    def _scaffold_fields(self) -> Sequence[Union[str, Field, ComputedField]]:
        field_iterator = self.fields
        if not field_iterator:
            field_iterator = [
                self._create_field(column.name)
                for column in self._get_model_columns()
            ]
        return field_iterator

    def _convert_column_for_which_no_converter_found(self, column: Column, field_name: str) -> Field:
        placeholder = column.description or ""
        return Field(
            display=displays.Display(),
            input=inputs.Input(
                placeholder=placeholder, null=column.nullable, default=column.default
            ),
            name=field_name,
            label=field_name.title()
        )

    def _get_model_columns(self) -> List[Any]:
        return list(inspect(self.model).attrs)
