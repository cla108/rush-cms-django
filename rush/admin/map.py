import json
import logging
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, List

import adminsortable2.admin as sortable_admin
from django import forms
from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.safestring import mark_safe
from silk.profiling.dynamic import silk_profile

from rush import models
from rush.admin import utils
from rush.admin.filters import PublishedStateFilter
from rush.admin.utils import SuperuserStrictCleanMixin, truncate_admin_text_from
from rush.admin.widgets import SummernoteWidget
from rush.models.duplicators import LayerDuplicator
from rush.models.style.tooltip import Direction

logger = logging.getLogger(__name__)


class StylesOnLayerInlineForm(forms.ModelForm):

    # Popup toggle
    draw_popup = forms.BooleanField(required=False)

    # Tooltip toggle (mostly aesthetic, but also lets the save() function know when
    # to attempt to create a related tooltip object on the styles-on-layer).
    draw_tooltip = forms.BooleanField(required=False)

    # Related Tooltip fields
    label = forms.CharField(required=False, label="Tooltip Label")
    label_strict_clean = forms.BooleanField(required=False, label="Tooltip Label Strict Clean")
    offset_x = forms.DecimalField(required=False, label="Tooltip offset X")
    offset_y = forms.DecimalField(required=False, label="Tooltip offset Y")
    opacity = forms.DecimalField(required=False, label="Tooltip Opacity")
    direction = forms.ChoiceField(choices=Direction.choices, required=False, label="Tooltip Direction")
    permanent = forms.BooleanField(required=False, label="Tooltip Permanent")
    sticky = forms.BooleanField(required=False, label="Tooltip Sticky")

    class Meta:
        model = models.StylesOnLayer
        fields = [
            "style",
            "feature_mapping",
            "legend_description",
            "legend_description_strict_clean",
            "draw_popup",  # only on form, not the model
            "popup",
            "popup_strict_clean",
        ]
        widgets = {
            "popup": SummernoteWidget(),
            "feature_mapping": forms.Textarea(attrs={"rows": 1, "cols": 50}),
        }

    def _init_tooltip_fields(self) -> None:
        """
        Initialize form widgets for related 'tooltip' object's form fields, and
        set the help-text for some of the form fields.
        """
        self.fields["label"].widget = SummernoteWidget(
            width="250px",
            height="100px",
            styleTags=[],
            toolbar=[["font", ["bold", "italic", "underline"]]],
        )
        self.fields["offset_x"].widget = utils.SliderAndTextboxNumberInput(min=-100, max=100, step=1)
        self.fields["offset_y"].widget = utils.SliderAndTextboxNumberInput(min=-100, max=100, step=1)
        self.fields["opacity"].widget = utils.SliderAndTextboxNumberInput(max=1, step=0.01)

        # Setting help text is done here instead of on the model because we're using custom form fields and
        # Django cannot automatically relate the tooltip formfields (on this form) to the tooltip model's fields.
        self.fields["direction"].help_text = "Where to draw the label relative to the marker."
        self.fields["permanent"].help_text = (
            "Turn this off if you only want the label to be visible when a user hovers their mouse over the marker area."
        )
        self.fields["sticky"].help_text = "Whether text attaches to the cursor when nearby."

    def _populate_initial_tooltip_fields(self, tooltip: models.Tooltip) -> None:
        """
        This function assumes that a related 'tooltip' object exists at form-initialization
        time, and uses its field values to populate the form fields for this inline form.
        """
        self.fields["label"].initial = tooltip.label
        self.fields["label_strict_clean"].initial = tooltip.label_strict_clean
        self.fields["offset_x"].initial = tooltip.offset_x
        self.fields["offset_y"].initial = tooltip.offset_y
        self.fields["opacity"].initial = tooltip.opacity
        self.fields["direction"].initial = tooltip.direction
        self.fields["permanent"].initial = tooltip.permanent
        self.fields["sticky"].initial = tooltip.sticky

    def _set_initial_tooltip_defaults(self) -> None:
        """
        This function assumes that there is no related "tooltip" object at form-initialization
        time, so it sets the form field values to their defaults, which are defined below.
        """
        self.fields["label"].initial = "Tooltip Text"
        self.fields["label_strict_clean"].initial = True
        self.fields["offset_x"].initial = Decimal(0.0)
        self.fields["offset_y"].initial = Decimal(0.0)
        self.fields["opacity"].initial = Decimal(0.8)
        self.fields["direction"].initial = Direction.CENTER
        self.fields["permanent"].initial = True
        self.fields["sticky"].initial = False

    def _save_tooltip_with_form_field_values(self, tooltip: models.Tooltip) -> None:
        """
        This function assumes that the 'draw_tooltip' form field is 'True', and that it is being
        run at "save time", after the form has been fully-cleaned. It then saves the relevant form
        field values to the given tooltip object.
        """
        try:

            # set tooltip field values
            tooltip.label = self.cleaned_data["label"]
            tooltip.label_strict_clean = self.cleaned_data["label_strict_clean"]
            tooltip.offset_x = self.cleaned_data["offset_x"]
            tooltip.offset_y = self.cleaned_data["offset_y"]
            tooltip.opacity = self.cleaned_data["opacity"]
            tooltip.direction = self.cleaned_data["direction"]
            tooltip.permanent = self.cleaned_data["permanent"]
            tooltip.sticky = self.cleaned_data["sticky"]

            # set tooltip object on styles-on-layer
            if self.instance is None:
                tooltip.delete()
                raise ValueError("Cannot save related tooltip if no styles-on-layer object exists on the form.")
            self.instance.tooltip = tooltip
            tooltip.style_on_layer = self.instance

            self.instance.full_clean()
            self.instance.save()
            tooltip.full_clean()
            tooltip.save()

        except Exception as e:
            raise ValueError(
                "Could not save related tooltip on styles on layer",
                {"tooltip": tooltip.id, "styles_on_layer": self.instance.id if self.instance else None},
            ) from e

    def _get_related_tooltip_or_none(self) -> models.Tooltip | None:
        if self.instance and hasattr(self.instance, "tooltip"):
            return self.instance.tooltip

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tooltip fields are pulled from related tooltip model
        self._init_tooltip_fields()
        if tooltip := self._get_related_tooltip_or_none():
            self.fields["draw_tooltip"].initial = True
            self._populate_initial_tooltip_fields(tooltip)
        else:
            self.fields["draw_tooltip"].initial = False
            self._set_initial_tooltip_defaults()

        # Draw-popup checkbox should be checked initially if the popup input box has any content
        if self.instance is None:
            # By default, don't draw a popup
            self.fields["draw_popup"].initial = False
        else:
            if self.instance.popup is not None and str(self.instance.popup).strip() != "":
                # If the popup already contains text, then check the box
                self.fields["draw_popup"].initial = True
            else:
                # If the popup contains nothing or is null then don't check the box
                self.fields["draw_popup"].initial = False

    def save(self, commit=True) -> Any:

        # If draw_popup checkbox is False then clear any saved popup text
        if self.cleaned_data["draw_popup"] == False:
            if self.instance:
                self.instance.popup = None

        return super().save(commit=commit)

    def save_related_tooltips(self) -> None:
        """
        Save related tooltips on this inline form. Should ONLY be called after the styles-on-layer
        has been saved, e.g., on the LayerAdmin the hook for this is `save_related`, because this is
        called after all the related StyleOnLayers are saved. Only then can we save the doubly-related
        tooltips, else Django complains with a very vague error message.
        """

        if self.cleaned_data["draw_tooltip"] == False:
            if tooltip := self._get_related_tooltip_or_none():
                # Delete existing tooltip (we no longer want to draw it)
                tooltip.delete()
        else:
            if tooltip := self._get_related_tooltip_or_none():
                # Update existing tooltip
                self._save_tooltip_with_form_field_values(tooltip)
            else:
                # create new tooltip
                tooltip = models.Tooltip.objects.create(label="")
                self._save_tooltip_with_form_field_values(tooltip)


