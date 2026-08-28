# Manual migration to fix incorrect foreign key constraint
# The old constraint points layer_group_on_question_id to rush_question instead of rush_layergrouponquestion

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0050_remove_layeronlayergroup_question_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Drop the incorrect foreign key constraint
                'ALTER TABLE rush_layeronlayergroup DROP CONSTRAINT IF EXISTS rush_layeronquestion_question_id_4b419a44_fk_rush_question_id;',
                # Delete orphaned LayerOnLayerGroup records that reference non-existent LayerGroupOnQuestion records
                '''DELETE FROM rush_layeronlayergroup
                   WHERE NOT EXISTS (
                       SELECT 1 FROM rush_layergrouponquestion
                       WHERE rush_layergrouponquestion.id = rush_layeronlayergroup.layer_group_on_question_id
                   );''',
                # Add the correct foreign key constraint
                'ALTER TABLE rush_layeronlayergroup ADD CONSTRAINT rush_layeronlayergroup_layer_group_on_question_fk FOREIGN KEY (layer_group_on_question_id) REFERENCES rush_layergrouponquestion(id) DEFERRABLE INITIALLY DEFERRED;',
            ],
            reverse_sql=[
                # Reverse: drop the correct constraint
                'ALTER TABLE rush_layeronlayergroup DROP CONSTRAINT IF EXISTS rush_layeronlayergroup_layer_group_on_question_fk;',
                # Note: We can't restore deleted orphaned records
                # Reverse: restore the old (incorrect) constraint
                'ALTER TABLE rush_layeronlayergroup ADD CONSTRAINT rush_layeronquestion_question_id_4b419a44_fk_rush_question_id FOREIGN KEY (layer_group_on_question_id) REFERENCES rush_question(id) DEFERRABLE INITIALLY DEFERRED;',
            ],
        ),
    ]
