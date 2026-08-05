import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.tasks import BATCHERS, enrich_transcript


@require_GET
@permission_required('transcripts.view_transcript')
def detail(request, pk):
    user = request.user
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    uploaded_file = transcript.uploaded_file
    project = uploaded_file.project

    context = dict(transcript=transcript, uploaded_file=uploaded_file, project=project)
    return render(request, 'transcripts/detail.html', context)


@require_GET
@permission_required('transcripts.change_transcript')
def edit(request, pk):
    user = request.user
    # The editor fetches the content through the detail_json view.
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    uploaded_file = transcript.uploaded_file
    project = uploaded_file.project

    context = dict(transcript=transcript, uploaded_file=uploaded_file, project=project)
    return render(request, 'transcripts/edit.html', context)


@require_GET
@permission_required('transcripts.view_transcript', raise_exception=True)
def detail_json(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)

    return JsonResponse(transcript.content)


@require_POST
@permission_required('transcripts.change_transcript', raise_exception=True)
def update_json(request, pk):
    user = request.user
    # The old content is overwritten without being read. Assigning content
    # below makes the field loaded again, so save() still writes it.
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )

    json_data = json.loads(request.body)
    content = json_data.get('content')

    if not content:
        return JsonResponse({'message': 'content is required.'}, status=400)

    try:
        validated = validate_mmt_content(content)
    except ValidationError as error:
        return JsonResponse(
            {'message': 'The transcript is not valid.', 'errors': error.messages},
            status=400,
        )

    # The validated model is stored rather than the posted dict, so a field
    # the client left out is written with its schema default. Every stored
    # transcript then has the same set of keys, whichever path produced it.
    transcript.content = validated.model_dump()
    transcript.save()

    return JsonResponse({'message': 'Transcript updated successfully.'}, status=200)


@require_POST
@permission_required('transcripts.change_transcript')
def enrich(request, pk):
    user = request.user
    # The Celery task loads the content itself.
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    batching = request.POST.get('batching', 'turns')
    if batching not in BATCHERS:
        return HttpResponseBadRequest('Unknown batching mode.')
    enrich_transcript.delay(transcript.pk, batching)
    messages.add_message(request, messages.INFO, _('Enrichment started.'))
    return redirect('uploaded_files:detail', pk=transcript.uploaded_file_id)


@require_POST
@permission_required('transcripts.delete_transcript')
def delete(request, pk):
    user = request.user
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    uploaded_file = transcript.uploaded_file

    try:
        transcript.delete()
        messages.add_message(
            request, messages.SUCCESS, _('Transcript deleted successfully.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)
    except Exception:
        return HttpResponseServerError(_('Could not delete transcript.'))
