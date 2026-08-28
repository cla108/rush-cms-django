from pytest import mark, raises

from rush.models import (
    BasemapSourceOnQuestion,
    Initiative,
    Layer,
    LayerGroupOnQuestion,
    LayerOnLayerGroup,
    PublishedState,
    Question,
    QuestionTab,
    Style,
    StylesOnLayer,
    Tooltip,
)
from rush.models.duplicators import (
    DuplicationFail,
    InitiativeDuplicator,
    LayerDuplicator,
    QuestionDuplicator,
)
from rush.tests.models.helpers import (
    create_test_initiative,
    create_test_layer,
    create_test_question,
    get_ids,
)

#######################
# Question Duplicator #
#######################


def _duplicate_question() -> tuple[Question, Question]:
    """
    Create a test question instance, and a duplicate version of it.
    """
    assert Question.objects.count() == 0
    instance = create_test_question()
    assert Question.objects.count() == 1
    duplicate = QuestionDuplicator(instance).duplicate()
    assert Question.objects.count() == 2
    assert Question.objects.filter(id=instance.id).first() == instance
    assert Question.objects.filter(id=duplicate.id).first() == duplicate
    return instance, duplicate


@mark.django_db
def test_question_duplicator_copies_non_unique_primitive_fields_by_value():
    """
    The question duplicator should copy the following non-unique primitive fields by value.
    """
    instance, duplicate = _duplicate_question()
    assert duplicate.title == f"DUPLICATE - {instance.title}"
    assert duplicate.subtitle == instance.subtitle
    assert duplicate.image.url == instance.image.url
    assert duplicate.is_image_compressed == instance.is_image_compressed
    assert duplicate.sash == instance.sash
    assert duplicate.region == instance.region


@mark.django_db
def test_question_duplicator_sets_published_state_to_draft():
    """
    The question duplicator should always set the published state to draft so that clients don't see
    duplicate data on the frontend.
    """
    instance, duplicate = _duplicate_question()
    assert instance.published_state == PublishedState.PUBLISHED
    assert duplicate.published_state == PublishedState.DRAFT


@mark.django_db
def test_question_duplicator_modifies_unique_primitive_fields():
    """
    The question duplicator should modify the following unique fields before copying them.
    """
    instance, duplicate = _duplicate_question()
    assert duplicate.id != instance.id
    assert duplicate.slug != instance.slug


@mark.django_db
def test_question_duplicator_sets_duplicate_display_order_to_zero():
    """
    Duplicated questions should appear at the top in the admin site.
    """
    _, duplicate = _duplicate_question()
    assert duplicate.display_order == 0


@mark.django_db
def test_question_duplicator_increments_existing_question_display_ordering():
    """
    All existing questions need to move 1 up in the display ordering when a question is duplicated.
    """
    q1 = create_test_question()
    q2 = create_test_question()
    q3 = create_test_question()
    assert q1.display_order == 0
    assert q2.display_order == 1
    assert q3.display_order == 2
    QuestionDuplicator(q1).duplicate()
    q1.refresh_from_db()
    q2.refresh_from_db()
    q3.refresh_from_db()
    assert q1.display_order == 1
    assert q2.display_order == 2
    assert q3.display_order == 3


@mark.django_db
@mark.parametrize(
    "target, err_msg",
    [
        (None, "Duplication instance cannot be none for <QuestionDuplicator>"),
        (object(), "Wrong instance type for <QuestionDuplicator>"),
    ],
)
def test_question_duplicator_raises_when_invalid_duplication_target(target, err_msg):
    with raises(DuplicationFail, match=err_msg):
        QuestionDuplicator(target).duplicate()


#
# Question Duplicator: Question-tab.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_tabs():
    instance, duplicate = _duplicate_question()
    assert instance.tabs.count() != 0  # type: ignore
    assert duplicate.tabs.count() != 0  # type: ignore
    assert instance.tabs.count() == duplicate.tabs.count()  # type: ignore


@mark.django_db
def test_question_duplicator_creates_new_tab_instances():
    """
    The question duplicator should duplicate tabs with different ids from the original question
    because a question tab can only correspond to one question.
    """
    instance, duplicate = _duplicate_question()
    instance_ids = get_ids(instance.tabs)  # type: ignore
    for duplicate_id in get_ids(duplicate.tabs):  # type: ignore
        assert duplicate_id not in instance_ids


