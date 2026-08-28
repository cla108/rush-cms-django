from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import SafeString, SafeText, mark_safe


class SuperuserStrictCleanMixin:
    """
    Mixin for ModelAdmin and InlineAdmin classes that hides all fields ending with
    `_strict_clean` from non-superusers. Superusers can still see and edit these fields.
    """

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [f for f in fields if not f.endswith("_strict_clean")]
        return fields


def get_decimal(obj: Any) -> Decimal:
    """
    Convert any object to a Decimal. If the object is numeric, then it will
    be converted to it's corresponding decimal number. Otherwise, this function
    will return zero.
    """
    try:
        return Decimal(str(obj))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


class InputType(Enum):
    SLIDER = "range"  # reserved string keyword "range" in django-land
    NUMBER = "number"


class SliderAndTextboxNumberInput(forms.Widget):
    """
    A number input Django form widget that provides both a slider and an
    input textbox so the user can choose their preferred way to enter data.

    NOTE: For this widget to work the corresponding `slider_textbox_input_sync.js`
          script must be included in the Django form Media subclass.
    """

    def __init__(self, attrs=None, min=0, max=1, step=0.01):
        self.min = min
        self.max = max
        self.step = step
        self.slider_input = None
        self.textbox_input = None
        super().__init__(attrs)

    def _create_input(self, type: InputType) -> forms.NumberInput:
        return forms.NumberInput(
            attrs={
                "type": type.value,
                "min": str(self.min),
                "max": str(self.max),
                "step": str(self.step),
            }
        )

    def render(self, name, value, attrs=None, renderer=None) -> SafeString:

        # lazily create the slider and number inputs
        if not self.slider_input:
            self.slider_input = self._create_input(InputType.SLIDER)
        if not self.textbox_input:
            self.textbox_input = self._create_input(InputType.NUMBER)

        def render(input: forms.NumberInput, id: str) -> SafeText:
            return input.render(
                name,
                round(get_decimal(value), 2),
                attrs={**self.attrs, "id": id},
                renderer=renderer,
            )

        return mark_safe(
            f"""
            <div class="dual-slider-textbox" data-fieldname="{name}">
                {render(self.slider_input, f"slider_{name}")}
                <div style="margin-right: 15px; display: inline;"></div>
                {render(self.textbox_input, f'id_{name}')}
            </div>
            """
        )


# class LiveImagePreviewInput(forms.ClearableFileInput):
#     """
#     An image upload input field with life-previewing of the selected image.

#     NOTE: For this widget to work the corresponding `live_image_preview_refresh.js`
#           script must be included in the Django form Media subclass.

#           TODO: This is not used anymore and could be improved / deprecated depending on how the code progresses.
#     """

#     def __init__(self, attrs=None):
#         super().__init__(attrs)

#     def render(self, name, value, attrs=None, renderer=None) -> str:
#         image_upload_html = forms.ClearableFileInput().render(
#             name=name,
#             value=value,
#             attrs={**self.attrs, "id": f"live_image_input_{name}"},
#             renderer=renderer,
#         )
#         src = f"{settings.MEDIA_URL}{value}" if value else "#"
#         return mark_safe(
#             f"""
#             {image_upload_html}
#             <img id="live_image_preview_{name}" src="{src}" style="max-width: 200px; display: none;" />
#             """
#         )


def image_html(image_url: str, image_width: int = 200) -> str:
    """
    Return HTML for rendering an image.
    TODO: See if I can't get the image preview to live-reload by injecting some JS here...
    """
    return mark_safe(f'<img src="{image_url}" width="{image_width}" height="auto" />')


def truncate_admin_text_from(
    admin_attr_name: str,
    max_chars: int = 500,
):
    """
    Return an admin model function that renders a preview of some
    content in the inline display.
    """

    def inner(admin_instance: admin.ModelAdmin, obj: models.Model) -> str:
        content = getattr(obj, admin_attr_name, None)
        if not content:
            return "No content"
        return format_html("{}...", content[:max_chars])

    return inner
