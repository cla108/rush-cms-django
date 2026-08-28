import uuid

from django.db import models

from rush.models.utils import SummernoteTextCleaner


class StylesOnLayer(models.Model):
    """
    Through table for adding multiple Styles on a single Layer with the ability to
    reuse styles on other Layers.
    """

    class Meta:
        ordering = ["display_order"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)

    style = models.ForeignKey("Style", on_delete=models.CASCADE)
    layer = models.ForeignKey("Layer", on_delete=models.CASCADE)

    legend_description = models.CharField(
        max_length=255,
        default="E.g., 'Grassland', '0-25%', or '>3 Tree Protection Score'.",
        help_text="A short description of what this style represents on the map.",
    )
    legend_description_strict_clean = models.BooleanField(default=True)
    popup_strict_clean = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True, editable=True)

    # Some expression that will be matched against a GeoJSON feature's properties
    # to decide whether this style will be applied to any given feature on the map.
    # The default is True, which means this style will be applied to all Features by default!
    feature_mapping = models.TextField(default="true")

    # Optional HTML text field for describing what the popup template will be used
    popup = models.TextField(null=True, blank=True)

    def clean(self) -> None:
        if self.popup:
            self.popup = SummernoteTextCleaner.clean(self.popup, strict_clean=self.popup_strict_clean)