@mark.django_db
def test_question_duplicator_copies_question_tab_data_by_value():
    """
    Every tab that was duplicated should have data corresponding to a tab from the original question.
    """
    instance, duplicate = _duplicate_question()
    tab_data = lambda question: [
        x
        for x in QuestionTab.objects.filter(question=question)
        .values_list("icon", "title", "content", "display_order")
        .order_by("display_order")
    ]
    instance_tab_data = tab_data(instance)
    for duplicate_tab_data in tab_data(duplicate):
        assert duplicate_tab_data in instance_tab_data


#
# Question Duplicator: Initiative.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_initiatives():
    instance, duplicate = _duplicate_question()
    assert instance.initiatives.count() != 0
    assert duplicate.initiatives.count() != 0
    assert instance.initiatives.count() == duplicate.initiatives.count()


@mark.django_db
def test_question_duplicator_copies_initiatives_by_reference():
    """
    The question duplicator should duplicate initiatives by reference (same ids).
    """
    instance, duplicate = _duplicate_question()
    instance_ids = get_ids(instance.initiatives)
    for duplicate_id in get_ids(duplicate.initiatives):
        assert duplicate_id in instance_ids


#
# Question Duplicator: Basemap-source.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_basemap_sources():
    instance, duplicate = _duplicate_question()
    assert instance.basemaps.count() != 0  # type: ignore
    assert duplicate.basemaps.count() != 0  # type: ignore
    assert instance.basemaps.count() == duplicate.basemaps.count()  # type: ignore


@mark.django_db
def test_question_duplicator_copies_basemap_sources_by_reference():
    """
    The question duplicator should duplicate basemaps by reference (same ids).
    """
    instance, duplicate = _duplicate_question()
    instance_ids = get_ids(instance.basemaps)  # type: ignore
    for duplicate_id in get_ids(duplicate.basemaps):  # type: ignore
        assert duplicate_id not in instance_ids


#
# Question Duplicator: Basemap-source-on-question.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_basemap_source_on_questions():
    instance, duplicate = _duplicate_question()
    duplicate_relations = BasemapSourceOnQuestion.objects.filter(question=duplicate)
    instance_relations = BasemapSourceOnQuestion.objects.filter(question=instance)
    assert duplicate_relations.count() != 0
    assert instance_relations.count() != 0
    assert duplicate_relations.count() == instance_relations.count()


@mark.django_db
def test_question_duplicator_creates_new_basemap_source_on_question_instances():
    """
    The question duplicator should create new basemap_source_on_question instances when duplicating because
    these instances join the basemap-source and question tables. Therefore: new question ==> new joins.
    """
    instance, duplicate = _duplicate_question()
    duplicate_relations = BasemapSourceOnQuestion.objects.filter(question=duplicate)
    instance_relation_ids = get_ids(BasemapSourceOnQuestion.objects.filter(question=instance))
    for duplicate_id in get_ids(duplicate_relations):
        assert duplicate_id not in instance_relation_ids


@mark.django_db
def test_question_duplicator_copies_layer_on_basemap_source_on_question_data_by_value():
    """
    Every basemap_source_on_question that was duplicated should have data that corresponds to a
    basemap_source_on_question from the original question.
    """
    instance, duplicate = _duplicate_question()
    data = lambda question: [
        x
        for x in BasemapSourceOnQuestion.objects.filter(question=question)
        .values_list("basemap_source", "is_default_for_question")
        .order_by("id")
    ]
    instance_data = data(instance)
    for duplicate_data in data(duplicate):
        assert duplicate_data in instance_data


#
# Question Duplicator: Layer.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_layers():
    instance, duplicate = _duplicate_question()
    duplicate_layers = [
        x.layer for x in LayerOnLayerGroup.objects.filter(layer_group_on_question__question=duplicate)
    ]
    instance_layers = [
        x.layer for x in LayerOnLayerGroup.objects.filter(layer_group_on_question__question=instance)
    ]
    assert len(instance_layers) != 0
    assert len(duplicate_layers) != 0
    assert len(instance_layers) == len(duplicate_layers)


