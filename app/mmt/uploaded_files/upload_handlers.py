from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler


class CoolFileUploadHandler(FileUploadHandler):
    """
    Upload handler that keeps interrupted files.
    Proof of concept version.
    """

    def new_file(self, *args, **kwargs):
        """
        Create the file object to append to as data is coming in.
        """
        super().new_file(*args, **kwargs)

        # Convert to int as a validation mechanism.
        self.uploaded_file_id = int(self.request.headers.get("Uploaded-File-ID"))
        path = settings.MMT_USER_FILES_DIR / str(self.uploaded_file_id)

        self.file = open(path, "wb")

    def receive_data_chunk(self, raw_data, start):
        self.file.write(raw_data)

    def file_complete(self, file_size):
        self.file.close()
        return None

    def upload_interrupted(self):
        self.file.close()
