import uuid

from django.core.exceptions import ValidationError
from django.db import models


class ChannelManager(models.Manager):

    def default_create_channel(self) -> "Channel":
        """
        The channel new content is tagged onto when its author doesn't pick one.
        """
        return self.get(name=Channel.DEFAULT_CREATE_CHANNEL)

    def default_view_channel(self) -> "Channel":
        """
        The channel content is served from when a request doesn't name one.
        """
        return self.get(name=Channel.DEFAULT_VIEW_CHANNEL)

    def draft(self) -> "Channel":
        """
        The channel unfinished content lives on.
        """
        return self.get(name=Channel.DRAFT_NAME)

    def published(self) -> "Channel":
        """
        The channel the live website is served from.
        """
        return self.get(name=Channel.PUBLISHED_NAME)


class Channel(models.Model):
    """
    A named "slice" of the site's content. Content is tagged onto zero or more channels, and every
    API request is scoped to one or more of them, so the same database can serve the live site, an
    in-progress draft, and any number of one-off channels (a partner preview, a conference demo,
    etc.) side by side.
    """

    # Channels that are always expected to exist. See the 0123 data migration.
    # NOTE: DO NOT EDIT THESE NAMES.
    DRAFT_NAME = "draft"
    PUBLISHED_NAME = "published"

    # Creating and viewing have different defaults on purpose: new content should start out of
    # sight, while an API request that doesn't name a channel should get the live website.
    DEFAULT_CREATE_CHANNEL = DRAFT_NAME
    DEFAULT_VIEW_CHANNEL = PUBLISHED_NAME

    UNDELETABLE_NAMES = (DRAFT_NAME, PUBLISHED_NAME)

    class Meta:
        ordering = ["name"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="The channel name used by API clients, e.g., '?channel=published'.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="An optional note about who this channel is for.",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Private channels will eventually require a viewer to log in before their content is served.",
    )

    objects: ChannelManager = ChannelManager()  # type: ignore

    def delete(self, using=None, keep_parents=False) -> tuple[int, dict[str, int]]:
        # The draft and published channels are relied upon by the admin-site and the duplicators.
        if self.name in self.UNDELETABLE_NAMES:
            raise ValidationError(f"Deleting the '{self.name}' channel is not allowed.")
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name
