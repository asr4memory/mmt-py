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
        "[mmt-py] A new user has registered.",
        recipients=["admin@example.com"],
        body=(
            f"Hi,\n\nThe user {user} has just registered on mmt-py.\n"
            "Please activate him.\n\n"
            "Regards,\nmmt-py"
        ),
    )
    mail.send(msg)


def send_admin_file_uploaded_email(username: str, email: str, filename: str):
    msg = Message(
        "[mmt-py] File uploaded",
        recipients=["admin@example.com"],
        body=(
            f"Hi,\n\nUser {username} ({email}) has uploaded the following file:\n{filename}\n\n"
            "Regards,\nmmt-py"
        ),
    )
    mail.send(msg)


def send_user_file_uploaded_email(to_username: str, to_email: str, filename: str):
    msg = Message(
        "[mmt-py] File uploaded",
        recipients=[to_email],
        body=(
            f"Hi {to_username},\n\nyour file {filename} has been uploaded.\n\n"
            "The file will now undergo a technical review and will subsequently "
            "be accessible within the oh.d system.\n\n"
            "The technical review and transcoding process may take several working days, "
            "depending on the scope, complexity, and workload. "
            "You will receive an email notification as soon as the file becomes "
            "available in the oh.d system.\n\n"
            "Regards,\nmmt-py"
        ),
    )
    mail.send(msg)
