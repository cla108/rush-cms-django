"""
Drop the published-state field now that channels (see 0123) carry the same information.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0123_seed_channels_from_published_state"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="initiative",
            name="published_state",
        ),
        migrations.RemoveField(
            model_name="layer",
            name="published_state",
        ),
        migrations.RemoveField(
            model_name="question",
            name="published_state",
        ),
    ]
