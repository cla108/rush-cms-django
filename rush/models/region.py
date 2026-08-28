import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Region(models.Model):
    """
    Geographical region for grouping and filtering questions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255, unique=True, help_text="Region name (e.g., 'Downtown', 'Victoria', 'Vancouver')"
    )
    latitude = models.FloatField(
        help_text="Latitude coordinate for default map center",
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
    )
    longitude = models.FloatField(
        help_text="Longitude coordinate for default map center",
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
    )
    default_zoom = models.FloatField(
        help_text="Default zoom level for map view (e.g., 12.0 for city level)",
        validators=[MinValueValidator(0.0)],
    )

    def __str__(self):
        return self.name
