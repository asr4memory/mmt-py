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


def send_new_user_email(user: str):
    msg = Message(
        "[MMT2] A new user has registered.",
        recipients=["admin@example.com"],
        body=f"Hi,\n\nThe user {user} has just registered on MMT2. Please activate him.\n\nRegards,\nMMT2",
    )
    mail.send(msg)
    return "Email sent successfully!"
