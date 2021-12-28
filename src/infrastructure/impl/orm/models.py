from sqlalchemy import Column, TIMESTAMP, func, Text, VARCHAR, Boolean, false, BIGINT, Identity, JSON

from fastapi_admin.database.models.abstract import Admin
from fastapi_admin.database.models.base import OrmModelBase


class Admin(Admin):
    last_login = Column(TIMESTAMP(timezone=True), server_default=func.now())
    email = Column(VARCHAR(200), default="")
    avatar = Column(VARCHAR(200), server_default="")
    intro = Column(Text, server_default="")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __str__(self):
        return f"{self.id}#{self.username}"


# class Category(Model):
#     slug = Column(VARCHAR(200))
#     name = Column(VARCHAR(200))
#     created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Product(OrmModelBase):
    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    # categories = fields.ManyToManyField("models.Category")
    name = Column(VARCHAR(50), default="")
    is_reviewed = Column(Boolean, server_default=false())
    # type = fields.IntEnumField(ProductType, description="Product Type")
    avatar = Column(VARCHAR(200), server_default="")
    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Config(OrmModelBase):
    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    label = Column(VARCHAR(200), server_default="")
    key = Column(VARCHAR(20), nullable=False, unique=True)
    value = Column(JSON(), nullable=False)
    # status: Status = fields.IntEnumField(Status, default=Status.on)
