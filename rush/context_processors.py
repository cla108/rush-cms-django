from django.conf import settings


def base_url_from_request(request) -> str:
    return request.build_absolute_uri("/").rstrip("/")


def base_media_url(request):
    return {
        "BASE_MEDIA_URL": base_url_from_request(request) + settings.MEDIA_URL,
    }


def base_static_url(request):
    return {
        "BASE_STATIC_URL": base_url_from_request(request) + settings.STATIC_URL,
    }
