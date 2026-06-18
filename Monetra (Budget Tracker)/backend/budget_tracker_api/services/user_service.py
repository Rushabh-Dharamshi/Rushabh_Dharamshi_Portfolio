import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.repositories.user_repository import UserRepository


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        email_service=None,
        expose_reset_tokens: bool = False,
        password_fingerprint_secret: str = "monetra-local",
    ):
        self._repository = repository
        self._email_service = email_service
        self._expose_reset_tokens = expose_reset_tokens
        self._password_fingerprint_secret = password_fingerprint_secret or "monetra-local"

    def register(self, payload: dict) -> dict:
        username = self._validate_username(payload.get("username"))
        email = self._validate_email(payload.get("email"))
        password = self._validate_password(payload.get("password"))

        if self._repository.get_user_by_username(username) or self._username_exists_case_insensitive(username):
            raise ValidationError("That username is already registered.")
        if self._repository.get_user_by_email(email):
            raise ValidationError("That email is already registered.")
        self._validate_password_policy(password, username=username, email=email)

        user = self._repository.create_user(
            username,
            email,
            generate_password_hash(password),
            self._password_fingerprint(password),
        )
        return self._public_user(user)

    def authenticate(self, username: str, password: str) -> dict | None:
        user = self._repository.get_user_by_username_or_email(str(username or ""))
        if user is None or not check_password_hash(user["password_hash"], str(password or "")):
            return None
        return self._public_user(user)

    def get_user(self, user_id: int) -> dict | None:
        user = self._repository.get_user_by_id(user_id)
        return self._public_user(user) if user is not None else None

    def list_users(self) -> list[dict]:
        return [
            self._public_user(user)
            for user in self._repository.list_users()
            if str(user.get("email") or "").strip()
        ]

    def count_users(self) -> int:
        return self._repository.count_users()

    def delete_user(self, user_id: int) -> dict:
        user = self._repository.get_user_by_id(user_id)
        if user is None:
            raise ValidationError("user account was not found.")
        deleted = self._repository.delete_user(user_id)
        if not deleted:
            raise ValidationError("user account was not found.")
        return {
            "message": "User account and all linked finance data were permanently deleted.",
            "registered_user_count": self.count_users(),
        }

    def request_password_reset(self, payload: dict) -> dict:
        identifier = str(payload.get("username") or payload.get("email") or "").strip()
        if not identifier:
            raise ValidationError("username or email is required.")

        user = self._repository.get_user_by_username_or_email(identifier)
        token_for_response = None
        if user is not None:
            token = secrets.token_urlsafe(24)
            expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat(timespec="seconds").replace("+00:00", "Z")
            self._repository.create_reset_token(user["id"], token, expires_at)
            if self._email_service is not None and self._email_service.is_configured():
                self._email_service.send_email(
                    subject="Monetra password reset code",
                    body=(
                        f"Your Monetra password reset code is:\n\n{token}\n\n"
                        "This code expires in 1 hour. If you did not request it, you can ignore this email."
                    ),
                    recipient=user["email"],
                )
            elif self._expose_reset_tokens:
                token_for_response = token

        response = {
            "message": "If that account exists, a password reset code has been sent.",
        }
        if token_for_response:
            response["reset_token"] = token_for_response
        return response

    def reset_password(self, payload: dict) -> dict:
        token = str(payload.get("token") or "").strip()
        password = self._validate_password(payload.get("password"))
        if not token:
            raise ValidationError("reset code is required.")

        token_record = self._repository.get_reset_token(token)
        if token_record is None or token_record.get("used_at"):
            raise ValidationError("The reset code is invalid or has already been used.")
        expires_at = datetime.fromisoformat(str(token_record["expires_at"]).replace("Z", "+00:00"))
        if expires_at < datetime.now(UTC):
            raise ValidationError("The reset code has expired.")

        user = self._repository.get_user_by_id(int(token_record["user_id"]))
        if user is None:
            raise ValidationError("The reset code is invalid or has already been used.")
        self._validate_password_policy(password, username=user["username"], email=user["email"])

        self._repository.update_password_hash(
            token_record["user_id"],
            generate_password_hash(password),
            self._password_fingerprint(password),
        )
        self._repository.mark_reset_token_used(token_record["id"])
        return {"message": "Password updated successfully. You can now sign in."}

    @staticmethod
    def _validate_username(value) -> str:
        username = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", username):
            raise ValidationError("username must be 3-80 characters using letters, numbers, dot, dash, or underscore.")
        return username

    @staticmethod
    def _validate_email(value) -> str:
        email = str(value or "").strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValidationError("email must be valid.")
        return email

    @staticmethod
    def _validate_password(value) -> str:
        password = str(value or "")
        if len(password) < 8:
            raise ValidationError("password must be at least 8 characters.")
        return password

    def _validate_password_policy(
        self,
        password: str,
        *,
        username: str,
        email: str,
    ) -> None:
        normalized_password = password.strip().lower()
        if normalized_password in {str(username or "").strip().lower(), str(email or "").strip().lower()}:
            raise ValidationError("password must be different from the username and email.")

        for user in self._repository.list_users():
            fingerprint = user.get("password_fingerprint")
            if fingerprint and hmac.compare_digest(str(fingerprint), self._password_fingerprint(password)):
                raise ValidationError("password is already used by an account.")
            if check_password_hash(user["password_hash"], password):
                raise ValidationError("password is already used by an account.")

    def _username_exists_case_insensitive(self, username: str) -> bool:
        normalized_username = username.strip().lower()
        return any(str(user.get("username") or "").strip().lower() == normalized_username for user in self._repository.list_users())

    def _password_fingerprint(self, password: str) -> str:
        normalized_password = str(password or "").strip().lower()
        return hmac.new(
            self._password_fingerprint_secret.encode("utf-8"),
            normalized_password.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _public_user(user: dict) -> dict:
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        }
