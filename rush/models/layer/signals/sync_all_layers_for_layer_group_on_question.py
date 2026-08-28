"""
This module contains signals that perform "sync" operations on layer-groups when
they are set-up to have the ALL_LAYERS behaviour. See the requirements below:
    1.  When a layer-group is created or updated to have the ALL_LAYERS behaviour,
        all existing layers are added (not active by default) to the group.
    2.  When a new layer is created, it is automatically added to any layer-groups
        that have the ALL_LAYERS behaviour.
    3.  We don't need a signal for when layers get deleted, because layer-on-layer-groups
        will automatically get deleted via CASCADE on their layer foreign-keys.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from rush.models.layer import Layer, LayerGroupOnQuestion, LayerOnLayerGroup


@receiver(post_save, sender=LayerGroupOnQuestion)
def add_all_layers_when_all_layers_behaviour_enabled(sender, instance, created, **kwargs):
    if not isinstance(instance, LayerGroupOnQuestion):
        raise ValueError(f"Expected {instance} to be a {LayerGroupOnQuestion.__class__}.")
    if instance.behaviour != LayerGroupOnQuestion.Behaviour.ALL_LAYERS:
        return None

    # Only fetch layer IDs to avoid loading massive serialized_leaflet_json and map_data fields
    existing_layer_ids = set(instance.layers.values_list("layer_id", flat=True))  # type: ignore
    all_layer_ids = Layer.objects.values_list("id", flat=True)

    for display_order, layer_id in enumerate(all_layer_ids):
        if layer_id in existing_layer_ids:
            # skip if layer already in group
            continue
        LayerOnLayerGroup.objects.create(
            layer_id=layer_id,
            layer_group_on_question=instance,
            display_order=display_order,
        )


def _all_layers_layer_order(layer_on_layer_group: LayerOnLayerGroup) -> str:
    """
    Sort by layer provider_state, and then alphabetically.
    """
    return f'{str(layer_on_layer_group.layer.map_data.provider_state)}{layer_on_layer_group.layer.name}'


@receiver(post_save, sender=Layer)
def add_layer_when_layer_created(sender, instance, created, **kwargs):
    if not isinstance(instance, Layer):
        raise ValueError(f"Expected {instance} to be a {Layer.__class__}.")
    if not created:
        # Skip if layer is being updated rather than created
        return None

    # Only fetch IDs to avoid loading all layer group data
    groups = LayerGroupOnQuestion.objects.filter(behaviour=LayerGroupOnQuestion.Behaviour.ALL_LAYERS).only("id")
    for group in groups:
        if group.layers.filter(layer_id=instance.id).exists():  # type: ignore
            # skip if layer already in group
            continue
        LayerOnLayerGroup.objects.create(
            layer_id=instance.id,
            layer_group_on_question=group,
            display_order=group.max_display_order() + 1,
        )
        # order layer-on-layer-groups in the layer group alphabetically
        display_order = 0
        for layer_on_layer_group in sorted(group.layers.all(), key=_all_layers_layer_order):  # type: ignore
            layer_on_layer_group.display_order = display_order
            layer_on_layer_group.full_clean()
            layer_on_layer_group.save()
            display_order += 1
