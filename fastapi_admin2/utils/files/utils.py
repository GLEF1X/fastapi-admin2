import pathlib
from datetime import datetime

from fastapi import UploadFile


def create_unique_file_identifier(file: UploadFile, *parts: str) -> str:
    file_extension = pathlib.Path(file.filename).suffix
    current_timestamp = str(datetime.now().timestamp()).replace('.', '')
    return ''.join(parts) + current_timestamp + file_extension
