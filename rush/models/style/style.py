import uuid
from decimal import Decimal

import django.db.models as models
from colorfield.fields import ColorField
from django.db.models.signals import pre_save
from django.dispatch import receiver

from rush.models.utils import CompressionFailed, compress_image
from rush.models.validators import (
    FiletypeValidator,
    validate_only_integers_and_whitespace,
)


class LineCap(models.TextChoices):
    """
    The shape to be used at the end of the line.
    """

    BUTT = "butt"
    ROUND = "round"
    SQUARE = "square"


class LineJoin(models.TextChoices):
    """
    The shape to be used at the corners where lines meet.
    """

    ARCS = "arcs"
    BEVEL = "bevel"
    MITER = "miter"
    MITER_CLIP = "miter-clip"
    ROUND = "round"


class FillRule(models.TextChoices):
    """
    TODO: I'm not really sure what this does. It's currently omitted from the style form.
    https://developer.mozilla.org/en-US/docs/Web/CSS/fill-rule
    """

    NONZERO = "nonzero"
    EVENODD = "evenodd"


class Style(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(max_length=255)

    ##########
    # Stroke #
    ##########
    draw_stroke = models.BooleanField(
        help_text="Check this box when you want to draw the line. Unchecking this box, for example, "
        + "will remove the borders from a polygon."
    )
    stroke_color = ColorField(
        default="#FFFFFF",
        verbose_name="Color",
        null=True,
        blank=True,
    )
    stroke_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(1),
        verbose_name="Thickness",
        null=True,
        blank=True,
    )
    stroke_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(1.0),
        verbose_name="Transparency",
        null=True,
        blank=True,
    )
    stroke_line_cap = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-linecap#usage_notes.
        max_length=32,
        choices=LineCap.choices,
        default=LineCap.ROUND,
        help_text="The shape of the end of a stroke. Options: butt, round, or square.",
        null=True,
        blank=True,
    )
    stroke_line_join = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-linejoin#usage_context.
        max_length=32,
        choices=LineJoin.choices,
        default=LineJoin.ROUND,
        help_text="The shape used to join two lines. Options: arcs, bevel, miter, miter clip, or round.",
        null=True,
        blank=True,
    )
    stroke_dash_array = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-dasharray#example.
        max_length=32,
        validators=[validate_only_integers_and_whitespace],
        null=True,
        blank=True,
        help_text="The pattern of dashes and gaps for the outline, e.g., '5 5' for 5 pixel long lines "
        + "separated by 5 pixels of whiespace. Only digits and whitespace are allowed (e.g., '12 34 56')",
    )
    stroke_dash_offset = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-dashoffset#example.
        max_length=32,
        null=True,
        blank=True,
        help_text="Offset where the dash pattern starts along the outline path.",
    )

    ########
    # Fill #
    ########
    draw_fill = models.BooleanField(
        help_text="Check this box if you want to fill the polygon.",
        default=True,
    )
    fill_color = ColorField(
        default="#FFFFFF",
        null=True,
        blank=True,
    )
    fill_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(0.8),
        null=True,
        blank=True,
    )
    fill_rule = models.CharField(
        # Unused in the admin form for now.
        max_length=32,
        choices=FillRule.choices,
        null=True,
        blank=True,
    )

    ##########
    # Marker #
    ##########
    draw_marker = models.BooleanField(
        help_text="Check this box if you want to draw the marker icon on each point this style is applied to.",
        default=True,
    )
    marker_icon = models.FileField(
        upload_to="marker_icons/",
        null=True,
        blank=True,
        validators=[FiletypeValidator(valid_names=["SVG", "JPEG", "PNG", "WEBP"])],
        help_text="The image that will appear at each point this style is applied to. Accepts PNG, JPEG, SVG, and WEBP files.",
    )
    is_marker_icon_compressed = models.BooleanField(default=False)
    marker_icon_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(0.8),
        null=True,
        blank=True,
    )
    marker_size = models.DecimalField(
        max_digits=6,  # 6 instead of 5 here to support sizes with triple digits begfore the decimal place, e.g., 101.23. I suppose the decimal place counts as a digit?
        decimal_places=3,
        default=Decimal(22),
        null=True,
        blank=True,
    )
    marker_background_color = ColorField(
        default="#F2F2F2",
        null=True,
        blank=True,
        verbose_name="Background Color",
    )
    marker_background_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(0.8),
        null=True,
        blank=True,
    )

    ##########
    # Circle #
    ##########
    draw_circle = models.BooleanField(
        help_text="Check this box if you want to fill a polygon area with circles instead of a solid color. IMPORTANT: the circles "
        + "are drawn using 'georeferenced units,' meaning that their size is determined by meters on the map, as opposed to pixels on the screen.",
        default=False,
    )
    circle_radius = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(5),
        verbose_name="Radius",
        null=True,
        blank=True,
    )
    circle_stroke_color = ColorField(
        default="#032697",
        verbose_name="Stroke color",
        null=True,
        blank=True,
    )
    circle_stroke_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(1),
        verbose_name="Stroke thickness",
        null=True,
        blank=True,
    )
    circle_stroke_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(1.0),
        verbose_name="Stroke transparency",
        null=True,
        blank=True,
    )
    circle_stroke_line_cap = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-linecap#usage_notes.
        max_length=32,
        choices=LineCap.choices,
        default=LineCap.ROUND,
        help_text="The shape of the end of a stroke. Options: butt, round, or square.",
        null=True,
        blank=True,
    )
    circle_stroke_line_join = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-linejoin#usage_context.
        max_length=32,
        choices=LineJoin.choices,
        default=LineJoin.ROUND,
        help_text="The shape used to join two lines. Options: arcs, bevel, miter, miter clip, or round.",
        null=True,
        blank=True,
    )
    circle_stroke_dash_array = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-dasharray#example.
        max_length=32,
        validators=[validate_only_integers_and_whitespace],
        null=True,
        blank=True,
        help_text="The pattern of dashes and gaps for the outline, e.g., '5 5' for 5 pixel long lines "
        + "separated by 5 pixels of whiespace. Only digits and whitespace are allowed (e.g., '12 34 56')",
    )
    circle_stroke_dash_offset = models.CharField(
        # See Mozilla docs: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/stroke-dashoffset#example.
        max_length=32,
        null=True,
        blank=True,
        help_text="Offset where the dash pattern starts along the outline path.",
    )
    circle_fill_color = ColorField(
        default="#FFFFFF",
        null=True,
        blank=True,
    )
    circle_fill_opacity = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal(0.8),
        null=True,
        blank=True,
    )

    # TODO: Add _hover style and _active style recursive foreign keys.

    def __str__(self):
        return self.name


@receiver(pre_save, sender=Style)
def compress_marker_icon(sender, instance: Style, **kwargs):
    if db_instance := Style.objects.filter(pk=instance.id).first():
        if instance.marker_icon != db_instance.marker_icon:
            # Mark file as needing compression if it has changed at all
            instance.is_marker_icon_compressed = False
    if instance.is_marker_icon_compressed:
        # Skip compression if marker-icon is already compressed.
        return
    if image := instance.marker_icon:
        try:
            compressed = compress_image(image, pixel_width=256)
            # save = False avoids double-saving for efficiency and just
            # assigns the compressed image value to the marker_icon field
            image.save(compressed.name, compressed, save=False)
            instance.is_marker_icon_compressed = True
        except CompressionFailed:
            pass
