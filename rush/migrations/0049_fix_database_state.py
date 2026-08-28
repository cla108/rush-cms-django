# Manual migration to fix database state inconsistency
# The database was manually corrected to match what migration 0048 should have done

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0048_remove_layeronquestion_layer_group_and_more"),
    ]

    operations = [
        # The RenameModel in 0048 renamed LayerGroup to LayerGroupOnQuestion,
        # but LayerGroup never had a question field. We need to add it.
        migrations.AddField(
            model_name="layergrouponquestion",
            name="question",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="rush.question",
                default=None,  # Will be populated in next step
                null=True,  # Allow null temporarily
            ),
        ),
    ]
