from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from rush.models.signals.utils import user_content_type
from rush.utils import get_client_ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=user_content_type().pk,
        object_id=user.pk,
        object_repr=str(user)[:200],
        action_flag=CHANGE,
        change_message=f"{user} login from {get_client_ip(None, request)}.",
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # user may be None if session expired
    username = user.username if user else "UNKNOWN (MOST LIKELY THE SESSION EXPIRED)"
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=user_content_type().pk,
        object_id=user.pk,
        object_repr=str(user)[:200],
        action_flag=CHANGE,
        change_message=f"{username} logout from {get_client_ip(None, request)}.",
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", None)
    anonymous_user, _ = get_user_model().objects.get_or_create(username="anonymous")
    client_ip = get_client_ip(None, request)
    if username is None:
        LogEntry.objects.log_action(
            user_id=anonymous_user.pk,
            content_type_id=user_content_type().pk,
            object_id=anonymous_user.pk,
            object_repr=str(anonymous_user)[:200],
            action_flag=CHANGE,
            change_message=f"Failed login attempt for an unspecified user from {client_ip}.",
        )
    elif not get_user_model().objects.filter(username=username).exists():
        LogEntry.objects.log_action(
            user_id=anonymous_user.pk,
            content_type_id=user_content_type().pk,
            object_id=anonymous_user.pk,
            object_repr=str(anonymous_user)[:200],
            action_flag=CHANGE,
            change_message=f"Failed login attempt for unknown user '{username}' from {client_ip}.",
        )
    else:
        user = get_user_model().objects.filter(username=username).get()
        LogEntry.objects.log_action(
            user_id=user.pk,
            content_type_id=user_content_type().pk,
            object_id=user.pk,
            object_repr=str(user)[:200],
            action_flag=CHANGE,
            change_message=f"Failed login attempt for '{user}' from {client_ip}.",
        )
