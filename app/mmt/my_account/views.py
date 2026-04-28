from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import (
    HttpResponseNotFound,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.core.utils import file_data
from mmt.my_account.forms import AcceptTermsForm, ProfileForm
from mmt.my_account.tasks import send_upload_permission_request_email

User = get_user_model()


@require_GET
@login_required()
def profile(request):
    user = request.user
    profile = user.safe_profile
    context = {
        'profile': profile,
        'show_change_password_link': not user.socialaccount_set.exists(),
        'terms_accepted_date': user.terms_accepted_at
        if user.has_accepted_terms
        else None,
        'show_dpa_section': user.is_external_user(),
        'dpa_accepted_date': user.dpa_accepted_at,
        'show_signed_dpa_link': bool(profile.dpa.name),
    }
    return render(request, 'account/profile.html', context)


@require_http_methods(['GET', 'POST'])
@login_required()
def edit_profile(request):
    user = request.user
    profile = user.safe_profile

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('account:profile'))
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'account/edit_profile.html', {'form': form})


@require_POST
@login_required()
def upload_permission(request):
    user = request.user
    if not user.upload_permission_requested_at:
        user.upload_permission_requested_at = timezone.now()
        user.save()
        messages.add_message(
            request, messages.SUCCESS, _('Upload permission requested.')
        )
        send_upload_permission_request_email.delay(user.id)

    return HttpResponseRedirect(reverse('account:profile'))


@require_http_methods(['GET', 'POST'])
@login_required()
def accept_terms(request):
    user = request.user
    should_accept_terms = not user.has_accepted_terms
    should_accept_dpa = user.has_to_agree_to_dpa()

    if request.method == 'POST':
        form = AcceptTermsForm(
            request.POST, terms=should_accept_terms, dpa=should_accept_dpa
        )

        if form.is_valid():
            if should_accept_terms:
                user.accept_terms()

            if should_accept_dpa:
                user.accept_dpa()

            user.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                _('You agreed to the required documents.'),
            )

            return HttpResponseRedirect(reverse('welcome'))
    else:
        form = AcceptTermsForm(terms=should_accept_terms, dpa=should_accept_dpa)

    return render(
        request,
        'account/accept_terms.html',
        dict(
            form=form,
            should_accept_terms=should_accept_terms,
            should_accept_dpa=should_accept_dpa,
        ),
    )


@require_GET
@login_required()
def download_dpa(request):
    user = request.user
    profile = user.safe_profile
    dpa = profile.dpa

    if not dpa:
        return HttpResponseNotFound('File does not exist.')

    file_path = Path(dpa.path)

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    response = StreamingHttpResponse(
        file_data(file_path), content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'inline; filename="{dpa.name}"'
    response['Content-Type'] = 'application/pdf'
    return response


@require_GET
@login_required()
@user_passes_test(
    lambda user: user.is_superuser, login_url='/', redirect_field_name=None
)
def debug(request):
    return render(request, 'account/debug.html')
