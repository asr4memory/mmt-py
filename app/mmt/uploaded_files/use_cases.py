from math import ceil

from django.conf import settings
from django.db import transaction

from mmt.uploaded_files.models import FileChunk, UploadedFile
from mmt.uploaded_files.tasks import calculate_server_checksum


def upload_chunk(uploaded_file: UploadedFile, index: int, data: bytes) -> bool:
    total_chunks = ceil(uploaded_file.size / settings.MMT_UPLOAD_CHUNK_SIZE)
    if index < 0 or index >= total_chunks:
        raise ValueError(
            f'Invalid chunk index {index} for file with {total_chunks} chunks.'
        )

    if FileChunk.objects.filter(uploaded_file=uploaded_file, index=index).exists():
        return not uploaded_file.missing_chunk_indices()

    chunk = FileChunk(uploaded_file=uploaded_file, index=index)
    chunk.chunk_path.write_bytes(data)
    chunk.create_checksum()
    chunk.save()

    with transaction.atomic():
        locked_file = UploadedFile.objects.select_for_update().get(pk=uploaded_file.pk)
        if not locked_file.has_file and not locked_file.missing_chunk_indices():
            locked_file.assemble_chunks()
            calculate_server_checksum.delay(locked_file.id)
            return True

    return False
