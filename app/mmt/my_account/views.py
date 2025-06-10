from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation.trans_real import parse_accept_lang_header
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ProfileForm, RegisterForm
from .models import Profile
from .tasks import send_new_user_email

User = get_user_model()


def get_preferred_language(request) -> str:
    result = "en"
    langs = parse_accept_lang_header(request.headers.get("Accept-Language"))
    for lang in reversed(langs):
        loc = lang[0][:2]
        if loc == "en" or loc == "de":
            result = loc

    return result


@require_http_methods(["GET", "POST"])
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            user.is_active = False
            user.save()

            locale = get_preferred_language(request)
            Profile.objects.create(user=user, locale=locale)
            user.create_user_directories()

            send_new_user_email.delay(user.id)

            return redirect("account:registration_complete")
        else:
            pass
    else:
        form = RegisterForm()

    context = {"form": form}
    return render(request, "account/register.html", context)


@require_GET
def registration_complete(request):
    return render(request, "account/registration_complete.html")


@require_GET
@login_required()
def profile(request):
    return render(request, "account/profile.html", {"profile": request.user.profile})


@require_http_methods(["GET", "POST"])
@login_required()
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("account:profile"))
    else:
        form = ProfileForm(instance=profile)

    return render(request, "account/edit_profile.html", {"form": form})
