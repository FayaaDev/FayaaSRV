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


def _registry_with_deps(*services: tuple[str, list[str]]) -> dict:
    registry = _minimal_registry(*(sid for sid, _deps in services))
    for svc, (_sid, deps) in zip(registry["services"], services, strict=True):
        if deps:
            svc["depends_on"] = deps
    return registry


def _registry_with_postgres(*postgres_ids: str) -> dict:
    registry = _minimal_registry(*postgres_ids)
    for svc in registry["services"]:
        svc["postgres"] = {
            "role": svc["id"],
            "db": f"{svc['id']}_db",
            "password_key": f"{svc['id'].upper()}_DB_PASS",
        }
    return registry


def _sync_state(
    tmp_path: Path,
    *,
    selected: list[str],
    deployed: list[str],
) -> tuple[State, Path]:
    state_file = tmp_path / ".fss-state.yaml"
    state = State(
        {
            "foundation_services": [],
            "selected_services": selected,
            "deployed": {
                "exists": bool(deployed),
                "foundation_services": [],
                "selected_services": deployed,
            },
        },
        path=state_file,
    )
    state.save(state_file)
    return state, state_file


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
    def test_add_failure_does_not_remove_existing_services(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("old", "new")
        mock_run.side_effect = RuntimeError("new failed")
        state, state_file = _sync_state(
            tmp_path,
            selected=["old", "new"],
            deployed=["old"],
        )

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False
        assert "old" not in [call.args[1] for call in mock_remove.call_args_list]

    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_mixed_add_remove_runs_added_before_removing_old_service(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("old", "new")
        events: list[str] = []
        state, state_file = _sync_state(tmp_path, selected=["new"], deployed=["old"])

        with (
            patch(
                "rakkib.cli.services_step.run_single_service",
                side_effect=lambda _state, svc_id: events.append(f"run:{svc_id}"),
            ),
            patch(
                "rakkib.cli.services_step.remove_single_service",
                side_effect=lambda _state, svc_id: events.append(f"remove:{svc_id}"),
            ),
            patch("rakkib.cli.services_step._reload_caddy"),
        ):
            ok = _sync_services_to_state_selection(state, state_file)

        assert ok is True
        assert events == ["run:new", "remove:old"]

    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_removal_failure_cleans_added_service_and_restores_state(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("old", "new")
        state, state_file = _sync_state(tmp_path, selected=["new"], deployed=["old"])
        with patch("rakkib.cli.services_step.remove_single_service") as mock_remove:
            mock_remove.side_effect = [RuntimeError("old remove failed"), None]

            ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False
        assert [call.args[1] for call in mock_remove.call_args_list] == ["old", "new"]
        reloaded = State.load(state_file)
        assert reloaded.get("selected_services") == ["new"]
        assert reloaded.get("deployed.selected_services") == ["old"]

    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_failure_after_removal_attempts_restore_removed_service(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _minimal_registry("old")
        mock_sync_artifacts.side_effect = RuntimeError("artifact sync failed")
        state, state_file = _sync_state(tmp_path, selected=[], deployed=["old"])

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False
        assert [call.args[1] for call in mock_remove.call_args_list] == ["old"]
        assert [call.args[1] for call in mock_run.call_args_list] == ["old"]
        reloaded = State.load(state_file)
        assert reloaded.get("deployed.selected_services") == ["old"]

    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_dependency_removal_order_remains_reverse_dependency_order(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _registry_with_deps(("db", []), ("app", ["db"]))
        state, state_file = _sync_state(tmp_path, selected=[], deployed=["db", "app"])

        with patch("rakkib.cli.services_step._reload_caddy"):
            ok = _sync_services_to_state_selection(state, state_file)

        assert ok is True
        assert [call.args[1] for call in mock_remove.call_args_list] == ["app", "db"]

    @patch("rakkib.cli.services_step._drop_service_postgres_resources")
    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_postgres_failure_drops_only_new_service_resources(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        mock_drop_pg,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _registry_with_postgres("oldpg", "newpg")
        mock_pg_run.side_effect = RuntimeError("postgres sync failed")
        state, state_file = _sync_state(tmp_path, selected=["oldpg", "newpg"], deployed=["oldpg"])

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False
        assert [call.args[0]["id"] for call in mock_drop_pg.call_args_list] == ["newpg"]
        mock_remove.assert_not_called()
        reloaded = State.load(state_file)
        assert reloaded.get("deployed.selected_services") == ["oldpg"]

    @patch("rakkib.cli.services_step._drop_service_postgres_resources")
    @patch("rakkib.cli.services_step.sync_shared_artifacts")
    @patch("rakkib.cli.services_step._generate_missing_secrets")
    @patch("rakkib.cli.services_step.remove_single_service")
    @patch("rakkib.cli.services_step.run_single_service")
    @patch("rakkib.cli.postgres_step.run")
    @patch("rakkib.cli.services_step._load_registry")
    def test_postgres_cleanup_skips_resources_removed_by_service_cleanup(
        self,
        mock_load_reg,
        mock_pg_run,
        mock_run,
        mock_remove,
        mock_secrets,
        mock_sync_artifacts,
        mock_drop_pg,
        tmp_path: Path,
    ):
        mock_load_reg.return_value = _registry_with_postgres("oldpg", "newpg")
        mock_run.side_effect = RuntimeError("service failed after postgres sync")
        state, state_file = _sync_state(tmp_path, selected=["oldpg", "newpg"], deployed=["oldpg"])

        ok = _sync_services_to_state_selection(state, state_file)

        assert ok is False
        assert [call.args[1] for call in mock_remove.call_args_list] == ["newpg"]
        mock_drop_pg.assert_not_called()

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
