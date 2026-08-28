import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from rush.models.layer import Layer
from rush.models.map_data import MapData

# Import the migration module (can't import normally because it starts with a number...)
migration_module = importlib.import_module("rush.migrations.0035_migrate_domain_url_in_serialized_leaflet_json")
populate_new_domain = migration_module.populate_new_domain


@pytest.mark.django_db
@pytest.mark.parametrize(
    "before_json, after_json",
    [
        (
            {"url": "https://whatstherush.earth/media/image1.png"},
            {"url": "https://admin.whatstherush.earth/media/image1.png"},
        ),
        (
            # Should not change if already correct
            {"url": "https://admin.whatstherush.earth/media/image1.png"},
            {"url": "https://admin.whatstherush.earth/media/image1.png"},
        ),
        (
            # Should not change external urls
            {"url": "https://example.com/media/image1.png"},
            {"url": "https://example.com/media/image1.png"},
        ),
    ],
)
def test_populate_new_domain(before_json, after_json):
    """
    Test that the migration function correctly updates domain URLs in serialized_leaflet_json.
    """
    map_data = MapData.objects.create(name="Test MapData", provider_state=MapData.ProviderState.GEOJSON)
    layer = Layer.objects.create(
        name="Test Layer",
        description="A test layer",
        map_data=map_data,
        serialized_leaflet_json=before_json,
    )
    executor = MigrationExecutor(connection)
    apps = executor.loader.project_state([("rush", "0035_migrate_domain_url_in_serialized_leaflet_json")]).apps
    populate_new_domain(apps, None)
    layer.refresh_from_db()
    assert layer.serialized_leaflet_json == after_json
