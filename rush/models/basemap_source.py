import uuid

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models


class BasemapSourceManager(models.Manager):

    def default(self) -> "BasemapSource":
        return self.get(is_default=True)


class BasemapSource(models.Model):
    """
    The source location of a "basemap," which is a tile-set used to style maps.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="only_one_basemap_source_can_be_the_default",
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(max_length=255)
    tile_url = models.CharField(max_length=2000, null=False, validators=[URLValidator(schemes=["https"])])
    max_zoom = models.PositiveIntegerField()
    attribution = models.TextField()
    attribution_strict_clean = models.BooleanField(default=True)
    # default here refers to a global default
    is_default = models.BooleanField(default=False)

    def delete(self, using=None, keep_parents=False) -> tuple[int, dict[str, int]]:
        # It shouldn't be possible to delete the default basemap source.
        default_basemap = BasemapSource.objects.default()
        if self.id == default_basemap.id:
            raise ValidationError("Deleting the default basemap source is not allowed.")
        return super().delete(using=using, keep_parents=keep_parents)

    objects: BasemapSourceManager = BasemapSourceManager()  # type: ignore

    def __str__(self):
        return self.name
