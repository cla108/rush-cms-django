from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from rush.models import GuessedMimeType
from rush.models.validators import *
from rush.tests.models.helpers import FakeFile


def valid_file(
    name: str,
    valid_names=None,
    invalid_names=None,
) -> tuple[Mock, bool, str, List[str] | None, List[str] | None]:
    valid_names = [] if valid_names is None else valid_names
    invalid_names = [] if invalid_names is None else invalid_names
    return (FakeFile(name), False, "", valid_names, invalid_names)


def invalid_file(
    name: str,
    err_msg: str,
    valid_names=None,
    invalid_names=None,
) -> tuple[Mock, bool, str, List[str] | None, List[str] | None]:
    valid_names = [] if valid_names is None else valid_names
    invalid_names = [] if invalid_names is None else invalid_names
    return (FakeFile(name), True, err_msg, valid_names, invalid_names)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file, raises, err_msg, valid_names, invalid_names",
    [
        valid_file("test.svg", valid_names=[]),  # No valid list should always pass
        valid_file("test.svg", valid_names=["SVG"]),
        valid_file("test.SVG", valid_names=["SVG"]),  # Uppercase file extension should also pass
        valid_file("test.svg", valid_names=["SVG", "TIFF"]),
        invalid_file("test.html5", "The mimetype of file 'test.html5' could not be parsed"),
        invalid_file("test.html", "The mimetype of file 'test.html' is currently not supported"),
        invalid_file("test.svg", "The mimetype SVG is invalid", valid_names=["TIFF"]),
        invalid_file("test.svg", "The mimetype SVG is invalid", valid_names=["SVG"], invalid_names=["SVG"]),
        valid_file(
            "test.svg",
            # Unsupported mimetypes shouldn't have an effect on validation.
            valid_names=["SVG", "FOOBAR"],
            invalid_names=["BAZ"],
        ),
        invalid_file(
            "test.svg",
            "The mimetype SVG is invalid",
            # Even though the mimetype isn't real, it's still the only valid one.
            valid_names=["FOOBAR"],
        ),
        valid_file(
            "test.svg",
            # A fake invalid mimetype means we should pass
            invalid_names=["FOOBAR"],
        ),
    ],
)
def test_validate_filetype(
    file: Mock,
    raises: bool,
    err_msg: str,
    valid_names: List[str],
    invalid_names: List[str],
):
    """
    Test FiletypeValidator with human-readable mimetype names.
    """
    validator = FiletypeValidator(valid_names=valid_names, invalid_names=invalid_names)
    if raises:
        with pytest.raises(GuessedMimeType.BaseValidationError, match=err_msg):
            validator(file)
    else:
        # Shouldn't raise
        validator(file)


@pytest.mark.parametrize(
    "value, raises",
    [
        ("123", False),
        ("  123", False),
        ("123  ", False),
        (" 1 2   3 ", False),
        ("123\n", False),  # newline is whitespace
        ("123\r", False),  # carriage return is whitespace
        ("123298312931   273234234234234", False),
        ("123.", True),
        ("a123", True),
        ("0a8ue98qy3r", True),
    ],
)
def test_validate_only_integers_and_whitespace(value: str, raises: bool):
    """
    Only digits and whitespace allowed.
    """
    if raises:
        msg = "This field must contain only digits and whitespace."
        with pytest.raises(ValidationError, match=msg):
            validate_only_integers_and_whitespace(value)
    else:
        validate_only_integers_and_whitespace(value)

@pytest.mark.parametrize(
    "value, raises",
    [
        (
            "https://google.com",
            True
        ),
        (
            # http not allowed
            "http://services6.arcgis.com/ubm4tcTYICKBpist/ArcGIS/rest/services/hpai_dashboard/FeatureServer/0",
            True
        ), 
        (
            "https://services6.arcgis.com/ubm4tcTYICKBpist/ArcGIS/rest/services/hpai_dashboard/FeatureServer/0",
            False            
        ),
        (
            "https://mapservices.crd.bc.ca/arcgis/rest/services/LandCoverAnalysis/MapServer/0",
            True
        ),
    ],
)

def test_validate_arcgis_feature_server_link(value: str, raises: bool):
    if raises:
        with pytest.raises(ValidationError):
            validate_arcgis_feature_server_link(value)
    else:
        validate_arcgis_feature_server_link(value)