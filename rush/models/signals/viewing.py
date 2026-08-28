from logging import getLogger

from django.contrib.admin.models import ADDITION, LogEntry
from django.dispatch import Signal, receiver

from rush.models.signals.utils import user_content_type
from rush.utils import get_client_ip

logger = getLogger(__name__)

# Fired when *any* admin changelist is viewed
admin_changelist_viewed = Signal()

# Fired when *any* admin changeform is viewed
admin_changeform_viewed = Signal()


@receiver(admin_changelist_viewed)
def log_changelist(sender, request, model, modeladmin, **kwargs):
    user = getattr(request, "user", None)
    if user is not None:
        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=user_content_type().pk,
            object_id=user.pk,
            object_repr=str(user)[:200],
            action_flag=ADDITION,
            change_message=f"{user} viewed the list of {model._meta.verbose_name_plural}.",
        )
    else:
        logger.warning(
            "Request from '{}' for viewing '{}' changelist has no user!".format(
                get_client_ip(None, request),
                model.__name__,
            )
        )


@receiver(admin_changeform_viewed)
def log_changeform(sender, request, model, object_id, modeladmin, **kwargs):
    user = getattr(request, "user", None)
    obj_exists = model.objects.filter(id=object_id).only("pk").exists()
    obj_desc = f"<{model.__name__}: {object_id}>" if obj_exists else f"<{model.__name__}: NOT FOUND>"
    if user is not None:
        try:
            LogEntry.objects.log_action(
                user_id=user.pk,
                content_type_id=user_content_type().pk,
                object_id=user.pk,
                object_repr=str(user)[:200],
                action_flag=ADDITION,
                change_message=f"{user} viewed {obj_desc}.",
            )
        except Exception as e:
            logger.error(
                "Coundn't create a 'LogEntry' when user '{}' viewed '{}'.".format(
                    str(user),
                    obj_desc,
                ),
                exc_info=e,
            )
    else:
        logger.warning(
            "Request from '{}' for viewing '{}' changeform has no user!".format(
                get_client_ip(None, request),
                obj_desc,
            )
        )
