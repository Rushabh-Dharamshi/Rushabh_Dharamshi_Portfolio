from werkzeug.security import check_password_hash

import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.user_service import UserService


class FakeUserRepository:
    def __init__(self):
        self.users = []
        self.reset_tokens = []
        self.next_user_id = 1
        self.next_token_id = 1

    def create_user(self, username, email, password_hash, password_fingerprint=None):
        user = {
            "id": self.next_user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "password_fingerprint": password_fingerprint,
            "created_at": "2026-06-05T12:00:00Z",
        }
        self.next_user_id += 1
        self.users.append(user)
        return user

    def get_user_by_id(self, user_id):
        return next((user for user in self.users if user["id"] == user_id), None)

    def get_user_by_username(self, username):
        return next((user for user in self.users if user["username"] == username), None)

    def get_user_by_email(self, email):
        return next((user for user in self.users if user["email"] == email), None)

    def get_user_by_username_or_email(self, identifier):
        if "@" in str(identifier):
            return self.get_user_by_email(str(identifier).lower())
        return self.get_user_by_username(str(identifier))

    def list_users(self):
        return list(self.users)

    def count_users(self):
        return len(self.users)

    def update_password_hash(self, user_id, password_hash, password_fingerprint=None):
        user = self.get_user_by_id(user_id)
        user["password_hash"] = password_hash
        user["password_fingerprint"] = password_fingerprint

    def delete_user(self, user_id):
        before = len(self.users)
        self.users = [user for user in self.users if user["id"] != user_id]
        self.reset_tokens = [token for token in self.reset_tokens if token["user_id"] != user_id]
        return len(self.users) < before

    def create_reset_token(self, user_id, token, expires_at):
        self.reset_tokens.append(
            {
                "id": self.next_token_id,
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at,
                "used_at": None,
            }
        )
        self.next_token_id += 1

    def get_reset_token(self, token):
        return next((record for record in self.reset_tokens if record["token"] == token), None)

    def mark_reset_token_used(self, token_id):
        token = next(record for record in self.reset_tokens if record["id"] == token_id)
        token["used_at"] = "2026-06-05T12:30:00Z"


def test_register_rejects_password_matching_username_or_email():
    service = UserService(FakeUserRepository())

    with pytest.raises(ValidationError, match="different from the username and email"):
        service.register({"username": "Rushabh123", "email": "rushabh@example.com", "password": "Rushabh123"})

    with pytest.raises(ValidationError, match="different from the username and email"):
        service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "rushabh@example.com"})


def test_register_rejects_password_used_by_another_account():
    service = UserService(FakeUserRepository())
    service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "StrongPass123"})

    with pytest.raises(ValidationError, match="already used by an account"):
        service.register({"username": "SecondUser", "email": "second@example.com", "password": "StrongPass123"})

    with pytest.raises(ValidationError, match="already used by an account"):
        service.register({"username": "ThirdUser", "email": "third@example.com", "password": "strongpass123"})


def test_register_rejects_repeated_username_case_insensitively():
    service = UserService(FakeUserRepository())
    service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "StrongPass123"})

    with pytest.raises(ValidationError, match="username is already registered"):
        service.register({"username": "rushabh", "email": "second@example.com", "password": "OtherPass456"})


def test_password_reset_rejects_another_users_password_and_updates_valid_password():
    repository = FakeUserRepository()
    service = UserService(repository, expose_reset_tokens=True)
    first = service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "StrongPass123"})
    second = service.register({"username": "SecondUser", "email": "second@example.com", "password": "OtherPass456"})
    token = service.request_password_reset({"email": second["email"]})["reset_token"]

    with pytest.raises(ValidationError, match="already used by an account"):
        service.reset_password({"token": token, "password": "StrongPass123"})

    service.reset_password({"token": token, "password": "FreshPass789"})

    updated_second = repository.get_user_by_id(second["id"])
    assert check_password_hash(updated_second["password_hash"], "FreshPass789")
    assert not check_password_hash(repository.get_user_by_id(first["id"])["password_hash"], "FreshPass789")


def test_password_reset_rejects_current_password_reuse():
    repository = FakeUserRepository()
    service = UserService(repository, expose_reset_tokens=True)
    user = service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "StrongPass123"})
    token = service.request_password_reset({"email": user["email"]})["reset_token"]

    with pytest.raises(ValidationError, match="already used by an account"):
        service.reset_password({"token": token, "password": "StrongPass123"})


def test_delete_user_removes_account_and_reports_remaining_count():
    repository = FakeUserRepository()
    service = UserService(repository)
    first = service.register({"username": "Rushabh", "email": "rushabh@example.com", "password": "StrongPass123"})
    service.register({"username": "SecondUser", "email": "second@example.com", "password": "OtherPass456"})

    result = service.delete_user(first["id"])

    assert result == {
        "message": "User account and all linked finance data were permanently deleted.",
        "registered_user_count": 1,
    }
    assert repository.get_user_by_id(first["id"]) is None
