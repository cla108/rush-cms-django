from pytest import mark

from rush.graphql import PublishedStateGraphQLView, convert_relative_links_to_absolute
from rush.models import PublishedState


@mark.parametrize(
    "params, expected",
    [
        # PUBLISHED is the default query visibility when unspecified
        (None, [PublishedState.PUBLISHED]),
        ({}, [PublishedState.PUBLISHED]),
        ({"visibility": "foobar"}, [PublishedState.PUBLISHED]),
        ({"foo": "barbaz"}, [PublishedState.PUBLISHED]),
        # the published-state returned corresponds to the visibility param, when it matches a published-state value
        ({"visibility": "published"}, [PublishedState.PUBLISHED]),
        ({"visibility": "draft"}, [PublishedState.DRAFT]),
        ({"visibility": "all"}, [PublishedState.PUBLISHED, PublishedState.DRAFT]),
    ],
)
def test_get_published_state_from_request_params(params: dict | None, expected: PublishedState):
    assert PublishedStateGraphQLView.get_published_state_from_request_params(params) == expected


def _relative_to_absolute_link_params(tag: str, key: str, closing=True) -> list[tuple[str, str]]:

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
    absolute = convert_relative_links_to_absolute(relative, base_media_url=base_media_url)
    assert expected == absolute
