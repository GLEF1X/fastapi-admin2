import abc
import inspect

from sqlalchemy import Column

from fastapi_admin2.ui.resources.model import ColumnToFieldConverter, FieldSpec
from fastapi_admin2.ui.widgets import displays, inputs


class SQLAlchemyColumnToFieldConverter(ColumnToFieldConverter, abc.ABC):
    def is_suitable(self, column: Column) -> bool:
        types = inspect.getmro(column)

        # Search by module + name
        for col_type in types:
            type_string = f"{col_type.__module__}.{col_type.__name__}"

            if type_string in self.converts:
                return True

        # Search by name
        for col_type in types:
            if col_type.__name__ in self.converts:
                return True

        return False


class BooleanColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = ["Boolean", "sqlalchemy.dialects.mssql.base.BIT"]

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Boolean(),
            input_=inputs.Switch(null=column.nullable, default=column.default),
        )


class DatetimeColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = "DateTime"

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        if column.default or column.server_default:
            input_ = inputs.DisplayOnly()
        else:
            input_ = inputs.DateTime(null=column.nullable, default=column.server_default)

        return FieldSpec(
            display=displays.DatetimeDisplay(),
            input_=input_
        )


class DateColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = "Date"

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.DateDisplay(),
            input_=inputs.Date(null=column.nullable, default=column.default),
        )


class EnumColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = "sqlalchemy.sql.sqltypes.Enum"

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Enum(
                column.type.__class__,
                null=column.nullable,
                default=column.default
            )
        )


class JSONColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = "JSON"

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Json(),
            input_=inputs.Json(null=column.nullable)
        )


class StringColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = ['Text', 'LargeBinary', 'Binary', 'CIText']

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.TextArea(
                placeholder=placeholder, null=column.nullable, default=column.default
            )
        )


class IntegerColumnToFieldConverter(SQLAlchemyColumnToFieldConverter):
    converts = 'Integer'

    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Number(
                placeholder=placeholder, null=column.nullable, default=column.default
            )
        )
