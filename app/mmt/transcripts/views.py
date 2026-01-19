from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseServerError
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from mmt.transcripts.models import Transcript
from mmt.transcripts.use_cases import delete_transcript


@require_GET
@permission_required('transcripts.view_transcript')
def edit(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)
    uploaded_file = transcript.uploaded_file
    project = transcript.project

    context = dict(transcript=transcript, uploaded_file=uploaded_file, project=project)
    return render(request, 'transcripts/detail.html', context)


@require_GET
@permission_required('transcripts.change_transcript')
def edit(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)
    uploaded_file = transcript.uploaded_file
    project = uploaded_file.project

    context = dict(transcript=transcript, uploaded_file=uploaded_file, project=project)
    return render(request, 'transcripts/edit.html', context)


@require_GET
@permission_required('transcripts.view_transcript')
def json(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)

    return JsonResponse(transcript.content)


@require_POST
@permission_required('transcripts.delete_transcript')
def delete(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, uploaded_file__project__user=user)
    uploaded_file = transcript.uploaded_file

    if delete_transcript(transcript):
        messages.add_message(
            request, messages.SUCCESS, _('Transcript deleted successfully.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)
    else:
        return HttpResponseServerError(_('Could not delete transcript.'))
