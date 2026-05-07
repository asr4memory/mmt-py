from mmt.uploaded_files.models import FileChunk, UploadedFile
from mmt.uploaded_files.tasks import calculate_server_checksum, create_waveform_data


def upload_chunk(uploaded_file: UploadedFile, index: int, data: bytes) -> bool:
    if FileChunk.objects.filter(uploaded_file=uploaded_file, index=index).exists():
        return not uploaded_file.missing_chunk_indices()

    chunk = FileChunk(uploaded_file=uploaded_file, index=index)
    chunk.chunk_path.write_bytes(data)
    chunk.create_checksum()
    chunk.save()

    if not uploaded_file.missing_chunk_indices():
        uploaded_file.assemble_chunks()
        calculate_server_checksum.delay(uploaded_file.id)
        create_waveform_data.delay(uploaded_file.id)
        return True

    return False
