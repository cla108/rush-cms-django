from unittest.mock import MagicMock, patch

import pytest

from rush.models.utils import *
from rush.models.utils import strip_foreign_blocks
from rush.tests.models.helpers import FakeFile


@pytest.mark.parametrize(
    "html, expected",
    [
        # Clean <p> passes through unchanged (attributes preserved)
        ("<p>Hello world</p>", "<p>Hello world</p>"),
        # Empty <p> preserved — blank line in editor
        ("<p></p>", "<p></p>"),
        # <p> Summernote styles and classes kept as-is
        ('<p class="foo" style="color:red">text</p>', '<p class="foo" style="color:red">text</p>'),
        # <div> with text becomes <p>, div attributes stripped
        ('<div class="foo">Some text</div>', "<p>Some text</p>"),
        # Empty <div> removed entirely
        ('<div class="bar"></div>', ""),
        # <div> wrapping a <p> is unwrapped
        ("<div><p>inner</p></div>", "<p>inner</p>"),
        # <div> with inline content becomes <p>, inline tags and their attrs preserved
        ("<div><strong>bold</strong> text</div>", "<p><strong>bold</strong> text</p>"),
        # <span> is unwrapped — tag removed, content kept
        ("<p><span>text</span></p>", "<p>text</p>"),
        ('<p><span class="foo" style="color:red">styled</span></p>', "<p>styled</p>"),
        ("<p>before <span>mid</span> after</p>", "<p>before mid after</p>"),
        # Inline formatting inside <p> preserved intact
        ("<p><strong>bold</strong> text</p>", "<p><strong>bold</strong> text</p>"),
        # Headings are Summernote output — kept as-is
        ("<h1>Title</h1>", "<h1>Title</h1>"),
        # Multiple paragraphs
        ("<p>first</p><p>second</p>", "<p>first</p><p>second</p>"),
        # Deeply nested <p> extracted by successive unwrapping
        ("<div><div><div><p>deep</p></div></div></div>", "<p>deep</p>"),
        # Lists preserved as-is
        ("<ul><li>item 1</li><li>item 2</li></ul>", "<ul><li>item 1</li><li>item 2</li></ul>"),
        ("<ol><li>first</li><li>second</li></ol>", "<ol><li>first</li><li>second</li></ol>"),
        # <div> wrapping a list is unwrapped
        ("<div><ul><li>item</li></ul></div>", "<ul><li>item</li></ul>"),
        # <img> preserved with attributes
        ('<img src="foo.png" alt="bar"/>', '<img alt="bar" src="foo.png"/>'),
        # <img> inside <p> preserved
        ('<p><img src="foo.png" alt="bar"/></p>', '<p><img alt="bar" src="foo.png"/></p>'),
        # <div> wrapping only an <img> becomes <p> (not dropped)
        ('<div><img src="foo.png"/></div>', '<p><img src="foo.png"/></p>'),
        # Empty string returned as-is
        ("", ""),
        # Whitespace-only returned as-is
        ("   ", "   "),
        # deeply nested Tailwind divs stripped, <p> content and blank lines preserved,
        # surfaced <br> tags remain.
        (
            "<p></p>"
            '<div class="pointer-events-none h-px w-px absolute bottom-0"></div>'
            "<p></p>"
            '<div class="flex flex-col text-sm">'
            "<br>"
            '<div class="text-base my-auto mx-auto pb-10 [--thread-content-margin:--spacing(4)]'
            " @w-sm/main:[--thread-content-margin:--spacing(6)]"
            " @w-lg/main:[--thread-content-margin:--spacing(16)]"
            ' px-(--thread-content-margin)">'
            '<div class="[--thread-content-max-width:40rem] @w-lg/main:[--thread-content-max-width:48rem]'
            " mx-auto max-w-(--thread-content-max-width) flex-1 group/turn-messages"
            ' focus-visible:outline-hidden relative flex w-full min-w-0 flex-col agent-turn">'
            '<div class="flex max-w-full flex-col grow">'
            '<div class="min-h-8 text-message relative flex w-full flex-col items-end gap-2'
            " text-start break-words whitespace-normal"
            ' [.text-message+&amp;]:mt-1">'
            '<div class="flex w-full flex-col gap-1 empty:hidden first:pt-[1px]">'
            '<div class="markdown prose dark:prose-invert w-full break-words light markdown-new-styling">'
            "<p>This program supports youth and young adults affiliated with the seven South Island"
            " Coast Salish Nations who are unable to live at home or are transitioning out of care."
            " Youth aged 16\u201318 can access individualized guidance, programs, and funding to build"
            " independence and life skills, including financial assistance with housing, counselling"
            " services, and programs such as Ready to Rent to support independent living."
            " Young adults aged 19\u201326 who were previously in NI\u013d TU,O\u2019s continuing care"
            " stream or had a Youth Agreement with a NI\u013d TU,O Social Worker can access funding"
            " and resources that support independence, training, and post-secondary education.</p>"
            "</div></div></div></div>"
            '<div class="z-0 flex min-h-[46px] justify-start"></div>'
            '<div class="mt-3 w-full empty:hidden"><div class="text-center"></div></div>'
            "</div></div>"
            "<br>"
            "</div>",
            # expected output below
            "<p></p><p></p>"
            "<br/>"
            "<p>This program supports youth and young adults affiliated with the seven South Island"
            " Coast Salish Nations who are unable to live at home or are transitioning out of care."
            " Youth aged 16\u201318 can access individualized guidance, programs, and funding to build"
            " independence and life skills, including financial assistance with housing, counselling"
            " services, and programs such as Ready to Rent to support independent living."
            " Young adults aged 19\u201326 who were previously in NI\u013d TU,O\u2019s continuing care"
            " stream or had a Youth Agreement with a NI\u013d TU,O Social Worker can access funding"
            " and resources that support independence, training, and post-secondary education.</p>"
            "<br/>",
        ),
    ],
)
def test_strip_foreign_blocks(html, expected):
    assert strip_foreign_blocks(html) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "file, raises",
    [
        (FakeFile("image.png"), False),
        (FakeFile("image.jpg"), False),
        (FakeFile("image.jpeg"), False),
        (FakeFile("image.webp"), False),
        (FakeFile("not_an_image.zyx"), True),
        (FakeFile("not_an_image.svg"), True),
        (FakeFile("not_an_image.tiff"), True),
    ],
)
def test_compress_image(file, raises):

    with patch("rush.models.utils.Image.open") as mock_open:

        # Mock a PIL Image instance
        mock_image = MagicMock()
        mock_image.size = (1024, 768)
        mock_open.return_value = mock_image

        if raises:
            with pytest.raises(CompressionFailed):
                compress_image(file)
        else:
            output = compress_image(file)
            assert isinstance(output, ContentFile)
            assert output.name.startswith("compressed_")
            assert output.name.endswith(".webp")  # always gets compressed as WEBP
            assert output.name.endswith(".webp")  # always gets compressed as WEBP
