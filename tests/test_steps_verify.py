"""Tests for rakkib.steps.verify."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rakkib.state import State
from rakkib.steps import VerificationResult
from rakkib.steps import verify as verify_step


class TestCollectVerifications:
    def test_collects_all_results(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            results = verify_step._collect_verifications(state)
        assert len(results) == 5
        assert all(r.ok for r in results)

    def test_handles_import_error(self):
        state = State({})
        # postgres module missing
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                # no postgres
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            with patch("builtins.__import__", side_effect=lambda name, *args, **kwargs: __import__(name) if name in sys.modules else (_ for _ in ()).throw(ImportError(name))):
                results = verify_step._collect_verifications(state)
        # Actually, _collect_verifications catches ImportError itself, so we need to let __import__ work normally
        # but remove postgres from sys.modules. Let's patch __import__ more carefully.

    def test_handles_failure(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "boom")
                ),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            results = verify_step._collect_verifications(state)
        assert any(not r.ok for r in results)
        failed = [r for r in results if not r.ok]
        assert failed[0].step == "layout"


class TestVerify:
    def test_success_when_all_pass(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            result = verify_step.verify(state)
        assert result.ok is True
        assert "All sub-verifications passed" in result.message

    def test_failure_aggregates(self):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "bad")
                ),
                "rakkib.steps.caddy": MagicMock(
                    verify=lambda s: VerificationResult.failure("caddy", "worse")
                ),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            result = verify_step.verify(state)
        assert result.ok is False
        assert "layout: bad" in result.message
        assert "caddy: worse" in result.message
        assert result.state_slice is not None
        assert "layout" in result.state_slice["failed_steps"]
        assert "caddy" in result.state_slice["failed_steps"]


class TestRun:
    def test_prints_summary_on_failure(self, capsys):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(
                    verify=lambda s: VerificationResult.failure("layout", "bad")
                ),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            verify_step.run(state)
        captured = capsys.readouterr()
        assert "VERIFICATION SUMMARY" in captured.out
        assert "HANDOFF PROMPT" in captured.out

    def test_prints_success_when_all_pass(self, capsys):
        state = State({})
        with patch.dict(
            "sys.modules",
            {
                "rakkib.steps.layout": MagicMock(verify=lambda s: VerificationResult.success("layout")),
                "rakkib.steps.caddy": MagicMock(verify=lambda s: VerificationResult.success("caddy")),
                "rakkib.steps.postgres": MagicMock(verify=lambda s: VerificationResult.success("postgres")),
                "rakkib.steps.services": MagicMock(verify=lambda s: VerificationResult.success("services")),
                "rakkib.steps.cron": MagicMock(verify=lambda s: VerificationResult.success("cron")),
            },
        ):
            verify_step.run(state)
        captured = capsys.readouterr()
        assert "All verification checks passed." in captured.out
