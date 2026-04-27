"""Step 7 — Verify.

Run the final smoke tests for the deployed server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rakkib.state import State
from rakkib.steps import VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_verifications(state: State) -> list[VerificationResult]:
    """Import and run verify() from all other step modules."""
    results: list[VerificationResult] = []

    step_modules = [
        ("layout", "rakkib.steps.layout"),
        ("caddy", "rakkib.steps.caddy"),
        ("cloudflare", "rakkib.steps.cloudflare"),
        ("postgres", "rakkib.steps.postgres"),
        ("services", "rakkib.steps.services"),
        ("cron", "rakkib.steps.cron"),
    ]

    for step_name, module_path in step_modules:
        try:
            module = __import__(module_path, fromlist=["verify"])
            verify_fn = getattr(module, "verify", None)
            if verify_fn is None:
                results.append(
                    VerificationResult.failure(
                        step_name,
                        f"Module {module_path} does not export verify()",
                    )
                )
                continue
            result = verify_fn(state)
            results.append(result)
        except ImportError:
            # Step module not yet implemented (e.g. postgres in early waves)
            results.append(
                VerificationResult.failure(
                    step_name,
                    f"Step module {module_path} not found",
                )
            )
        except Exception as exc:
            results.append(
                VerificationResult.failure(
                    step_name,
                    f"verify() raised {type(exc).__name__}: {exc}",
                )
            )

    return results


def _print_summary(results: list[VerificationResult]) -> None:
    """Print a plain-text summary of verification results."""
    print("")
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.ok else "FAIL"
        icon = "✓" if r.ok else "✗"
        print(f"{icon}  [{status}]  Step {r.step:<12}  {r.message}")
        if not r.ok and r.log_path:
            print(f"      Log: {r.log_path}")

    failures = [r for r in results if not r.ok]
    print("-" * 60)
    print(f"Total: {len(results)} checks, {len(failures)} failures")
    print("")

    if failures:
        print("ACTION REQUIRED")
        print("-" * 60)
        print(
            "Some verification checks failed. Review the failures above, "
            "check the relevant logs, and re-run `rakkib pull` to retry."
        )
        print("")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(state: State) -> None:
    results = _collect_verifications(state)
    failures = [r for r in results if not r.ok]

    if failures:
        _print_summary(results)
    else:
        print("All verification checks passed.")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify(state: State) -> VerificationResult:
    results = _collect_verifications(state)
    failures = [r for r in results if not r.ok]

    if not failures:
        return VerificationResult.success("verify", "All sub-verifications passed")

    messages = [f"{r.step}: {r.message}" for r in failures]
    return VerificationResult.failure(
        "verify",
        f"{len(failures)} verification(s) failed: " + "; ".join(messages),
        state_slice={"failed_steps": [r.step for r in failures]},
    )
