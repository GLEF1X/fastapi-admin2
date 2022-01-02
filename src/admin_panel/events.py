from typing import Callable, Coroutine, Any

from fastapi import FastAPI

from fastapi_admin.database.models.base import OrmModelBase


def create_on_startup_handler(app: FastAPI) -> Callable[..., Coroutine[Any, Any, None]]:
    async def on_startup() -> None:
        pass
        # engine = app.state.engine
        # async with engine.begin() as conn:
        #     await conn.run_sync(OrmModelBase.metadata.drop_all)
        #     await conn.run_sync(OrmModelBase.metadata.create_all)

    return on_startup


def create_on_shutdown_handler(app: FastAPI) -> Callable[..., Coroutine[Any, Any, None]]:
    async def on_shutdown() -> None:
        pass

    return on_shutdown
