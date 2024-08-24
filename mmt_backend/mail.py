from flask import render_template
from flask_mail import Mail, Message

mail = Mail()


CONST_SUBJECT_PREFIX = "[mmt-py]"


def send_test_email():
    body = render_template("mail/en/test_mail.txt")
    msg = Message(
        "Hello",
        recipients=["recipient@example.com"],
        body=body,
    )
    mail.send(msg)


def send_new_user_email(recipients: list[str], user: str):
    subject = "A new user has registered."
    body = render_template("mail/en/new_user.txt", username=user)
    msg = Message(subject=f"{CONST_SUBJECT_PREFIX} {subject}", recipients=recipients, body=body)
    mail.send(msg)


def send_admin_file_uploaded_email(recipients: list[str], username: str, filename: str):
    subject = "File uploaded"
    body = render_template(
        "mail/en/file_uploaded_admin.txt", username=username, filename=filename
    )
    msg = Message(subject=f"{CONST_SUBJECT_PREFIX} {subject}", recipients=recipients, body=body)
    mail.send(msg)


def send_user_file_uploaded_email(
    to_username: str, to_email: str, filename: str, locale: str = "en"
):
    subject = "Datei hochgeladen" if locale == "de" else "File uploaded"
    body = render_template(
        f"mail/{locale}/file_uploaded_user.txt", username=to_username, filename=filename
    )
    msg = Message(
        subject=f"{CONST_SUBJECT_PREFIX} {subject}",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)


def send_user_activation_email(to_username: str, to_email: str, locale: str = "en"):
    subject = (
        "Ihr Konto wurde aktiviert."
        if locale == "de"
        else "Your account has been activated."
    )
    body = render_template(f"mail/{locale}/user_activated.txt", username=to_username)
    msg = Message(
        subject=f"{CONST_SUBJECT_PREFIX} {subject}",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)
