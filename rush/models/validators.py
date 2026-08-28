import re
from typing import List

from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile

from rush.models import MimeType

class FiletypeValidator:
    """
    Args:
        valid_names: List of human-readable mimetype names that are allowed.
        invalid_names: List of human-readable mimetype names that are not allowed.
    """

    def __init__(
        self,
        valid_names: List[str] | None = None,
        invalid_names: List[str] | None = None,
    ):
        self.valid_names = valid_names
        self.invalid_names = invalid_names

    def __call__(self, file: FieldFile):
        # Resolve names to MimeType instances at runtime
        valid_types = None
        invalid_types = None

        if self.valid_names:
            valid_types = [MimeType.by_name(name) for name in self.valid_names]

        if self.invalid_names:
            invalid_types = [MimeType.by_name(name) for name in self.invalid_names]

        # Use existing validation logic
        MimeType.guess(file.name).validate(valid_types, invalid_types)

    def __eq__(self, other):
        return (
            isinstance(other, FiletypeValidator)
            and self.valid_names == other.valid_names
            and self.invalid_names == other.invalid_names
        )

    def deconstruct(self):
        """
        Required for migration serialization.
        """
        return (
            "rush.models.validators.FiletypeValidator",
            [],
            {"valid_names": self.valid_names, "invalid_names": self.invalid_names},
        )


def validate_only_integers_and_whitespace(value):
    """
    Validates that the value contains only integers and whitespace.
    Examples of valid values: "1", "123", "12 34 56", " 7  8 9 "
    """
    if not re.fullmatch(r"[0-9\s]*", value):
        raise ValidationError("This field must contain only digits and whitespace.")


OGM_MAP_EXPLORE_RE = re.compile(r"^https://greenmap\.org/explore/maps/(?P<id>[0-9A-Za-z-]+)/?$")
OGM_MAP_BROWSE_RE = re.compile(r"^https://greenmap\.org/browse/maps/(?P<id>[0-9A-Za-z-]+)/map-view/?$")
OGM_CAMPAIGN_RE = re.compile(r"^https://greenmap\.org/explore/survey/(?P<id>[0-9A-Za-z-]+)/?$")


def validate_ogm_map_link(value: str) -> None:
    """
    Validate that the string looks like an OpenGreenMaps map-link.
    i.e., one of:
        https://greenmap.org/explore/maps/<uuid>
        https://greenmap.org/browse/maps/<uuid>/map-view
    """

    if not OGM_MAP_EXPLORE_RE.match(value) and not OGM_MAP_BROWSE_RE.match(value):
        raise ValidationError(
            "Invalid OpenGreenMap map link. It should look like {}.".format(
                " or ".join(
                    [
                        '"https://greenmap.org/explore/maps/<random-letters-and-numbers>"',
                        '"https://greenmap.org/browse/maps/<random-letters-and-numbers>/map-view"',
                    ]
                )
            )
        )


def validate_ogm_campaign_link(value: str) -> None:
    """
    Validate that the string looks like an OpenGreenMaps map-link.
    i.e., in the format:
        https://greenmap.org/explore/survey/<uuid>
    """
    if not OGM_CAMPAIGN_RE.match(value):
        raise ValidationError(
            "Invalid OpenGreenMap campaign link. It should look like {}.".format(
                " or ".join(
                    [
                        '"https://greenmap.org/explore/survey/<random-letters-and-numbers>"',
                    ]
                )
            )
        )

ARCGIS_FEATURE_SERVER_RE = re.compile(
    r"^https:\/\/services\d+\.arcgis\.com\/[A-Za-z0-9]+\/ArcGIS\/rest\/services\/[A-Za-z0-9_]+\/FeatureServer\/\d+$"
)

def validate_arcgis_feature_server_link(value: str) -> None:
    """
    Validate that the string looks like a valid ArcGIS FeatureServer URL.
    i.e., in the format:
        https://servicesX.arcgis.com/<org_id>/ArcGIS/rest/services/<service_name>/FeatureServer/<layer_id>
    """

    if not ARCGIS_FEATURE_SERVER_RE.match(value):
        raise ValidationError(
            "Invalid ArcGIS FeatureServer link. It should look like: {}.".format(
                "https://servicesX.arcgis.com/<org_id>/ArcGIS/rest/services/<service_name>/FeatureServer/<positive_integer>"
            )
        )