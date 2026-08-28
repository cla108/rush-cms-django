from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from rush import views
from rush.graphql import PublishedStateGraphQLView, get_schema

urlpatterns = [
    path("login/", views.rush_login_view),
    path("summernote/", include("django_summernote.urls")),
    path("_nested_admin/", include("nested_admin.urls")),
    path(
        # TODO: Remove csrf exempt here and add the token to internal graphQL requests!
        "graphql/",
        csrf_exempt(PublishedStateGraphQLView.as_view(graphiql=True, schema=get_schema())),
    ),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# add silk urls during development
if settings.DEBUG or settings.ENABLE_SILK_PROFILING:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

# Add admin urls at the end so others can resolve before this "catch all" (base url)
urlpatterns += [path("", admin.site.urls)]
