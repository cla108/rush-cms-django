"""
Seed the "draft" and "published" channels, then tag every existing Question, Layer and Initiative
onto the channel matching its old published-state. The mapping is 1:1, so content that was live
lands on "published" only, and content that was a draft lands on "draft" only.
"""

import uuid

from django.db import migrations

DRAFT = "draft"
PUBLISHED = "published"

CHANNELS = {
    DRAFT: "Work-in-progress content that is not visible on the live website.",
    PUBLISHED: "The content served on the live website.",
}

TAGGED_MODELS = ["Question", "Layer", "Initiative"]


def seed_channels_from_published_state(apps, schema_editor):
    Channel = apps.get_model("rush", "Channel")
    for name, description in CHANNELS.items():
        Channel.objects.get_or_create(
            name=name,
            defaults={
                "id": uuid.uuid4(),
                "description": description,
            },
        )

    channels_by_published_state = {
        name: Channel.objects.get(name=name) for name in CHANNELS
    }
    for model_name in TAGGED_MODELS:
        model = apps.get_model("rush", model_name)
        for instance in model.objects.all():
            channel = channels_by_published_state.get(instance.published_state)
            if channel is None:
                # Unknown published-state values are treated as drafts so that nothing that
                # wasn't already live becomes live by accident.
                channel = channels_by_published_state[DRAFT]
            instance.channels.set([channel])


def unseed_channels_to_published_state(apps, schema_editor):
    Channel = apps.get_model("rush", "Channel")
    for model_name in TAGGED_MODELS:
        model = apps.get_model("rush", model_name)
        for instance in model.objects.all():
            is_published = instance.channels.filter(name=PUBLISHED).exists()
            instance.published_state = PUBLISHED if is_published else DRAFT
            instance.save(update_fields=["published_state"])
            instance.channels.clear()
    Channel.objects.filter(name__in=CHANNELS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rush", "0122_channel_and_channels_on_content"),
    ]

    operations = [
        migrations.RunPython(
            seed_channels_from_published_state,
            reverse_code=unseed_channels_to_published_state,
        ),
    ]
