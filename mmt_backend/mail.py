from flask import render_template
from flask_mail import Mail, Message

mail = Mail()


def send_test_email():
    body = render_template("mail/en/test_mail.txt")
    msg = Message(
        "Hello",
        recipients=["recipient@example.com"],
        body=body,
    )
    mail.send(msg)


def send_new_user_email(recipients: list[str], user: str):
    body = render_template("mail/en/new_user.txt", username=user)
    msg = Message(
        "[mmt-py] A new user has registered.", recipients=recipients, body=body
    )
    mail.send(msg)


def send_admin_file_uploaded_email(recipients: list[str], username: str, filename: str):
    body = render_template(
        "mail/en/file_uploaded_admin.txt", username=username, filename=filename
    )
    msg = Message("[mmt-py] File uploaded", recipients=recipients, body=body)
    mail.send(msg)


def send_user_file_uploaded_email(
    to_username: str, to_email: str, filename: str, locale: str = "en"
):
    body = render_template(
        f"mail/{locale}/file_uploaded_user.txt", username=to_username, filename=filename
    )
    msg = Message(
        "[mmt-py] File uploaded",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)


def send_user_activation_email(to_username: str, to_email: str, locale: str = "en"):
    body = render_template(f"mail/{locale}/user_activated.txt", username=to_username)
    msg = Message(
        "[mmt-py] Your account has been activated.",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)
