"""Shared config models for the Rakkib web runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebRuntimeConfig:
    """Configuration for the local ASGI web server."""

    host: str
    port: int
    token_auth_enabled: bool
    startup_token: str | None
