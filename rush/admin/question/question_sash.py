from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from rush.models import QuestionSash


@admin.register(QuestionSash)
class QuestionSashAdmin(admin.ModelAdmin):
    exclude = ["id"]
    list_display = ["sash_preview", "related_questions"]
    search_fields = ["text"]

    @admin.display(description="Sash")
    def sash_preview(self, obj: QuestionSash):
        return mark_safe(obj.get_html_preview())

    @admin.display(description="Questions with this sash")
    def related_questions(self, obj: QuestionSash):
        questions = obj.questions.all()  # type: ignore
        if not questions.exists():
            return "-"
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            [
                (
                    reverse("admin:rush_question_change", args=[question.pk]),
                    question.title,
                )
                for question in questions
            ],
        )
