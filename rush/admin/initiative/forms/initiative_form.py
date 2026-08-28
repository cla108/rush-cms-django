from django.forms import ModelForm

from rush.admin.utils import image_html
from rush.admin.widgets import SummernoteWidget
from rush.models import Initiative


class InitiativeForm(ModelForm):

    class Meta:
        model = Initiative
        exclude = ["id"]
        fields = [
            "title",
            "link",
            "image",
            "content",
            "content_strict_clean",
            "tags",
            "published_state",
        ]

    def __init__(self, *args, **kwargs):
        """
        Inject image HTML in "image" field help text.
        """
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.image:
            self.fields["image"].help_text = image_html(self.instance.image.url)

        self.fields["content"].widget = SummernoteWidget()

    def clean_image(self):
        """
        Can add custom image validation here if we want...
        """
        image = self.cleaned_data.get("image")
        return image
