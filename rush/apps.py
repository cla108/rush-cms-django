from django.apps import AppConfig


class RushConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rush"

    def ready(self):
        self.patch_admin_site_to_emit_changelist_view_signals()
        self.patch_admin_site_to_emit_changeform_view_signals()

    def patch_admin_site_to_emit_changeform_view_signals(self):
        """
        Patch all admin models to emit a signal when a model's changeform is viewed.
        """

        from django.contrib.admin import ModelAdmin

        from rush.models.signals import admin_changeform_viewed

        original_changeform_view = ModelAdmin.changeform_view

        def changeform_wrapper(self, request, object_id=None, *args, **kwargs):
            admin_changeform_viewed.send(
                sender=self.__class__,
                request=request,
                model=self.model,
                object_id=object_id,
                modeladmin=self,
            )
            return original_changeform_view(self, request, object_id, *args, **kwargs)

        ModelAdmin.changeform_view = changeform_wrapper

    def patch_admin_site_to_emit_changelist_view_signals(self):
        """
        Patch all admin models to emit a signal when a model's changelist is viewed.
        """

        from django.contrib.admin import ModelAdmin

        from rush.models.signals import admin_changelist_viewed

        original_changelist_view = ModelAdmin.changelist_view

        def changelist_wrapper(self, request, *args, **kwargs):
            admin_changelist_viewed.send(
                sender=self.__class__,
                request=request,
                model=self.model,
                modeladmin=self,
            )
            return original_changelist_view(self, request, *args, **kwargs)

        ModelAdmin.changelist_view = changelist_wrapper
