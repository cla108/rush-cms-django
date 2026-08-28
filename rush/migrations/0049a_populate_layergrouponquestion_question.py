# Manual migration to populate the question field on LayerGroupOnQuestion
from django.db import migrations


def populate_question_field(apps, schema_editor):
    """
    Populate the question field on LayerGroupOnQuestion by finding the question
    from related LayerOnLayerGroup records (which still have the question field).
    """
    LayerGroupOnQuestion = apps.get_model("rush", "LayerGroupOnQuestion")
    LayerOnLayerGroup = apps.get_model("rush", "LayerOnLayerGroup")

    for layer_group in LayerGroupOnQuestion.objects.all():
        # Find a LayerOnLayerGroup that references this layer group
        layer_on_group = LayerOnLayerGroup.objects.filter(
            layer_group_on_question=layer_group
        ).first()

        if layer_on_group and hasattr(layer_on_group, 'question'):
            layer_group.question = layer_on_group.question
            layer_group.save(update_fields=['question'])
            print(f"Set question for LayerGroupOnQuestion {layer_group.id}")
        else:
            print(f"WARNING: Could not find question for LayerGroupOnQuestion {layer_group.id}")


def reverse_populate(apps, schema_editor):
    """
    Reverse operation - just clear the question field
    """
    LayerGroupOnQuestion = apps.get_model("rush", "LayerGroupOnQuestion")
    LayerGroupOnQuestion.objects.all().update(question=None)


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0049_fix_database_state"),
    ]

    operations = [
        migrations.RunPython(populate_question_field, reverse_populate),
    ]
