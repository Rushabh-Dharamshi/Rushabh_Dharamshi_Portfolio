import smtplib
from email.message import EmailMessage
from pathlib import Path

from budget_tracker_api.errors import ServiceUnavailableError


class EmailService:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_use_tls: bool,
        default_recipient: str,
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._smtp_use_tls = smtp_use_tls
        self._default_recipient = default_recipient

    @property
    def default_recipient(self) -> str:
        return self._default_recipient

    def is_configured(self) -> bool:
        return bool(
            self._smtp_host
            and self._smtp_port
            and self._smtp_username
            and self._smtp_password
            and self._default_recipient
        )

    def send_email(
        self,
        subject: str,
        body: str,
        recipient: str | None = None,
    ) -> dict:
        if not self.is_configured():
            raise ServiceUnavailableError(
                "Email delivery is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and REPORT_EMAIL_TO."
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._smtp_username
        message["To"] = recipient or self._default_recipient
        message.set_content(body)

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30) as smtp:
            if self._smtp_use_tls:
                smtp.starttls()
            smtp.login(self._smtp_username, self._smtp_password)
            smtp.send_message(message)

        return {
            "recipient": recipient or self._default_recipient,
            "subject": subject,
        }

    def send_report_email(
        self,
        subject: str,
        body: str,
        attachment_path: Path,
        recipient: str | None = None,
    ) -> dict:
        if not self.is_configured():
            raise ServiceUnavailableError(
                "Email delivery is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and REPORT_EMAIL_TO."
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._smtp_username
        message["To"] = recipient or self._default_recipient
        message.set_content(body)

        attachment_bytes = attachment_path.read_bytes()
        message.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="pdf",
            filename=attachment_path.name,
        )

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30) as smtp:
            if self._smtp_use_tls:
                smtp.starttls()
            smtp.login(self._smtp_username, self._smtp_password)
            smtp.send_message(message)

        return {
            "recipient": recipient or self._default_recipient,
            "subject": subject,
            "attachment_name": attachment_path.name,
        }
