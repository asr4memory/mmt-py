import json
from collections.abc import Callable

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from mmt.core.utils import filename_safe
from mmt.transcripts import mmt_schema
from mmt.transcripts.exporters import export_to_srt, export_to_vtt, export_to_whisperx
from mmt.transcripts.forms import TranscriptLabelForm
from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.statistics import derive_statistics
from mmt.transcripts.tasks import enrich_transcript


@require_GET
@permission_required('transcripts.view_transcript')
def detail(request, pk):
    user = request.user
    # The content is loaded here, unlike in the other transcript views: the
    # statistics are derived from it.
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)
    uploaded_file = transcript.uploaded_file
    project = uploaded_file.project

    context = dict(
        transcript=transcript,
        uploaded_file=uploaded_file,
        project=project,
        statistics=derive_statistics(transcript.content),
    )
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


@require_http_methods(['PATCH'])
@permission_required('transcripts.change_transcript', raise_exception=True)
def update_json(request: HttpRequest, pk: int) -> HttpResponse:
    """Write the fields named in the request body, and only those.

    The editor saves the label and the content in one request, but either one
    may be sent on its own. A field the body does not name is not written, so
    a write made by another request in the meantime is kept.
    """
    user = request.user
    # The old content is overwritten without being read. Assigning content
    # below makes the field loaded again, so save() still writes it.
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'The body is not valid JSON.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'message': 'No fields to update.'}, status=400)

    written = []

    # Both fields are validated before either is written, so a body with a
    # valid label and an invalid content leaves the transcript untouched.
    if 'label' in payload:
        form = TranscriptLabelForm({'label': payload['label']}, instance=transcript)
        if not form.is_valid():
            return JsonResponse(
                {
                    'message': 'The transcript is not valid.',
                    'errors': form.errors.get_json_data(),
                },
                status=400,
            )
        written.append('label')

    if 'content' in payload:
        content = payload['content']
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
        written.append('content')

    if not written:
        return JsonResponse({'message': 'No fields to update.'}, status=400)

    # The cleaned label is on the instance already: the form was built with the
    # transcript as its instance, and validating it writes the value there.
    transcript.save(update_fields=[*written, 'updated_at'])

    return JsonResponse({'message': 'Transcript updated successfully.'}, status=200)


@require_POST
@permission_required('transcripts.change_transcript')
def enrich(request, pk):
    user = request.user
    # The Celery task loads the content itself.
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    enrich_transcript.delay(transcript.pk)
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


def _export(
    request: HttpRequest,
    pk: int,
    export: Callable[[mmt_schema.Transcript], bytes],
    extension: str,
    content_type: str,
) -> HttpResponse:
    """Shared body of the export views. A helper, never routed to directly."""
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)

    # validate_mmt_content builds the Pydantic model.
    content = validate_mmt_content(transcript.content)

    response = HttpResponse(export(content), content_type=content_type)
    response['Content-Disposition'] = (
        f'attachment; filename="{_export_filename(transcript, extension)}"'
    )
    return response


def _export_filename(transcript: Transcript, extension: str) -> str:
    try:
        stem = filename_safe(transcript.label)
    except ValueError:
        # A label of only punctuation leaves nothing to name the file after.
        stem = f'transcript_{transcript.pk}'

    return f'{stem}.{extension}'


@require_GET
@permission_required('transcripts.view_transcript')
def export_whisperx(request: HttpRequest, pk: int) -> HttpResponse:
    return _export(request, pk, export_to_whisperx, 'json', 'application/json')


@require_GET
@permission_required('transcripts.view_transcript')
def export_vtt(request: HttpRequest, pk: int) -> HttpResponse:
    return _export(request, pk, export_to_vtt, 'vtt', 'text/vtt; charset=utf-8')


@require_GET
@permission_required('transcripts.view_transcript')
def export_srt(request: HttpRequest, pk: int) -> HttpResponse:
    return _export(
        request, pk, export_to_srt, 'srt', 'application/x-subrip; charset=utf-8'
    )
