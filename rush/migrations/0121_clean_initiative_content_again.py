"""
Re-run Initiative.content cleaning now that <span> tags are also stripped.
"""

from django.db import migrations


def clean_initiative_content(apps, schema_editor):
    from rush.models.utils import strip_foreign_blocks

    Initiative = apps.get_model("rush", "Initiative")
    for initiative in Initiative.objects.all():
        if initiative.content:
            initiative.content = strip_foreign_blocks(initiative.content)
            initiative.save(update_fields=["content"])


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0120_clean_initiative_content"),
    ]

    operations = [
        migrations.RunPython(clean_initiative_content, reverse_code=migrations.RunPython.noop),
    ]
