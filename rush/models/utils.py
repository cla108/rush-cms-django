from io import BytesIO
from logging import getLogger

import bleach
import bleach.css_sanitizer
from bs4 import BeautifulSoup
from bs4.element import Tag as BSTag
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile
from PIL import Image

from rush.models.validators import FiletypeValidator

logger = getLogger(__name__)


class CompressionFailed(Exception):
    """
    Compressing the image failed.
    """

    ...


def compress_image(image: FieldFile, pixel_width=128) -> ContentFile:
    """
    Compress and resize the given image and return it as a ContentFile.
    The returned ContentFile can be manually assigned to a model's FieldFile.
    """

    try:

        FiletypeValidator(
            valid_names=[
                "WEBP",
                "JPEG",
                "PNG",
                # NOTE: SVGs/TIFFs should not be compressed
            ]
        )(image)

        # Resize image
        img = Image.open(image)
        original_width, original_height = img.size
        pixel_width = min(original_width, pixel_width)
        w_ratio = pixel_width / original_width
        new_height = int(original_height * w_ratio)
        img = img.resize((pixel_width, new_height), Image.Resampling.LANCZOS)

        # Save to in-memory buffer
        img_io = BytesIO()
        img.save(
            img_io,
            format="WEBP",
            lossless=False,
            quality=90,  # 85-95 is visually lossless for most images
            method=6,  # 0-6, where 6 is the most compressed but takes longer
        )

        original_name = image.name
        compressed_name = f"compressed_{original_name.split('/')[-1].rsplit('.', 1)[0]}.webp"

        # Return a ContentFile with name
        return ContentFile(img_io.getvalue(), name=compressed_name)

    except Exception as e:
        logger.error(f"Failed to compress file: {image.name}.", exc_info=e)
        raise CompressionFailed from e


class SummernoteTextCleaner:
    """
    Responsible for sanitizing summernote TextField data before it
    gets saved to the database.
    """

    ALLOWED_TOOLTIP_TAGS = [
        "b",
        "i",
        "u",
        "p",
        "strong",
        "em",
        "a",
    ]

    ALLOWED_TAGS = [
        "p",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "div",
        "span",
        "a",
        "blockquote",
        "pre",
        "figure",
        "figcaption",
        "br",
        "code",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "picture",
        "source",
        "img",
        "del",
        "b",
        "i",
        "u",
        "button",
        "input",
        "font",
    ]

    ALLOWED_ATTRIBUTES = [
        "alt",
        "class",
        "src",
        "srcset",
        "href",
        "media",
        "style",
        "align",
    ]

    # Which CSS properties are allowed in 'style' attributes (assuming style is
    # an allowed attribute)
    BLEACH_ALLOWED_STYLES = [
        "width",
        "height",
        "max-width",
        "max-height",
        "min-width",
        "min-height",
        "font-family",
        "font-weight",
        "font-size",
        "background-color",
        "color",
        "display",
        "padding",
        "padding-left",
        "padding-right",
        "padding-top",
        "padding-bottom",
        "margin",
        "margin-left",
        "margin-right",
        "margin-top",
        "margin-bottom",
    ]

    @classmethod
    def clean(cls, text: str, strict_clean=True) -> str:
        unescaped = text.replace("&quot;", "'")
        if strict_clean:
            cleaned = bleach.clean(
                text=unescaped,
                attributes=cls.ALLOWED_ATTRIBUTES,
                tags=cls.ALLOWED_TAGS,
                css_sanitizer=bleach.css_sanitizer.CSSSanitizer(
                    allowed_css_properties=cls.BLEACH_ALLOWED_STYLES,
                ),
            )
        else:
            cleaned = unescaped
        return cleaned

    @classmethod
    def clean_tooltip(cls, text: str, strict_clean=True) -> str:
        unescaped = text.replace("&quot;", "'")
        if strict_clean:
            cleaned = bleach.clean(text=unescaped, tags=cls.ALLOWED_TOOLTIP_TAGS)
        else:
            cleaned = unescaped
        return cleaned


_SKIP_TAGS = frozenset({"script", "style", "meta", "link", "noscript", "template"})


def _get_text(node: BSTag) -> str:
    raw = node.get_text(separator=" ")
    return " ".join(raw.split())


_JUNK_BLOCK_TAGS = frozenset(
    {
        "div",
        "section",
        "article",
        "header",
        "footer",
        "main",
        "aside",
        "nav",
        "details",
        "summary",
        "address",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "dl",
        "dt",
        "dd",
        "form",
        "fieldset",
    }
)

# Inline tags that are always unwrapped (tag removed, content kept in place)
_UNWRAP_INLINE_TAGS = frozenset({"span"})

# Block tags that are legitimate Summernote output — not treated as junk
_PRESERVED_BLOCK_TAGS = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "blockquote",
        "pre",
        "figure",
        "figcaption",
    }
)


def _has_block_child_for_dediv(tag: BSTag) -> bool:
    return any(
        isinstance(c, BSTag) and c.name and c.name.lower() in (_JUNK_BLOCK_TAGS | _PRESERVED_BLOCK_TAGS)
        for c in tag.children
    )


def strip_foreign_blocks(html: str) -> str:
    """
    Remove copy-paste structural elements (div, section, article, etc.) while
    preserving Summernote-generated content: <p> tags with their attributes,
    inline formatting (<strong>, <em>, <font>, <span>, etc.), lists, and headings.

    Junk block elements are handled as follows:
    - Has block-level children → unwrapped (tag removed, children kept in place)
    - Has only inline content → converted to <p> (tag attributes stripped)
    - Empty → removed entirely
    """
    if not html or not html.strip():
        return html

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(list(_SKIP_TAGS)):
        tag.decompose()

    while True:
        junk = soup.find(list(_JUNK_BLOCK_TAGS))
        if junk is None:
            break

        if _has_block_child_for_dediv(junk):
            junk.unwrap()
        else:
            text = _get_text(junk)
            has_child_elements = any(isinstance(c, BSTag) for c in junk.children)
            if text or has_child_elements:
                junk.name = "p"
                junk.attrs = {}
            else:
                junk.decompose()

    for tag in soup.find_all(list(_UNWRAP_INLINE_TAGS)):
        tag.unwrap()

    return str(soup)
