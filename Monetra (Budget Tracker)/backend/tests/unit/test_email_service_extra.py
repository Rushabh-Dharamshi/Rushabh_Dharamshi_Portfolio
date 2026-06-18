from pathlib import Path
from email.message import EmailMessage
import smtplib
import ssl

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
    service = EmailService("smtp.example.com", 587, "user@example.com", "secret", True, "to@example.com", allowed_recipients="to@example.com")
    assert service.default_recipient == "to@example.com"
    assert service.recipient_name == "Rushabh Dharamshi"
    assert service.is_configured() is True


def test_email_service_can_be_configured_without_default_recipient():
    service = EmailService("smtp.example.com", 587, "user@example.com", "secret", True, "", allowed_recipients="to@example.com")
    assert service.default_recipient == ""
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

    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "to@example.com",
        allowed_recipients="to@example.com,override@example.com",
    )
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
    service = EmailService("smtp.example.com", 25, "user@example.com", "secret", False, "to@example.com", allowed_recipients="to@example.com")
    service.send_email("Subject", "Body")
    assert smtp.started_tls is False


def test_send_email_to_mailpit_without_smtp_auth(monkeypatch):
    smtp = FakeSMTP("mailpit", 1025, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "mailpit",
        1025,
        "noreply@monetra.local",
        "",
        False,
        "owner@monetra.test",
        smtp_require_auth=False,
        allowed_recipients="owner@monetra.test,dummy001@monetra.test",
    )

    result = service.send_email("Subject", "Body", recipient="dummy001@monetra.test")

    assert result == {"recipient": "dummy001@monetra.test", "subject": "Subject"}
    assert smtp.logged_in is None
    assert smtp.sent_messages[0]["To"] == "dummy001@monetra.test"


def test_email_service_blocks_recipients_outside_allowlist(monkeypatch):
    def fail_smtp(*args, **kwargs):
        raise AssertionError("blocked recipient must not open SMTP")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fail_smtp)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "sender@gmail.com",
        "secret",
        True,
        "",
        allowed_recipients="owned.one@gmail.com,owned.two@gmail.com",
    )

    with pytest.raises(ServiceUnavailableError, match="EMAIL_ALLOWED_RECIPIENTS"):
        service.send_email("Subject", "Body", recipient="random.person@gmail.com")


def test_email_service_blocks_real_smtp_when_allowlist_is_missing(monkeypatch):
    def fail_smtp(*args, **kwargs):
        raise AssertionError("missing allowlist must not open SMTP")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fail_smtp)
    service = EmailService("smtp.gmail.com", 587, "sender@gmail.com", "secret", True, "", delivery_mode="real")

    with pytest.raises(ServiceUnavailableError, match="EMAIL_ALLOWED_RECIPIENTS"):
        service.send_email("Subject", "Body", recipient="owned.one@gmail.com")


def test_email_service_sends_to_allowlisted_recipient(monkeypatch):
    smtp = FakeSMTP("smtp.gmail.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "sender@gmail.com",
        "secret",
        True,
        "",
        allowed_recipients="owned.one@gmail.com,owned.two@gmail.com",
    )

    result = service.send_email("Subject", "Body", recipient="Owned.One@gmail.com")

    assert result == {"recipient": "Owned.One@gmail.com", "subject": "Subject"}
    assert smtp.sent_messages[0]["To"] == "Owned.One@gmail.com"


def test_email_service_retries_transient_starttls_failure(monkeypatch):
    attempts = []

    class FlakySMTP(FakeSMTP):
        def starttls(self):
            attempts.append(self)
            if len(attempts) == 1:
                raise ssl.SSLEOFError("temporary EOF during STARTTLS")
            super().starttls()

    def fake_smtp(host, port, timeout):
        return FlakySMTP(host, port, timeout)

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fake_smtp)
    monkeypatch.setattr("budget_tracker_api.services.email_service.time.sleep", lambda seconds: None)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "sender@gmail.com",
        "secret",
        True,
        "",
        allowed_recipients="owned.one@gmail.com",
    )

    result = service.send_email("Subject", "Body", recipient="owned.one@gmail.com")

    assert result == {"recipient": "owned.one@gmail.com", "subject": "Subject"}
    assert len(attempts) == 2
    assert attempts[1].sent_messages[0]["To"] == "owned.one@gmail.com"


