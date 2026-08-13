"""Demo user directory.

Roles are always resolved server-side from `user_id` — a client request
never gets to assert its own role, which is the whole point of the
permission layer downstream.
"""
from __future__ import annotations

from app.core.models import User

_DEMO_USERS: dict[str, User] = {
    "u_viewer": User(id="u_viewer", role="viewer"),
    "u_analyst": User(id="u_analyst", role="analyst"),
    "u_operator": User(id="u_operator", role="operator"),
    "u_admin": User(id="u_admin", role="admin"),
}


def get_user(user_id: str) -> User | None:
    return _DEMO_USERS.get(user_id)


def list_users() -> list[User]:
    return list(_DEMO_USERS.values())
