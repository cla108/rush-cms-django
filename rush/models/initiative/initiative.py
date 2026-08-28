import uuid

from django.core.validators import URLValidator
from django.db import models

from rush.models import PublishedState
from rush.models.utils import SummernoteTextCleaner


class Initiative(models.Model):
    """
    A project, group, or resource relevant to answering one or more questions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    link = models.CharField(max_length=2048, validators=[URLValidator()])
    image = models.ImageField(upload_to="initiative_images/", null=True, blank=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    content_strict_clean = models.BooleanField(default=True)
    tags = models.ManyToManyField(to="InitiativeTag", related_name="initiatives")
    published_state = models.CharField(
        max_length=255,
        choices=PublishedState.choices,
        help_text="WARNING: Changing this to 'Published' will make this Initiative appear on the website immediately.",
    )

    def clean(self) -> None:
        self.content = SummernoteTextCleaner.clean(self.content, strict_clean=self.content_strict_clean)

    def __str__(self):
        return self.title
