from flask import render_template
from flask_mail import Mail, Message

mail = Mail()


def send_test_email():
    msg = Message(
        "Hello",
        recipients=["recipient@example.com"],
        body="This is a test email sent from Flask-Mail!",
    )
    mail.send(msg)
    return "Email sent successfully!"


def send_new_user_email(recipients: list[str], user: str):
    body = render_template("mail/new_user.txt", username=user)
    msg = Message(
        "[mmt-py] A new user has registered.", recipients=recipients, body=body
    )
    mail.send(msg)


def send_admin_file_uploaded_email(recipients: list[str], username: str, filename: str):
    body = render_template(
        "mail/file_uploaded_admin.txt", username=username, filename=filename
    )
    msg = Message("[mmt-py] File uploaded", recipients=recipients, body=body)
    mail.send(msg)


def send_user_file_uploaded_email(to_username: str, to_email: str, filename: str):
    body = render_template(
        "mail/file_uploaded_user.txt", username=to_username, filename=filename
    )
    msg = Message(
        "[mmt-py] File uploaded",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)


def send_user_activation_email(to_username: str, to_email: str):
    body = render_template("mail/user_activated.txt", username=to_username)
    msg = Message(
        "[mmt-py] Your account has been activated.",
        recipients=[to_email],
        body=body,
    )
    mail.send(msg)
