import json
import logging
from typing import List
from urllib.parse import urljoin

import graphene
from bs4 import BeautifulSoup
from django.conf import settings
from django.db.models import Prefetch, QuerySet
from graphene.types import ResolveInfo
from graphene_django.types import DjangoObjectType
from graphene_django.views import GraphQLView

from rush import models
from rush.context_processors import base_url_from_request
from rush.models import MimeType, PublishedState
from rush.models.validators import (
    OGM_CAMPAIGN_RE,
    OGM_MAP_BROWSE_RE,
    OGM_MAP_EXPLORE_RE,
)
from rush.utils import log_execution_time_with_result

"""
The GraphQL Schema for RUSH models. For more information see: https://docs.graphene-python.org/projects/django/en/latest/.
"""


logger = logging.getLogger(__name__)


def convert_relative_links_to_absolute(html: str, base_media_url: str) -> str:
    """
    Convert all relative HTML <img> src and <a> href to absolute paths using HTTPS. External links should
    be preserved while unspecified domains should automatically resolve to the site's base-media-url.
    """
    base_media_domain = base_media_url.removeprefix("https://www.")
    soup = None
    try:
        soup = BeautifulSoup(html, "html.parser")

        def _convert(html_tag: str, key: str):
            for element in soup.find_all(html_tag):
                link = element.get(key)
                if not isinstance(link, str):
                    logger.error("Expected HTML link to be a string!", {"link": link})
                    continue

                if link.startswith("https://https://"):
                    link = link.replace("https://https://", "https://", 1)
                elif link.startswith("http://https://"):
                    link = link.replace("http://https://", "https://", 1)
                elif link.startswith("https://"):
                    # link is already formatted correctly
                    continue
                elif link.startswith("http://"):
                    link = link.replace("http://", "https://", 1)
                elif link.startswith("www."):
                    link = link.replace("www.", "https://www.", 1)
                elif link.startswith("//"):
                    link = link.replace("//", base_media_url, 1)
                elif link.startswith(base_media_domain):
                    # e.g., src = "admin.whatstherush.earth/example.png".
                    link = urljoin(base_media_url, link.replace(base_media_domain, "", 1).lstrip("/"))
                elif "." in link.split("/")[0]:
                    if MimeType.guess(link.split("/")[0]).guessed.is_valid:
                        # NOTE: This uses mime-type model to differentiate between a domain and a supported filetype.
                        # e.g., src = "example.png".
                        link = urljoin(base_media_url, link)
                    else:
                        # e.g., src = "google.com/example.png".
                        link = f"https://www.{link.lstrip("/")}"
                else:
                    # internal resource location with trailing slash
                    # e.g., src = "/example.png".
                    link = urljoin(base_media_url, link.lstrip("/"))

                element[key] = link

        tag_keys = {"img": "src", "a": "href"}
        for tag in tag_keys:
            key = tag_keys[tag]
            _convert(html_tag=tag, key=key)

        return str(soup)
    finally:
        if soup is not None:
            soup.decompose()


class MapDataType(DjangoObjectType):
    class Meta:
        model = models.MapData
        fields = [
            "id",
            "name",
            "provider_state",
            "geojson",
            "map_link",
            "campaign_link",
            "geotiff_link",
        ]

    geojson = graphene.String()
    ogm_map_id = graphene.String()
    ogm_campaign_id = graphene.String()
    map_link = graphene.String()
    campaign_link = graphene.String()
    geotiff_link = graphene.String()

    def resolve_map_link(self, info):
        if not isinstance(self, models.MapData):
            raise ValueError("Expected object to be of type MapData when resolving query.")
        # LOG TODO: Log a warning here. This should be deprecated and I wanna make sure it's no longer being used when I delete it.
        return self.map_link

    def resolve_campaign_link(self, info):
        if not isinstance(self, models.MapData):
            raise ValueError("Expected object to be of type MapData when resolving query.")
        # LOG TODO: Log a warning here. This should be deprecated and I wanna make sure it's no longer being used when I delete it.
        return self.campaign_link

    def resolve_geojson(self, info):
        if not isinstance(self, models.MapData):
            raise ValueError("Expected object to be of type MapData when resolving query.")
        return self.geojson

    def resolve_geotiff_link(self, info):
        if not isinstance(self, models.MapData):
            return None
        if not self.geotiff.name:
            # .geotiff.name doesn't make an (ASYNC IN PROD) file-existance check, unlike .geotiff.
            return None
        return self.geotiff.url

    def resolve_ogm_map_id(self, info):
        if not isinstance(self, models.MapData) or not isinstance(self.map_link, str):
            return None
        for regex in [OGM_MAP_EXPLORE_RE, OGM_MAP_BROWSE_RE]:
            m = regex.match(self.map_link)
            if m:
                return m.group("id")
        # LOG TODO: Log error here...
        raise ValueError(f"{self.map_link} didn't match the expected map_link regex.")

    def resolve_ogm_campaign_id(self, info):
        if not isinstance(self, models.MapData) or not isinstance(self.campaign_link, str):
            return None
        for regex in [OGM_CAMPAIGN_RE]:
            m = regex.match(self.campaign_link)
            if m:
                return m.group("id")
        # LOG TODO: Log error here...
        raise ValueError(f"{self.campaign_link} didn't match the expected campaign_link regex.")


