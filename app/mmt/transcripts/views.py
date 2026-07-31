import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from mmt.core.utils import filename_safe
from mmt.transcripts.exporters import EXPORT_FORMATS, ExportContext
from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.models import Transcript
from mmt.transcripts.normalize import normalize_content
from mmt.transcripts.tasks import BATCHERS, enrich_transcript

logger = logging.getLogger(__name__)


@require_GET
@permission_required('transcripts.view_transcript')
def detail(request, pk):
    user = request.user
    transcript = get_object_or_404(
        Transcript.objects.defer('content'), pk=pk, uploaded_file__project__user=user
    )
    uploaded_file = transcript.uploaded_file
    project = uploaded_file.project

    context = dict(
        transcript=transcript,
        uploaded_file=uploaded_file,
        project=project,
        export_formats=EXPORT_FORMATS.values(),
    )
    return render(request, 'transcripts/detail.html', context)


@require_GET
@permission_required('transcripts.view_transcript')
def export(request, pk, format_key):
    user = request.user
    export_format = EXPORT_FORMATS.get(format_key)
    if export_format is None:
        raise Http404('Unknown export format.')

    transcript = get_object_or_404(
        Transcript.objects.select_related('uploaded_file__project'),
        pk=pk,
        uploaded_file__project__user=user,
    )
    uploaded_file = transcript.uploaded_file

    try:
        # The normalised content is not saved: an export is a read, so a
        # transcript stored in the legacy whisper shape stays in that shape.
        content = normalize_content(transcript.content)
    except ValidationError:
        logger.exception('Transcript %s cannot be exported: invalid content', pk)
        messages.add_message(
            request,
            messages.ERROR,
            _(
                'This transcript cannot be exported because its content is '
                'invalid. Please contact an administrator.'
            ),
        )
        return redirect('transcripts:detail', pk=pk)

    export_context = ExportContext(
        transcript=content,
        label=transcript.label,
        created_at=transcript.created_at,
        project_title=uploaded_file.project.title,
        filename=uploaded_file.filename,
        media_type=uploaded_file.media_type,
        duration=uploaded_file.duration,
    )

    try:
        stem = filename_safe(transcript.label)
    except ValueError:
        # A label made only of punctuation reduces to an empty string.
        stem = f'transcript_{transcript.pk}'

    response = HttpResponse(
        export_format.export(export_context),
        content_type=export_format.content_type,
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{stem}.{export_format.extension}"'
    )
    return response


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
        validate_mmt_content(content)
    except ValidationError as error:
        return JsonResponse(
            {'message': 'The transcript is not valid.', 'errors': error.messages},
            status=400,
        )

    transcript.content = content
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
