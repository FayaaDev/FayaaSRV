"""Atomicity tests for cli._run_service_pull and _sync_services_to_state_selection.

A failed deploy must leave on-disk state matching the pre-call baseline and
remove any services that were freshly added during the same batch. Without
these guarantees, `rakkib add` silently drifts between state.yaml,
state.deployed.*, and the actual docker / data dirs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rakkib.cli import _run_service_pull, _sync_services_to_state_selection
from rakkib.state import State


def _minimal_registry(*ids: str) -> dict:
    return {
        "services": [
            {
                "id": sid,
                "title": sid,
                "category": "test",
                "state_bucket": "selected_services",
                "buckets_allowed": ["selected_services"],
            }
            for sid in ids
        ]
    }


class TestRunServicePullRollback:
    def _baseline(self, tmp_path: Path) -> tuple[State, Path]:
        state_file = tmp_path / ".fss-state.yaml"
        state = State(
            {"foundation_services": [], "selected_services": []},
            path=state_file,
        )
        state.save(state_file)
        return state, state_file

    @patch("rakkib.cli._run_pre_service_steps", return_value=True)
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.services_step._load_registry")
    def test_run_failure_rolls_back_state_file(
        self,
        mock_load_reg,
        mock_run,
        mock_pre,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("alpha")
        mock_run.side_effect = RuntimeError("docker daemon refused")

        state, state_file = self._baseline(tmp_path)

        ok = _run_service_pull(state, state_file, "alpha")

        assert ok is False
        # State must not record alpha as selected/deployed after rollback.
        reloaded = State.load(state_file)
        assert "alpha" not in (reloaded.get("selected_services") or [])
        assert "alpha" not in (reloaded.get("foundation_services") or [])
        # In-memory state must also be rolled back.
        assert "alpha" not in (state.get("selected_services") or [])

    @patch("rakkib.cli._run_pre_service_steps", return_value=True)
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.services_step._load_registry")
    def test_success_persists_deployed_bucket(
        self,
        mock_load_reg,
        mock_run,
        mock_pre,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("alpha")
        mock_run.return_value = None  # success

        state, state_file = self._baseline(tmp_path)

        ok = _run_service_pull(state, state_file, "alpha")

        assert ok is True
        reloaded = State.load(state_file)
        assert "alpha" in (reloaded.get("selected_services") or [])


class TestSyncRollback:
    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_failure_mid_batch_cleans_up_and_restores_state(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        registry = _minimal_registry("alpha", "beta", "gamma", "delta", "epsilon")
        mock_load_reg.return_value = registry

        def run_side_effect(state, svc_id):
            if svc_id == "gamma":
                raise RuntimeError("simulated failure")

        mock_run.side_effect = run_side_effect

        state_file = tmp_path / ".fss-state.yaml"
        state = State(
            {
                "foundation_services": [],
                "selected_services": ["alpha", "beta", "gamma", "delta", "epsilon"],
            },
            path=state_file,
        )
        state.save(state_file)

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False, "sync should fail when run_single_service raises"

        # Cleanup: alpha + beta fully ran; gamma partially. All three must be removed.
        removed_ids = [call.args[1] for call in mock_remove.call_args_list]
        assert "alpha" in removed_ids
        assert "beta" in removed_ids
        assert "gamma" in removed_ids
        assert "delta" not in removed_ids, "delta never ran; no cleanup needed"
        assert "epsilon" not in removed_ids

        # State must be back to the pre-call baseline: deployed.* untouched.
        reloaded = State.load(state_file)
        assert reloaded.get("deployed.foundation_services") in (None, [])
        assert reloaded.get("deployed.selected_services") in (None, [])

    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_success_persists_deployed_bucket(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("alpha", "beta")
        mock_run.return_value = None

        state_file = tmp_path / ".fss-state.yaml"
        state = State(
            {
                "foundation_services": [],
                "selected_services": ["alpha", "beta"],
            },
            path=state_file,
        )
        state.save(state_file)

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is True
        mock_remove.assert_not_called()
        reloaded = State.load(state_file)
        assert sorted(reloaded.get("deployed.selected_services") or []) == ["alpha", "beta"]
