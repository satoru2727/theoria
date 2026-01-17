from __future__ import annotations

import base64
import hashlib
import secrets
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_CALLBACK_PORT = 19876
DEFAULT_REDIRECT_URI = f"http://127.0.0.1:{DEFAULT_CALLBACK_PORT}/callback"


@dataclass
class PKCEParams:
    verifier: str
    challenge: str
    state: str


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


def generate_pkce() -> PKCEParams:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    return PKCEParams(verifier=verifier, challenge=challenge, state=state)


def build_authorize_url(
    authorize_endpoint: str,
    client_id: str,
    redirect_uri: str,
    pkce: PKCEParams,
    scope: str = "openid profile email",
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": pkce.state,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
    }
    return f"{authorize_endpoint}?{urlencode(params)}"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    state: str | None = None
    error: str | None = None

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        OAuthCallbackHandler.code = query.get("code", [None])[0]
        OAuthCallbackHandler.state = query.get("state", [None])[0]
        OAuthCallbackHandler.error = query.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if OAuthCallbackHandler.error:
            body = f"<html><body><h1>Error: {OAuthCallbackHandler.error}</h1></body></html>"
        else:
            body = (
                "<html><body><h1>Authorization successful!</h1>"
                "<p>You can close this window.</p></body></html>"
            )

        self.wfile.write(body.encode())


def wait_for_callback(
    port: int = DEFAULT_CALLBACK_PORT,
    timeout: float = 300,
) -> tuple[str | None, str | None, str | None]:
    OAuthCallbackHandler.code = None
    OAuthCallbackHandler.state = None
    OAuthCallbackHandler.error = None

    server = HTTPServer(("127.0.0.1", port), OAuthCallbackHandler)
    server.timeout = timeout
    server.handle_request()

    return (
        OAuthCallbackHandler.code,
        OAuthCallbackHandler.state,
        OAuthCallbackHandler.error,
    )


async def exchange_code_for_tokens(
    token_endpoint: str,
    client_id: str,
    code: str,
    redirect_uri: str,
    verifier: str,
    client_secret: str | None = None,
) -> OAuthTokens:
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with httpx.AsyncClient() as client:
        response = await client.post(token_endpoint, data=data)
        response.raise_for_status()
        result = response.json()

    return OAuthTokens(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", ""),
        expires_in=result.get("expires_in", 3600),
        token_type=result.get("token_type", "Bearer"),
    )


async def refresh_access_token(
    token_endpoint: str,
    client_id: str,
    refresh_token: str,
    client_secret: str | None = None,
) -> OAuthTokens:
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with httpx.AsyncClient() as client:
        response = await client.post(token_endpoint, data=data)
        response.raise_for_status()
        result = response.json()

    return OAuthTokens(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", refresh_token),
        expires_in=result.get("expires_in", 3600),
        token_type=result.get("token_type", "Bearer"),
    )


def start_oauth_flow(
    authorize_url: str,
    open_browser: Callable[[str], bool] = webbrowser.open,
) -> bool:
    return open_browser(authorize_url)
