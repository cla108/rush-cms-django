from django.contrib.admin import SimpleListFilter

from rush.models import Channel


class ChannelFilter(SimpleListFilter):
    """
    An admin filter for models tagged onto channels. Defaults to showing every channel, so that
    editors never lose track of content that isn't on the channel they happen to be looking at.
    """

    title = "Channel"
    parameter_name = "channel"

    def lookups(self, request, model_admin):  # type: ignore
        return (
            (None, "All"),
            *(
                (channel.name, channel.name.capitalize())
                for channel in Channel.objects.all()
            ),
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
        if self.value() is None or self.value() == "all":
            return queryset
        elif Channel.objects.filter(name=self.value()).exists():
            return queryset.filter(channels__name=self.value())
        else:
            raise ValueError(f"Unknown channel: {self.value()}")
