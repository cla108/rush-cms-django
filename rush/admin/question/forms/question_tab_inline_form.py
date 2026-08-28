from django.forms import ModelForm

from rush.admin.widgets import SummernoteWidget, TiledForeignKeyWidget
from rush.models import Icon, QuestionTab


class QuestionTabInlineForm(ModelForm):

    class Meta:
        model = QuestionTab
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        """
        Tiled foreign key widget needs to access the form, to get the request, so it can
        render thumbnails using the correct base-media-url.
        """
        super().__init__(*args, **kwargs)
        self.fields["icon"].widget = TiledForeignKeyWidget(
            display_choices=[
                TiledForeignKeyWidget.Choice(
                    id=str(icon.id),
                    thumbnail_url=icon.file.url,
                    instance=self.instance,
                    fk_name="icon",
                    request=getattr(self, "request"),
                )
                for icon in Icon.objects.order_by("-created_at")[:10]
            ],
        )
        self.fields["content"].widget = SummernoteWidget()
