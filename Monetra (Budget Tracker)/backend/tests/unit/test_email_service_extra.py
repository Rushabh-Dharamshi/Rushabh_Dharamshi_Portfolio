from pathlib import Path

import pytest

from budget_tracker_api.errors import ServiceUnavailableError
from budget_tracker_api.services.email_service import EmailService


class FakeSMTP:
    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.sent_messages = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.sent_messages.append(message)


def test_email_service_configuration_and_default_recipient():
    service = EmailService("smtp.example.com", 587, "user@example.com", "secret", True, "to@example.com")
    assert service.default_recipient == "to@example.com"
    assert service.recipient_name == "Rushabh Dharamshi"
    assert service.is_configured() is True


def test_email_service_requires_configuration(tmp_path):
    service = EmailService("", 0, "", "", True, "")
    with pytest.raises(ServiceUnavailableError):
        service.send_email("Subject", "Body")
    with pytest.raises(ServiceUnavailableError):
        service.send_report_email("Subject", "Body", tmp_path / "missing.pdf")


def test_send_email_and_report_email(monkeypatch, tmp_path):
    fake_instances = []

    def fake_smtp(host, port, timeout):
        smtp = FakeSMTP(host, port, timeout)
        fake_instances.append(smtp)
        return smtp

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fake_smtp)

    service = EmailService("smtp.example.com", 587, "user@example.com", "secret", True, "to@example.com")
    simple_result = service.send_email("Subject", "Body", recipient="override@example.com")

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    report_result = service.send_report_email("Report", "Attached", pdf_path)

    assert simple_result == {"recipient": "override@example.com", "subject": "Subject"}
    assert report_result == {
        "recipient": "to@example.com",
        "subject": "Report",
        "attachment_name": "report.pdf",
    }
    assert fake_instances[0].started_tls is True
    assert fake_instances[0].logged_in == ("user@example.com", "secret")
    assert fake_instances[0].sent_messages[0]["To"] == "override@example.com"
    assert fake_instances[1].sent_messages[0].get_payload()[-1].get_filename() == "report.pdf"


def test_send_email_without_tls(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 25, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService("smtp.example.com", 25, "user@example.com", "secret", False, "to@example.com")
    service.send_email("Subject", "Body")
    assert smtp.started_tls is False


def test_send_email_replaces_recipient_name_placeholder(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "to@example.com",
        recipient_name="Rushabh Dharamshi",
    )

    service.send_email("Subject", "Dear [Recipient's Name],\n\nYour report is ready.")

    content = smtp.sent_messages[0].get_content()
    assert "Dear Rushabh Dharamshi," in content
    assert "[Recipient's Name]" not in content