class StyleOnLayerInline(SuperuserStrictCleanMixin, sortable_admin.SortableStackedInline, admin.StackedInline):
    form = StylesOnLayerInlineForm
    verbose_name_plural = "Styles applied to this Layer"
    model = models.StylesOnLayer
    extra = 0
    exclude = ["id"]
    sortable_field_name = "display_order"
    autocomplete_fields = [
        # uses the searchable textbox in the admin form to add/remove Styles
        "style"
    ]

    def get_formset(self, request, obj=None, **kwargs):
        """Profile inline formset creation"""
        return super().get_formset(request, obj, **kwargs)


class MapDataChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj) -> str:
        if obj and isinstance(obj, models.MapData):
            # Customize the MapData dropdown label without touching __str__
            return f"{obj.name} ({obj.provider_state.upper()})"
        return "Unknown Map Data"


class LayerForm(forms.ModelForm):

    class Meta:
        model = models.Layer
        exclude = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].widget = SummernoteWidget(height="300px")

    class LeafletSerializationFail(Exception):
        """
        Something went wrong while trying to serialize the leaflet
        JSON before saving it to the Layer model.
        """

        ...

    serialized_leaflet_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    map_data = MapDataChoiceField(
        # Defer loading the large _geojson field to improve form rendering performance
        # Only load id, name, and provider_state which are needed for the dropdown
        queryset=models.MapData.objects.only(
            "id",
            "name",
            "provider_state",
        ).order_by("name")
    )

    @silk_profile(name="LayerForm clean_serialized_leaflet_json")
    def clean_serialized_leaflet_json(self):
        """
        Prevent double-serialization of submitted GeoJSON data.
        """
        try:
            map_data: models.MapData = self.cleaned_data["map_data"]
            if map_data.provider_state == models.MapData.ProviderState.GEOJSON:
                data = self.cleaned_data["serialized_leaflet_json"]
                # The json.loads here avoids double-serialization. We need it because
                # the data is serialized pre-transit to the server, and then again (mistakenly)
                # by Django's JSONField.
                return json.loads(data)
        except Exception as e:
            raise self.LeafletSerializationFail from e