def test_email_service_uses_configured_sender_email(monkeypatch):
    smtp = FakeSMTP("smtp.gmail.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "rushabh.dharamshi@gmail.com",
        "secret",
        True,
        "",
        allowed_recipients="testpurposes683@gmail.com",
        sender_email="rushabh.dharamshi@gmail.com",
    )

    service.send_email("Reminder", "Body", recipient="testpurposes683@gmail.com")

    assert smtp.sent_messages[0]["From"] == "rushabh.dharamshi@gmail.com"
    assert smtp.sent_messages[0]["To"] == "testpurposes683@gmail.com"


def test_hybrid_email_sends_real_allowlisted_recipient(monkeypatch):
    smtp = FakeSMTP("smtp.gmail.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "rushabh.dharamshi@gmail.com",
        "secret",
        True,
        "",
        delivery_mode="hybrid",
        allowed_recipients="rushabh.dharamshi@gmail.com,testpurposes683@gmail.com",
        sender_email="rushabh.dharamshi@gmail.com",
        mock_domains="monetra.test",
        mock_sender_email="demo@monetra.test",
    )

    result = service.send_email("Subject", "Body", recipient="testpurposes683@gmail.com")

    assert result == {"recipient": "testpurposes683@gmail.com", "subject": "Subject"}
    assert smtp.started_tls is True
    assert smtp.logged_in == ("rushabh.dharamshi@gmail.com", "secret")
    assert smtp.sent_messages[0]["From"] == "rushabh.dharamshi@gmail.com"
    assert smtp.sent_messages[0]["To"] == "testpurposes683@gmail.com"


def test_hybrid_email_records_mock_domain_without_smtp(monkeypatch, tmp_path):
    def fail_smtp(*args, **kwargs):
        raise AssertionError("mock-domain recipient must not open SMTP")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fail_smtp)
    service = EmailService(
        "",
        0,
        "",
        "",
        False,
        "",
        delivery_mode="hybrid",
        allowed_recipients="rushabh.dharamshi@gmail.com",
        mock_domains="@monetra.test,example.test",
        mock_sender_email="demo@monetra.test",
    )
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    simple_result = service.send_email("Subject", "Body", recipient="dummy001@monetra.test")
    report_result = service.send_report_email("Report", "Attached", pdf_path, recipient="user@example.test")

    assert service.is_configured() is True
    assert simple_result == {"recipient": "dummy001@monetra.test", "subject": "Subject", "status": "simulated"}
    assert report_result == {
        "recipient": "user@example.test",
        "subject": "Report",
        "attachment_name": "report.pdf",
        "status": "simulated",
    }
    recorded_messages = service.recorded_messages
    assert len(recorded_messages) == 2
    assert recorded_messages[0]["id"] == 1
    assert recorded_messages[0]["created_at"].endswith("Z")
    assert recorded_messages[0]["recipient"] == "dummy001@monetra.test"
    assert recorded_messages[0]["subject"] == "Subject"
    assert recorded_messages[0]["sender"] == "demo@monetra.test"
    assert recorded_messages[0]["body"] == "Body\n\nKind Regards,\nMonetra Organisation\n"
    assert recorded_messages[0]["status"] == "simulated"
    assert recorded_messages[0]["has_attachment"] is False
    assert recorded_messages[0]["attachment_name"] is None
    assert recorded_messages[1]["recipient"] == "user@example.test"
    assert recorded_messages[1]["subject"] == "Report"
    assert recorded_messages[1]["sender"] == "demo@monetra.test"
    assert recorded_messages[1]["body"] == "Attached\n\nKind Regards,\nMonetra Organisation\n"
    assert recorded_messages[1]["status"] == "simulated"
    assert recorded_messages[1]["has_attachment"] is True
    assert recorded_messages[1]["attachment_name"] == "report.pdf"
    assert recorded_messages[1]["attachment_url"] == "/api/reports/monthly"
    assert service.list_mock_messages("dummy001@monetra.test")[0]["subject"] == "Subject"


def test_mock_inbox_is_limited_to_mock_domains():
    service = EmailService("", 0, "", "", False, "", delivery_mode="hybrid", mock_domains="monetra.test")
    service.send_email("Reset", "Reset code 123", recipient="demo@monetra.test")

    assert service.is_mock_recipient("demo@monetra.test") is True
    assert service.is_mock_recipient("real@gmail.com") is False
    assert service.list_mock_messages("demo@monetra.test")[0]["body"] == "Reset code 123\n\nKind Regards,\nMonetra Organisation\n"
    with pytest.raises(ServiceUnavailableError, match="mock email domains"):
        service.list_mock_messages("real@gmail.com")


