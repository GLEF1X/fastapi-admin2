from sqlalchemy import Column, TIMESTAMP, func, Text, VARCHAR, Boolean, false, BIGINT, Identity, JSON, Enum, \
    ForeignKey
from sqlalchemy.orm import relationship

from fastapi_admin.database.models.abstract_admin import AbstractAdmin
from fastapi_admin.database.models.base import OrmModelBase
from src.entities.enums import Status


class Admin(AbstractAdmin):
    __tablename__ = "admins"

    last_login = Column(TIMESTAMP(timezone=True), server_default=func.now())
    email = Column(VARCHAR(200), default="")
    intro = Column(Text, server_default="")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __str__(self):
        return f"{self.id}#{self.username}"


class Category(OrmModelBase):
    __tablename__ = "categories"

    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    slug = Column(VARCHAR(200))
    name = Column(VARCHAR(200))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __str__(self) -> str:
        return self.name


class Product(OrmModelBase):
    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    category_id = Column(BIGINT(), ForeignKey("categories.id"), nullable=False)
    name = Column(VARCHAR(50), default="")
    is_reviewed = Column(Boolean, server_default=false())
    avatar = Column(VARCHAR(200), server_default="")
    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    category: Category = relationship("Category", backref="products")


class Config(OrmModelBase):
    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    label = Column(VARCHAR(200), server_default="")
    key = Column(VARCHAR(20), nullable=False, unique=True)
    value = Column(JSON(), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.on)
