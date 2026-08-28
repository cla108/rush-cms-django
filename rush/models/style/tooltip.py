import uuid
from decimal import Decimal

import django.db.models as models

from rush.models.utils import SummernoteTextCleaner


class Direction(models.TextChoices):
    """
    Where to attempt to draw the text relative to the point coordinates.
    """

    RIGHT = "right"
    LEFT = "left"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    AUTO = "auto"


class Tooltip(models.Model):
    """
    A way to display text directly on the map for point data. This model is one-to-one with `StyleOnLayer` and was
    made into a separate model more for organizational purposes than anything else.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    style_on_layer = models.OneToOneField(
        to="StylesOnLayer",
        on_delete=models.CASCADE,
        related_name="tooltip",
        null=True,
    )
    label = models.TextField()
    label_strict_clean = models.BooleanField(default=True)
    offset_x = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal(0))
    offset_y = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal(0))
    opacity = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal(0.8))
    direction = models.CharField(max_length=32, choices=Direction.choices)
    permanent = models.BooleanField(default=True)
    sticky = models.BooleanField(default=True)

    def clean(self) -> None:
        self.label = SummernoteTextCleaner.clean_tooltip(self.label, strict_clean=self.label_strict_clean)

    def __str__(self):
        return self.label
