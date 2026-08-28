from django.contrib.admin import ModelAdmin, action, display, register
from django.http import HttpResponseRedirect

from rush.admin.filters import PublishedStateFilter
from rush.admin.initiative.forms import InitiativeForm
from rush.admin.utils import SuperuserStrictCleanMixin, image_html, truncate_admin_text_from
from rush.models import Initiative
from rush.models.duplicators import InitiativeDuplicator


@register(Initiative)
class InitiativeAdmin(SuperuserStrictCleanMixin, ModelAdmin):
    form = InitiativeForm
    list_display = ["title", "link", "content_preview", "image_preview", "get_tags", "site_visibility"]
    list_filter = [PublishedStateFilter]
    content_preview = truncate_admin_text_from("content")
    autocomplete_fields = [
        # uses the searchable textbox in the admin form to add/remove Tags
        "tags"
    ]
    search_fields = ["title"]
    actions = ["duplicate_object"]

    @action(description="Duplicate selected items")
    def duplicate_object(self, request, queryset):
        for obj in queryset:
            InitiativeDuplicator(obj).duplicate()
        self.message_user(request, f"Successfully duplicated {queryset.count()} item(s).")
        return HttpResponseRedirect("?published_state=all")

    @display(description="Site Visibility")
    def site_visibility(self, obj):
        return obj.published_state

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Prefetch tags to avoid N+1 queries in get_tags() display method
        return qs.prefetch_related("tags")

    def image_preview(self, obj):
        """
        Image preview inline.
        """
        if obj.image:
            return image_html(obj.image.url)
        return "No image"

    @display(description="Tags")
    def get_tags(self, obj):
        if obj.tags.count() > 0:
            return ", ".join([tag.name for tag in obj.tags.all()])
        return "No Tags"

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "tags":
            # Tags not required to create an initiative
            kwargs["required"] = False
        return super().formfield_for_manytomany(db_field, request, **kwargs)
