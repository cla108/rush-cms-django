from types import SimpleNamespace

from graphql import GraphQLError
from pytest import mark, raises

from rush.graphql import (
    convert_relative_links_to_absolute,
    request_channels,
    scope_request_to_channels,
)
from rush.models import Channel


def _fake_info() -> SimpleNamespace:
    """
    Stand-in for the graphene ResolveInfo, which only needs to carry a request context here.
    """
    return SimpleNamespace(context=SimpleNamespace())


@mark.django_db
@mark.parametrize(
    "channels_arg, expected",
    [
        # the published channel is served when a request doesn't name any
        (None, [Channel.DEFAULT_VIEW_CHANNEL]),
        ([], [Channel.DEFAULT_VIEW_CHANNEL]),
        # otherwise the named channels are served, in the order they were asked for
        ([Channel.DRAFT_NAME], [Channel.DRAFT_NAME]),
        ([Channel.PUBLISHED_NAME], [Channel.PUBLISHED_NAME]),
        # several channels can be unioned in one request
        (
            [Channel.PUBLISHED_NAME, Channel.DRAFT_NAME],
            [Channel.PUBLISHED_NAME, Channel.DRAFT_NAME],
        ),
        # repeats collapse
        (
            [Channel.DRAFT_NAME, Channel.PUBLISHED_NAME, Channel.DRAFT_NAME],
            [Channel.DRAFT_NAME, Channel.PUBLISHED_NAME],
        ),
    ],
)
def test_scope_request_to_channels(channels_arg: list[str] | None, expected: list[str]):
    info = _fake_info()
    assert [
        channel.name for channel in scope_request_to_channels(info, channels_arg)
    ] == expected
    # nested resolvers must filter by the same channels as the root query they were reached through
    assert [channel.name for channel in request_channels(info)] == expected


@mark.django_db
@mark.parametrize(
    "channels_arg, expected_message",
    [
        (["not-a-channel"], "Unknown channel(s): 'not-a-channel'."),
        # a request fails if any one of the named channels is unknown
        (
            [Channel.PUBLISHED_NAME, "not-a-channel"],
            "Unknown channel(s): 'not-a-channel'.",
        ),
        (["nope", "nada"], "Unknown channel(s): 'nope', 'nada'."),
    ],
)
def test_scope_request_to_unknown_channels_fails(
    channels_arg: list[str], expected_message: str
):
    with raises(
        GraphQLError, match=expected_message.replace("(", r"\(").replace(")", r"\)")
    ):
        scope_request_to_channels(_fake_info(), channels_arg)


@mark.django_db
def test_request_channels_defaults_when_no_root_query_scoped_them():
    assert [channel.name for channel in request_channels(_fake_info())] == [
        Channel.DEFAULT_VIEW_CHANNEL
    ]


def _relative_to_absolute_link_params(
    tag: str, key: str, closing=True
) -> list[tuple[str, str]]:

    def _tagify(link: str):
        if closing == True:
            return f"<{tag} {key}={link}></{tag}>"
        else:
            return f"<{tag} {key}={link}/>"

    return [
        ############ Same as BASE_MEDIA_URL ####################
        (
            # HTTPS image URL remains unchanged
            _tagify('"https://www.kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # HTTP image URL changes to HTTPS
            _tagify('"http://www.kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # protocol agnostic URL changes to HTTPS. See: https://stackoverflow.com/questions/28446314.
            _tagify('"//example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # protocol agnostic URL changes to HTTPS (even when double forward-slash present in url)
            _tagify('"//something//example.png"'),
            _tagify('"https://www.kagi.com/something//example.png"'),
        ),
        (
            # HTTPS is appended if missing
            _tagify('"www.kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # HTTPS and www are appended if missing
            _tagify('"kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # HTTPS, www, and base media url are appended if missing
            _tagify('"example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # HTTPS, www, and base media url are appended if missing (even when resource is prefixed by a
            # forward-slash)
            _tagify('"/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # extra http:// is stripped
            #
            ######
            #
            # (FIXME the extra http:// is added by summernote when a template variable, e.g., {{ URL }} is formatted
            # as a link by an admin user in the editor). Ideally this would be fixed before the data is saved. However, since
            # we can't re-serialize all the map data at this moment without manually re-saving each layer on the admin site, I'm
            # choosing to fix this issue in the data on the way out (via the GraphQL API).
            #
            # This fixme comment can be removed when https://linear.app/naturnd/issue/V3-182/ is completed.
            #
            #########
            _tagify('"http://https://www.kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        (
            # extra https:// is stripped
            #
            ######
            #
            # (FIXME the extra https:// is added by summernote when a template variable, e.g., {{ URL }} is formatted
            # as a link by an admin user in the editor). Ideally this would be fixed before the data is saved. However, since
            # we can't re-serialize all the map data at this moment without manually re-saving each layer on the admin site, I'm
            # choosing to fix this issue in the data on the way out (via the GraphQL API).
            #
            # This fixme comment can be removed when https://linear.app/naturnd/issue/V3-182/ is completed.
            #
            #########
            _tagify('"https://https://www.kagi.com/example.png"'),
            _tagify('"https://www.kagi.com/example.png"'),
        ),
        ############### DIFFERENT DOMAIN ####################
        (
            # HTTPS image URL remains unchanged
            _tagify('"https://www.google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
        (
            # HTTP image URL changes to HTTPS
            _tagify('"http://www.google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
        (
            # HTTPS is appended if missing
            _tagify('"www.google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
        (
            # HTTPS and www are appended if missing
            _tagify('"google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
        (
            # extra https// is stripped
            #
            ######
            #
            # (FIXME the extra https// is added by summernote when a template variable, e.g., {{ URL }} is formatted
            # as a link by an admin user in the editor). Ideally this would be fixed before the data is saved. However, since
            # we can't re-serialize all the map data at this moment without manually re-saving each layer on the admin site, I'm
            # choosing to fix this issue in the data on the way out (via the GraphQL API).
            #
            # This fixme comment can be removed when https://linear.app/naturnd/issue/V3-182/ is completed.
            #
            #########
            _tagify('"http://https://www.google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
        (
            # extra https:// is stripped
            #
            ######
            #
            # (FIXME the extra https:// is added by summernote when a template variable, e.g., {{ URL }} is formatted
            # as a link by an admin user in the editor). Ideally this would be fixed before the data is saved. However, since
            # we can't re-serialize all the map data at this moment without manually re-saving each layer on the admin site, I'm
            # choosing to fix this issue in the data on the way out (via the GraphQL API).
            #
            # This fixme comment can be removed when https://linear.app/naturnd/issue/V3-182/ is completed.
            #
            #########
            _tagify('"https://https://www.google.com/example.png"'),
            _tagify('"https://www.google.com/example.png"'),
        ),
    ]


@mark.django_db
@mark.parametrize(
    "relative, expected",
    [
        *_relative_to_absolute_link_params(tag="img", key="src", closing=False),
        *_relative_to_absolute_link_params(tag="a", key="href", closing=True),
    ],
)
def test_convert_relative_links_to_absolute(relative, expected):
    base_media_url = "https://www.kagi.com/"
    absolute = convert_relative_links_to_absolute(
        relative, base_media_url=base_media_url
    )
    assert expected == absolute
