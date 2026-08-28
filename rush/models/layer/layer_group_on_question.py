import uuid

from django.db import models
from django.db.models import Max

from rush.models.utils import SummernoteTextCleaner


class LayerGroupOnQuestion(models.Model):
    """
    A group of layers applied to a single question. For example, a question about
    the environmental health might have a "Forests" group, with layers describing
    forest health, flora composition, soil data, etc.
    """

    class Meta:
        ordering = ["display_order"]

    class Behaviour(models.TextChoices):
        """
        Hidden (in the form) group behaviour that lets superusers specify special
        behaviour for a layer-group-on-question.
        """

        DEFAULT = "default"
        ALL_LAYERS = "all_layers"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    group_name = models.CharField(max_length=255)
    group_description = models.TextField(blank=True, help_text="An optional description for the group.")
    group_description_strict_clean = models.BooleanField(default=True)
    question = models.ForeignKey(to="Question", on_delete=models.CASCADE, related_name="layer_groups")
    display_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True, editable=True)

    behaviour = models.CharField(max_length=255, default=Behaviour.DEFAULT, choices=Behaviour.choices)

    def max_display_order(self) -> int:
        """
        The maximum `display_order` currently being used by related layers in this group.
        """
        max_order = self.layers.aggregate(Max("display_order"))["display_order__max"]  # type: ignore
        if not max_order:
            return 0
        return max_order

    def clean(self) -> None:
        self.group_description = SummernoteTextCleaner.clean(self.group_description, strict_clean=self.group_description_strict_clean)

    def __str__(self):
        return self.group_name
