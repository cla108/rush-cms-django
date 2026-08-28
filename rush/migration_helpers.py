import uuid
from typing import Type

from django.db.migrations.operations import (
    AddField,
    AlterField,
    RemoveField,
    RenameField,
)
from django.db.migrations.operations.base import Operation
from django.db.models import BigIntegerField, Model, UUIDField

"""
Functions that help write customized migration code.
"""


def big_int_to_uuid_operations(model: Type[Model] | str, field: str) -> list[Operation]:
    """
    Replace the specified BigIntegerField field with a UUID field of the same name, where the new UUID field
    is a primary key, automatically added, and backfills the database with newly generated UUIDs.

    Args:
        model: Either a Model class or a string with the model name (lowercase)
        field: The field name to convert from BigInteger to UUID
    """

    model_name = model if isinstance(model, str) else model.__name__.lower()
    tmp_field_name = f"__tmp_migration_{field}"
    return [
        # make not primary key
        AlterField(
            model_name=model_name,
            name=field,
            field=BigIntegerField(primary_key=False, null=False),
        ),
        # rename temporarily
        RenameField(model_name=model_name, old_name=field, new_name=tmp_field_name),
        # add new field
        AddField(
            model_name=model_name,
            name=field,
            field=UUIDField(primary_key=True, default=uuid.uuid4, null=False),
            preserve_default=False,
        ),
        # remove temporary field
        RemoveField(model_name=model_name, name=tmp_field_name),
    ]
