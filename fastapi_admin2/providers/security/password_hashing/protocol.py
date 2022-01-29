from typing import Optional, Protocol, Union


class HashVerifyFailedError(Exception):

    def __init__(self, orig: Optional[Exception] = None):
        self.orig = orig


class PasswordHasherProto(Protocol):

    def is_rehashing_required(self, hash_: str) -> bool: ...

    def verify(self, hash_: str, password: str) -> None:
        """
        Verifies hash and plain text password.
        It raises exception(HashingFailedError) if something fail.
        """

    def hash(self, password: Union[str, bytes]) -> str: ...