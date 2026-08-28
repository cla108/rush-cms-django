from django.contrib import admin
from rush.models import Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["name", "latitude", "longitude", "default_zoom"]
    search_fields = ["name"]
    ordering = ["name"]
