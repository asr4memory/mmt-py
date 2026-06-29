from pathlib import Path
import zoneinfo

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
from mmt.my_account.tasks import (
    send_upload_permission_request_email,
    create_dpa_pdf,
)

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
            request, messages.INFO, _('Upload permission requested.')
        )
        send_upload_permission_request_email.delay(user.id)

    return HttpResponseRedirect(reverse('account:profile'))


@require_http_methods(['GET', 'POST'])
@login_required()
def accept_terms(request):
    user = request.user
    show_accept_terms_part = not user.has_accepted_terms
    show_accept_dpa_part = user.has_to_agree_to_dpa()

    if request.method == 'POST':
        form = AcceptTermsForm(
            request.POST, terms=show_accept_terms_part, dpa=show_accept_dpa_part
        )

        if form.is_valid():
            if show_accept_terms_part:
                user.accept_terms()

            if show_accept_dpa_part:
                user.accept_dpa()

            user.save()

            if show_accept_dpa_part:
                create_dpa_pdf.delay(user.id)

            messages.add_message(
                request,
                messages.SUCCESS,
                _('You agreed to the required documents.'),
            )

            return HttpResponseRedirect(reverse('welcome'))
    else:
        form = AcceptTermsForm(terms=show_accept_terms_part, dpa=show_accept_dpa_part)

    return render(
        request,
        'account/accept_terms.html',
        dict(
            form=form,
            show_accept_terms_part=show_accept_terms_part,
            show_accept_dpa_part=show_accept_dpa_part,
        ),
    )


@require_GET
def dpa_sample(request):
    context = dict(
        full_name='[Vor- und Nachnamen des Nutzenden]',
        dpa_accepted_at='[Datum, Uhrzeit, Zeitzone]',
    )

    return render(request, 'dpa/dpa_sample.html', context)


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
    response['Content-Disposition'] = f'inline; filename="{Path(dpa.name).name}"'
    response['Content-Type'] = 'application/pdf'
    return response


@require_GET
@login_required()
@user_passes_test(
    lambda user: user.is_superuser, login_url='/', redirect_field_name=None
)
def debug(request):
    return render(request, 'account/debug.html')
