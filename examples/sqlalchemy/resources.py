from datetime import datetime
from typing import List, Any

import orjson
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.sql.operators import match_op
from starlette.requests import Request

from examples.sqlalchemy.entities import enums
from examples.sqlalchemy.orm_models import Admin, Category, Product, Config
from examples.sqlalchemy.settings import BASE_DIR
from fastapi_admin2.app import FastAPIAdmin
from fastapi_admin2.constants import DATETIME_FORMAT
from fastapi_admin2.backends.sqla import filters
from fastapi_admin2.backends.sqla.filters import full_text_search_op
from fastapi_admin2.backends.sqla.model_resource import Model
from fastapi_admin2.enums import HTTPMethod
from fastapi_admin2.resources import Action, Dropdown, Field, Link, ToolbarAction
from fastapi_admin2.utils.file_upload import OnPremiseFileUploader, StaticFileUploader
from fastapi_admin2.widgets import displays, inputs


def register(app: FastAPIAdmin):
    app.register_resources(
        Dashboard,
        AdminResource,
        ConfigResource,
        Content,
    )


class Dashboard(Link):
    label = "Главная"
    icon = "fas fa-home"
    url = "/admin"


class AdminResource(Model):
    label = "Администраторы"
    model = Admin
    icon = "fas fa-user"
    page_pre_title = "Список администраторов"
    page_title = "Администраторы"
    filters = [
        filters.Search(
            name="username",
            label="Имя",
            placeholder="Никнейм",
        ),
        filters.DateTimeRange(name="created_at", label="Дата создания"),
    ]
    fields = [
        "id",
        "username",
        Field(
            name="renew_password",
            label="Пароль",
            display=displays.InputOnly(),
            input_=inputs.Password(),
        ),
        Field(name="email", label="Email", input_=inputs.Email()),
        Field(
            name="avatar",
            label="Аватарка",
            display=displays.Image(width="40"),
            input_=inputs.Image(null=True, upload=StaticFileUploader(
                OnPremiseFileUploader(uploads_dir=BASE_DIR / "static" / "uploads")
            )),
        ),
        Field(
            "created_at",
            label="Дата создания",
            input_=inputs.DateTime(),
            display=displays.DatetimeDisplay()
        ),
    ]

    async def get_toolbar_actions(self, request: Request) -> List[ToolbarAction]:
        return []

    async def generate_cell_css_attributes(self, request: Request, obj: dict, field: Field) -> dict:
        if field.name.lower() == "id":
            return {"class": "bg-danger text-white"}
        return await super().generate_cell_css_attributes(request, obj, field)

    async def get_actions(self, request: Request) -> List[Action]:
        return []

    async def get_bulk_actions(self, request: Request) -> List[Action]:
        return []


class Content(Dropdown):
    class CategoryResource(Model):
        model = Category
        label = "Категории"
        fields = ["id", "name", "slug", "created_at"]

    class ProductResource(Model):
        label = "Продукты"
        model = Product
        filters = [
            filters.Enum(enum=enums.ProductType, name="type", label="Тип продукта"),
            filters.DateTimeRange(name="created_at", label="Дата создания"),
            filters.Boolean(name="is_reviewed", label="Готов к продаже"),
            # filters.ForeignKey(to_column=Product.category_id, name="category", label="Категория")
        ]

        fields = [
            "id",
            Field("name", label="Имя"),
            Field("is_reviewed", label="Готов к продаже", input_=inputs.Switch(), display=displays.Boolean()),
            Field("type", label="Тип", input_=inputs.Enum(enums.ProductType)),
            Field(name="image", label="Картинка", display=displays.Image(width="40")),
            Field(name="body", label="Описание", input_=inputs.Editor()),
            Field(
                "created_at", label="Дата создания",
                input_=inputs.DateTime(default=datetime.now().strftime(DATETIME_FORMAT))
            ),
            # Field(
            #     "category_id",
            #     label="Категория",
            #     input_=inputs.ForeignKey(to_column=Product.category_id)
            # )
        ]

    label = "Контент"
    icon = "fas fa-bars"
    resources = [ProductResource, CategoryResource]


class ConfigResource(Model):
    label = "Конфигурация"
    model = Config
    icon = "fas fa-cogs"
    filters = [
        filters.Enum(enum=enums.Status, name="status", label="Статус"),
        filters.Search(name="key", label="Ключ", sqlalchemy_operator=full_text_search_op),
    ]
    fields = [
        "id",
        Field("label", label="ярлык"),
        Field("key", label="ключ"),
        Field(
            "value",
            label="значение",
            display=displays.Json(dumper=orjson.dumps),
            input_=inputs.Json(dumper=orjson.dumps)
        ),
        Field(
            name="status",
            label="статус",
            input_=inputs.RadioEnum(enums.Status, default=enums.Status.on),
        ),
    ]

    async def generate_row_attributes(self, request: Request, obj: Any) -> dict:
        if getattr(obj, "status") == enums.Status.on:
            return {"class": "bg-green"}
        return await super().generate_row_attributes(request, obj)

    async def get_actions(self, request: Request) -> List[Action]:
        actions = await super().get_actions(request)
        switch_status = Action(
            label="Изменить статус",
            icon="ti ti-toggle-left",
            name="switch_status",
            method=HTTPMethod.PUT,
        )
        actions.append(switch_status)
        return actions
