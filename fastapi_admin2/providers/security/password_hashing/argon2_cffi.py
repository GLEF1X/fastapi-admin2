from typing import Union

from argon2 import PasswordHasher, DEFAULT_TIME_COST, DEFAULT_MEMORY_COST, DEFAULT_PARALLELISM, \
    DEFAULT_HASH_LENGTH, DEFAULT_RANDOM_SALT_LENGTH, Type
from argon2.exceptions import InvalidHash, VerifyMismatchError, VerificationError

from fastapi_admin2.providers.security.password_hashing.protocol import PasswordHasherProto, \
    HashVerifyFailedError


class Argon2PasswordHasher(PasswordHasherProto):

    def __init__(
            self,
            time_cost: int = DEFAULT_TIME_COST,
            memory_cost: int = DEFAULT_MEMORY_COST,
            parallelism: int = DEFAULT_PARALLELISM,
            hash_len: int = DEFAULT_HASH_LENGTH,
            salt_len: int = DEFAULT_RANDOM_SALT_LENGTH,
            encoding: str = "utf-8",
            type: Type = Type.ID,
    ):
        self._hasher = PasswordHasher(time_cost, memory_cost, parallelism, hash_len, salt_len, encoding, type)

    def is_rehashing_required(self, hash_: str) -> bool:
        return self._hasher.check_needs_rehash(hash_)

    def verify(self, hash_: str, password: str) -> None:
        try:
            self._hasher.verify(hash_, password)
        except (InvalidHash, VerifyMismatchError, VerificationError) as ex:
            raise HashVerifyFailedError(ex)

    def hash(self, password: Union[str, bytes]) -> str:
        return self._hasher.hash(password)