class MapDataWithoutGeoJsonType(DjangoObjectType):
    class Meta:  # type: ignore
        model = models.MapData
        fields = [x for x in MapDataType._meta.fields if x != "geojson"]

    # Still need this resolved and field definition here because inheritance of
    # mapDataType in this class keeps geojson accessible for some reason...
    geotiff_link = graphene.String()

    def resolve_geotiff_link(self, info):
        if isinstance(self, models.MapData):
            if self.geotiff:
                return self.geotiff.url
            return None
        raise ValueError("Expected API object to be an instance of MapData!")

    ogm_map_id = graphene.String()
    ogm_campaign_id = graphene.String()

    def resolve_ogm_map_id(self, info):
        if not isinstance(self, models.MapData) or not isinstance(self.map_link, str):
            return None
        for regex in [OGM_MAP_EXPLORE_RE, OGM_MAP_BROWSE_RE]:
            m = regex.match(self.map_link)
            if m:
                return m.group("id")
        # LOG TODO: Log error here...
        raise ValueError(f"{self.map_link} didn't match the expected map_link regex.")

    def resolve_ogm_campaign_id(self, info):
        if not isinstance(self, models.MapData) or not isinstance(self.campaign_link, str):
            return None
        for regex in [OGM_CAMPAIGN_RE]:
            m = regex.match(self.campaign_link)
            if m:
                return m.group("id")
        # LOG TODO: Log error here...
        raise ValueError(f"{self.campaign_link} didn't match the expected campaign_link regex.")


class StylesOnLayersType(DjangoObjectType):
    class Meta:
        model = models.StylesOnLayer
        fields = [
            "id",
            "legend_description",
            "display_order",
            "style",
            "layer",
        ]

    legend_description = graphene.String()

    def resolve_legend_description(self, info) -> str:
        if not isinstance(self, models.StylesOnLayer):
            raise ValueError("Expected object to be of type StylesOnLayer when resolving query.")
        if not isinstance(self.legend_description, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected StylesOnLayer.legend_description to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.legend_description, base_media_url=base_media_url)


class StyleType(DjangoObjectType):
    class Meta:
        model = models.Style
        fields = [
            "id",
            "name",
            # stroke fields
            "draw_stroke",
            "stroke_color",
            "stroke_weight",
            "stroke_opacity",
            "stroke_line_cap",
            "stroke_line_join",
            "stroke_dash_array",
            "stroke_dash_offset",
            # fill fields
            "draw_fill",
            "fill_color",
            "fill_opacity",
            # marker fields
            "draw_marker",
            "marker_icon",
            "marker_icon_opacity",
            "marker_background_color",
            "marker_background_opacity",
            "marker_size",
            # circle fields
            "draw_circle",
            "circle_radius",
            "circle_stroke_color",
            "circle_stroke_weight",
            "circle_stroke_opacity",
            "circle_stroke_line_cap",
            "circle_stroke_line_join",
            "circle_stroke_dash_array",
            "circle_stroke_dash_offset",
            "circle_fill_color",
            "circle_fill_opacity",
        ]


