from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType


def user_content_type() -> ContentType:
    return ContentType.objects.get_for_model(get_user_model())