def test_hybrid_email_blocks_unknown_real_recipient(monkeypatch):
    def fail_smtp(*args, **kwargs):
        raise AssertionError("blocked recipient must not open SMTP")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fail_smtp)
    service = EmailService(
        "smtp.gmail.com",
        587,
        "rushabh.dharamshi@gmail.com",
        "secret",
        True,
        "",
        delivery_mode="hybrid",
        allowed_recipients="rushabh.dharamshi@gmail.com",
        mock_domains="monetra.test",
    )

    with pytest.raises(ServiceUnavailableError, match="EMAIL_ALLOWED_RECIPIENTS"):
        service.send_email("Subject", "Body", recipient="random.person@gmail.com")


def test_dry_run_email_requires_no_smtp_and_does_not_open_connection(monkeypatch, tmp_path):
    def fail_smtp(*args, **kwargs):
        raise AssertionError("dry-run mode must not open SMTP")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", fail_smtp)
    service = EmailService("", 0, "", "", False, "", delivery_mode="mock")
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    simple_result = service.send_email("Subject", "Body", recipient="dummy001@monetra.test")
    report_result = service.send_report_email("Report", "Attached", pdf_path, recipient="dummy001@monetra.test")

    assert service.is_configured() is True
    assert service.delivery_mode == "dry_run"
    assert simple_result == {"recipient": "dummy001@monetra.test", "subject": "Subject", "status": "simulated"}
    assert report_result == {
        "recipient": "dummy001@monetra.test",
        "subject": "Report",
        "attachment_name": "report.pdf",
        "status": "simulated",
    }
    recorded_messages = service.recorded_messages
    assert len(recorded_messages) == 2
    assert recorded_messages[0]["recipient"] == "dummy001@monetra.test"
    assert recorded_messages[0]["subject"] == "Subject"
    assert recorded_messages[0]["sender"] == "noreply@monetra.local"
    assert recorded_messages[0]["body"] == "Body\n\nKind Regards,\nMonetra Organisation\n"
    assert recorded_messages[0]["status"] == "simulated"
    assert recorded_messages[0]["has_attachment"] is False
    assert recorded_messages[0]["attachment_name"] is None
    assert recorded_messages[1]["recipient"] == "dummy001@monetra.test"
    assert recorded_messages[1]["subject"] == "Report"
    assert recorded_messages[1]["sender"] == "noreply@monetra.local"
    assert recorded_messages[1]["body"] == "Attached\n\nKind Regards,\nMonetra Organisation\n"
    assert recorded_messages[1]["status"] == "simulated"
    assert recorded_messages[1]["has_attachment"] is True
    assert recorded_messages[1]["attachment_name"] == "report.pdf"
    assert recorded_messages[1]["attachment_url"] == "/api/reports/monthly"


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
        allowed_recipients="to@example.com",
    )

    service.send_email("Subject", "Dear [Recipient's Name],\n\nYour report is ready.")

    content = smtp.sent_messages[0].get_content()
    assert "Dear Rushabh Dharamshi," in content
    assert "[Recipient's Name]" not in content
    assert content.endswith("Kind Regards,\nMonetra Organisation\n")


def test_send_email_uses_registered_username_for_recipient(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "",
        recipient_name="Fallback Name",
        allowed_recipients="rushabh@example.com,unknown@example.com",
        recipient_name_resolver=lambda email: {"username": "Rushabh_4"} if email == "rushabh@example.com" else None,
    )

    service.send_email("Subject", "Dear [Recipient's Name],\n\nYour report is ready.", recipient="rushabh@example.com")
    service.send_email("Subject", "Dear User, Your report is ready.", recipient="unknown@example.com")

    first_content = smtp.sent_messages[0].get_content()
    second_content = smtp.sent_messages[1].get_content()
    assert "Dear Rushabh_4," in first_content
    assert "Fallback Name" not in first_content
    assert "Dear Fallback Name," in second_content
    assert "Dear User" not in second_content


def test_send_email_replaces_dear_user_salutation(monkeypatch):
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
        allowed_recipients="to@example.com",
    )

    service.send_email("Subject", "Dear User, Your report is ready.")

    content = smtp.sent_messages[0].get_content()
    assert content.count("Dear Rushabh Dharamshi,") == 1
    assert "Dear User" not in content
    assert "Your report is ready." in content


