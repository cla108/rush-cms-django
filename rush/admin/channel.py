from django.contrib.admin import ModelAdmin, display, register
from django.utils.html import format_html

from rush.admin.utils import channel_url
from rush.models import Channel


@register(Channel)
class ChannelAdmin(ModelAdmin):
    list_display = ["name", "site_link", "is_private", "tagged_content"]
    list_filter = ["is_private"]
    search_fields = ["name"]

    @display(description="Website Link")
    def site_link(self, obj: Channel):
        url = channel_url(obj)
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, url)

    @display(description="Tagged Content")
    def tagged_content(self, obj: Channel):
        return "{questions} question(s), {layers} layer(s), {initiatives} initiative(s)".format(
            questions=obj.questions.count(),  # type: ignore
            layers=obj.layers.count(),  # type: ignore
            initiatives=obj.initiatives.count(),  # type: ignore
        )

    def get_deleted_objects(self, objs, request):
        # Channel.delete() refuses to delete the draft/published channels, but bulk admin
        # deletion goes through the queryset, so it has to be blocked here as well.
        deletable, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        protected = list(protected) + [
            f"The '{obj.name}' channel cannot be deleted." for obj in objs if obj.name in Channel.UNDELETABLE_NAMES
        ]
        return deletable, model_count, perms_needed, protected
