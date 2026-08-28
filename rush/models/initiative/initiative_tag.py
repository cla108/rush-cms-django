import uuid

from colorfield.fields import ColorField
from django.db import models


class InitiativeTag(models.Model):
    """
    A descriptive word or phrase that represents a category of initiatives.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(max_length=255)
    text_color = ColorField()
    background_color = ColorField()

    def __str__(self):
        return self.name
