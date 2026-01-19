from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import (
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from mmt.transcripts.models import Transcript
from mmt.transcripts.use_cases import create_transcript


@require_GET
@permission_required('transcripts.change_transcript')
def edit(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, project__user=user)
    project = transcript.project

    context = {
        'transcript': transcript,
        'project': project,
    }
    return render(request, 'transcripts/transcript_edit.html', context)


@require_GET
@permission_required('transcripts.view_transcript')
def json(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, project__user=user)

    return JsonResponse(transcript.content)
