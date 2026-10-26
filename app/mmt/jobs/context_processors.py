from mmt.jobs.overview import active_job_count
from mmt.transcripts.models import EntityExtractionJob, TranscriptionJob


def job_counts(request):
    user = request.user
    if not user.has_perm('transcripts.view_transcriptionjob'):
        return {}

    # The template calls the function, so the queries run only on pages
    # that render the navigation.
    def count():
        return active_job_count(
            TranscriptionJob.objects.owned_by(user),
            EntityExtractionJob.objects.owned_by(user),
        )

    return {'active_job_count': count}
