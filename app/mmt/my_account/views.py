from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ProfileForm

User = get_user_model()


@require_GET
@login_required()
def profile(request):
    user = request.user
    profile = user.safe_profile
    context = {"profile": profile}
    return render(request, "account/profile.html", context)


@require_http_methods(["GET", "POST"])
@login_required()
def edit_profile(request):
    user = request.user
    profile = user.safe_profile

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("account:profile"))
    else:
        form = ProfileForm(instance=profile)

    return render(request, "account/edit_profile.html", {"form": form})


@require_GET
@login_required()
@user_passes_test(
    lambda user: user.is_superuser, login_url="/", redirect_field_name=None
)
def debug(request):
    return render(request, "account/debug.html")
