from datetime import datetime
from typing import List

from fastapi_admin.app import FastAPIAdmin
from fastapi_admin.constants import DATETIME_FORMAT
from fastapi_admin.enums import HTTPMethod
from fastapi_admin.services.file_upload import DiskFileUploader
from fastapi_admin.resources import Action, Dropdown, Field, Link, Model, ToolbarAction
from fastapi_admin.widgets import displays, filters, inputs
from starlette.requests import Request

from src.admin_panel.settings import BASE_DIR
from src.entities import enums
from src.entities.enums import ProductType
from src.infrastructure.impl.orm.models import Admin, Product, Config

upload = DiskFileUploader(uploads_dir=BASE_DIR / "static" / "uploads")


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
            search_mode="contains",
            placeholder="Никнейм",
        ),
        filters.Datetime(name="created_at", label="Дата создания"),
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
            input_=inputs.Image(null=True, upload=upload),
        ),
        "created_at",
    ]

    async def get_toolbar_actions(self, request: Request) -> List[ToolbarAction]:
        return []

    async def cell_attributes(self, request: Request, obj: dict, field: Field) -> dict:
        if field.name == "id":
            return {"class": "bg-danger text-white"}
        return await super().cell_attributes(request, obj, field)

    async def get_actions(self, request: Request) -> List[Action]:
        return []

    async def get_bulk_actions(self, request: Request) -> List[Action]:
        return []


class Content(Dropdown):
    class CategoryResource(Model):
        label = "Категория"
        fields = ["id", "name", "slug", "created_at"]

    class ProductResource(Model):
        label = "Продукты"
        model = Product
        filters = [
            filters.Enum(enum=enums.ProductType, name="type", label="Тип продукта"),
            filters.Datetime(name="created_at", label="Дата создания"),
        ]

        fields = [
            "id",
            Field("name", label="Имя"),
            Field("is_reviewed", label="Готов к продаже", input_=inputs.Switch(), display=displays.Boolean()),
            Field("type", label="Тип", input_=inputs.Enum(ProductType)),
            Field(name="image", label="Картинка", display=displays.Image(width="40")),
            Field(name="body", label="Описание", input_=inputs.Editor()),
            Field(
                "created_at", label="Дата создания",
                input_=inputs.DateTime(default=datetime.now().strftime(DATETIME_FORMAT))
            ),
        ]

    label = "Контент"
    icon = "fas fa-bars"
    resources = [ProductResource]


class ConfigResource(Model):
    label = "Конфигурация"
    model = Config
    icon = "fas fa-cogs"
    filters = [
        filters.Enum(enum=enums.Status, name="status", label="Статус"),
        filters.Search(name="key", label="Ключ"),
    ]
    fields = [
        "id",
        Field("label", label="ярлык"),
        Field("key", label="ключ"),
        Field("value", label="значение"),
        Field(
            name="status",
            label="статус",
            input_=inputs.RadioEnum(enums.Status, default=enums.Status.on),
        ),
    ]

    async def row_attributes(self, request: Request, obj: dict) -> dict:
        if obj.get("status") == enums.Status.on:
            return {"class": "bg-green text-white"}
        return await super().row_attributes(request, obj)

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