def test_send_email_collapses_duplicate_personal_salutations(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "to@example.com",
        recipient_name="Rushabh",
        allowed_recipients="to@example.com",
    )

    service.send_email("Subject", "Dear [Recipient's Name],\n\nDear Rushabh, Your bill is due.")

    content = smtp.sent_messages[0].get_content()
    assert content.count("Dear Rushabh,") == 1
    assert "Dear Rushabh,\n\nYour bill is due." in content


def test_send_email_replaces_existing_signoff(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "to@example.com",
        allowed_recipients="to@example.com",
    )

    service.send_email("Subject", "Your report is ready.\n\nBest regards,\nRushabh Dharamshi")

    content = smtp.sent_messages[0].get_content()
    assert "Best regards" not in content
    assert content.endswith("Kind Regards,\nMonetra Organisation\n")


def test_send_email_replaces_same_line_standard_signoff(monkeypatch):
    smtp = FakeSMTP("smtp.example.com", 587, 30)
    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", lambda *args, **kwargs: smtp)
    service = EmailService(
        "smtp.example.com",
        587,
        "user@example.com",
        "secret",
        True,
        "to@example.com",
        allowed_recipients="to@example.com",
    )

    service.send_email("Subject", "Your report is ready. Kind Regards, Monetra Organisation")

    content = smtp.sent_messages[0].get_content()
    assert content.count("Kind Regards") == 1
    assert content.count("Monetra Organisation") == 1
    assert "Your report is ready.\n\nKind Regards,\nMonetra Organisation\n" in content


def test_email_service_remaining_edge_paths(monkeypatch):
    service = EmailService(
        "smtp.example.com",
        587,
        "sender@example.com",
        "secret",
        True,
        "",
        delivery_mode="hybrid",
        allowed_recipients=["real@example.com"],
        mock_domains=["monetra.test"],
        mock_sender_email="demo@monetra.test",
    )

    mock_result = service.send_email("Subject", "Dear User,\n\nBody", recipient="demo@monetra.test")
    assert mock_result["status"] == "simulated"
    assert service.list_mock_messages("demo@monetra.test", limit="bad")[0]["sender"] == "demo@monetra.test"
    service.set_recipient_name_resolver(lambda recipient: (_ for _ in ()).throw(RuntimeError("resolver failed")))
    assert service._recipient_name_for("demo@monetra.test") == "Rushabh Dharamshi"
    assert service._with_standard_signoff("") == "Kind Regards,\nMonetra Organisation"
    assert EmailService._normalize_allowed_recipients(["A@EXAMPLE.COM", "", " b@example.com "]) == {"a@example.com", "b@example.com"}
    assert EmailService._normalize_domain_list(["@monetra.test", "example.test"]) == {"monetra.test", "example.test"}
    assert service._is_mock_domain_recipient("not-an-email") is False

    unconfigured_real = EmailService(
        "",
        0,
        "",
        "",
        True,
        "",
        delivery_mode="hybrid",
        allowed_recipients="real@example.com",
        mock_domains="monetra.test",
    )
    with pytest.raises(ServiceUnavailableError, match="Email delivery is not configured"):
        unconfigured_real.send_email("Subject", "Body", recipient="real@example.com")


def test_email_service_retries_and_reports_smtp_failure(monkeypatch):
    class RaisingSMTP:
        attempts = 0

        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            RaisingSMTP.attempts += 1
            raise smtplib.SMTPException("smtp down")

    monkeypatch.setattr("budget_tracker_api.services.email_service.smtplib.SMTP", RaisingSMTP)
    monkeypatch.setattr("budget_tracker_api.services.email_service.time.sleep", lambda seconds: None)

    service = EmailService(
        "smtp.example.com",
        587,
        "sender@example.com",
        "secret",
        True,
        "real@example.com",
        allowed_recipients="real@example.com",
    )

    with pytest.raises(ServiceUnavailableError, match="smtp down"):
        service.send_email("Subject", "Body")
    assert RaisingSMTP.attempts == 2


def test_email_message_body_and_attachment_fallbacks():
    multipart = EmailMessage()
    multipart["Subject"] = "HTML"
    multipart.set_content("<p>HTML</p>", subtype="html")
    multipart.make_mixed()
    assert EmailService._plain_body(multipart) == ""

    no_filename = EmailMessage()
    no_filename.set_content("Body")
    no_filename.add_attachment(b"abc", maintype="application", subtype="octet-stream")
    for part in no_filename.iter_attachments():
        part.replace_header("Content-Disposition", "attachment")
    assert EmailService._attachment_name(no_filename) is None
