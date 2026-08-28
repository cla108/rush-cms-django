from django.core.management import call_command
from django.db import migrations


def reorder_models(apps, schema_editor):
    """
    Reorder display_order fields for sortable models. This ensures sequential ordering starting
    from 0 and is required for django-admin-sortable2 to function as an initial migration.
    """
    # Get models from apps registry (historical versions at this migration point)
    Question = apps.get_model("rush", "Question")
    QuestionTab = apps.get_model("rush", "QuestionTab")
    LayerOnLayerGroup = apps.get_model("rush", "LayerOnLayerGroup")
    LayerGroupOnQuestion = apps.get_model("rush", "LayerGroupOnQuestion")

    models_to_reorder = [
        (Question, "Question"),
        (QuestionTab, "QuestionTab"),
        (LayerOnLayerGroup, "LayerOnLayerGroup"),
        (LayerGroupOnQuestion, "LayerGroupOnQuestion"),
    ]

    for model_class, model_name in models_to_reorder:
        try:
            # Manually reorder using the historical model
            instances = list(model_class.objects.order_by("display_order"))
            for index, instance in enumerate(instances):
                if instance.display_order != index:
                    instance.display_order = index
                    instance.save(update_fields=["display_order"])
            print(f"Successfully reordered model \"rush.{model_name}\"")
        except Exception as e:
            print(f"ERROR: Could not reorder rush.{model_name}: {e}")


def reverse_reorder(apps, schema_editor):
    """
    Reverse operation - does nothing as reordering is non-destructive.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0052_alter_layergrouponquestion_group_description"),
    ]

    operations = [
        migrations.RunPython(reorder_models, reverse_reorder),
    ]
