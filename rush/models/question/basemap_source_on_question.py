import uuid

from django.core.exceptions import ValidationError
from django.db import models


class BasemapSourceOnQuestion(models.Model):
    """
    Through table for adding multiple basemap-sources on a single Question with the ability to
    reuse basemap-sources on other questions.
    """

    class Meta:
        verbose_name = "Basemap"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    basemap_source = models.ForeignKey("BasemapSource", on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE, related_name="basemaps")
    is_default_for_question = models.BooleanField(default=False)

    def clean(self) -> None:
        # Check to make sure no other basemap-source-on-question is marked
        # as the default for this question (we can't have two defaults!)
        if (
            BasemapSourceOnQuestion.objects.filter(question=self.question, is_default_for_question=True)
            .exclude(id=self.id)
            .exists()
        ):
            raise ValidationError("There can only be one default Basemap on a Question!")
        return super().clean()
