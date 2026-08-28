from django.forms import ModelForm

from rush.admin.utils import image_html
from rush.models import Question


class QuestionForm(ModelForm):
    """
    Override the default add/change page for the Question model admin.
    """

    class Meta:
        model = Question
        fields = [
            "title",
            "slug",
            "subtitle",
            "image",
            "sash",
            "initiatives",
            "region",
            "published_state",
        ]

    def __init__(self, *args, **kwargs):
        """
        Inject image HTML in "image" field help text.
        TODO Test to see if this is actually doing anything. If not, delete.
        """
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.image:
            self.fields["image"].help_text = image_html(self.instance.image.url)
