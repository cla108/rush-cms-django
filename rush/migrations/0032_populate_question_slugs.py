"""
Populate Question.slug for existing records.

This migration will iterate over all Question objects and call save() to
trigger the model's slug generation logic when slug is empty.

It is safe to run multiple times; existing slugs are left intact.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import migrations
from django.db.models import QuerySet
from django.utils.text import slugify

if TYPE_CHECKING:
    from rush.models.question import Question


def populate_slugs(apps, schema_editor):
    QuestionModel: Question = apps.get_model("rush", "Question")
    questions: QuerySet[Question] = QuestionModel.objects.all()
    for question in questions:
        if not question.slug:
            question.slug = slugify(question.title)
            try:
                question.full_clean()
            except ValidationError as e:
                print(f"WARNING: Duplicate slug found on question '{question.id}', generating a random slug...", e)
                question.slug = f"{question.slug}{uuid4().hex}"
            question.save()


def populate_slugs_historical(apps, schema_editor):
    HistoricalQuestionModel: Question = apps.get_model("rush", "HistoricalQuestion")
    questions: QuerySet[Question] = HistoricalQuestionModel.objects.all()
    for question in questions:
        if not question.slug:
            question.slug = slugify(question.title)
            try:
                question.full_clean()
            except ValidationError as e:
                print(
                    f"WARNING: Duplicate slug found on historical question '{question.id}', generating a random slug...",
                    e,
                )
                question.slug = f"{question.slug}{uuid4().hex}"
            question.save()


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0031_historicalquestion_slug_question_slug"),
    ]

    operations = [
        migrations.RunPython(populate_slugs, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(populate_slugs_historical, reverse_code=migrations.RunPython.noop),
    ]