@admin.register(models.Layer)
class LayerAdmin(SuperuserStrictCleanMixin, sortable_admin.SortableAdminBase, admin.ModelAdmin):  # type: ignore
    form = LayerForm
    inlines = [StyleOnLayerInline]
    autocomplete_fields = ["map_data"]
    search_fields = ["name"]
    list_display = ["name", "description_preview", "site_visibility"]
    description_preview = truncate_admin_text_from("description")
    list_filter = [PublishedStateFilter]
    actions = ["duplicate_object"]

    @admin.action(description="Duplicate selected items")
    def duplicate_object(self, request, queryset):
        for obj in queryset:
            LayerDuplicator(obj).duplicate()
        self.message_user(request, f"Successfully duplicated {queryset.count()} item(s).")
        return HttpResponseRedirect("?published_state=all")

    @admin.display(description="Site Visibility")
    def site_visibility(self, obj):
        return obj.published_state

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Defer expensive fields when listing Layers
        return qs.select_related("map_data").defer("serialized_leaflet_json", "map_data___geojson")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Handles both GET (load form) and POST (save form) requests"""
        # Dynamic profile name based on request method
        profile_name = f"LayerAdmin changeform_view ({request.method})"
        with silk_profile(name=profile_name):
            return super().changeform_view(request, object_id, form_url, extra_context)

    @silk_profile(name="LayerAdmin save_model")
    def save_model(self, request: HttpRequest, obj: Any, form: forms.ModelForm, change: bool) -> None:
        return super().save_model(request, obj, form, change)

    @silk_profile(name="LayerAdmin get_form")
    def get_form(self, request, obj=None, change=False, **kwargs):
        """Profile form instantiation"""
        return super().get_form(request, obj, change, **kwargs)

    @silk_profile(name="LayerAdmin render_change_form")
    def render_change_form(self, request, context, *args, **kwargs):
        map_preview_html = mark_safe(
            '<div id="map-preview" style="height: 600px; margin-bottom: 1em;"></div>'
            '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />'
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
        )
        try:
            context["adminform"].form.fields["map_data"].help_text = map_preview_html
        except (KeyError, AttributeError):
            logger.exception("Failed to inject map preview.")
        finally:
            return super().render_change_form(request, context, *args, **kwargs)

    def save_related(
        self,
        request: HttpRequest,
        form: forms.ModelForm,
        formsets: forms.BaseModelFormSet,
        change: bool,
    ) -> None:

        for formset in formsets:
            if forms := getattr(formset, "forms", None):
                for inline_form in forms:
                    if isinstance(inline_form, StylesOnLayerInlineForm):
                        # Save any related tooltips (if needed) on each styles-on-layer inline
                        inline_form.save_related_tooltips()

        return super().save_related(request, form, formsets, change)


@dataclass
class MapDataAdminFormConfig:
    """
    This form is a little more complicated and requires some configuration to determine
    it's business logic. An instance of this class stores all the necessary configuration
    data for this form.
    """

    @dataclass
    class Field:
        fieldname: str
        required: bool  # is the field required on form save?

    @dataclass
    class Provider:
        state: models.MapData.ProviderState
        fields: List["MapDataAdminFormConfig.Field"]
        map_preview: bool  # Whether to render the map preview for this provider

    providers: List["MapDataAdminFormConfig.Provider"]

    def get_fields(self) -> List[Field]:
        fields = []
        for provider in self.providers:
            for field in provider.fields:
                fields.append(field)
        return fields

    def get_provider(self, provider_state: models.MapData.ProviderState | str) -> Provider | None:
        """
        Get an admin form config `Provider` from a `ProviderState`, or return None if none could be found.
        """
        if not isinstance(provider_state, models.MapData.ProviderState):
            provider_state = models.MapData.ProviderState(provider_state)
        for provider in self.providers:
            if provider.state == provider_state:
                return provider
        return None


mdaf_config = MapDataAdminFormConfig(
    providers=[
        MapDataAdminFormConfig.Provider(
            state=models.MapData.ProviderState.GEOJSON,
            fields=[MapDataAdminFormConfig.Field("_geojson", required=True)],
            map_preview=True,
        ),
        MapDataAdminFormConfig.Provider(
            state=models.MapData.ProviderState.OPEN_GREEN_MAP,
            fields=[
                MapDataAdminFormConfig.Field("map_link", required=True),
                MapDataAdminFormConfig.Field("campaign_link", required=False),
            ],
            map_preview=False,
        ),
        MapDataAdminFormConfig.Provider(
            state=models.MapData.ProviderState.GEOTIFF,
            fields=[MapDataAdminFormConfig.Field("geotiff", required=True)],
            map_preview=False,
        ),
    ]
)


class MapDataAdminForm(forms.ModelForm):
    """
    For submitting `MapData` info.
    """

    class Meta:
        model = models.MapData
        fields = ["id", "name", "provider_state", *[field.fieldname for field in mdaf_config.get_fields()]]
        labels = {"provider_state": "Data Type"}

    def get_initial_for_field(self, field, field_name):
        if field_name == "_geojson":
            if self.instance and isinstance(self.instance, models.MapData):
                if self.instance._geojson is None:
                    # Replace "null" in geojson form field with "{}"
                    return {}
        return super().get_initial_for_field(field, field_name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Remove "UNSET" option from dropdown menu
        self.fields["provider_state"].choices = [
            (value, label)
            for value, label in models.MapData.ProviderState.choices
            if value != models.MapData.ProviderState.UNSET
        ]

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        provider = mdaf_config.get_provider(cleaned_data["provider_state"])

        if not (
            self.instance
            and provider
            and isinstance(self.instance, models.MapData)
            and "provider_state" in cleaned_data
            and cleaned_data["provider_state"] in models.MapData.ProviderState
        ):
            # Exit early
            return cleaned_data

        required_fieldnames = [field.fieldname for field in provider.fields if field.required]
        for fieldname in required_fieldnames:
            if fieldname not in self.errors:
                if fieldname not in cleaned_data or not cleaned_data[fieldname]:
                    # Enforce required fields dynamically (depending on selected provider state)
                    self.add_error(fieldname, "This field is required.")

        non_provider_fieldnames = [
            field.fieldname for field in mdaf_config.get_fields() if field not in provider.fields
        ]
        for fieldname in non_provider_fieldnames:
            # Ignore fields dynamically (belonging to other provider states)
            if fieldname in self.errors:
                self.errors.pop(fieldname)
            cleaned_data[fieldname] = None

        return cleaned_data


@admin.register(models.MapData)
class MapDataAdmin(admin.ModelAdmin):
    form = MapDataAdminForm
    exclude = ["id"]
    list_display = ["name", "provider_state"]
    search_fields = ["name"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # avoid fetching map_data and geotiff data when listing all MapDatas
        return qs.defer("_geojson", "geotiff")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Handles both GET (load form) and POST (save form) requests"""
        # Dynamic profile name based on request method
        profile_name = f"MapDataAdmin changeform_view ({request.method})"
        with silk_profile(name=profile_name):
            return super().changeform_view(request, object_id, form_url, extra_context)

    @silk_profile(name="MapDataAdmin save")
    def save_model(self, request: HttpRequest, obj: Any, form: forms.ModelForm, change: bool) -> None:
        return super().save_model(request, obj, form, change)

    @silk_profile(name="MapDataAdmin get_form")
    def get_form(self, request, obj=None, change=False, **kwargs):
        return super().get_form(request, obj, change, **kwargs)

    @silk_profile(name="MapDataAdmin log_change")
    def log_change(self, request, object, message):
        """
        Skip expensive change message for large JSON fields.
        """
        # Don't construct detailed change message, just log the action
        from django.contrib.admin.models import CHANGE, LogEntry
        from django.contrib.contenttypes.models import ContentType

        return LogEntry.objects.log_action(
            user_id=request.user.pk,  # type: ignore
            content_type_id=ContentType.objects.get_for_model(object).pk,
            object_id=object.pk,
            object_repr=str(object)[:200],
            action_flag=CHANGE,
            change_message="Modified",  # Simple message instead of detailed diff
        )

    @silk_profile(name="MapDataAdmin render_change_form")
    def render_change_form(self, request, context, *args, **kwargs):
        """
        Inject initial GeoJSON data into page so we can render an initial
        `MapData` preview in the change form.
        """
        geojson = None
        if map_data := context.get("original"):
            if isinstance(map_data, models.MapData):
                if raw_geojson := map_data.geojson:
                    geojson = raw_geojson
        geojson = "{}" if geojson is None else geojson
        context["map_data_admin_form_config"] = mark_safe(json.dumps(asdict(mdaf_config)))
        context["initial_geojson_data"] = mark_safe(geojson)
        return super().render_change_form(request, context, *args, **kwargs)


