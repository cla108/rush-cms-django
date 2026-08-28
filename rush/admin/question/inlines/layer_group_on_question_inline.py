from django.forms import ModelForm
from nested_admin.forms import SortableHiddenMixin
from nested_admin.nested import NestedTabularInline

from rush.admin.question.inlines import LayerOnLayerGroupInline
from rush.admin.utils import SuperuserStrictCleanMixin
from rush.admin.widgets import SummernoteWidget
from rush.models import LayerGroupOnQuestion


class LayerGroupOnQuestionInlineForm(ModelForm):
    class Meta:
        model = LayerGroupOnQuestion
        fields = [
            "group_name",
            "group_description",
            "group_description_strict_clean",
            "behaviour",
            "display_order",
        ]
        widgets = {
            "group_description": SummernoteWidget(
                toolbar=[
                    ["style", ["style"]],
                    ["font", ["bold", "underline", "clear"]],
                    ["fontname", ["fontname"]],
                    ["fontsize", ["fontsize"]],
                    ["color", ["color"]],
                    ["para", ["ul", "ol", "paragraph"]],
                    [
                        "insert",
                        [
                            "link",
                            "picture",
                        ],
                    ],
                    ["view", ["codeview"]],
                ],
            ),
        }


class LayerGroupOnQuestionInline(SuperuserStrictCleanMixin, SortableHiddenMixin, NestedTabularInline):
    """
    An inline group of layers that are assigned to a question.
    """

    verbose_name_plural = "Layer Groups"
    form = LayerGroupOnQuestionInlineForm
    model = LayerGroupOnQuestion
    extra = 0
    exclude = ["id"]
    inlines = [LayerOnLayerGroupInline]
    sortable_field_name = "display_order"

    def get_queryset(self, request):
        """
        Optimize queryset to prefetch nested LayerOnLayerGroup objects with deferred heavy fields.
        """
        qs = super().get_queryset(request)
        # Prefetch the layers relation to avoid N+1 queries and defer heavy fields
        from django.db.models import Prefetch

        from rush.models import Layer, LayerOnLayerGroup

        return qs.prefetch_related(
            Prefetch(
                "layers",  # This is the related_name from LayerOnLayerGroup
                queryset=LayerOnLayerGroup.objects.select_related("layer__map_data").defer(
                    "layer__serialized_leaflet_json",
                    "layer__map_data___geojson",
                    "layer__map_data__geotiff",
                ),
            )
        )

    def get_fields(self, request, obj=None):
        """
        Only superusers should be able to see and edit the hidden field `group_type`.
        Group type defines special behaviour for `LayerGroupOnQuestion` that should
        not be exposed to regular staff users.
        """
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [x for x in fields if x != "behaviour"]
        return fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "group_description":
            formfield.initial = (
                '<p class="rush-subtitle"><span style="font-size: 10px;">Example group title</span></p>'
            )
        return formfield
