from typing import Callable, Coroutine, Any

from fastapi import FastAPI


def create_on_startup_handler(app: FastAPI) -> Callable[..., Coroutine[Any, Any, None]]:
    async def on_startup() -> None:
        ...

    return on_startup


def create_on_shutdown_handler(app: FastAPI) -> Callable[..., Coroutine[Any, Any, None]]:
    async def on_shutdown() -> None:
        ...

    return on_shutdown
