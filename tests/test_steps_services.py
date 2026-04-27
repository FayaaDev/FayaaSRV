"""Tests for rakkib.steps.services."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from rakkib.state import State
from rakkib.steps import VerificationResult
from rakkib.steps import services as services_step


@pytest.fixture
def fake_repo(tmp_path: Path):
    """Create a minimal repo structure with registry and templates."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Registry
    registry = {
        "services": [
            {"id": "postgres", "depends_on": [], "host_service": False, "default_port": 5432},
            {"id": "nocodb", "depends_on": ["postgres"], "host_service": False, "default_port": 8080},
            {"id": "authentik", "depends_on": ["postgres"], "host_service": False, "default_port": 9000},
            {"id": "homepage", "depends_on": [], "host_service": False, "default_port": 3000},
            {"id": "openclaw", "depends_on": [], "host_service": True, "default_port": 18789},
        ]
    }
    (repo / "registry.yaml").write_text(yaml.dump(registry))

    # Templates
    for svc in ["postgres", "nocodb", "authentik", "homepage"]:
        tmpl_dir = repo / "templates" / "docker" / svc
        tmpl_dir.mkdir(parents=True)
        (tmpl_dir / "docker-compose.yml.tmpl").write_text(f"# {svc} compose\n")
        (tmpl_dir / ".env.example").write_text(f"{svc.upper()}_VAR={{VALUE}}\n")

    # Caddy routes
    caddy_dir = repo / "templates" / "caddy" / "routes"
    caddy_dir.mkdir(parents=True)
    for svc in ["nocodb", "authentik", "homepage"]:
        (caddy_dir / f"{svc}.caddy.tmpl").write_text(f"# {svc} route\n")

    return repo


class TestSelectedServiceDefs:
    def test_dependency_order(self, fake_repo: Path):
        state = State({
            "foundation_services": ["nocodb", "authentik"],
            "selected_services": ["homepage"],
        })
        registry = services_step._load_registry()
        defs = services_step._selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        # homepage and authentik both have in-degree 0 (postgres not selected),
        # so they sort alphabetically: authentik, homepage, nocodb
        assert ids == ["authentik", "homepage", "nocodb"]

    def test_skips_unselected(self, fake_repo: Path):
        state = State({"foundation_services": ["nocodb"]})
        registry = services_step._load_registry()
        defs = services_step._selected_service_defs(state, registry)
        ids = [d["id"] for d in defs]
        assert "authentik" not in ids
        assert "homepage" not in ids


class TestGenerateMissingSecrets:
    def test_generates_postgres_password(self):
        state = State({})
        services_step._generate_missing_secrets(state)
        assert state.get("POSTGRES_PASSWORD") is not None
        assert len(state.get("POSTGRES_PASSWORD")) >= 16

    def test_preserves_existing_secret(self):
        state = State({"POSTGRES_PASSWORD": "keepme"})
        services_step._generate_missing_secrets(state)
        assert state.get("POSTGRES_PASSWORD") == "keepme"

    def test_generates_nocodb_secrets(self):
        state = State({"foundation_services": ["nocodb"]})
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_ADMIN_PASS") is not None
        assert state.get("NOCODB_DB_PASS") is not None

    def test_generates_oidc_when_both_present(self):
        state = State({
            "foundation_services": ["nocodb", "authentik"],
        })
        services_step._generate_missing_secrets(state)
        assert state.get("NOCODB_OIDC_CLIENT_ID") is not None
        assert state.get("NOCODB_OIDC_CLIENT_SECRET") is not None

    def test_generates_n8n_encryption_when_fresh(self):
        state = State({
            "selected_services": ["n8n"],
            "secrets": {"n8n_mode": "fresh"},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("N8N_ENCRYPTION_KEY") is not None

    def test_does_not_generate_n8n_encryption_when_migrate(self):
        state = State({
            "selected_services": ["n8n"],
            "secrets": {"n8n_mode": "migrate"},
        })
        services_step._generate_missing_secrets(state)
        assert state.get("N8N_ENCRYPTION_KEY") is None


class TestRenderEnvExample:
    def test_renders_and_sets_perms(self, tmp_path: Path):
        state = State({"VALUE": "hello"})
        tmpl = tmp_path / "env.tmpl"
        tmpl.write_text("VAR={{VALUE}}")
        dst = tmp_path / ".env"
        services_step._render_env_example(state, tmpl, dst)
        assert dst.exists()
        assert "hello" in dst.read_text()
        assert oct(dst.stat().st_mode)[-3:] == "600"

    def test_preserves_existing_keys(self, tmp_path: Path):
        state = State({"KEEP": "new_val"})
        existing_env = tmp_path / ".env"
        existing_env.write_text("KEEP=old_val\nOTHER=stuff\n")
        tmpl = tmp_path / "env.tmpl"
        tmpl.write_text("KEEP={{KEEP}}\nOTHER={{OTHER}}")
        services_step._render_env_example(state, tmpl, existing_env, preserve_keys=["KEEP"])
        content = existing_env.read_text()
        assert "old_val" in content


class TestRun:
    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services.health_check")
    def test_deploys_selected_services(
        self,
        mock_health: MagicMock,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run(state)

        mock_compose.assert_called_once()
        args, kwargs = mock_compose.call_args
        assert "nocodb" in str(args[0])
        mock_reload.assert_called_once()

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services.health_check")
    def test_skips_host_service(
        self,
        mock_health: MagicMock,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": [],
            "selected_services": ["openclaw"],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
        })
        services_step.run(state)
        mock_compose.assert_not_called()

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.compose_up")
    @patch("rakkib.steps.services._reload_caddy")
    @patch("rakkib.steps.services.health_check")
    def test_renders_env_from_example(
        self,
        mock_health: MagicMock,
        mock_reload: MagicMock,
        mock_compose: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
        tmp_path: Path,
    ):
        mock_repo.return_value = fake_repo
        data_root = tmp_path / "srv"
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
            "data_root": str(data_root),
            "backup_dir": str(data_root / "backups"),
            "VALUE": "test123",
        })
        services_step.run(state)
        env_path = data_root / "docker" / "nocodb" / ".env"
        assert env_path.exists()


class TestVerify:
    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    @patch("rakkib.steps.services.container_publishes_port")
    def test_all_running_passes(
        self,
        mock_port: MagicMock,
        mock_running: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
    ):
        mock_repo.return_value = fake_repo
        mock_running.return_value = True
        mock_port.return_value = True
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is True

    @patch("rakkib.steps.services._repo_dir")
    @patch("rakkib.steps.services.container_running")
    def test_missing_container_fails(
        self,
        mock_running: MagicMock,
        mock_repo: MagicMock,
        fake_repo: Path,
    ):
        mock_repo.return_value = fake_repo
        mock_running.return_value = False
        state = State({
            "foundation_services": ["nocodb"],
            "selected_services": [],
        })
        result = services_step.verify(state)
        assert result.ok is False
        assert "nocodb" in result.message
