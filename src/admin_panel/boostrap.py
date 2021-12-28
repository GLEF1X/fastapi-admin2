import aioredis
import uvicorn
from dynaconf import Dynaconf
from fastapi import FastAPI
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

import resources
from events import create_on_startup_handler
from fastapi_admin.app import FastAPIAdmin
from fastapi_admin.database.repository.admin import UserRepository
from fastapi_admin.database.repository.dependencies import SessionPoolDependencyMarker
from fastapi_admin.exceptions import not_found_error_exception, forbidden_error_exception, \
    unauthorized_error_exception, server_error_exception
from fastapi_admin.providers.security.dependencies import UserRepositoryDependencyMarker, \
    RedisClientDependencyMarker
from fastapi_admin.routes import router
from fastapi_admin.services.file_upload import DiskFileUploader
from fastapi_admin.services.i18n import SimpleI18nMiddleware
from providers import SecurityProvider
from src.admin_panel import routes
from src.admin_panel.settings import BASE_DIR
from src.infrastructure.impl.orm.models import Admin


class ApplicationBuilder:

    def __init__(self):
        self._main_app = FastAPI()
        self._admin_app = FastAPIAdmin()
        self._settings = Dynaconf(
            settings_files=["settings.toml", ".secrets.toml"],
            redis=True,
            preload=[BASE_DIR / "settings.toml"],
            environments=["development", "production", "testing"],
            load_dotenv=False,
            auto_cast=True,
        )
        self._main_app.mount("/admin", self._admin_app)
        self._main_app.mount(
            "/static",
            StaticFiles(directory=BASE_DIR / "static"),
            name="static",
        )

    def build_application(self) -> FastAPI:
        self._register_dependencies()
        self._register_events()
        self._register_middlewares()
        self._configure_admin_contraptions()
        return self._main_app

    def _register_dependencies(self) -> None:
        redis = aioredis.from_url(
            self._settings.redis_connection_uri,
            decode_responses=True,
            encoding="utf8",
        )

        engine = create_async_engine(
            url=make_url(self._settings.postgres_connection_uri),
            echo=True,
            echo_pool="debug"
        )
        session_pool = sessionmaker(
            engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession
        )

        self._admin_app.dependency_overrides[UserRepositoryDependencyMarker] = lambda: UserRepository(
            session_pool(), Admin)
        self._admin_app.dependency_overrides[RedisClientDependencyMarker] = lambda: redis
        self._admin_app.dependency_overrides[SessionPoolDependencyMarker] = lambda: session_pool

        self._admin_app.configure(
            logo_url="https://svgshare.com/i/d4D.svg",
            template_folders=[str(BASE_DIR / "templates")],
            favicon_url="https://raw.githubusercontent.com/fastapi-admin/fastapi-admin/dev/images/favicon.png",
            providers=[
                SecurityProvider(
                    login_logo_url="https://preview.tabler.io/static/logo.svg",
                    avatar_uploader=DiskFileUploader(uploads_dir=BASE_DIR / "static" / "uploads")
                )
            ],
            i18n_middleware=SimpleI18nMiddleware
        )

    def _register_events(self) -> None:
        self._main_app.add_event_handler("startup", create_on_startup_handler(self._admin_app))

    def _configure_admin_contraptions(self) -> None:
        self._admin_app.include_router(router)

        self._admin_app.add_exception_handler(HTTP_500_INTERNAL_SERVER_ERROR, server_error_exception)
        self._admin_app.add_exception_handler(HTTP_404_NOT_FOUND, not_found_error_exception)
        self._admin_app.add_exception_handler(HTTP_403_FORBIDDEN, forbidden_error_exception)
        self._admin_app.add_exception_handler(HTTP_401_UNAUTHORIZED, unauthorized_error_exception)

        self._admin_app.include_router(routes.home.admin_panel_main_router)

        resources.register(self._admin_app)

    def _register_middlewares(self) -> None:
        self._main_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )


def main():
    application_builder = ApplicationBuilder()
    application = application_builder.build_application()
    uvicorn.run(application)


if __name__ == '__main__':
    main()