@mark.django_db
def test_question_duplicator_copies_layers_by_reference():
    instance, duplicate = _duplicate_question()
    duplicate_layers = [
        x.layer for x in LayerOnLayerGroup.objects.filter(layer_group_on_question__question=duplicate)
    ]
    instance_layers_ids = [
        x.layer.id for x in LayerOnLayerGroup.objects.filter(layer_group_on_question__question=instance)
    ]
    for duplicate_layer in duplicate_layers:
        assert duplicate_layer.id in instance_layers_ids


#
# Question Duplicator: Layer-on-layer-group.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_layer_on_layer_groups():
    instance, duplicate = _duplicate_question()
    duplicate_lolgs = LayerOnLayerGroup.objects.filter(layer_group_on_question__question=duplicate)
    instance_lolgs = LayerOnLayerGroup.objects.filter(layer_group_on_question__question=instance)
    assert duplicate_lolgs.count() != 0
    assert instance_lolgs.count() != 0
    assert duplicate_lolgs.count() == instance_lolgs.count()


@mark.django_db
def test_question_duplicator_creates_new_layer_on_layer_group_instances():
    """
    The question duplicator should create new layer-on-layer-group instances when duplicating because
    these instances join the layer and question tables. Therefore: new question ==> new joins.
    """
    instance, duplicate = _duplicate_question()
    duplicate_lolgs = LayerOnLayerGroup.objects.filter(layer_group_on_question__question=duplicate)
    instance_lolg_ids = get_ids(LayerOnLayerGroup.objects.filter(layer_group_on_question__question=instance))
    for duplicate_id in get_ids(duplicate_lolgs):
        assert duplicate_id not in instance_lolg_ids


@mark.django_db
def test_question_duplicator_copies_layer_on_layer_group_data_by_value():
    """
    Every layer-on-layer-group that was duplicated should have data that corresponds to a
    layer-on-layer-group from the original question.
    """
    instance, duplicate = _duplicate_question()
    data = lambda question: [
        x
        for x in LayerOnLayerGroup.objects.filter(layer_group_on_question__question=question)
        .values_list("layer", "active_by_default", "display_order")
        .order_by("display_order")
    ]
    instance_data = data(instance)
    for duplicate_data in data(duplicate):
        assert duplicate_data in instance_data


#
# Question Duplicator: Layer-group-on-question.
#


@mark.django_db
def test_question_duplicator_copies_correct_number_of_layer_group_on_questions():
    instance, duplicate = _duplicate_question()
    duplicate_lgoqs = LayerGroupOnQuestion.objects.filter(question=duplicate)
    instance_lgoqs = LayerGroupOnQuestion.objects.filter(question=instance)
    assert duplicate_lgoqs.count() != 0
    assert instance_lgoqs.count() != 0
    assert duplicate_lgoqs.count() == instance_lgoqs.count()


@mark.django_db
def test_question_duplicator_creates_new_layer_group_on_question_instances():
    """
    The question duplicator should create new layer-group-on-question instances when duplicating because
    these instances join the layer and question tables. Therefore: new question ==> new joins.
    """
    instance, duplicate = _duplicate_question()
    duplicate_groups = LayerGroupOnQuestion.objects.filter(question=duplicate)
    instance_group_ids = get_ids(LayerGroupOnQuestion.objects.filter(question=instance))
    for duplicate_id in get_ids(duplicate_groups):
        assert duplicate_id not in instance_group_ids


@mark.django_db
def test_question_duplicator_copies_layer_group_on_question_data_by_value():
    """
    Every layer-group-on-question that was duplicated should have data that corresponds to a
    layer-group-on-question from the original question.
    """
    instance, duplicate = _duplicate_question()
    data = lambda question: [
        x
        for x in LayerGroupOnQuestion.objects.filter(question=question)
        .values_list("group_name", "group_description", "behaviour", "display_order")
        .order_by("display_order")
    ]
    instance_data = data(instance)
    for duplicate_data in data(duplicate):
        assert duplicate_data in instance_data


#########################
# Initiative Duplicator #
#########################


