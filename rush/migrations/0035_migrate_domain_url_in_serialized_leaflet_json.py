"""
Custom Python migration for changing the Domain used for media URLs inside
the alread-saved serializedLeafletJSON on the admin site.
"""

import json
from typing import TYPE_CHECKING

from django.db import migrations
from django.db.models import QuerySet

if TYPE_CHECKING:
    from rush.models.layer import Layer


def populate_new_domain(apps, schema_editor):
    LayerModel: Layer = apps.get_model("rush", "Layer")
    all_layers: QuerySet[Layer] = LayerModel.objects.all()
    domain_from = "https://whatstherush.earth"
    domain_to = "https://admin.whatstherush.earth"
    for layer in all_layers:
        try:
            print(
                "\nMigrating <Layer: {}, {}> serializedLeafletJson's media domain from {} -> {}...".format(
                    layer.name,
                    layer.id,
                    domain_from,
                    domain_to,
                ),
                end="",
            )
            # Convert to JSON string, replace domain, then parse back to dict
            json_str = json.dumps(layer.serialized_leaflet_json)
            updated_json_str = json_str.replace(domain_from, domain_to)
            layer.serialized_leaflet_json = json.loads(updated_json_str)
            layer.full_clean()
            layer.save()
            print("Done!")
        except Exception as e:
            print(f"Something went wrong while trying to migrate layer: {layer}!", e)


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0034_merge_20251010_0122"),
    ]

    operations = [
        migrations.RunPython(populate_new_domain, reverse_code=migrations.RunPython.noop),
    ]
