from nested_admin.forms import SortableHiddenMixin
from nested_admin.nested import NestedTabularInline

from rush.models import Layer, LayerOnLayerGroup


class LayerOnLayerGroupInline(SortableHiddenMixin, NestedTabularInline):
    """
    A layer that is nested inside of a layer-group on a question.
    """

    verbose_name_plural = "Layers"
    model = LayerOnLayerGroup
    extra = 0
    exclude = ["id"]
    autocomplete_fields = ["layer"]
    sortable_field_name = "display_order"

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if "layer" in formset.form.base_fields:
            # Modify the layer field queryset to defer heavy fields. This can't be done in QuestionAdmin
            # because the nested-inline-admin does a lot of dynamic formset/queryset creation on the fly.
            formset.form.base_fields["layer"].queryset = Layer.objects.select_related("map_data").defer(
                "serialized_leaflet_json",
                "map_data___geojson",
                "map_data__geotiff",
            )
        return formset
