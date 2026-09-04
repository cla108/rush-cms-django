"""
Drop the unused Channel.is_private flag.
"""


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0124_remove_published_state"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="channel",
            name="is_private",
        ),
    ]
