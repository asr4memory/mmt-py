from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from mmt.jobs.overview import grouped_jobs
from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


@require_GET
@login_required
@permission_required('transcripts.view_transcriptionjob', raise_exception=True)
def job_list(request):
    user = request.user
    jobs = grouped_jobs(
        TranscriptionJob.objects.owned_by(user),
        EntityExtractionJob.objects.owned_by(user),
    )
    return render(request, 'jobs/job_list.html', {'jobs': jobs})
