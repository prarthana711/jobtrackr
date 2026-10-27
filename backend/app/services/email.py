import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("jobtrackr.email")


def _one_line(text: str) -> str:
    """Collapse line breaks and repeated spaces, so user text can never add email headers."""
    return " ".join(text.split())


def build_reminder_email(*, to, job_title, company, status, note) -> EmailMessage:
    title = _one_line(job_title)
    company_name = _one_line(company)

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = f"Follow-up reminder: {title} at {company_name}"

    lines = [
        f"This is your reminder to follow up on {title} at {company_name}.",
        f"Current status: {status.replace('_', ' ')}",
    ]
    if note:
        lines += ["", f"Your note: {note}"]
    lines += ["", "Sent by JobTrackr."]
    message.set_content("\n".join(lines))
    return message


def send_email(message: EmailMessage) -> None:
    if not settings.smtp_host:
        # Development mode: show the email in the log instead of sending it
        logger.info("EMAIL (not sent, SMTP is not configured)\n%s", message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)