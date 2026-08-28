from django.forms import ModelForm

from rush.models import InitiativeTag


class InitiativeTagForm(ModelForm):

    class Meta:
        model = InitiativeTag
        exclude = ["id"]
        fields = [
            "name",
            "text_color",
            "background_color",
        ]
