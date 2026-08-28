import uuid

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from rush.models import MimeType
from rush.models.utils import CompressionFailed, compress_image
from rush.models.validators import FiletypeValidator


class Icon(models.Model):
    """
    An SVG, PNG, WEBP, or JPEG icon.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    mime_type = models.ForeignKey(to=MimeType, on_delete=models.DO_NOTHING)
    file = models.FileField(
        upload_to="icons/",
        validators=[FiletypeValidator(valid_names=["PNG", "JPEG", "SVG", "WEBP"])],
    )
    is_file_compressed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


@receiver(pre_save, sender=Icon)
def inject_mime_type(sender, instance: Icon, **kwargs):
    existing_icon = Icon.objects.filter(pk=instance.id).first()
    if existing_icon is None or existing_icon.mime_type is None:
        instance.mime_type = MimeType.guess(instance.file.name).guessed


@receiver(pre_save, sender=Icon)
def compress_icon_file(sender, instance: Icon, **kwargs):
    if db_instance := Icon.objects.filter(pk=instance.id).first():
        if instance.file != db_instance.file:
            # Mark file as needing compression if it has changed at all
            instance.is_file_compressed = False
    if instance.is_file_compressed:
        # Skip compression if image is already compressed.
        return
    if image := instance.file:
        try:
            compressed = compress_image(image, pixel_width=512)
            # save = False avoids double-saving for efficiency and just
            # assigns the compressed image value to the marker_icon field
            image.save(compressed.name, compressed, save=False)
            instance.is_file_compressed = True
        except CompressionFailed:
            pass
