import json
from dataclasses import dataclass
from logging import getLogger
from typing import Any, List

from django.db.models import Model
from django.forms import Select
from django.forms.utils import flatatt
from django.template import Context, Engine
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_summernote.widgets import SummernoteWidgetBase

from rush.context_processors import base_url_from_request

logger = getLogger(__name__)


class SummernoteWidget(SummernoteWidgetBase):
    """
    Provide a default summernote-editor widget for RUSH admin, that can optionally be passed
    some summernote configuration overrides, e.g., to change the width or height of the widget.

    **How to implement**:
    1. Add this widget to an admin field. See `rush/admin/question/forms/question_tab_inline_form.py` for an example.
    2. Use the SummernoteTextCleaner to clean the text before it gets saved to the database. See `rush/models/layer/layer_group_on_question.py` for an example.
    3. Use `convert_relative_images_to_absolute` in `graphql.py` on the API field to convert any media links to use RUSH's base media url
        before sending the text data to the client. There are many examples of how to do this in `graphql.py`.
    4. Add another field to the model to toggle strict_clean behaviour, and add the SuperuserStrictCleanMixin to the model admin
        class.
    5. Test that the field data in the graphql playground is recieved without causing any errors!

    """

    DEFAULT_SUMMERNOTE_SETTINGS = {
        "height": "500px",
        "width": "500px",
        # Disable client-side code view filtering so tags like <script> are not
        # stripped when toggling between code view and WYSIWYG. The backend
        # SummernoteTextCleaner is the real line of defence on save.
        "codeviewFilter": False,
        "codeviewIframeFilter": False,
        "toolbar": [
            ["style", ["style"]],
            ["font", ["bold", "underline", "clear"]],
            ["fontname", ["fontname"]],
            ["fontsize", ["fontsize"]],
            ["color", ["color"]],
            ["para", ["ul", "ol", "paragraph"]],
            # ["table", ["table"]],
            [
                "insert",
                [
                    "link",
                    "picture",
                    # "video",
                ],
            ],
            ["view", ["codeview"]],
        ],
        "styleTags": [
            {
                "tag": "p",
                "title": "Title",
                "className": "rush-title",
                "value": "p",
            },
            {
                "tag": "p",
                "title": "Subtitle",
                "className": "rush-subtitle",
                "value": "p",
            },
            {
                "tag": "p",
                "title": "Normal",
                "value": "p",
            },
            {
                "tag": "p",
                "title": "Hint",
                "className": "rush-hint",
                "value": "p",
            },
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ],
        "fontNames": [
            "Poppins",
            "Urbanist",
            "Raleway",
            "Figtree",
            "Bitter",
        ],
        "fontNamesIgnoreCheck": [
            "Poppins",
            "Urbanist",
            "Raleway",
            "Figtree",
            "Bitter",
        ],
        # "addDefaultFonts": False,
    }

    def __init__(self, **override_summernote_settings):
        self.override_summernote_settings = override_summernote_settings
        super().__init__()

    def render(self, name, value, attrs=None, **kwargs):
        if attrs is None:
            attrs = {}
        summernote_settings = self.summernote_settings()
        summernote_settings.update(self.DEFAULT_SUMMERNOTE_SETTINGS)
        summernote_settings.update(self.override_summernote_settings)
        html = super().render(name, value, attrs=attrs, **kwargs)
        context = {
            "id": attrs["id"],
            "id_safe": attrs["id"].replace("-", "_"),
            "flat_attrs": flatatt(self.final_attr(attrs)),
            "settings": json.dumps(summernote_settings),
            "src": reverse("django_summernote-editor", kwargs={"id": attrs["id"]}),
            # Width and height have to be pulled out to create an iframe with correct size
            "width": summernote_settings["width"],
            "height": summernote_settings["height"],
        }
        html += render_to_string("django_summernote/widget_iframe.html", context)
        return mark_safe(html)