class LayerType(DjangoObjectType):
    class Meta:
        model = models.Layer
        fields = [
            "id",
            "name",
            "legend_title",
            "map_data",
            "description",
            "styles_on_layer",
            "serialized_leaflet_json",
        ]

    styles_on_layer = graphene.List(StylesOnLayersType)

    def resolve_styles_on_layer(self, info):
        if isinstance(self, models.Layer):
            if prefetch_cache := getattr(self, "_prefetched_objects_cache", None):
                if "stylesonlayer_set" in prefetch_cache:
                    # use prefetched styles-on-layer if available
                    return self.stylesonlayer_set.all()  # type: ignore
            return models.StylesOnLayer.objects.filter(layer__id=self.id)
        raise ValueError("Expected Layer object while resolving query!")

    description = graphene.String()

    def resolve_description(self, info) -> str:
        if not isinstance(self, models.Layer):
            raise ValueError("Expected object to be of type Layer when resolving query.")
        if not isinstance(self.description, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected Layer.description to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.description, base_media_url=base_media_url)

    serialized_leaflet_json = graphene.String()

    def resolve_serialized_leaflet_json(self, info) -> str:
        with log_execution_time_with_result("resolve_serialized_leaflet_json", log_level=logging.DEBUG) as result:
            if not isinstance(self, models.Layer):
                raise ValueError("Expected object to be of type Layer when resolving query.")
            if not isinstance(self.serialized_leaflet_json, dict):
                # Not sure why but the linter thinks self.serialized_leaflet_json here is potentially
                # graphene.String() when the same code works for MapData.geojson.
                raise ValueError("Expected Layer.serialized_leaflet_json to be of type dict at runtime.")

            result["layer_id"] = self.id
            result["layer_name"] = self.name

            data_obj = self.serialized_leaflet_json

            base_media_url = base_url_from_request(info.context)

            # Jeez, I can't wait until I move the serialization code to the backend...
            # HACK: This is for cleaning the image src to make sure it uses the absolute media url.
            for feature in data_obj["featureCollection"]["features"]:
                if "properties" in feature:
                    properties = feature["properties"]
                    if "__popupHTML" in properties and properties["__popupHTML"] is not None:
                        properties["__popupHTML"] = convert_relative_links_to_absolute(
                            html=properties["__popupHTML"],
                            base_media_url=base_media_url,
                        )
                    if (
                        "__pointDivIconStyleProps" in properties
                        and "html" in properties["__pointDivIconStyleProps"]
                        and properties["__pointDivIconStyleProps"]["html"] is not None
                    ):
                        properties["__pointDivIconStyleProps"]["html"] = convert_relative_links_to_absolute(
                            html=properties["__pointDivIconStyleProps"]["html"],
                            base_media_url=base_media_url,
                        )
            return json.dumps(data_obj)


class LayerTypeWithoutSerializedLeafletJSON(DjangoObjectType):
    """
    Defensive type to prevent people from querying serializedLeafletJSON from allLayers, which
    would be too computationally expensive and probably isn't needed by any API client.
    """

    map_data = graphene.Field(MapDataWithoutGeoJsonType)

    class Meta:  # type: ignore
        model = models.Layer
        fields = [
            "id",
            "name",
            "description",
            "map_data",
        ]

    description = graphene.String()

    def resolve_description(self, info) -> str:
        if not isinstance(self, models.Layer):
            raise ValueError("Expected object to be of type Layer when resolving query.")
        if not isinstance(self.description, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected Layer.description to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.description, base_media_url=base_media_url)


class LayerOnLayerGroupType(DjangoObjectType):

    class Meta:
        model = models.LayerOnLayerGroup
        fields = [
            "active_by_default",
            "display_order",
        ]

    layer_id = graphene.String()

    def resolve_layer_id(self, info):
        if isinstance(self, models.LayerOnLayerGroup):
            return str(self.layer.id)
        raise ValueError("Expected LayerOnLayerGroup object while resolving query!")


