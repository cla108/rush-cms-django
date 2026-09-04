"""
Add the Channel model and tag Questions, Layers and Initiatives onto channels.
"""


import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0121_clean_initiative_content_again"),
    ]

    operations = [
        migrations.CreateModel(
            name="Channel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="The channel name used by API clients, e.g., '?channel=published'.",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="An optional note about who this channel is for.",
                    ),
                ),
                (
                    "is_private",
                    models.BooleanField(
                        default=False,
                        help_text="Private channels will eventually require a viewer to log in before their content is served.",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="initiative",
            name="channels",
            field=models.ManyToManyField(
                blank=True,
                help_text="WARNING: Tagging this Initiative onto the 'published' channel will make it appear on the live website immediately. Leave this empty and the Initiative will be tagged onto the default channel on save.",
                related_name="initiatives",
                to="rush.channel",
            ),
        ),
        migrations.AddField(
            model_name="layer",
            name="channels",
            field=models.ManyToManyField(
                blank=True,
                help_text="WARNING: Tagging this Layer onto the 'published' channel will make it appear on the live website immediately. Leave this empty and the Layer will be tagged onto the default channel on save.",
                related_name="layers",
                to="rush.channel",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="channels",
            field=models.ManyToManyField(
                blank=True,
                help_text="WARNING: Tagging this Question onto the 'published' channel will make it appear on the live website immediately. Leave this empty and the Question will be tagged onto the default channel on save.",
                related_name="questions",
                to="rush.channel",
            ),
        ),
    ]