class StyleForm(forms.ModelForm):

    class Meta:
        model = models.Style
        fields = [
            # Stroke data
            "draw_stroke",
            "stroke_color",
            "stroke_weight",
            "stroke_opacity",
            "stroke_line_cap",
            "stroke_line_join",
            "stroke_dash_array",
            "stroke_dash_offset",
            # Fill data
            "draw_fill",
            "fill_color",
            "fill_opacity",
            # Icon data
            "draw_marker",
            "marker_background_color",
            "marker_background_opacity",
            "marker_icon",
            "marker_icon_opacity",
            "marker_size",
            # "fill_rule", <-- gonna handle this later. Seems like an extreme edge-case for using the admin site.
            # Circle data
            "draw_circle",
            "circle_radius",
            "circle_fill_color",
            "circle_fill_opacity",
            "circle_stroke_color",
            "circle_stroke_weight",
            "circle_stroke_opacity",
            "circle_stroke_line_cap",
            "circle_stroke_line_join",
            "circle_stroke_dash_array",
            "circle_stroke_dash_offset",
            # I put the style name at end of submission because I feel like people will want to create
            # the style, and then name it after they have a solid idea of what it will look like, but that's just me.
            "name",
        ]
        widgets = {
            "stroke_weight": utils.SliderAndTextboxNumberInput(max=30, step=0.05, attrs={"class": "inline-field"}),
            "stroke_opacity": utils.SliderAndTextboxNumberInput(),
            "stroke_dash_offset": utils.SliderAndTextboxNumberInput(max=100, step=1),
            "fill_opacity": utils.SliderAndTextboxNumberInput(),
            "marker_icon_opacity": utils.SliderAndTextboxNumberInput(),
            "marker_background_opacity": utils.SliderAndTextboxNumberInput(),
            "marker_icon": forms.FileInput(),
            "marker_size": utils.SliderAndTextboxNumberInput(min=10, max=150),
            "circle_radius": utils.SliderAndTextboxNumberInput(min=5, max=250, step=1),
            "circle_stroke_weight": utils.SliderAndTextboxNumberInput(
                max=30, step=0.05, attrs={"class": "inline-field"}
            ),
            "circle_stroke_opacity": utils.SliderAndTextboxNumberInput(),
            "circle_fill_opacity": utils.SliderAndTextboxNumberInput(),
            "circle_stroke_dash_offset": utils.SliderAndTextboxNumberInput(max=100, step=1),
        }


@admin.register(models.Style)
class StyleAdmin(admin.ModelAdmin):
    form = StyleForm
    readonly_fields = ["style_preview"]
    exclude = ["id"]
    search_fields = ["name"]

    @admin.display(description="Style Preview")
    def style_preview(self, obj):
        """
        Readonly field that previews the style while it's being changed or created.
        The `style_preview.js` file hooks into the HTML element generated by this function.
        """
        return mark_safe('<div id="style_preview" style="position: relative;"></div>')