class TiledForeignKeyWidget(Select):
    """
    A foreign-key selection widget for the admin site that displays foreign-key
    instances in a tile-like manner which can be selected by a user clicking on them.
    """

    @dataclass
    class Choice:
        """
        A possible choice of which foreign-key to select.
        """

        id: str

        # Relative url (e.g., from file-field)
        thumbnail_url: str

        # the form model instance (of type A) that has a foreign-key to a model (of type B),
        # whose instances we wish to display as selectable tiles.
        instance: Model

        # The name of the foreign key field (to a model of type B), on the form model instance model (of type A).
        fk_name: str

        request: Any

        def selected_str(self) -> str:
            """
            True when the fk object is attached to the form instance.
            """
            related = getattr(self.instance, self.fk_name, None)
            if related is None:
                logger.error("Cannot accss fk field '{}' on {}.".format(self.fk_name, self.instance))
                return ""
            selected = str(related.id) == self.id
            return "selected" if selected else ""

        def base_media_url(self) -> str:
            return base_url_from_request(self.request)

    def __init__(self, display_choices: List[Choice], attrs=None):
        self.display_choices = display_choices
        super().__init__(
            attrs,
            [
                # Just use id as the label for choices here, since the
                # display_html is shown in lieu of a label.
                (x.id, x.id)
                for x in display_choices
            ],
        )

    def render(self, name, value, attrs=None, renderer=None):
        """
        Renders the widget as a grid of tiles with images.
        """

        # Prepare context
        context = {
            "name": name,
            "value": value,
            "display_choices": self.display_choices,
        }
        template_str = """
        <div class="tiled-foreignkey-widget-container">
            <div class="tiled-foreignkey-widget">

                <!-- Upload new tile -->
                <div class="tile upload-tile" data-action="upload">
                    <span class="plus-icon">+</span>
                </div>

                {% for choice in display_choices %}
                    <div class="tile {{ choice.selected_str }}" data-value="{{ choice.id }}">
                        <img src="{{ choice.base_media_url }}{{ choice.thumbnail_url }}" alt="">
                    </div>
                {% endfor %}

                <!-- Hidden select -->
                <select name="{{ name }}" class="tiled-fk-select" style="display:none;">
                    {% for choice in display_choices %}
                        <option value="{{ choice.id }}" {{ choice.selected_str }}></option>
                    {% endfor %}
                </select>

            </div>

            <!-- Upload Modal -->
            <div class="upload-modal" style="display:none;">
                <div class="modal-overlay"></div>
                <div class="modal-content">
                    <h3>Upload New Icon</h3>
                    <input type="file" class="icon-file-input" accept=".svg,.png,.webp,.jpg,.jpeg">
                    <div class="preview-container" style="display:none;">
                        <img class="preview-image" src="" alt="Preview">
                    </div>
                    <div class="modal-actions">
                        <button type="button" class="upload-btn">Upload</button>
                        <button type="button" class="cancel-btn">Cancel</button>
                    </div>
                    <div class="upload-status"></div>
                </div>
            </div>
        </div>

        <style>
            .tiled-foreignkey-widget {
                display: flex;
                flex-wrap: wrap;
                width: 136px; /* controls 2 tiles per row */
                gap: 10px;
                justify-content: left;
                margin-top: 8px;
                max-height: 300px;
                overflow-y: auto;
                padding-right: 5px;
            }

            .tiled-foreignkey-widget .tile {
                width: 60px;
                height: 60px;
                border: 2px solid #ddd;
                border-radius: 6px;
                box-sizing: border-box;
                cursor: pointer;
                display: flex;
                padding: 4px;
                justify-content: center;
                align-items: center;
                background: #fafafa;
                transition: border 0.18s ease, box-shadow 0.18s ease;
            }

            .tiled-foreignkey-widget .tile:hover {
                border-color: #4285f4;
                box-shadow: 0 0 4px rgba(66,133,244,0.4);
            }

            .tiled-foreignkey-widget .tile.selected {
                border-color: #1e65d6;
                background: #e8f0fe;
                box-shadow: 0 0 0 2px rgba(30,101,214,0.3);
            }

            .tiled-foreignkey-widget img {
                width: 100%;
                height: auto;
                object-fit: contain;
            }

            /* Upload tile styles */
            .tiled-foreignkey-widget .upload-tile {
                border: 2px dashed #aaa;
                background: #f5f5f5;
            }

            .tiled-foreignkey-widget .upload-tile:hover {
                border-color: #4285f4;
                background: #e8f0fe;
            }

            .tiled-foreignkey-widget .plus-icon {
                font-size: 32px;
                color: #666;
                font-weight: 300;
            }

            /* Modal styles */
            .upload-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 10000;
            }

            .upload-modal .modal-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
            }

            .upload-modal .modal-content {
                position: relative;
                background: white;
                margin: 100px auto;
                padding: 30px;
                width: 500px;
                max-width: 90%;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }

            .upload-modal h3 {
                margin-top: 0;
                margin-bottom: 20px;
                font-size: 20px;
            }

            .upload-modal .icon-file-input {
                display: block;
                margin-bottom: 15px;
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }

            .upload-modal .preview-container {
                margin-bottom: 15px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                background: #fafafa;
            }

            .upload-modal .preview-image {
                max-width: 200px;
                max-height: 200px;
            }

            .upload-modal .modal-actions {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }

            .upload-modal button {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }

            .upload-modal .upload-btn {
                background: #4285f4;
                color: white;
                flex: 1;
            }

            .upload-modal .upload-btn:hover {
                background: #357ae8;
            }

            .upload-modal .upload-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }

            .upload-modal .cancel-btn {
                background: #f1f1f1;
                color: #333;
            }

            .upload-modal .cancel-btn:hover {
                background: #e1e1e1;
            }

            .upload-modal .upload-status {
                color: #d32f2f;
                font-size: 14px;
                min-height: 20px;
            }
        </style>
        """
        engine = Engine()
        template = engine.from_string(template_str)
        html = template.render(Context(context))
        return mark_safe(html)
