from django.contrib.admin import ModelAdmin, display, register
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from rush import models
from rush.admin.initiative.forms import InitiativeTagForm


@register(models.InitiativeTag)
class InitiativeTagAdmin(ModelAdmin):
    form = InitiativeTagForm
    exclude = ["id"]
    list_display = ["name", "preview", "tagged_initiatives"]
    search_fields = ["name"]

    # Reverse relation is readonly in the add/change view for now, we can
    # change this later, but the solution is a little complicated.
    readonly_fields = ["tagged_initiatives"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Prefetch initiatives to avoid N+1 queries in tagged_initiatives() display method
        return qs.prefetch_related("initiatives")

    def preview(self, obj: models.InitiativeTag):
        return format_html(
            f"""
                <p style='
                    color: {obj.text_color};
                    background-color: {obj.background_color};
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    border-radius: 0.125rem;
                    font-family: "Bitter Variable", serif;
                    width: fit-content;
                    padding-left: 0.25rem;
                    padding-right: 0.25rem;
                    font-weight: 700;
                '>
                    {obj.name}
                </p>
            """
        )

    @display(description="Initiatives with this tag")
    def tagged_initiatives(self, obj):
        initiatives = obj.initiatives.all()
        if not initiatives.exists():
            return "-"
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            [
                (
                    reverse("admin:rush_initiative_change", args=[initiative.pk]),
                    initiative.title,
                )
                for initiative in initiatives
            ],
        )
