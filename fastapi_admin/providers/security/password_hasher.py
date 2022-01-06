from typing import Protocol, Union, Any, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash, VerificationError


class HashingFailedError(Exception):

    def __init__(self, orig: Optional[Exception] = None):
        self.orig = orig


class PasswordHasherProto(Protocol):

    def is_rehashing_required(self, hash_: str) -> bool: ...

    def verify(self, hash_: str, password: str) -> None:
        """
        Verifies hash and plain text password.
        It has to raise exception(HashingFailedError) if something was failed.
        """

    def hash(self, password: Union[str, bytes]) -> str: ...


class Argon2PasswordHasher(PasswordHasherProto):

    def __init__(self, **options: Any):
        self._hasher = PasswordHasher(**options)

    def is_rehashing_required(self, hash_: str) -> bool:
        return self._hasher.check_needs_rehash(hash_)

    def verify(self, hash_: str, password: str) -> None:
        try:
            self._hasher.verify(hash_, password)
        except (InvalidHash, VerifyMismatchError, VerificationError) as ex:
            raise HashingFailedError(ex)

    def hash(self, password: Union[str, bytes]) -> str:
        return self._hasher.hash(password)
