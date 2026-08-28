from django.contrib.admin import ModelAdmin, register
from django.http import JsonResponse
from django.urls import path

from rush.admin.utils import image_html
from rush.models import Icon


@register(Icon)
class IconAdmin(ModelAdmin):
    exclude = ["id", "mime_type", "is_file_compressed"]
    list_display = ["preview"]

    def preview(self, obj):
        if obj.file:
            return image_html(obj.file.url, image_width=60)
        return "No image"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "ajax-upload/",
                self.admin_site.admin_view(self.ajax_upload_view),
                name="icon_ajax_upload",
            ),
        ]
        return custom_urls + urls

    def ajax_upload_view(self, request):
        """
        Handle AJAX icon upload from TiledForeignKeyWidget.
        """
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)
        try:
            uploaded_file = request.FILES["file"]
            icon = Icon.objects.create(file=uploaded_file)
            return JsonResponse(
                {
                    "id": str(icon.id),
                    "url": icon.file.url,
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
