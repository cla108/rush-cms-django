import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from rush.models import Layer, LayerGroupOnQuestion, LayerOnLayerGroup, MapData

from .helpers import (
    create_test_layer,
    create_test_layer_group,
    create_test_map_data,
    create_test_question,
)


def _all_layers_group() -> LayerGroupOnQuestion:
    question = create_test_question(layer_groups=[])
    return create_test_layer_group(
        question=question,
        layers_on_layer_group=lambda group: [],
        behaviour=LayerGroupOnQuestion.Behaviour.ALL_LAYERS,
    )


def _ordered_layer_names(group: LayerGroupOnQuestion) -> list[str]:
    return [
        layer_on_layer_group.layer.name
        for layer_on_layer_group in LayerOnLayerGroup.objects.filter(
            layer_group_on_question=group
        ).order_by("display_order")
    ]


def _queries_to_add_one_layer(map_data: MapData, name: str) -> int:
    """
    The number of queries a single layer creation costs, signals included.
    """
    with CaptureQueriesContext(connection) as captured:
        Layer.objects.create(name=name, description="d", map_data=map_data)
    return len(captured.captured_queries)


@pytest.mark.django_db
def test_adding_a_layer_orders_an_all_layers_group_by_provider_state_then_name():
    """
    Layers in an ALL_LAYERS group are ordered by their map-data's provider-state, then by name.
    """
    group = _all_layers_group()
    geojson = create_test_map_data(
        name="GeoJSON data", provider_state=MapData.ProviderState.GEOJSON
    )
    geotiff = create_test_map_data(
        name="GeoTIFF data", provider_state=MapData.ProviderState.GEOTIFF
    )

    create_test_layer(name="Zebras", map_data=geojson)
    create_test_layer(name="Apples", map_data=geotiff)
    create_test_layer(name="Bananas", map_data=geojson)

    assert _ordered_layer_names(group) == ["Bananas", "Zebras", "Apples"]


@pytest.mark.django_db
def test_adding_a_layer_does_not_query_per_layer_already_in_an_all_layers_group():
    """
    Ordering an ALL_LAYERS group must not fetch each layer (and its map-data) one row at a time:
    those rows drag along huge JSON fields, and the resulting N+1 was enough to take the
    admin-site down when a new layer was added. Adding a layer to a big group should therefore
    cost exactly as many queries as adding one to a small group.
    """
    group = _all_layers_group()
    map_data = create_test_map_data(name="Shared map data")

    for index in range(2):
        Layer.objects.create(
            name=f"Small group layer {index}", description="d", map_data=map_data
        )
    small_group_queries = _queries_to_add_one_layer(
        map_data, name="Added to a small group"
    )

    for index in range(20):
        Layer.objects.create(
            name=f"Big group layer {index}", description="d", map_data=map_data
        )
    big_group_queries = _queries_to_add_one_layer(map_data, name="Added to a big group")

    assert LayerOnLayerGroup.objects.filter(layer_group_on_question=group).count() == 24
    assert big_group_queries == small_group_queries