def _duplicate_initiative() -> tuple[Initiative, Initiative]:
    """
    Create a test initiative instance, and a duplicate version of it.
    """
    assert Initiative.objects.count() == 0
    instance = create_test_initiative()
    assert Initiative.objects.count() == 1
    duplicate = InitiativeDuplicator(instance).duplicate()
    assert Initiative.objects.count() == 2
    assert Initiative.objects.filter(id=instance.id).first() == instance
    assert Initiative.objects.filter(id=duplicate.id).first() == duplicate
    return instance, duplicate


@mark.django_db
def test_initiative_duplicator_copies_non_unique_primitive_fields_by_value():
    """
    The initiative duplicator should copy the following non-unique primitive fields by value.
    """
    instance, duplicate = _duplicate_initiative()
    assert duplicate.link == instance.link
    assert duplicate.image.url == instance.image.url
    assert duplicate.title == f"DUPLICATE - {instance.title}"
    assert duplicate.content == instance.content


@mark.django_db
def test_initiative_duplicator_sets_published_state_to_draft():
    """
    The initiative duplicator should always set the published state to draft so that clients don't see
    duplicate data on the frontend.
    """
    instance, duplicate = _duplicate_initiative()
    assert instance.published_state == PublishedState.PUBLISHED
    assert duplicate.published_state == PublishedState.DRAFT


@mark.django_db
@mark.parametrize(
    "target, err_msg",
    [
        (None, "Duplication instance cannot be none for <InitiativeDuplicator>"),
        (object(), "Wrong instance type for <InitiativeDuplicator>"),
    ],
)
def test_initiative_duplicator_raises_when_invalid_duplication_target(target, err_msg):
    with raises(DuplicationFail, match=err_msg):
        InitiativeDuplicator(target).duplicate()


#
# Initiative Duplicator: Initiative-tag.
#


@mark.django_db
def test_initiative_duplicator_copies_correct_number_of_initiative_tags():
    instance, duplicate = _duplicate_initiative()
    assert duplicate.tags.count() != 0
    assert instance.tags.count() != 0
    assert instance.tags.count() == duplicate.tags.count()


@mark.django_db
def test_initiative_duplicator_copies_initiative_tags_by_reference():
    instance, duplicate = _duplicate_initiative()
    instance_tag_ids = [x.id for x in instance.tags.all()]
    for duplicate_tag in duplicate.tags.all():
        assert duplicate_tag.id in instance_tag_ids


####################
# Layer Duplicator #
####################


def _duplicate_layer() -> tuple[Layer, Layer]:
    """
    Create a test layer instance, and a duplicate version of it.
    """
    assert Layer.objects.count() == 0
    instance = create_test_layer()
    assert Layer.objects.count() == 1
    duplicate = LayerDuplicator(instance).duplicate()
    assert Layer.objects.count() == 2
    assert Layer.objects.filter(id=instance.id).first() == instance
    assert Layer.objects.filter(id=duplicate.id).first() == duplicate
    return instance, duplicate


@mark.django_db
def test_layer_duplicator_copies_non_unique_primitive_fields_by_value():
    """
    The layer duplicator should copy the following non-unique primitive fields by value.
    """
    instance, duplicate = _duplicate_layer()
    assert duplicate.name == f"DUPLICATE - {instance.name}"
    assert duplicate.legend_title == instance.legend_title
    assert duplicate.description == instance.description
    assert duplicate.serialized_leaflet_json == instance.serialized_leaflet_json


@mark.django_db
def test_layer_duplicator_sets_published_state_to_draft():
    """
    The layer duplicator should always set the published state to draft so that clients don't see
    duplicate data on the frontend.
    """
    instance, duplicate = _duplicate_layer()
    assert instance.published_state == PublishedState.PUBLISHED
    assert duplicate.published_state == PublishedState.DRAFT


@mark.django_db
@mark.parametrize(
    "target, err_msg",
    [
        (None, "Duplication instance cannot be none for <LayerDuplicator>"),
        (object(), "Wrong instance type for <LayerDuplicator>"),
    ],
)
def test_layer_duplicator_raises_when_invalid_duplication_target(target, err_msg):
    with raises(DuplicationFail, match=err_msg):
        LayerDuplicator(target).duplicate()


#
# Layer Duplicator: Map-data.
#


