import pytest
from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.urls import reverse

from rush.admin.filters import ChannelFilter
from rush.admin.initiative import InitiativeAdmin
from rush.models import Channel, Initiative

from ..models.helpers import create_test_initiative


@pytest.fixture
def admin_client(client):
    User.objects.create_superuser(username="editor", email="editor@example.com", password="password")
    client.login(username="editor", password="password")
    return client


@pytest.mark.django_db
def test_add_form_starts_on_the_default_create_channel(admin_client):
    """
    The "add" form should pre-select the create channel so authors can see where content lands.
    """
    response = admin_client.get(reverse("admin:rush_initiative_add"))
    assert response.status_code == 200
    assert response.context["adminform"].form.initial["channels"] == [Channel.objects.draft().pk]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "posted_channels, expected",
    [
        # content saved without any channel falls back to the create channel
        ([], [Channel.DRAFT_NAME]),
        # otherwise the author's choice is respected, even when that is the live website
        ([Channel.PUBLISHED_NAME], [Channel.PUBLISHED_NAME]),
        ([Channel.DRAFT_NAME, Channel.PUBLISHED_NAME], [Channel.DRAFT_NAME, Channel.PUBLISHED_NAME]),
    ],
)
def test_saving_content_tags_it_onto_channels(admin_client, posted_channels: list[str], expected: list[str]):
    response = admin_client.post(
        reverse("admin:rush_initiative_add"),
        {
            "title": "A new initiative",
            "link": "https://example-initiative.com",
            "content": "<p>Hello!</p>",
            "content_strict_clean": "on",
            "tags": [],
            "channels": [str(Channel.objects.get(name=name).pk) for name in posted_channels],
        },
    )
    assert response.status_code == 302, response.context["adminform"].form.errors
    initiative = Initiative.objects.get(title="A new initiative")
    assert sorted(channel.name for channel in initiative.channels.all()) == sorted(expected)


@pytest.mark.django_db
def test_channel_filter_shows_every_channel_by_default(rf):
    """
    An unfiltered changelist should show content from every channel, so that editors don't lose
    track of anything that isn't on the channel they happen to be looking at.
    """
    drafted = create_test_initiative(title="Drafted", channels=[Channel.objects.draft()])
    live = create_test_initiative(title="Live", channels=[Channel.objects.published()])

    model_admin = InitiativeAdmin(Initiative, django_admin.site)

    def filtered(value: str | None) -> set[str]:
        request = rf.get("/", {} if value is None else {"channel": value})
        channel_filter = ChannelFilter(request, dict(request.GET.lists()), Initiative, model_admin)
        queryset = channel_filter.queryset(request, Initiative.objects.all())
        return {initiative.title for initiative in queryset}  # type: ignore

    assert filtered(None) == {drafted.title, live.title}
    assert filtered("all") == {drafted.title, live.title}
    assert filtered(Channel.DRAFT_NAME) == {drafted.title}
    assert filtered(Channel.PUBLISHED_NAME) == {live.title}
