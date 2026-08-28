from django.contrib.admin import TabularInline

from rush.models import BasemapSource, BasemapSourceOnQuestion


class BasemapSourceOnQuestionInline(TabularInline):
    """
    Allow editing of BasemapSource objects straight from the Question form.
    """

    exclude = ["id"]
    model = BasemapSourceOnQuestion
    extra = 0
    sortable_options = (
        # Added for compatibility TabularInline <--> NestedModelAdmin (on QuestionAdmin page)
        []
    )
