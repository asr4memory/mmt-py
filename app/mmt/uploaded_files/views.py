import json
from http import HTTPStatus

import aiofiles
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import UploadedFile
from .tasks import calculate_server_checksum


@require_POST
@permission_required('uploaded_files.add_uploadedfile')
async def upload(request, pk):
    uploaded_file = await UploadedFile.objects.select_related('project').aget(pk=pk)
    project = uploaded_file.project

    user = await request.auser()
    if project.user_id != user.id:
        return JsonResponse(
            {'message': 'You are not allowed to upload this file.'}, status=403
        )

    file_path = await uploaded_file.afile_path

    if 'file' in request.FILES:
        file = request.FILES['file']
        await handle_uploaded_file(file, file_path)
        uploaded_file.has_file = True
        uploaded_file.transferred = file.size
        await uploaded_file.asave()
        calculate_server_checksum.delay(pk)
        return JsonResponse({'success': True})
    else:
        await uploaded_file.adelete()
        return JsonResponse({'success': False}, status=HTTPStatus.BAD_REQUEST)


async def handle_uploaded_file(file, file_path):
    async with aiofiles.open(file_path, 'wb') as f:
        for chunk in file.chunks():
            await f.write(chunk)


@require_POST
@permission_required('uploaded_files.change_uploadedfile', raise_exception=True)
def update(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project
    if project.user_id != request.user.id:
        return JsonResponse(
            {'message': 'You are not allowed to update this file.'}, status=403
        )

    json_data = json.loads(request.body)
    checksum_client = json_data.get('checksum_client')

    if not checksum_client:
        return JsonResponse({'message': 'checksum_client is required.'}, status=400)

    uploaded_file.checksum_client = checksum_client
    uploaded_file.save()

    return JsonResponse({'message': 'Uploaded file updated successfully.'}, status=200)


@require_POST
@permission_required('uploaded_files.delete_uploadedfile')
def delete(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project

    uploaded_file.delete_file()
    uploaded_file.delete()
    messages.add_message(
        request, messages.SUCCESS, _('Uploaded file deleted successfully.')
    )

    return redirect('projects:detail', pk=project.id)
