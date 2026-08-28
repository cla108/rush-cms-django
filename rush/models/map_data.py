import json
import sys
import uuid

import django.db.models as models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import URLValidator
from storages.backends.s3 import S3Storage

from rush.models.validators import (
    FiletypeValidator,
    validate_ogm_campaign_link,
    validate_ogm_map_link,
    validate_arcgis_feature_server_link,
)
from rush.storage import BackblazeStorageFactory
from django.core.validators import MinValueValidator, MaxValueValidator


def get_raster_storage() -> S3Storage | FileSystemStorage:
    """
    Get storage for raster image files (GeoTIFF).
    """
    if settings.DEBUG or "pytest" in sys.modules:
        # Don't try to connect to Backblaze in a dev environment or during tests
        return FileSystemStorage(location=f"{settings.MEDIA_ROOT}/debug_raster_image_storage")
    return BackblazeStorageFactory.create_from_bucket_name(
        settings.BACKBLAZE_RASTER_BUCKET_NAME,
        validate_visibility=BackblazeStorageFactory.Visibility.PUBLIC,
        persistance=BackblazeStorageFactory.Persistance.HARD_DELETE,
        duplication=BackblazeStorageFactory.Duplication.LATEST_VERSION_ONLY,
    )


class MapData(models.Model):

    class ProviderState(models.TextChoices):
        UNSET = "unset"
        GEOJSON = "geojson"
        GEOTIFF = "geotiff"  # for raster image data
        OPEN_GREEN_MAP = "open_green_map"
        ARCGIS_REST = "arcgis_rest"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(max_length=255, unique=True)
    provider_state = models.CharField(max_length=255, choices=ProviderState.choices, default=ProviderState.UNSET)

    # Geojson provider fields
    _geojson = models.JSONField(default=dict, null=True, blank=True)

    # Open green map provider fields
    map_link = models.CharField(
        max_length=2000,
        null=True,
        blank=True,
        validators=[URLValidator(schemes=["https"]), validate_ogm_map_link],
    )
    campaign_link = models.CharField(
        max_length=2000,
        null=True,
        blank=True,
        validators=[URLValidator(schemes=["https"]), validate_ogm_campaign_link],
    )

    # Geotiff provider fields
    geotiff = models.FileField(
        null=True,
        blank=True,
        storage=get_raster_storage,
        validators=[FiletypeValidator(valid_names=["TIFF"])],
        help_text="A GeoTIFF file to upload. It may take up to a couple minutes to upload depending on the file size.",
    )

    # ArcGIS REST provider fields
    arcgis_feature_server_link = models.CharField(
        max_length=2000,
        null=True,
        blank=True,
        validators = [URLValidator(schemes=["https"]), validate_arcgis_feature_server_link],
    )

    arcgis_cache_seconds = models.IntegerField(
        null=True,
        blank=True,
        # one day
        default=86400,
        validators=[
            # allowed between 30 mins and ~1 month
            MinValueValidator(1800),
            MaxValueValidator(2592000)
        ],
    )

    arcgis_last_fetched_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    @property
    def geojson(self) -> str | None:
        """
        Get the geojson from this map data object. Return `None` if the
        provider state doesn't support a geojson-representation.
        """

        if self.provider_state == self.ProviderState.GEOJSON and self._geojson:
            return json.dumps(self._geojson)

        # NOTE: Other ProviderState's may be supported in the future.
        return None

    def __str__(self):
        # Don't change me. Breaks graphql API getMapDataByName for clients.
        return f"{self.name} ({self.provider_state.upper()})"

    def __repr__(self):
        return "<MapData '{}', provided by: {}, {}>".format(
            self.name,
            self.provider_state,
            self.id,
        )

    class Meta:
        # better plural name in the admin table list
        verbose_name_plural = "Map Data"
