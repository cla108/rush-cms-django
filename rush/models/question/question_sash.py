import uuid

from colorfield.fields import ColorField
from django.db import models


class QuestionSash(models.Model):
    """
    A decorative sash that can be added to questions for flair.
    """

    class Meta:
        verbose_name_plural = "Question Sashes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, null=False)
    text = models.CharField(max_length=24)
    text_color = ColorField()
    background_color = ColorField()

    def __str__(self):
        return self.text

    def get_html_preview(self) -> str:
        return f"""
            <p style='
                color: {self.text_color};
                background-color: {self.background_color};
                font-size: 0.75rem;
                text-transform: uppercase;
                border-radius: 0.125rem;
                font-family: "Bitter Variable", serif;
                width: fit-content;
                padding-left: 0.25rem;
                padding-right: 0.25rem;
                font-weight: 700;
            '>
                {self.text}
            </p>
            """
