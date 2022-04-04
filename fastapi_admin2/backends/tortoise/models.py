from tortoise import fields, Model

from fastapi_admin2.domain.entities import AbstractAdmin


class AbstractAdminModel(Model, AbstractAdmin):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=200)
    profile_pic = fields.CharField(max_length=100)

    class Meta:
        abstract = True
