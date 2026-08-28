import uuid

from django.core.exceptions import ValidationError
from django.db import models

from rush.models.layer.layer import Layer
from rush.models.layer.layer_group_on_question import LayerGroupOnQuestion
from rush.models.question.question import Question


class LayerOnLayerGroup(models.Model):
    """
    A layer on a layer group, which is then applied to a question. This model
    is one of the two models that link Layer --> Question. It goes as follows:
    `Layer <-- LayerOnLayerGroup --> LayerGroupOnQuestion --> Question`
    """

    class Meta:
        ordering = ["display_order"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    layer = models.ForeignKey(to="Layer", on_delete=models.CASCADE)
    layer_group_on_question = models.ForeignKey(
        to="LayerGroupOnQuestion",
        on_delete=models.CASCADE,
        related_name="layers",
    )
    active_by_default = models.BooleanField(
        default=False,
        help_text="Whether the layer is active by default when a new question is loaded.",
    )
    display_order = models.PositiveIntegerField(default=0, blank=False, null=False, db_index=True, editable=True)

    def delete(self, using=None, keep_parents=False):
        self._prevent_delete_from_all_layers_group()
        return super().delete(using, keep_parents)

    def _prevent_delete_from_all_layers_group(self) -> None:
        """
        It shouldn't be possible to delete a layer from a layer group with the ALL_LAYERS behaviour.
        """
        from rush.models.layer.layer_group_on_question import LayerGroupOnQuestion

        if self.layer_group_on_question.behaviour == LayerGroupOnQuestion.Behaviour.ALL_LAYERS:
            raise ValidationError(
                "Cannot delete {} from {} because the group is set to contain all layers.".format(
                    self,
                    self.layer_group_on_question,
                )
            )

    def __str__(self) -> str:
        # Being careful not to access any more related data than we absolutely need here...
        related_layer = Layer.objects.only("name").filter(id=self.layer_id).first()  # type: ignore
        related_lgoq = LayerGroupOnQuestion.objects.only("question__id").filter(id=self.layer_group_on_question_id).first()  # type: ignore
        related_question = Question.objects.only("title").filter(id=related_lgoq.question_id).first()  # type: ignore
        return "{} on {}".format(
            related_layer.name if related_layer else "Deleted Layer",
            related_question.title if related_question else "Deleted LayerGroupOnQuestion or Question",
        )
