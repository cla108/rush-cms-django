import uuid

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from rush.models import PublishedState
from rush.models.utils import CompressionFailed, compress_image
from rush.models.validators import FiletypeValidator


class Question(models.Model):
    """
    A question that ties together one or more map layers into a data-driven narrative.
    """

    class Meta:
        ordering = ["display_order"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to="question_images/",
        null=True,
        blank=True,
        validators=[FiletypeValidator(valid_names=["SVG", "JPEG", "PNG", "WEBP"])],
    )
    is_image_compressed = models.BooleanField(default=False)
    initiatives = models.ManyToManyField(to="Initiative", blank=True)
    slug = models.SlugField(max_length=255, unique=True)
    sash = models.ForeignKey(
        to="QuestionSash",
        # Sash should be set to null if deleted.
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="A decorative sash that can be added to questions for flair.",
        related_name="questions",
    )

    region = models.ForeignKey(
        to="Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary region where this question appears",
        related_name="questions",
    )
    display_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True, editable=True)
    published_state = models.CharField(
        max_length=255,
        choices=PublishedState.choices,
        help_text="WARNING: Changing this to 'Published' will make this Question appear on the website immediately.",
    )

    def __str__(self):
        return self.title


@receiver(pre_save, sender=Question)
def compress_image_pre_save(sender, instance: Question, **kwargs):
    if db_instance := Question.objects.filter(pk=instance.id).first():
        if instance.image != db_instance.image:
            # Mark file as needing compression if it has changed at all
            instance.is_image_compressed = False
    if instance.is_image_compressed:
        # Skip compression if image is already compressed.
        return
    if image := instance.image:
        try:
            compressed = compress_image(image, pixel_width=512)
            # save = False avoids double-saving for efficiency and just
            # assigns the compressed image value to the marker_icon field
            image.save(compressed.name, compressed, save=False)
            instance.is_image_compressed = True
        except CompressionFailed:
            pass
