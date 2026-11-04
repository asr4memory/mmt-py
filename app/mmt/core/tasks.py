from celery import shared_task

# smtplib.SMTPException and the connection errors are all subclasses of OSError.
# A failed delivery is retried with exponentially growing delays, because most
# SMTP failures, such as greylisting, are temporary.
email_task = shared_task(
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 5},
)


@shared_task
def add(x, y):
    return x + y
