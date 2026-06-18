import smtplib
import ssl
import time
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
import re

from budget_tracker_api.errors import ServiceUnavailableError


class EmailService:
    _STANDARD_SIGNOFF = "Kind Regards,\nMonetra Organisation"
    _RECIPIENT_PLACEHOLDERS = (
        "[Recipient's Name]",
        "[Recipient’s Name]",
        "[Recipient Name]",
        "[Recipient]",
        "[Name]",
    )

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_use_tls: bool,
        default_recipient: str,
        recipient_name: str = "Rushabh Dharamshi",
        delivery_mode: str = "smtp",
        smtp_require_auth: bool = True,
        allowed_recipients: str | list[str] | tuple[str, ...] | set[str] = "",
        sender_email: str = "",
        mock_domains: str | list[str] | tuple[str, ...] | set[str] = "",
        mock_sender_email: str = "demo@monetra.test",
        recipient_name_resolver=None,
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._smtp_use_tls = smtp_use_tls
        self._default_recipient = default_recipient
        self._recipient_name = recipient_name.strip() or "Rushabh Dharamshi"
        self._delivery_mode = self._normalize_delivery_mode(delivery_mode)
        self._smtp_require_auth = smtp_require_auth
        self._allowed_recipients = self._normalize_allowed_recipients(allowed_recipients)
        self._sender_email = sender_email.strip()
        self._mock_domains = self._normalize_domain_list(mock_domains)
        self._mock_sender_email = mock_sender_email.strip() or "demo@monetra.test"
        self._recipient_name_resolver = recipient_name_resolver
        self._recorded_messages: list[dict] = []

    @property
    def default_recipient(self) -> str:
        return self._default_recipient

    @property
    def recipient_name(self) -> str:
        return self._recipient_name

    @property
    def delivery_mode(self) -> str:
        return self._delivery_mode

    @property
    def recorded_messages(self) -> list[dict]:
        return list(self._recorded_messages)

    def is_mock_recipient(self, recipient: str) -> bool:
        return self._is_mock_domain_recipient(str(recipient or ""))

    def list_mock_messages(self, recipient: str, limit: int = 20) -> list[dict]:
        recipient_address = str(recipient or "").strip().lower()
        if not self.is_mock_recipient(recipient_address):
            raise ServiceUnavailableError(
                "Demo inbox is only available for configured mock email domains."
            )
        try:
            safe_limit = max(1, min(int(limit), 50))
        except (TypeError, ValueError):
            safe_limit = 20
        messages = [
            message
            for message in self._recorded_messages
            if str(message.get("recipient") or "").strip().lower() == recipient_address
        ]
        return list(reversed(messages[-safe_limit:]))

    def set_recipient_name_resolver(self, resolver) -> None:
        self._recipient_name_resolver = resolver

    def _recipient_name_for(self, recipient: str | None) -> str:
        recipient_address = str(recipient or "").strip().lower()
        if self._recipient_name_resolver is not None and recipient_address:
            try:
                resolved = self._recipient_name_resolver(recipient_address)
            except Exception:
                resolved = None
            if isinstance(resolved, dict):
                resolved_name = (
                    resolved.get("display_name")
                    or resolved.get("name")
                    or resolved.get("username")
                )
            else:
                resolved_name = resolved
            resolved_name = str(resolved_name or "").strip()
            if resolved_name:
                return resolved_name
        return self._recipient_name

    def _personalize_body(self, body: str, recipient: str | None = None) -> str:
        recipient_name = self._recipient_name_for(recipient)
        personalized = body or ""
        for placeholder in self._RECIPIENT_PLACEHOLDERS:
            personalized = personalized.replace(placeholder, recipient_name)

        personalized = re.sub(
            r"(?im)^Dear\s*,\s*$",
            f"Dear {recipient_name},",
            personalized,
        )
        personalized = re.sub(
            r"(?im)^Dear\s+User,\s*",
            f"Dear {recipient_name},\n\n",
            personalized,
            count=1,
        )
        personalized = self._collapse_duplicate_salutation(personalized)
        return self._with_standard_signoff(personalized)

    @staticmethod
    def _collapse_duplicate_salutation(body: str) -> str:
        return re.sub(
            r"(?is)^\s*(Dear\s+[^,\n\r]{1,120},)\s*(?:\r?\n\s*)+Dear\s+[^,\n\r]{1,120},\s*",
            r"\1\n\n",
            str(body or "").strip(),
            count=1,
        )

    @classmethod
    def _with_standard_signoff(cls, body: str) -> str:
        cleaned = str(body or "").strip()
        cleaned = re.sub(
            r"(?is)\n*\s*(best regards|kind regards|regards),?\s*\n+.*$",
            "",
            cleaned,
        ).strip()
        cleaned = re.sub(
            r"(?is)\s*(best regards|kind regards|regards),?\s*(?:\n|\r|\s)*(?:monetra organisation|rushabh dharamshi|the finance operations team|the finance team)?\s*$",
            "",
            cleaned,
        ).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        if not cleaned:
            return cls._STANDARD_SIGNOFF
        return f"{cleaned}\n\n{cls._STANDARD_SIGNOFF}"

    def is_configured(self) -> bool:
        if self._delivery_mode == "dry_run":
            return True
        if self._delivery_mode == "hybrid" and self._mock_domains:
            return True
        return bool(
            self._smtp_host
            and self._smtp_port
            and self._smtp_username
            and (not self._smtp_require_auth or self._smtp_password)
        )

    def send_email(
        self,
        subject: str,
        body: str,
        recipient: str | None = None,
    ) -> dict:
        recipient_address = self._resolve_recipient(recipient)
        delivery_route = self._delivery_route(recipient_address)
        self._ensure_can_send(delivery_route)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender(delivery_route)
        message["To"] = recipient_address
        message.set_content(self._personalize_body(body, recipient_address))

        self._deliver(message, delivery_route)

        result = {
            "recipient": recipient_address,
            "subject": subject,
        }
        if delivery_route == "dry_run":
            result["status"] = "simulated"
        return result

    def send_report_email(
        self,
        subject: str,
        body: str,
        attachment_path: Path,
        recipient: str | None = None,
    ) -> dict:
        recipient_address = self._resolve_recipient(recipient)
        delivery_route = self._delivery_route(recipient_address)
        self._ensure_can_send(delivery_route)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender(delivery_route)
        message["To"] = recipient_address
        message.set_content(self._personalize_body(body, recipient_address))
        message["X-Monetra-Attachment-Url"] = "/api/reports/monthly"

        attachment_bytes = attachment_path.read_bytes()
        message.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="pdf",
            filename=attachment_path.name,
        )

        self._deliver(message, delivery_route)

        result = {
            "recipient": recipient_address,
            "subject": subject,
            "attachment_name": attachment_path.name,
        }
        if delivery_route == "dry_run":
            result["status"] = "simulated"
        return result

    def _resolve_recipient(self, recipient: str | None) -> str:
        recipient_address = str(recipient or self._default_recipient or "").strip()
        if not recipient_address:
            raise ServiceUnavailableError(
                "Email delivery is not configured. Set REPORT_EMAIL_TO or pass a recipient email address."
            )
        if not self._is_allowed_recipient(recipient_address):
            raise ServiceUnavailableError(
                "Email recipient is not allowed for real SMTP delivery. Add the address to EMAIL_ALLOWED_RECIPIENTS before sending."
            )
        return recipient_address

    def _ensure_can_send(self, delivery_route: str) -> None:
        if delivery_route == "dry_run":
            return
        if not self._smtp_is_configured():
            raise ServiceUnavailableError(
                "Email delivery is not configured. Set EMAIL_MODE=mock or configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD."
            )

    def _sender(self, delivery_route: str) -> str:
        if delivery_route == "dry_run" and self._delivery_mode == "hybrid":
            return self._mock_sender_email
        return self._sender_email or self._smtp_username or "noreply@monetra.local"

    def _deliver(self, message: EmailMessage, delivery_route: str) -> None:
        if delivery_route == "dry_run":
            self._recorded_messages.append(
                {
                    "id": len(self._recorded_messages) + 1,
                    "recipient": str(message["To"]),
                    "subject": str(message["Subject"]),
                    "sender": str(message["From"]),
                    "body": self._plain_body(message),
                    "status": "simulated",
                    "has_attachment": message.is_multipart(),
                    "attachment_name": self._attachment_name(message),
                    "attachment_url": self._attachment_url(message),
                    "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                }
            )
            return

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                self._deliver_once(message)
                return
            except (OSError, smtplib.SMTPException, ssl.SSLError) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                break

        raise ServiceUnavailableError(
            f"Email delivery failed after retrying the SMTP connection: {last_error}"
        )

    def _deliver_once(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30) as smtp:
            if self._smtp_use_tls:
                smtp.starttls()
            if self._smtp_require_auth or self._smtp_password:
                smtp.login(self._smtp_username, self._smtp_password)
            smtp.send_message(message)

    @staticmethod
    def _normalize_delivery_mode(delivery_mode: str) -> str:
        normalized = (delivery_mode or "smtp").strip().lower()
        if normalized == "real":
            return "smtp"
        if normalized in {"mock", "dry-run"}:
            return "dry_run"
        return normalized

    @staticmethod
    def _normalize_allowed_recipients(
        allowed_recipients: str | list[str] | tuple[str, ...] | set[str],
    ) -> set[str]:
        if isinstance(allowed_recipients, str):
            raw_items = allowed_recipients.split(",")
        else:
            raw_items = list(allowed_recipients)
        return {str(item).strip().lower() for item in raw_items if str(item).strip()}

    @staticmethod
    def _normalize_domain_list(
        domains: str | list[str] | tuple[str, ...] | set[str],
    ) -> set[str]:
        if isinstance(domains, str):
            raw_items = domains.split(",")
        else:
            raw_items = list(domains)
        return {
            str(item).strip().lower().removeprefix("@")
            for item in raw_items
            if str(item).strip()
        }

    def _is_allowed_recipient(self, recipient: str) -> bool:
        if self._delivery_mode == "dry_run":
            return True
        if self._delivery_mode == "hybrid":
            return self._is_real_allowed_recipient(recipient) or self._is_mock_domain_recipient(recipient)
        return self._is_real_allowed_recipient(recipient)

    def _is_real_allowed_recipient(self, recipient: str) -> bool:
        if not self._allowed_recipients:
            return False
        return recipient.strip().lower() in self._allowed_recipients

    def _is_mock_domain_recipient(self, recipient: str) -> bool:
        normalized = recipient.strip().lower()
        if "@" not in normalized:
            return False
        recipient_domain = normalized.rsplit("@", 1)[-1]
        return bool(recipient_domain and recipient_domain in self._mock_domains)

    def _delivery_route(self, recipient: str) -> str:
        if self._delivery_mode == "dry_run":
            return "dry_run"
        if self._delivery_mode == "hybrid":
            if self._is_real_allowed_recipient(recipient):
                return "smtp"
            if self._is_mock_domain_recipient(recipient):
                return "dry_run"
        return "smtp"

    def _smtp_is_configured(self) -> bool:
        return bool(
            self._smtp_host
            and self._smtp_port
            and self._smtp_username
            and (not self._smtp_require_auth or self._smtp_password)
        )

    @staticmethod
    def _plain_body(message: EmailMessage) -> str:
        if message.is_multipart():
            body = message.get_body(preferencelist=("plain",))
            if body is not None:
                return body.get_content()
            return ""
        return message.get_content()

    @staticmethod
    def _attachment_name(message: EmailMessage) -> str | None:
        if not message.is_multipart():
            return None
        for part in message.iter_attachments():
            filename = part.get_filename()
            if filename:
                return filename
        return None

    @staticmethod
    def _attachment_url(message: EmailMessage) -> str | None:
        value = str(message.get("X-Monetra-Attachment-Url") or "").strip()
        return value or None
