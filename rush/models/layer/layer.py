import uuid

import django.db.models as models
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from rush.models import PublishedState
from rush.models.utils import SummernoteTextCleaner


class Layer(models.Model):
    """
    MapData + Styling + Legend information combo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(max_length=255)
    legend_title = models.CharField(
        verbose_name="Legend Title",
        null=True,
        blank=True,
        help_text="An optional title that gives more context about what the legend categories represent.",
    )
    description = models.TextField(
        help_text="The layer description that will appear in the map legend to help people understand what the layer data represents."
    )
    description_strict_clean = models.BooleanField(default=True)
    map_data = models.ForeignKey(
        to="MapData",
        # MapData deletion should fail if a Layer references it.
        # TODO: Check if this actually works or if I got it backwards...
        on_delete=models.PROTECT,
    )
    styles = models.ManyToManyField("Style", through="StylesOnLayer")
    serialized_leaflet_json = models.JSONField(default=dict, null=True, blank=True)
    published_state = models.CharField(
        max_length=255,
        choices=PublishedState.choices,
        help_text="WARNING: Changing this to 'Published' will make this Layer appear on the website immediately.",
    )

    def clean(self) -> None:
        self.description = SummernoteTextCleaner.clean(self.description, strict_clean=self.description_strict_clean)

    def __str__(self):
        return self.name


@receiver([post_save, post_delete], sender=Layer)
def invalidate_layer_cache_entry(sender, instance, **kwargs):
    """
    Invalidate layer cache entries when layers are changed or deleted.
    """
    large_key = f"graphql:resolve_layer_LARGE:{instance.id}"
    small_key = f"graphql:resolve_layer_SMALL:{instance.id}"
    cache.delete_many([large_key, small_key])
