import io
import tempfile
from contextlib import ExitStack
from decimal import Decimal
from functools import wraps
from typing import Callable
from unittest.mock import Mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import QuerySet
from django.test import override_settings
from PIL import Image

from rush.models import (
    BasemapSource,
    BasemapSourceOnQuestion,
    Icon,
    Initiative,
    InitiativeTag,
    Layer,
    LayerGroupOnQuestion,
    LayerOnLayerGroup,
    MapData,
    MimeType,
    PublishedState,
    Question,
    QuestionSash,
    QuestionTab,
    Region,
    Style,
    StylesOnLayer,
    Tooltip,
)
from rush.models.style import FillRule, LineCap, LineJoin
from rush.models.style.tooltip import Direction


class FakeFile(Mock):

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def __repr__(self) -> str:
        return f'<FakeFile: "{self.name}">'


def use_tmp_media_dir(func):
    """
    Tell Django to use a temporary MEDIA_ROOT directory which is cleaned up
    after the decorated function finishes executing.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with ExitStack() as stack:
            cm1 = tempfile.TemporaryDirectory()
            dirname = stack.enter_context(cm1)
            cm2 = override_settings(MEDIA_ROOT=dirname)
            # Pylance doesn't like override_settings because of BaseException in __exit__
            stack.enter_context(cm2)  # type: ignore[arg-type]
            return func(*args, **kwargs)

    return wrapper


def create_test_image(name: str, size=(100, 100), color=(255, 0, 0)) -> SimpleUploadedFile:
    ext = name.split(".")[-1].lower()
    if ext.lower() == "jpg":
        ext = "jpeg"
    image_bytes = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(image_bytes, format=ext)
    image_bytes.seek(0)
    return SimpleUploadedFile(
        name=name,
        content=image_bytes.read(),
        content_type=f"image/{ext}",
    )


def create_test_svg(name: str) -> SimpleUploadedFile:
    svg_content = b"""<?xml version="1.0"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
      <rect width="100" height="100" style="fill:rgb(0,0,255);" />
    </svg>"""
    return SimpleUploadedFile(name, svg_content, content_type="image/svg+xml")


def create_test_region(
    name="Greater Victoria Area",
    latitude=48.454026266404306,
    longitude=-123.34758806021976,
    default_zoom=12,
) -> Region:
    return Region.objects.create(
        name=name,
        latitude=latitude,
        longitude=longitude,
        default_zoom=default_zoom,
    )


SINGLETON_REGION = None


def _provide_singleton_test_region() -> Region:
    global SINGLETON_REGION
    if SINGLETON_REGION is None or not Region.objects.filter(id=SINGLETON_REGION.id).exists():
        SINGLETON_REGION = create_test_region()
    return SINGLETON_REGION


def create_test_initiative_tag(
    name="Test initiative tag",
    text_color="#0000FF",
    background_color="#FF00FF",
) -> InitiativeTag:
    return InitiativeTag.objects.create(
        name=name,
        text_color=text_color,
        background_color=background_color,
    )


def _provide_initiative_tags() -> list[InitiativeTag]:
    return [
        create_test_initiative_tag(name="Tag 1"),
        create_test_initiative_tag(name="Tag 2"),
        create_test_initiative_tag(name="Tag 3"),
    ]


DEFAULT_INITIATIVE_IMAGE = create_test_image("test_initiative_image.png")
DEFAULT_INITIATIVE_TAGS_PROVIDER = _provide_initiative_tags


def create_test_initiative(
    link="https://example-initiative.com",
    image: SimpleUploadedFile = DEFAULT_INITIATIVE_IMAGE,
    title="A test initiative",
    content="This is a test initiative. Please read carefully and enjoy!",
    tags: list[InitiativeTag] | Callable[[], list[InitiativeTag]] = DEFAULT_INITIATIVE_TAGS_PROVIDER,
    published_state=PublishedState.PUBLISHED,
) -> Initiative:
    tags = tags if not isinstance(tags, Callable) else tags()
    initiative = Initiative.objects.create(
        link=link,
        image=image,
        title=title,
        content=content,
        published_state=published_state,
    )
    # tags must be set like this because they are a many-to-many field
    initiative.tags.set(tags)
    return initiative


def _provide_test_initiatives() -> list[Initiative]:
    return [
        create_test_initiative(title="Peninsula Streams Society"),
        create_test_initiative(title="Friends of Maltby Lake Society"),
    ]


def create_test_question_sash(
    text="New Question!!!",
    text_color="#0000FF",
    background_color="#FF00FF",
) -> QuestionSash:
    return QuestionSash.objects.create(
        text=text,
        text_color=text_color,
        background_color=background_color,
    )


def create_test_icon(file_prefix="example_icon", mimetype="PNG") -> Icon:
    """
    Create a test icon object and an associated file with the correct mime-type.
    """
    mimetype = MimeType.by_name(mimetype)
    filename = f"{file_prefix}.{mimetype.human_name.lower()}"
    MimeType.guess(filename).validate()
    if mimetype.human_name.upper() == "SVG":
        file = create_test_svg(filename)
    else:
        file = create_test_image(filename)
    return Icon.objects.create(file=file)


DEFAULT_QUESTION_TAB_ICON_PROVIDER = create_test_icon
DEFAULT_QUESTION_TAB_SLUG_RESOLVER = lambda question: f"question-tab-slug-{question.tabs.count()}"
DEFAULT_QUESTION_TAB_DISPLAY_ORDER_RESOLVER = lambda question: question.tabs.count()


def create_test_question_tab(
    question: Question,
    icon: Icon | Callable[[], Icon] = DEFAULT_QUESTION_TAB_ICON_PROVIDER,
    title="Test question tab",
    content="Test content.",
    slug: str | Callable[[Question], str] = DEFAULT_QUESTION_TAB_SLUG_RESOLVER,
    display_order: int | Callable[[Question], int] = DEFAULT_QUESTION_TAB_DISPLAY_ORDER_RESOLVER,
) -> QuestionTab:
    slug = slug if not isinstance(slug, Callable) else slug(question)
    display_order = display_order if not isinstance(display_order, Callable) else display_order(question)
    icon = icon if not isinstance(icon, Callable) else icon()
    return QuestionTab.objects.create(
        question=question,
        icon=icon,
        title=title,
        content=content,
        slug=slug,
        display_order=display_order,
    )


def _provide_test_question_tabs(question: Question) -> list[QuestionTab]:
    return [
        create_test_question_tab(question, title="Question Tab 1"),
        create_test_question_tab(question, title="Question Tab 2"),
        create_test_question_tab(question, title="Question Tab 3"),
    ]


def create_test_basemap_source(
    name="Test Basemap Source",
    tile_url="https://example-map-tiles.com",
    max_zoom=18,
    attribution="All rights reserved, Test and Co.",
    is_default=False,
) -> BasemapSource:
    return BasemapSource.objects.create(
        name=name,
        tile_url=tile_url,
        max_zoom=max_zoom,
        attribution=attribution,
        is_default=is_default,
    )


SECOND_BASEMAP_SOURCE_SINGLETON = None


def _provide_singleton_test_basemap_sources() -> list[BasemapSource]:
    global SECOND_BASEMAP_SOURCE_SINGLETON
    if (
        # First test-run
        SECOND_BASEMAP_SOURCE_SINGLETON is None
        # Subsequent test-runs (it's been deleted from the database during a reset)
        or not BasemapSource.objects.filter(id=SECOND_BASEMAP_SOURCE_SINGLETON.id).exists()
    ):
        SECOND_BASEMAP_SOURCE_SINGLETON = create_test_basemap_source(name="Heightmap")
    return [
        # See migration 0079 for more info
        BasemapSource.objects.get(name="Satellite Basemap (Default)"),
        SECOND_BASEMAP_SOURCE_SINGLETON,
    ]


DEFAULT_MAP_DATA_GEOJSON = {
    "type": "FeatureCollection",
    "name": "Test Map Data",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": [
        {
            "type": "Feature",
            "properties": {
                "Name": "North Park Heatwave Map",
                "Description": "A community map of the North Park neighbourhood showing assets, concerns, and opportunities for dealing with heatwave events in the future. Created by UVic geography students Tenaya Lynx, Julia Frasher, Riley Sondergaard.",
                "URL": "https://www.google.com/maps/d/viewer?mid=12YLjmNqss6nHrcWQYYgK0ffl8JqkYaKd&ll=48.431337468326106%2C-123.35707554999999&z=16",
                "color": "#fdda0d",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-123.3609917, 48.4354733],
                        [-123.3618928, 48.4286964],
                        [-123.3589104, 48.428554],
                        [-123.3589533, 48.4275146],
                        [-123.353267, 48.4272013],
                        [-123.3522583, 48.4349893],
                        [-123.3609917, 48.4354733],
                    ]
                ],
            },
        }
    ],
}


def create_test_map_data(
    name="Test Map Data",
    provider_state=MapData.ProviderState.GEOJSON,
    geojson=DEFAULT_MAP_DATA_GEOJSON,
    map_link=None,
    campaign_link=None,
    geotiff=None,
) -> MapData:
    return MapData.objects.create(
        name=name,
        provider_state=provider_state,
        _geojson=geojson,
        map_link=map_link,
        campaign_link=campaign_link,
        geotiff=geotiff,
    )


DEFAULT_MAP_DATA_SINGLETON = None


def _get_singleton_test_map_data() -> MapData:
    global DEFAULT_MAP_DATA_SINGLETON
    if (
        # First test-run
        DEFAULT_MAP_DATA_SINGLETON is None
        # Subsequent test-runs (it's been deleted from the database during a reset)
        or not MapData.objects.filter(id=DEFAULT_MAP_DATA_SINGLETON.id).exists()
    ):
        DEFAULT_MAP_DATA_SINGLETON = create_test_map_data()
    return DEFAULT_MAP_DATA_SINGLETON


DEFAULT_MARKER_ICON_IMAGE = create_test_image("test_marker_icon_image.png")


def create_test_style(
    name="Test Style",
    # stroke
    draw_stroke=True,
    stroke_color="#4BEB32",
    stroke_weight=Decimal(4.5),
    stroke_opacity=Decimal(0.8),
    stroke_line_cap=LineCap.ROUND,
    stroke_line_join=LineJoin.ROUND,
    stroke_dash_array="5 5 11",
    stroke_dash_offset="2",
    # fill
    draw_fill=True,
    fill_color="#1080AD",
    fill_opacity=Decimal(0.8),
    fill_rule=FillRule.EVENODD,
    # marker
    draw_marker=True,
    marker_icon: SimpleUploadedFile | None = DEFAULT_MARKER_ICON_IMAGE,
    is_marker_icon_compressed=False,
    marker_icon_opacity=Decimal(0.8),
    marker_size=Decimal(22),
    marker_background_color="#EDF3F5",
    marker_background_opacity=Decimal(0.8),
) -> Style:
    return Style.objects.create(
        name=name,
        # stroke
        draw_stroke=draw_stroke,
        stroke_color=stroke_color,
        stroke_weight=stroke_weight,
        stroke_opacity=stroke_opacity,
        stroke_line_cap=stroke_line_cap,
        stroke_line_join=stroke_line_join,
        stroke_dash_array=stroke_dash_array,
        stroke_dash_offset=stroke_dash_offset,
        # fill
        draw_fill=draw_fill,
        fill_color=fill_color,
        fill_opacity=fill_opacity,
        fill_rule=fill_rule,
        # marker
        draw_marker=draw_marker,
        marker_icon=marker_icon,
        is_marker_icon_compressed=is_marker_icon_compressed,
        marker_icon_opacity=marker_icon_opacity,
        marker_size=marker_size,
        marker_background_color=marker_background_color,
        marker_background_opacity=marker_background_opacity,
    )


def create_test_tooltip(
    styles_on_layer: StylesOnLayer,
    label="Test Tooltip",
    offset_x=Decimal(0),
    offset_y=Decimal(0),
    opacity=Decimal(0.8),
    direction=Direction.CENTER,
    permanent=True,
    sticky=True,
) -> Tooltip:
    return Tooltip.objects.create(
        style_on_layer=styles_on_layer,
        label=label,
        offset_x=offset_x,
        offset_y=offset_y,
        opacity=opacity,
        direction=direction,
        permanent=permanent,
        sticky=sticky,
    )


DEFAULT_STYLE_PROVIDER = create_test_style
DEFAULT_STYLES_ON_LAYER_DISPLAY_ORDER_PROVIDER = lambda layer: layer.styles.count()
DEFAULT_TOOLTIP_PROVIDER = create_test_tooltip


def create_test_styles_on_layer(
    layer: Layer,
    style: Style | Callable[[], Style] = DEFAULT_STYLE_PROVIDER,
    legend_description="This is a test layer's legend description!",
    display_order: int | Callable[[Layer], int] = DEFAULT_STYLES_ON_LAYER_DISPLAY_ORDER_PROVIDER,
    feature_mapping="true",
    popup="<h1>Popup text!</h1>",
    tooltip: None | Callable[[StylesOnLayer], Tooltip] = DEFAULT_TOOLTIP_PROVIDER,
) -> StylesOnLayer:
    style = style if not isinstance(style, Callable) else style()
    display_order = display_order if not isinstance(display_order, Callable) else display_order(layer)
    styles_on_layer = StylesOnLayer.objects.create(
        style=style,
        layer=layer,
        legend_description=legend_description,
        display_order=display_order,
        feature_mapping=feature_mapping,
        popup=popup,
    )
    # by default we add a tooltip, but it can also be set to None
    if tooltip is not None:
        tooltip(styles_on_layer)
    return styles_on_layer


def _provide_test_styles_on_layers(layer: Layer) -> list[StylesOnLayer]:
    return [
        create_test_styles_on_layer(layer),
        create_test_styles_on_layer(layer),
        create_test_styles_on_layer(layer),
    ]


INCREMENTAL_LAYER_NAME_RESOLVER = lambda: f"Layer {Layer.objects.count()}"
DEFAULT_MAP_DATA_PROVIDER = _get_singleton_test_map_data
DEFAULT_STYLES_ON_LAYER_PROVIDER = _provide_test_styles_on_layers


def create_test_layer(
    name="Test Layer",
    legend_title="Test legend title.",
    description="This is a test layer!",
    map_data: MapData | Callable[[], MapData] = DEFAULT_MAP_DATA_PROVIDER,
    published_state=PublishedState.PUBLISHED,
    styles_on_layer: Callable[[Layer], list[StylesOnLayer]] = DEFAULT_STYLES_ON_LAYER_PROVIDER,
) -> Layer:
    map_data = map_data if not isinstance(map_data, Callable) else map_data()
    layer = Layer.objects.create(
        name=name,
        legend_title=legend_title,
        description=description,
        map_data=map_data,
        published_state=published_state,
    )
    # should automatically link Layer <--> StylesOnLayer
    styles_on_layer(layer)
    return layer


def _incremental_geojson_layer(
    name: str | Callable[[], str] = INCREMENTAL_LAYER_NAME_RESOLVER,
    legend_title="Test legend title.",
    description="This is a test layer!",
    map_data: MapData | Callable[[], MapData] = DEFAULT_MAP_DATA_PROVIDER,
) -> Layer:
    name = name if not isinstance(name, Callable) else name()
    map_data = map_data if not isinstance(map_data, Callable) else map_data()
    return create_test_layer(
        name=name,
        legend_title=legend_title,
        description=description,
        map_data=map_data,
    )


DEFAULT_LAYER_RESOLVER = _incremental_geojson_layer
DEFAULT_LAYER_ON_LAYER_GROUP_DISPLAY_ORDER_RESOLVER = lambda group: LayerOnLayerGroup.objects.filter(
    layer_group_on_question=group
).count()


def create_test_layer_on_layer_group(
    layer_group: LayerGroupOnQuestion,
    layer: Layer | Callable[[], Layer] = DEFAULT_LAYER_RESOLVER,
    active_by_default=True,
    display_order: (
        int | Callable[[LayerGroupOnQuestion], int]
    ) = DEFAULT_LAYER_ON_LAYER_GROUP_DISPLAY_ORDER_RESOLVER,
) -> LayerOnLayerGroup:
    layer = layer if not isinstance(layer, Callable) else layer()
    display_order = display_order if not isinstance(display_order, Callable) else display_order(layer_group)
    return LayerOnLayerGroup.objects.create(
        layer=layer,
        layer_group_on_question=layer_group,
        active_by_default=active_by_default,
        display_order=display_order,
    )


def _provide_test_layers_on_layer_group(layer_group: LayerGroupOnQuestion) -> list[LayerOnLayerGroup]:
    return [
        create_test_layer_on_layer_group(layer_group),
        create_test_layer_on_layer_group(layer_group),
        create_test_layer_on_layer_group(layer_group),
        create_test_layer_on_layer_group(layer_group),
    ]


DEFAULT_LAYER_GROUP_ON_QUESTION_DISPLAY_ORDER_RESOLVER = lambda: LayerGroupOnQuestion.objects.count()
DEFAULT_LAYERS_ON_LAYER_GROUP_PROVIDER = _provide_test_layers_on_layer_group


def create_test_layer_group(
    question: Question,
    group_name="Test layer group",
    group_description="This is a test layer group.",
    layers_on_layer_group: (
        list[LayerOnLayerGroup] | Callable[[LayerGroupOnQuestion], list[LayerOnLayerGroup]]
    ) = DEFAULT_LAYERS_ON_LAYER_GROUP_PROVIDER,
    display_order: int | Callable[[], int] = DEFAULT_LAYER_GROUP_ON_QUESTION_DISPLAY_ORDER_RESOLVER,
    behaviour=LayerGroupOnQuestion.Behaviour.DEFAULT,
) -> LayerGroupOnQuestion:
    display_order = display_order if not isinstance(display_order, Callable) else display_order()
    group = LayerGroupOnQuestion.objects.create(
        question=question,
        group_name=group_name,
        group_description=group_description,
        display_order=display_order,
        behaviour=behaviour,
    )
    layers_on_layer_group = (
        layers_on_layer_group if not isinstance(layers_on_layer_group, Callable) else layers_on_layer_group(group)
    )
    group.layers.set(layers_on_layer_group)  # type: ignore
    return group


def _provide_test_layer_groups(question: Question) -> list[LayerGroupOnQuestion]:
    return [
        create_test_layer_group(question, group_name="Layer Group 1"),
        create_test_layer_group(question, group_name="Layer Group 2"),
    ]


DEFAULT_QUESTION_IMAGE = create_test_image("test_question_image.png")
DEFAULT_QUESTION_INITIATIVES_PROVIDER = _provide_test_initiatives
DEFAULT_QUESTION_REGION_PROVIDER = _provide_singleton_test_region
DEFAULT_QUESTION_DISPLAY_ORDER_RESOLVER = lambda: Question.objects.count()
DEFAULT_QUESTION_SASH_PROVIDER = create_test_question_sash
DEFAULT_QUESTION_SLUG_RESOLVER = lambda: f"question-slug-{Question.objects.count() + 1}"
DEFAULT_QUESTION_TABS_PROVIDER = _provide_test_question_tabs
DEFAULT_BASEMAP_SOURCE_PROVIDER = _provide_singleton_test_basemap_sources
DEFAULT_LAYER_GROUPS_PROVIDER = _provide_test_layer_groups


def create_test_question(
    title="A test question",
    subtitle="This is a test question",
    image: SimpleUploadedFile | None = DEFAULT_QUESTION_IMAGE,
    is_image_compressed=True,
    initiatives: list[Initiative] | Callable[[], list[Initiative]] = DEFAULT_QUESTION_INITIATIVES_PROVIDER,
    layer_groups: (
        list[LayerGroupOnQuestion] | Callable[[Question], list[LayerGroupOnQuestion]] | None
    ) = DEFAULT_LAYER_GROUPS_PROVIDER,
    slug: str | Callable[[], str] = DEFAULT_QUESTION_SLUG_RESOLVER,
    sash: QuestionSash | None | Callable[[], QuestionSash] = DEFAULT_QUESTION_SASH_PROVIDER,
    region: Region | Callable[[], Region] = DEFAULT_QUESTION_REGION_PROVIDER,
    display_order: int | Callable[[], int] = DEFAULT_QUESTION_DISPLAY_ORDER_RESOLVER,
    tabs: Callable[[Question], list[QuestionTab]] = DEFAULT_QUESTION_TABS_PROVIDER,
    published_state=PublishedState.PUBLISHED,
    basemaps: list[BasemapSource] | Callable[[], list[BasemapSource]] = DEFAULT_BASEMAP_SOURCE_PROVIDER,
) -> Question:
    initiatives = initiatives if not isinstance(initiatives, Callable) else initiatives()
    slug = slug if not isinstance(slug, Callable) else slug()
    sash = sash if not isinstance(sash, Callable) else sash()
    region = region if not isinstance(region, Callable) else region()
    display_order = display_order if not isinstance(display_order, Callable) else display_order()
    basemaps = basemaps if not isinstance(basemaps, Callable) else basemaps()
    question = Question.objects.create(
        title=title,
        subtitle=subtitle,
        image=image,
        is_image_compressed=is_image_compressed,
        slug=slug,
        sash=sash,
        region=region,
        display_order=display_order,
        published_state=published_state,
    )
    # tabs can only be created in relation to a question
    tabs(question)
    # initiatives must be set like this because they are a many-to-many field
    question.initiatives.set(initiatives)
    layer_groups = layer_groups if not isinstance(layer_groups, Callable) else layer_groups(question)
    question.layer_groups.set(layer_groups)  # type: ignore
    # basemaps must be set like this because they are a many-to-many field
    # implemented using a through-table.
    for basemap in basemaps:
        BasemapSourceOnQuestion.objects.create(
            basemap_source=basemap,
            question=question,
            # simplification (the globally default basemap is set to the default for each question)
            is_default_for_question=basemap.is_default,
        )
    return question


def get_initiative_dict(initiative: Initiative) -> dict:
    """
    Helper function that returns a dictionary of "relevant" information
    about the given initiative model instance.
    """
    return {
        "id": str(initiative.id),
        "title": str(initiative.title),
        "link": str(initiative.link),
        "image": str(initiative.image),
        "content": str(initiative.content),
        "tags": [str(x.name) for x in initiative.tags.all()],
        "published_state": str(initiative.published_state),
    }


def get_layer_group_on_question_dict(layer_group: LayerGroupOnQuestion) -> dict:
    """
    Helper function that returns a dictionary of "relevant" information
    about the given layer_group model instance.
    """
    return {
        "id": str(layer_group.id),
        "group_name": str(layer_group.group_name),
        "group_description": str(layer_group.group_description),
        "display_order": int(layer_group.display_order),
        "behaviour": str(layer_group.behaviour),
    }


def get_layer_dict(layer: Layer) -> dict:
    return {
        "layer_id": str(layer.id),
        "name": str(layer.name),
        "legend_title": str(layer.legend_title),
        "description": str(layer.description),
        "map_data": {
            "id": str(layer.map_data.id),
            "name": str(layer.map_data.name),
            "provider_state": str(layer.map_data.provider_state),
        },
        # style data omitted for now...
        "published_state": str(layer.published_state),
    }


def get_layer_on_layer_group_dict(layer_on_layer_group: LayerOnLayerGroup) -> dict:
    """
    Helper function that returns a dictionary of "relevant" information
    about the given layer_on_layer_group model instance.
    """
    return {
        "layer_on_layer_group_id": str(layer_on_layer_group.id),
        "active_by_default": bool(layer_on_layer_group.active_by_default),
        "display_order": int(layer_on_layer_group.display_order),
    } | get_layer_dict(layer_on_layer_group.layer)


def get_question_dict(question: Question) -> dict:
    """
    Helper function that returns a dictionary of "relevant" information
    about the given question model instance.
    """
    return {
        "id": str(question.id),
        "title": str(question.title),
        "subtitle": (question.subtitle),
        "image": (question.image.url),
        "is_image_compressed": bool(question.is_image_compressed),
        "initiatives": [get_initiative_dict(x) for x in question.initiatives.all()],
        "layer_groups": [
            get_layer_group_on_question_dict(x)
            | {
                "attached_layers": [
                    get_layer_on_layer_group_dict(y)
                    for y in LayerOnLayerGroup.objects.filter(layer_group_on_question=x)
                ]
            }
            for x in LayerGroupOnQuestion.objects.filter(question=question)
        ],
        "slug": str(question.slug),
        "sash": str(question.sash.text),  # type: ignore
        "region": {
            "id": str(question.region.id),  # type: ignore
            "name": str(question.region.name),  # type: ignore
            "latitude": str(question.region.latitude),  # type: ignore
            "longitude": str(question.region.longitude),  # type: ignore
            "default_zoom": str(question.region.default_zoom),  # type: ignore
        },
        "basemaps": [
            {
                "id": str(x.basemap_source.id),
                "name": str(x.basemap_source.name),
                "tile_url": str(x.basemap_source.tile_url),
                "max_zoom": str(x.basemap_source.max_zoom),
                "is_global_default": str(x.basemap_source.is_default),
                "is_default_for_question": bool(x.is_default_for_question),
            }
            for x in BasemapSourceOnQuestion.objects.filter(question=question)
        ],
        "display_order": int(question.display_order),
        "published_state": str(question.published_state),
    }


def get_ids(qs: QuerySet) -> set[str]:
    return set(str(x.id) for x in qs.all().order_by("id"))
    return set(str(x.id) for x in qs.all().order_by("id"))