class LayerGroupOnQuestionType(DjangoObjectType):
    class Meta:
        model = models.LayerGroupOnQuestion
        fields = [
            "group_name",
            "group_description",
            "display_order",
        ]

    group_description = graphene.String()

    def resolve_group_description(self, info) -> str:
        if not isinstance(self, models.LayerGroupOnQuestion):
            raise ValueError("Expected object to be of type LayerGroupOnQuestion when resolving query.")
        if not isinstance(self.group_description, str):
            # Not sure why but the linter thinks self.group_description here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected page.group_description to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.group_description, base_media_url=base_media_url)

    layers_on_layer_group = graphene.List(LayerOnLayerGroupType)

    def resolve_layers_on_layer_group(self, info):
        if isinstance(self, models.LayerGroupOnQuestion):
            if prefetch_cache := getattr(self, "_prefetched_objects_cache", None):
                if "layers" in prefetch_cache:
                    # use prefetched layers if available
                    return self.layers.all().filter(layer__published_state__in=info.context.published_state)  # type: ignore
            return (
                models.LayerOnLayerGroup.objects.filter(layer_group_on_question=self)
                .distinct()
                .select_related("layer")
                .defer(
                    "layer__serialized_leaflet_json",
                )
                .filter(layer__published_state__in=info.context.published_state)
            )
        raise ValueError("Expected LayerGroupOnQuestion object while resolving query!")


class QuestionTabType(DjangoObjectType):

    class Meta:
        model = models.QuestionTab
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "slug",
            "icon_url",
        ]

    icon_url = graphene.String()

    def resolve_icon_url(self, info):
        if isinstance(self, models.QuestionTab):
            url = str(self.icon.file.url)
            if url.startswith(settings.MEDIA_URL):
                # HACK: For some reason that I cannot figure out, the media
                # url gets appended to the start of this file field, but not
                # any others that I have observed. This is a hacky fix.
                return url.removeprefix(settings.MEDIA_URL)
            return url
        raise ValueError("Expected QuestionTab object while resolving query!")

    content = graphene.String()

    def resolve_content(self, info) -> str:
        if not isinstance(self, models.QuestionTab):
            raise ValueError("Expected object to be of type QuestionTab when resolving query.")
        if not isinstance(self.content, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected QuestionTab.content to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.content, base_media_url=base_media_url)


class InitiativeTagType(DjangoObjectType):
    class Meta:
        model = models.InitiativeTag
        fields = ["id", "name", "text_color", "background_color"]


class InitiativeType(DjangoObjectType):
    class Meta:
        model = models.Initiative
        fields = [
            "id",
            "title",
            "link",
            "image",
            "content",
            "tags",
        ]

    content = graphene.String()

    def resolve_content(self, info) -> str:
        if not isinstance(self, models.Initiative):
            raise ValueError("Expected object to be of type Initiative when resolving query.")
        if not isinstance(self.content, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected initiative.content to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.content, base_media_url=base_media_url)


class QuestionSashType(DjangoObjectType):
    class Meta:
        model = models.QuestionSash
        fields = [
            "id",
            "text",
            "text_color",
            "background_color",
        ]


class BasemapSourceType(DjangoObjectType):
    class Meta:
        model = models.BasemapSource
        fields = [
            "name",
            "tile_url",
            "max_zoom",
            "attribution",
            # "is_default"
            # ^^ excluded because being "default" is an overloaded concept here. When you see "is_default=True", it means that
            #    that basemap is the global default basemap for all questions at question-editing time, while "is_default_for_question"
            #    means that when a particular question is clicked on by a visitor to the site, that is the basemap that should be loaded
            #    by default.
        ]


class BasemapSourceOnQuestionType(DjangoObjectType):
    class Meta:
        model = models.BasemapSourceOnQuestion
        fields = [
            "basemap_source",
            "is_default_for_question",
        ]


