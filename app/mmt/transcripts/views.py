from django.contrib.auth.decorators import login_required, permission_required
from django.http import (
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from mmt.transcripts.models import Transcript


#
# Transcripts
#
@require_GET
@permission_required('projects.view_transcript')
def transcript_detail(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, project__user=user)
    project = transcript.project

    context = {
        'transcript': transcript,
        'project': project,
    }
    return render(request, 'transcripts/transcript_detail.html', context)


@require_GET
@permission_required('projects.view_transcript')
def transcript_json(request, pk):
    user = request.user
    transcript = get_object_or_404(Transcript, pk=pk, project__user=user)

    return JsonResponse(transcript.content)
