from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from mmt.my_account.forms import ProfileForm
from mmt.my_account.tasks import send_upload_permission_request_email

User = get_user_model()


@require_GET
@login_required()
def profile(request):
    user = request.user
    profile = user.safe_profile
    context = {
        "profile": profile,
        "show_change_password_link": not user.socialaccount_set.exists(),
    }
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


@require_POST
@login_required()
def upload_permission(request):
    user = request.user
    if not user.upload_permission_requested_at:
        user.upload_permission_requested_at = timezone.now()
        user.save()
        messages.add_message(
            request, messages.SUCCESS, _("Upload permission requested.")
        )
        send_upload_permission_request_email.delay(user.id)

    return HttpResponseRedirect(reverse("account:profile"))


@require_GET
@login_required()
@user_passes_test(
    lambda user: user.is_superuser, login_url="/", redirect_field_name=None
)
def debug(request):
    return render(request, "account/debug.html")