class QuestionType(DjangoObjectType):
    class Meta:
        model = models.Question
        fields = [
            "id",
            "title",
            "subtitle",
            "image",
            "sash",
            "initiatives",
            "tabs",
            "slug",
            "display_order",
            "basemaps",
            "num_initiatives",
        ]

    # Link one half of the many-to-many through table in the graphql schema
    layer_groups_on_question = graphene.List(LayerGroupOnQuestionType)

    def resolve_layer_groups_on_question(self, info):
        if prefetch_cache := getattr(self, "_prefetched_objects_cache", None):
            if "layer_groups" in prefetch_cache:
                # use prefetched layer-groups if available
                return self.layer_groups.all()  # type: ignore
        return models.LayerGroupOnQuestion.objects.filter(question=self)

    basemaps = graphene.List(BasemapSourceOnQuestionType)

    def resolve_basemaps(self, info):
        return models.BasemapSourceOnQuestion.objects.filter(question=self)

    def resolve_initiatives(self, info):
        return models.Initiative.objects.filter(published_state__in=info.context.published_state, question=self)

    num_initiatives = graphene.Int()

    def resolve_num_initiatives(self, info):
        return models.Initiative.objects.filter(
            published_state__in=info.context.published_state, question=self
        ).count()


class PageType(DjangoObjectType):
    class Meta:
        model = models.Page
        fields = [
            "id",
            "title",
            "content",
            "background_image",
        ]

    content = graphene.String()

    def resolve_content(self, info) -> str:
        if not isinstance(self, models.Page):
            raise ValueError("Expected object to be of type Page when resolving query.")
        if not isinstance(self.content, str):
            # Not sure why but the linter thinks self.content here is potentially
            # graphene.String() when the same code works for MapData.geojson.
            raise ValueError("Expected page.content to be of type string at runtime.")

        base_media_url = base_url_from_request(info.context)
        return convert_relative_links_to_absolute(html=self.content, base_media_url=base_media_url)


def get_requested_fields(info: ResolveInfo) -> List[str]:
    """
    Get the graphene fields being resolved at this stage of the request.
    NOTE: Fields are returned in Graphql-style camelCase, e.g., "fieldName".
    """
    selection_set = info.field_nodes[0].selection_set
    if selection_set is None:
        return []
    requested_fields = []
    for field in selection_set.selections:
        name = getattr(field, "name", None)
        value = getattr(name, "value", None)
        if value is not None:
            requested_fields.append(value)
    return requested_fields


def optimized_map_data_resolve_qs(info: ResolveInfo) -> QuerySet[models.MapData]:
    """
    Defer expensive map-data fields when they're not requested to speed up loading times.
    """
    queryset = models.MapData.objects.all()
    requested_fields = get_requested_fields(info)
    if "geojson" not in requested_fields:
        queryset = queryset.defer("_geojson")
    return queryset.all()


def optimized_layer_resolve_qs(info: ResolveInfo) -> QuerySet[models.Layer]:
    """
    Defer expensive map-data fields when they're not requested to speed up loading times.
    """
    queryset = models.Layer.objects.all()
    requested_fields = get_requested_fields(info)
    if "serializedLeafletJson" not in requested_fields:
        # We know we won't be accessing serialized_leaflet_json
        queryset = queryset.defer("serialized_leaflet_json")
    # This will always send another request when accessing _geojson, but
    # it will speed up queries that don't access _geojson significantly.
    queryset = queryset.select_related("map_data").defer("map_data___geojson")

    # Styles on a layer are often fetched at the same time.
    queryset = queryset.prefetch_related("stylesonlayer_set")

    return queryset.all()


def optimized_question_resolve_qs() -> QuerySet[models.Question]:
    """
    Defer the expensive `serialized_leaflet_json` field and prefetch layers + layer-groups.
    """
    return models.Question.objects.prefetch_related(
        Prefetch(
            # Prefetch layer groups on each question
            "layer_groups",
            queryset=models.LayerGroupOnQuestion.objects.prefetch_related(
                Prefetch(
                    # Prefetch layer ids on each layer group
                    "layers",
                    queryset=models.LayerOnLayerGroup.objects.select_related("layer")
                    .defer("layer__serialized_leaflet_json")
                    .order_by("display_order"),
                )
            ).order_by("display_order"),
        ),
    ).prefetch_related("basemaps")


