import dataclasses
import pathlib
from typing import Union

from pydantic import AnyHttpUrl, PostgresDsn

BASE_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent


@dataclasses.dataclass(frozen=True)
class ServerSettings:
    port: int = 8080
    host: str = "localhost"
    debug: bool = False


@dataclasses.dataclass()
class DatabaseSettings:
    user: str
    password: str
    host: Union[str, AnyHttpUrl]
    db_name: str

    def assemble_connection_uri(self) -> str:
        sync_connection_url = PostgresDsn.build(
            scheme="postgresql",
            user=self.user,
            password=self.password,
            host=self.host,
            path=f"/{self.db_name or ''}",
        )
        return sync_connection_url.replace("postgresql", "postgresql+asyncpg")


@dataclasses.dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    server: ServerSettings = ServerSettings()
