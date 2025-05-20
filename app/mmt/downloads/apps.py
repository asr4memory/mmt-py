import atexit
import os
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from .tasks import send_new_file_email


observer = PollingObserver()
upload_path = settings.MMT_USER_FILES_DIR


def on_shutdown():
    observer.stop()
    observer.join()


class MyEventHandler(FileSystemEventHandler):
    # FileCreatedEvent(src_path='./test2.txt', dest_path='', event_type='created', is_directory=False, is_synthetic=False)
    def on_created(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)
        rel_path = path.relative_to(upload_path)
        parts = rel_path.parts

        if len(parts) == 3 and not event.is_directory:
            username_dir, type_dir, filename = parts
            if type_dir == "downloads":
                try:
                    User = get_user_model()
                    user = User.objects.get(username=username_dir)
                    send_new_file_email.delay(user.id, filename)
                except User.DoesNotExist:
                    # Maybe notifiy admin?
                    pass


class DownloadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mmt.downloads"

    def ready(self):
        if os.environ.get("RUN_MAIN") and settings.MMT_DETECT_DOWNLOADABLE_FILES:
            event_handler = MyEventHandler()

            observer.schedule(event_handler, upload_path, recursive=True)
            observer.start()

            atexit.register(on_shutdown)
