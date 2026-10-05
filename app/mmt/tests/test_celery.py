from celery import current_app


def test_django_process_sends_media_tasks_to_the_media_queue():
    """The web process sends tasks with the app configured from the settings."""
    route = current_app.amqp.router.route(
        {}, 'mmt.uploaded_files.tasks.task_generate_web_video'
    )

    assert route['queue'].name == 'media'
