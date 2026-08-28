import os
from typing import Any

import pytest

from rush.models.style import Style
from rush.tests.models.helpers import (
    create_test_image,
    create_test_svg,
    use_tmp_media_dir,
)


def create_style_kwargs() -> dict[str, Any]:
    return {
        "name": "Test Style",
        "draw_stroke": True,
        "draw_fill": True,
        "draw_marker": True,
    }


@use_tmp_media_dir
@pytest.mark.django_db
@pytest.mark.parametrize(
    "image, save_name",
    [
        (create_test_image("test_image.png"), "compressed_test_image.webp"),
        (create_test_image("test_image.jpg"), "compressed_test_image.webp"),
        (create_test_image("test_image.jpeg"), "compressed_test_image.webp"),
    ],
)
def test_create_style_compresses_marker_icon_images(image, save_name: str):
    kwargs = create_style_kwargs() | {"marker_icon": image}
    style = Style.objects.create(**kwargs)

    assert os.path.exists(style.marker_icon.path)
    assert style.marker_icon.name.endswith(save_name)
    assert style.marker_icon.size < image.size  # compressed image should be smaller


@use_tmp_media_dir
@pytest.mark.django_db
def test_create_style_does_not_compress_marker_icon_svgs():

    svg = create_test_svg("test_image.svg")
    kwargs = create_style_kwargs() | {"marker_icon": svg}
    style = Style.objects.create(**kwargs)

    assert os.path.exists(style.marker_icon.path)
    assert style.marker_icon.name == "marker_icons/test_image.svg"
    assert style.marker_icon.size == svg.size  # no compression