class Query(graphene.ObjectType):

    base_admin_url = graphene.Field(graphene.String)

    layer = graphene.Field(LayerType, id=graphene.UUID(required=True))

    all_questions = graphene.List(QuestionType)
    question = graphene.Field(QuestionType, id=graphene.UUID(required=True))
    question_by_slug = graphene.Field(QuestionType, slug=graphene.String(required=True))
    question_tab_by_id = graphene.Field(QuestionTabType, id=graphene.UUID(required=True))
    question_tab_by_slug = graphene.Field(
        QuestionTabType,
        question_slug=graphene.String(required=True),
        question_tab_slug=graphene.String(required=True),
    )
    default_question_tab = graphene.Field(
        QuestionTabType,
        question_slug=graphene.String(required=True),
    )

    all_map_datas = graphene.List(MapDataWithoutGeoJsonType)
    map_data = graphene.Field(MapDataType, id=graphene.UUID(required=True))
    map_data_by_dropdown_name = graphene.Field(MapDataType, dropdownName=graphene.String(required=True))

    all_styles_on_layers = graphene.List(StylesOnLayersType)
    styles_on_layer = graphene.Field(StylesOnLayersType, id=graphene.UUID(required=True))

    all_styles = graphene.List(StyleType)
    style = graphene.Field(StyleType, id=graphene.UUID(required=True))

    all_pages = graphene.List(PageType)
    page = graphene.Field(PageType, id=graphene.UUID(required=True))

    def resolve_base_admin_url(self, info):
        return base_url_from_request(info.context)

    def resolve_layer(self, info, id):
        return optimized_layer_resolve_qs(info).filter(published_state__in=info.context.published_state).get(pk=id)

    def resolve_layer_group(self, info, question_id):
        return (
            models.LayerGroupOnQuestion.objects.filter(layeronquestion__question__id=question_id)
            .select_related("layer_on_layer_group")
            .distinct()
        )

    def resolve_all_questions(self, info):
        return optimized_question_resolve_qs().filter(published_state__in=info.context.published_state)

    def resolve_question(self, info, id):
        return optimized_question_resolve_qs().filter(published_state__in=info.context.published_state).get(pk=id)

    def resolve_question_by_slug(self, info, slug: str):
        return models.Question.objects.filter(published_state__in=info.context.published_state).get(slug=slug)

    def resolve_question_tab_by_slug(self, info, question_slug: str, question_tab_slug: str):
        return models.QuestionTab.objects.filter(
            slug=question_tab_slug,
            question__slug=question_slug,
            question__published_state__in=info.context.published_state,
        ).first()

    def resolve_default_question_tab(self, info, question_slug: str):
        return models.QuestionTab.objects.filter(
            question__slug=question_slug,
            question__published_state__in=info.context.published_state,
        ).first()

    def resolve_question_tab_by_id(self, info, id):
        return models.QuestionTab.objects.filter(
            question__published_state__in=info.context.published_state,
        ).get(pk=id)

    def resolve_all_map_datas(self, info):
        return optimized_map_data_resolve_qs(info).all()

    def resolve_map_data(self, info, id):
        return optimized_map_data_resolve_qs(info).get(pk=id)

    def resolve_map_data_by_dropdown_name(self, info, dropdownName: str):
        optimized_map_data_resolve_qs(info).get(name=dropdownName.split("(")[0].strip())

    def resolve_all_styles_on_layers(self, info):
        return models.StylesOnLayer.objects.all()

    def resolve_styles_on_layer(self, info, id):
        return models.StylesOnLayer.objects.get(pk=id)

    def resolve_all_styles(self, info):
        return models.Style.objects.all()

    def resolve_style(self, info, id):
        return models.Style.objects.get(pk=id)

    def resolve_all_pages(self, info):
        return models.Page.objects.all()

    def resolve_page(self, info, id):
        return models.Page.objects.get(pk=id)


def get_schema() -> graphene.Schema:
    return graphene.Schema(query=Query)


class PublishedStateGraphQLView(GraphQLView):

    @staticmethod
    def get_published_state_from_request_params(params: dict | None) -> list[PublishedState]:
        if params is not None and "visibility" in params:
            if params["visibility"] == "all":
                return [PublishedState.PUBLISHED, PublishedState.DRAFT]
            elif params["visibility"] == "draft":
                return [PublishedState.DRAFT]
        return [PublishedState.PUBLISHED]

    def get_context(self, request):
        context = super().get_context(request)
        # add published state to every graphql request's context
        context.published_state = self.get_published_state_from_request_params(request.GET)
        return context
