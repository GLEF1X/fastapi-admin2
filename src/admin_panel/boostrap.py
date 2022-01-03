import aioredis
import uvicorn
from dynaconf import Dynaconf
from fastapi import FastAPI
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

import resources
from events import create_on_startup_handler, create_on_shutdown_handler
from fastapi_admin.app import setup_admin_application
from fastapi_admin.i18n import I18nMiddleware
from fastapi_admin.utils.file_upload import OnPremiseFileUploader, StaticFileUploader
from providers import SecurityProvider
from src.admin_panel.routes.admin.home import admin_panel_main_router
from src.admin_panel.settings import BASE_DIR
from src.infrastructure.impl.orm.models import Admin


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
            # echo_pool="debug"
        )
        session_pool = sessionmaker(
            engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession
        )
        app = setup_admin_application(engine, session_pool, admin_model_cls=Admin)
        self._main_app.state.engine = engine

        resources.register(app)
        app.configure(
            logo_url="https://svgshare.com/i/d4D.svg",
            template_folders=[str(BASE_DIR / "templates")],
            favicon_url="https://raw.githubusercontent.com/fastapi-admin/fastapi-admin/dev/images/favicon.png",
            providers=[
                SecurityProvider(
                    login_logo_url="https://preview.tabler.io/static/logo.svg",
                    avatar_uploader=StaticFileUploader(
                        OnPremiseFileUploader(uploads_dir=BASE_DIR / "static" / "uploads"),
                        static_path_prefix="/static/uploads"
                    ),
                    redis=redis
                )
            ],
            i18n_middleware=I18nMiddleware
        )
        app.include_router(admin_panel_main_router)
        self._main_app.mount("/admin", app)

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