@mark.django_db
def test_layer_duplicator_copies_map_data_by_reference():
    instance, duplicate = _duplicate_layer()
    assert duplicate.map_data.id == instance.map_data.id


#
# Layer Duplicator: Styles-on-layer.
#


@mark.django_db
def test_layer_duplicator_copies_the_correct_number_of_styles_on_layers():
    instance, duplicate = _duplicate_layer()
    duplicate_tooltips = StylesOnLayer.objects.filter(layer=duplicate)
    instance_tooltips = StylesOnLayer.objects.filter(layer=instance)
    assert duplicate_tooltips.count() != 0
    assert instance_tooltips.count() != 0
    assert duplicate_tooltips.count() == instance_tooltips.count()


@mark.django_db
def test_layer_duplicator_creates_new_styles_on_layer_instances():
    instance, duplicate = _duplicate_layer()
    duplicate_styles_on_layers = StylesOnLayer.objects.filter(layer=duplicate)
    instance_styles_on_layer_ids = get_ids(StylesOnLayer.objects.filter(layer=instance))
    for duplicate_id in get_ids(duplicate_styles_on_layers):
        assert duplicate_id not in instance_styles_on_layer_ids


@mark.django_db
def test_layer_duplicator_copies_styles_on_layer_data_by_value():
    instance, duplicate = _duplicate_layer()

    data = lambda layer: [
        x
        for x in StylesOnLayer.objects.filter(layer=layer)
        .values_list("style", "legend_description", "display_order", "feature_mapping", "popup")
        .order_by("display_order")
    ]

    instance_data = data(instance)
    for duplicate_data in data(duplicate):
        assert duplicate_data in instance_data


#
# Layer Duplicator: Tooltip.
#


@mark.django_db
def test_layer_duplicator_copies_correct_number_of_tooltips():
    """
    Tooltips are 1-1 with styles-on-layer, and therefore need to be copied over as well.
    """

    instance, duplicate = _duplicate_layer()
    duplicate_tooltips = Tooltip.objects.filter(style_on_layer__layer=duplicate)
    instance_tooltips = Tooltip.objects.filter(style_on_layer__layer=instance)
    assert duplicate_tooltips.count() != 0
    assert instance_tooltips.count() != 0
    assert duplicate_tooltips.count() == instance_tooltips.count()


@mark.django_db
def test_layer_duplicator_creates_new_tooltip_instances():
    instance, duplicate = _duplicate_layer()
    duplicate_tooltips = Tooltip.objects.filter(style_on_layer__layer=duplicate)
    instance_tooltip_ids = get_ids(Tooltip.objects.filter(style_on_layer__layer=instance))
    for duplicate_id in get_ids(duplicate_tooltips):
        assert duplicate_id not in instance_tooltip_ids


@mark.django_db
def test_layer_duplicator_copies_tooltip_data_by_value():

    instance, duplicate = _duplicate_layer()

    data = lambda layer: [
        x
        for x in Tooltip.objects.filter(style_on_layer__layer=layer)
        .values_list(
            # tooltip-data
            "label",
            "offset_x",
            "offset_y",
            "opacity",
            "direction",
            "permanent",
            "sticky",
            # styles-on-layer data (used as a fingerprint here) because the tooltip
            # should be copied over onto the correct styles-on-layer, but we can't compare
            # ids because both are deep-copied.
            "style_on_layer__style",
            "style_on_layer__legend_description",
            "style_on_layer__display_order",
            "style_on_layer__feature_mapping",
            "style_on_layer__popup",
        )
        .order_by("style_on_layer__display_order")
    ]

    instance_data = data(instance)
    for duplicate_data in data(duplicate):
        assert duplicate_data in instance_data


#
# Layer Duplicator: Style.
#


@mark.django_db
def test_layer_duplicator_copies_correct_number_of_styles():
    instance, duplicate = _duplicate_layer()
    assert duplicate.styles.count() != 0
    assert instance.styles.count() != 0
    assert duplicate.styles.count() == instance.styles.count()


@mark.django_db
def test_layer_duplicator_copies_styles_by_reference():
    instance, duplicate = _duplicate_layer()
    instance_style_ids = [x.id for x in instance.styles.all()]
    for duplicate_tag in duplicate.styles.all():
        assert duplicate_tag.id in instance_style_ids
