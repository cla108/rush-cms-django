from django.contrib.admin import SimpleListFilter

from rush.models import PublishedState


class PublishedStateFilter(SimpleListFilter):
    """
    An admin filter for models with a "published_state" field.
    """

    # You need to edit the ordering of `lookups` if you change this default
    DEFAULT = PublishedState.PUBLISHED.value

    title = "Site Visibility"
    parameter_name = "published_state"

    def lookups(self, request, model_admin):  # type: ignore
        return (
            (None, "Published"),
            ("draft", "Draft"),
            ("all", "All"),
        )

    def choices(self, cl):  # type: ignore
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": cl.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        if self.value() == None:
            return queryset.filter(published_state=self.DEFAULT)
        elif self.value() in PublishedState.values:
            return queryset.filter(published_state=self.value())
        elif self.value() == "all":
            return queryset
        else:
            raise ValueError(f"Unknown published-state: {self.value()}")
