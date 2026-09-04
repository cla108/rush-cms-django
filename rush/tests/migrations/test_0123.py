import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = "0122_channel_and_channels_on_content"
AFTER = "0124_remove_published_state"


def _migrate_to(target: str):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([("rush", target)])
    executor.loader.build_graph()
    return executor.loader.project_state([("rush", target)]).apps


@pytest.fixture
def migrated_back_to_0122():
    """
    Roll the test database back to just before channels were seeded, then put it back the way it
    was found so the rest of the suite still runs against the latest schema.
    """
    try:
        yield _migrate_to(BEFORE)
    finally:
        _migrate_to(AFTER)


@pytest.mark.django_db(transaction=True)
def test_0123_tags_content_onto_the_channel_matching_its_published_state(migrated_back_to_0122):
    """
    Existing content should be tagged 1:1 onto the channel named after its old published-state.
    """
    apps = migrated_back_to_0122
    MapData = apps.get_model("rush", "MapData")
    Layer = apps.get_model("rush", "Layer")

    map_data = MapData.objects.create(name="Test MapData", provider_state="geojson")
    published_layer = Layer.objects.create(
        name="Published layer",
        description="A published layer",
        map_data=map_data,
        published_state="published",
    )
    draft_layer = Layer.objects.create(
        name="Draft layer",
        description="A draft layer",
        map_data=map_data,
        published_state="draft",
    )

    _migrate_to(AFTER)

    from rush.models import Channel, Layer as CurrentLayer

    assert set(Channel.objects.values_list("name", flat=True)) == {Channel.DRAFT_NAME, Channel.PUBLISHED_NAME}
    assert [c.name for c in CurrentLayer.objects.get(pk=published_layer.pk).channels.all()] == [
        Channel.PUBLISHED_NAME
    ]
    assert [c.name for c in CurrentLayer.objects.get(pk=draft_layer.pk).channels.all()] == [Channel.DRAFT_NAME]
