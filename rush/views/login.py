from django.contrib import messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django_ratelimit.decorators import ratelimit

from rush.utils import get_client_ip


@ratelimit(key=get_client_ip, rate="10/m", method="POST", block=True)
@ratelimit(key=get_client_ip, rate="500/d", method="POST", block=True)
def rush_login_view(request):
    """
    GET --> Render the RUSH Admin login page.
    POST --> Submit login form data and redirect to admin homepage.
    """

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            messages.error(request, "Invalid username or password")

    form = AdminAuthenticationForm(request)
    return render(
        request=request,
        template_name="admin/rush_login_page.html",
        context={"form": form},
    )
