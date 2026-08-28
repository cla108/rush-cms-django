from abc import ABC, abstractmethod
from typing import Type
from uuid import uuid4

from django.db.models import Model

from rush.models import (
    BasemapSourceOnQuestion,
    Initiative,
    Layer,
    LayerGroupOnQuestion,
    LayerOnLayerGroup,
    PublishedState,
    Question,
    QuestionTab,
    StylesOnLayer,
    Tooltip,
)

"""
This file contains logic for duplicating RUSH models in the database.
"""


class DuplicatorBase(ABC):
    """
    A duplicator defines how a Django model type should be successfully "duplicated" in the database.
    It should also duplicate any related objects, and change any field values that would violate a
    unique constraint in the database.
    """

    def __init__(self, instance: Model):
        self.instance = instance
        if instance is None:
            raise DuplicationFail(self, "duplication instance cannot be none")
        if not isinstance(instance, self.duplication_cls()):
            raise DuplicationFail(self, "wrong instance type")

    @abstractmethod
    def duplication_cls(self) -> Type[Model]:
        """
        The type of Django model this duplicator works on.
        """
        ...

    @abstractmethod
    def duplicate(self) -> Model:
        """
        Duplicate a Django in the database. Return the duplicated model.
        """
        ...


class DuplicationFail(Exception):
    """
    Something went wrong while trying to duplicate an object.
    """

    def __init__(self, duplicator: DuplicatorBase, message: str):
        super().__init__(
            "{message} for <{classname}> with instance '{instance}'.".format(
                message=message.capitalize(),
                classname=duplicator.__class__.__name__,
                instance=str(duplicator.instance),
            )
        )


class QuestionDuplicator(DuplicatorBase):

    def duplicate(self) -> Question:
        """
        Create and return a duplicate Question.
        """

        assert isinstance(self.instance, Question)
        for question in Question.objects.all():
            # move all questions up in the order to make room for the duplicate
            question.display_order += 1
            question.full_clean()
            question.save()

        duplicate = Question.objects.create(
            title=f"DUPLICATE - {self.instance.title}",
            subtitle=self.instance.subtitle,
            image=self.instance.image,
            is_image_compressed=self.instance.is_image_compressed,
            slug=f"{self.instance.slug}-copy-{str(uuid4())[:4]}",
            sash=self.instance.sash,
            region=self.instance.region,
            display_order=0,
            published_state=PublishedState.DRAFT,
        )

        # Copy initiatives by reference
        duplicate.initiatives.set(self.instance.initiatives.all())

        # Copy tabs by value
        for tab in self.instance.tabs.all():  # type: ignore
            QuestionTab.objects.create(
                question=duplicate,
                icon=tab.icon,
                title=tab.title,
                content=tab.content,
                slug=tab.slug,
                display_order=tab.display_order,
            )

        # Copy basemap-sources by reference (through the basemap-source-on-question model
        # which is copied by value).
        for basemap_source_on_question in BasemapSourceOnQuestion.objects.filter(question=self.instance):  # type: ignore
            BasemapSourceOnQuestion.objects.create(
                question=duplicate,
                basemap_source=basemap_source_on_question.basemap_source,
                is_default_for_question=basemap_source_on_question.is_default_for_question,
            )

        group_map = {}  # id --> Layer-group-on-question
        for layer_on_layer_group in LayerOnLayerGroup.objects.filter(
            layer_group_on_question__question=self.instance
        ):
            instance_group = layer_on_layer_group.layer_group_on_question
            if instance_group.id not in group_map:
                # create duplicate layer-group-on-questions "on the fly"
                duplicate_group = LayerGroupOnQuestion.objects.create(
                    group_name=instance_group.group_name,
                    group_description=instance_group.group_description,
                    question=duplicate,
                    behaviour=instance_group.behaviour,
                    display_order=instance_group.display_order,
                )
                group_map[instance_group.id] = duplicate_group

            # now, create layer-on-layer-group poinging to correct (duplicated) group and
            # original layer reference.
            LayerOnLayerGroup.objects.create(
                layer=layer_on_layer_group.layer,
                layer_group_on_question=group_map[instance_group.id],
                active_by_default=layer_on_layer_group.active_by_default,
                display_order=layer_on_layer_group.display_order,
            )

        duplicate.full_clean()
        duplicate.save()
        return duplicate

    def duplication_cls(self) -> Type[Model]:
        return Question


class InitiativeDuplicator(DuplicatorBase):

    def duplicate(self) -> Initiative:
        """
        Create and return a duplicate Initiative.
        """

        assert isinstance(self.instance, Initiative)
        duplicate = Initiative.objects.create(
            link=self.instance.link,
            image=self.instance.image,
            title=f"DUPLICATE - {self.instance.title}",
            content=self.instance.content,
            published_state=PublishedState.DRAFT,
        )
        duplicate.tags.set(self.instance.tags.all())
        return duplicate

    def duplication_cls(self) -> Type[Model]:
        return Initiative


class LayerDuplicator(DuplicatorBase):

    def duplicate(self) -> Layer:
        """
        Create and return a duplicate Layer.
        """

        assert isinstance(self.instance, Layer)
        duplicate = Layer.objects.create(
            name=f"DUPLICATE - {self.instance.name}",
            legend_title=self.instance.legend_title,
            description=self.instance.description,
            map_data=self.instance.map_data,
            serialized_leaflet_json=self.instance.serialized_leaflet_json,
            published_state=PublishedState.DRAFT,
        )
        for styles_on_layer in StylesOnLayer.objects.filter(layer=self.instance):

            # create related styles-on-layer
            duplicate_style_on_layer = StylesOnLayer.objects.create(
                layer=duplicate,
                style=styles_on_layer.style,
                legend_description=styles_on_layer.legend_description,
                display_order=styles_on_layer.display_order,
                feature_mapping=styles_on_layer.feature_mapping,
                popup=styles_on_layer.popup,
            )

            # create double-related tooltip (if it exists)
            if tooltip := Tooltip.objects.filter(style_on_layer__id=styles_on_layer.id).first():
                Tooltip.objects.create(
                    style_on_layer=duplicate_style_on_layer,
                    label=tooltip.label,
                    offset_x=tooltip.offset_x,
                    offset_y=tooltip.offset_y,
                    opacity=tooltip.opacity,
                    direction=tooltip.direction,
                    permanent=tooltip.permanent,
                    sticky=tooltip.sticky,
                )

        return duplicate

    def duplication_cls(self) -> Type[Model]:
        return Layer
