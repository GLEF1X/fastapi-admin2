import aioredis
import uvicorn
from dynaconf import Dynaconf
from fastapi import FastAPI
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from examples.sqlalchemy import resources
from examples.sqlalchemy.events import create_on_startup_handler, create_on_shutdown_handler
from examples.sqlalchemy.orm_models import Admin
from examples.sqlalchemy.routes.admin.home import admin_panel_main_router
from examples.sqlalchemy.settings import BASE_DIR
from fastapi_admin2.app import FastAPIAdmin
from fastapi_admin2.backends.sqla import SQLAlchemyBackend
from fastapi_admin2.providers.security import SecurityProvider
from fastapi_admin2.providers.security.password_hashing.argon2_cffi import Argon2PasswordHasher
from fastapi_admin2.utils.files.s3 import S3FileManager


class ApplicationBuilder:

    def __init__(self):
        self._main_app = FastAPI()
        self._settings = Dynaconf(
            settings_files=["settings.toml", ".secrets.toml"],
            redis=True,
            preload=[BASE_DIR / "settings.toml"],
            environments=["development", "production", "testing"],
            load_dotenv=False,
            auto_cast=True,
        )
        self._main_app.mount(
            "/static",
            StaticFiles(directory=BASE_DIR / "static"),
            name="static",
        )

    def build_application(self) -> FastAPI:
        self._register_middlewares()
        self._setup_admin_panel()
        self._register_events()
        return self._main_app

    def _register_events(self) -> None:
        self._main_app.add_event_handler("startup", create_on_startup_handler(self._main_app))
        self._main_app.add_event_handler("shutdown", create_on_shutdown_handler(self._main_app))

    def _setup_admin_panel(self) -> None:
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

        admin_app = FastAPIAdmin(
            orm_backend=SQLAlchemyBackend(session_pool, Admin),
            logo_url="https://svgshare.com/i/d4D.svg",
            template_folders=[BASE_DIR / "templates"],
            favicon_url="https://raw.githubusercontent.com/fastapi-admin/fastapi-admin/dev/images/favicon.png",
            providers=[
                SecurityProvider(
                    login_logo_url="https://preview.tabler.io/static/logo.svg",
                    file_manager=S3FileManager(
                        bucket_name=self._settings.s3.bucket_name,
                        access_key=self._settings.s3.access_key,
                        secret_key=self._settings.s3.secret_key,
                        region=self._settings.s3.region,
                        file_identifier_prefix=self._settings.s3.file_identifier_prefix,
                    ),
                    redis=redis,
                    password_hasher=Argon2PasswordHasher()
                )
            ]
        )

        self._main_app.state.engine = engine

        resources.register(admin_app)
        admin_app.include_router(admin_panel_main_router)

        self._main_app.mount("/admin", admin_app)

        admin_app.add_template_folder(BASE_DIR / "templates")

    def _register_middlewares(self) -> None:
        self._main_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )


application_builder = ApplicationBuilder()
app = application_builder.build_application()

if __name__ == '__main__':
    uvicorn.run(app, port=8080)
