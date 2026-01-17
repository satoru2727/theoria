from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping

CONFIG_DIR = Path.home() / ".config" / "theoria"
AUTH_FILE = CONFIG_DIR / "auth.json"


class AuthType(str, Enum):
    API = "api"
    OAUTH = "oauth"


class ApiAuth(BaseModel):
    type: AuthType = AuthType.API
    key: str


class OAuthAuth(BaseModel):
    type: AuthType = AuthType.OAUTH
    access: str
    refresh: str
    expires: int
    account_id: str | None = None


AuthInfo = ApiAuth | OAuthAuth


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_all() -> dict[str, dict[str, object]]:
    if not AUTH_FILE.exists():
        return {}
    with AUTH_FILE.open() as f:
        return dict(json.load(f))


def save_all(data: Mapping[str, object]) -> None:
    ensure_config_dir()
    with AUTH_FILE.open("w") as f:
        json.dump(data, f, indent=2)
    AUTH_FILE.chmod(0o600)


def get(provider_id: str) -> AuthInfo | None:
    data = load_all()
    if provider_id not in data:
        return None
    info = data[provider_id]
    if not isinstance(info, dict):
        return None
    auth_type = info.get("type")
    if auth_type == AuthType.API.value:
        return ApiAuth.model_validate(info)
    if auth_type == AuthType.OAUTH.value:
        return OAuthAuth.model_validate(info)
    return None


def set_api_key(provider_id: str, key: str) -> None:
    data = load_all()
    data[provider_id] = {"type": AuthType.API.value, "key": key}
    save_all(data)


def set_oauth(
    provider_id: str,
    access: str,
    refresh: str,
    expires: int,
    account_id: str | None = None,
) -> None:
    data = load_all()
    data[provider_id] = {
        "type": AuthType.OAUTH.value,
        "access": access,
        "refresh": refresh,
        "expires": expires,
        "account_id": account_id,
    }
    save_all(data)


def remove(provider_id: str) -> bool:
    data = load_all()
    if provider_id in data:
        del data[provider_id]
        save_all(data)
        return True
    return False


def list_providers() -> list[str]:
    return list(load_all().keys())


def get_api_key_from_env(provider_id: str) -> str | None:
    env_map: dict[str, list[str]] = {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "google": ["GOOGLE_GENERATIVE_AI_API_KEY", "GOOGLE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "mistral": ["MISTRAL_API_KEY"],
        "cohere": ["COHERE_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
    }
    env_vars = env_map.get(provider_id, [f"{provider_id.upper()}_API_KEY"])
    for var in env_vars:
        if value := os.environ.get(var):
            return value
    return None


def resolve_api_key(provider_id: str) -> str | None:
    if env_key := get_api_key_from_env(provider_id):
        return env_key
    auth = get(provider_id)
    if isinstance(auth, ApiAuth):
        return auth.key
    return None
