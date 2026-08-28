from django.forms import ModelForm

from rush.admin.widgets import SummernoteWidget
from rush.models import Page


class PageForm(ModelForm):

    class Meta:
        model = Page
        fields = "__all__"
        exclude = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = SummernoteWidget()
