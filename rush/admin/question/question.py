from uuid import uuid4

from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from nested_admin.nested import NestedModelAdmin

from rush.admin import PublishedStateFilter
from rush.admin.question.forms import QuestionForm
from rush.admin.question.inlines import (
    BasemapSourceOnQuestionInline,
    LayerGroupOnQuestionInline,
    QuestionTabInline,
)
from rush.admin.utils import image_html
from rush.models import BasemapSource, BasemapSourceOnQuestion, Question
from rush.models.duplicators import QuestionDuplicator


@admin.register(Question)
class QuestionAdmin(SortableAdminMixin, NestedModelAdmin):  # type: ignore
    form = QuestionForm
    exclude = ["id"]
    list_display = [
        "title",
        "slug",
        "image_preview",
        "sash_preview",
        "get_question_tabs",
        "display_order",
        "site_visibility",
    ]
    list_filter = [PublishedStateFilter]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["initiatives", "sash"]
    inlines = [
        BasemapSourceOnQuestionInline,
        QuestionTabInline,
        LayerGroupOnQuestionInline,
    ]
    actions = ["duplicate_object"]
    sortable_field_name = "display_order"  # Enable drag-and-drop for Questions in the list view
    # filter_horizontal = ["initiatives"]  # better admin editing for many-to-many fields

    @admin.display(description="Site Visibility")
    def site_visibility(self, obj: Question):
        return obj.published_state

    @admin.display(description="Sash")
    def sash_preview(self, obj: Question):
        if obj and obj.sash:
            return mark_safe(obj.sash.get_html_preview())
        return "-"

    def image_preview(self, obj):
        """
        Image preview inline.
        """
        if obj.image:
            return image_html(obj.image.url)
        return "No image"

    @admin.display(description="Question Tabs")
    def get_question_tabs(self, obj):
        tabs = obj.tabs.all()
        if tabs:
            return ", ".join([tab.title for tab in tabs])
        return "-"

    def get_queryset(self, request):
        """
        Optimize queryset to prevent loading massive JSONFields from related Layer objects.
        """
        qs = super().get_queryset(request)
        # Prefetch question tabs to avoid N+1 queries in get_question_tabs() display method
        return qs.prefetch_related("tabs")

    @admin.action(description="Duplicate selected items")
    def duplicate_object(self, request, queryset):
        for obj in queryset:
            QuestionDuplicator(obj).duplicate()
        self.message_user(request, f"Successfully duplicated {queryset.count()} item(s).")
        return HttpResponseRedirect("?published_state=all")

    def save_related(self, request, form, formsets, change):
        """
        Runs AFTER the main object is saved, and AFTER all inlines are saved.
        Perfect place to enforce defaults or create missing inline rows.
        # TODO: HOLY CRAP I NEED TO UNIT TEST THIS.
        """
        super().save_related(request, form, formsets, change)

        question = form.instance
        basemaps = BasemapSourceOnQuestion.objects.filter(question=question)

        if not basemaps.exists():
            # If no related basemaps exist, add a default basemap inline.
            BasemapSourceOnQuestion.objects.create(
                question=question,
                basemap_source=BasemapSource.objects.default(),
                is_default_for_question=True,
            )
        elif not basemaps.filter(is_default_for_question=True).exists():
            # There are basemaps, but none of them are marked as default.
            # Just choose one of them to be the default at random.
            if basemap := basemaps.first():
                basemap.is_default_for_question = True
                basemap.full_clean()
                basemap.save()
            else:
                raise ValueError("This should never happen! Basemap should exist here.")
