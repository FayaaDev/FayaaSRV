"""Rakkib setup steps.

Each step module exports ``run()`` and ``verify()``:
- ``run()`` executes the step idempotently.
- ``verify()`` returns ok or a structured failure (step, log path, state slice).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class VerificationResult:
    """Result of a step verification check."""

    ok: bool
    step: str
    log_path: Path | None = None
    state_slice: dict[str, Any] | None = None
    message: str = ""

    @classmethod
    def success(cls, step: str, message: str = "") -> "VerificationResult":
        return cls(ok=True, step=step, message=message)

    @classmethod
    def failure(
        cls,
        step: str,
        message: str,
        log_path: Path | None = None,
        state_slice: dict[str, Any] | None = None,
    ) -> "VerificationResult":
        return cls(
            ok=False,
            step=step,
            message=message,
            log_path=log_path,
            state_slice=state_slice,
        )
