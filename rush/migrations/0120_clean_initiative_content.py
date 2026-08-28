"""
Remove copy-paste structural junk (divs, etc.) from Initiative.content.

Preserves Summernote-generated content: <p> tags with their styles/attributes,
inline formatting, lists, headings, and images. Block elements from external
paste (div, section, table, etc.) are unwrapped or converted to <p>.
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
        ("rush", "0119_stylesonlayer_popup_strict_clean"),
    ]

    operations = [
        migrations.RunPython(clean_initiative_content, reverse_code=migrations.RunPython.noop),
    ]
