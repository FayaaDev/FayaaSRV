"""Tests for rakkib.cli."""

from __future__ import annotations

import os
import shutil
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rakkib.cli import _build_add_choices, _postgres_sync_needed, _print_deployed_urls, cli
from rakkib.state import State
from rakkib.web.host_auth import HostAuthStatus


class TestInit:
    def test_init_runs_interview(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()

        # Create minimal question files so load_all_schemas works
        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with patch("rakkib.cli.run_interview") as mock_run:
            mock_run.return_value = State({"platform": "linux", "confirmed": False})
            result = runner.invoke(
                cli,
                ["init"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        assert "Rakkib init" in result.output
        assert "State is not confirmed" in result.output
        mock_run.assert_called_once()

    def test_init_confirmed_state_goes_through_interview(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        questions_dir = repo_dir / "questions"
        questions_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        (questions_dir / "01-platform.md").write_text(
            "## AgentSchema\n```yaml\nschema_version: 1\nphase: 1\nfields:\n"
            "  - id: platform\n    type: single_select\n    prompt: Platform?\n"
            "    canonical_values: [linux, mac]\n    records: [platform]\n```\n"
        )

        with (
            patch("rakkib.cli.run_interview") as mock_interview,
            patch("rakkib.cli._run_steps") as mock_steps,
        ):
            mock_interview.return_value = State({"platform": "linux", "confirmed": True})
            result = runner.invoke(
                cli,
                ["init"],
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 0
        mock_interview.assert_called_once()
        mock_steps.assert_not_called()
        assert "Run rakkib pull to install" in result.output


class TestUninstall:
    def test_uninstall_removes_symlink(self, tmp_path: Path, monkeypatch):
        bin_dir = tmp_path / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        shim = bin_dir / "rakkib"
        shim.symlink_to("/dev/null")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert not shim.exists()

    def test_uninstall_no_shim(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert "No rakkib CLI shim found" in result.output


class TestStatus:
    def test_status_unconfirmed_shows_message(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        result = runner.invoke(cli, ["status"], obj={"repo_dir": repo_dir})
        assert result.exit_code == 0
        assert "No confirmed deployment state found" in result.output

    def test_status_confirmed_shows_details(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "domain: example.com\n"
            "data_root: /srv\n"
            "platform: linux\n"
            "foundation_services:\n  - nocodb\n  - homepage\n"
            "selected_services:\n  - n8n\n"
            "host_addons:\n  - vergo_terminal\n"
            "subdomains:\n  nocodb: nocodb\n  n8n: n8n\n"
        )
        result = runner.invoke(cli, ["status"], obj={"repo_dir": repo_dir})
        assert result.exit_code == 0
        assert "example.com" in result.output
        assert "nocodb" in result.output
        assert "n8n" in result.output
        assert "vergo_terminal" in result.output

    def test_status_reads_checkout_state_from_package_repo_dir(self, tmp_path: Path):
        runner = CliRunner()
        checkout = tmp_path / "repo"
        package_dir = checkout / "src" / "rakkib"
        package_dir.mkdir(parents=True)
        (checkout / ".git").mkdir()
        (checkout / ".fss-state.yaml").write_text(
            "confirmed: true\n"
            "domain: example.com\n"
            "data_root: /srv\n"
            "foundation_services: []\n"
            "selected_services: []\n"
        )

        result = runner.invoke(cli, ["status"], obj={"repo_dir": package_dir})

        assert result.exit_code == 0
        assert "example.com" in result.output


class TestUpdate:
    def test_update_success_current_branch(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        branch = MagicMock(returncode=0, stdout="main\n", stderr="")
        with patch("rakkib.cli.subprocess.run", side_effect=[branch, ok, ok]) as mock_run:
            result = runner.invoke(cli, ["update"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Updated to the latest origin/main code" in result.output
        assert [call.kwargs["cwd"] for call in mock_run.call_args_list] == [repo_dir] * 3
        assert [call.args[0] for call in mock_run.call_args_list] == [
            ["git", "branch", "--show-current"],
            ["git", "fetch", "origin", "main"],
            ["git", "pull", "--ff-only", "origin", "main"],
        ]

    def test_update_non_git_checkout_fails(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        result = runner.invoke(cli, ["update"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "git checkout" in result.output
        assert "Reinstall Rakkib" in result.output

    def test_update_pull_failure_exits_nonzero(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        branch = MagicMock(returncode=0, stdout="main\n", stderr="")
        failed = MagicMock(returncode=1, stdout="", stderr="pull blocked by local changes")
        with patch("rakkib.cli.subprocess.run", side_effect=[branch, ok, failed]):
            result = runner.invoke(cli, ["update"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Update failed:" in result.output
        assert "pull blocked by local changes" in result.output

    def test_update_resolves_checkout_from_package_dir(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        package_dir = repo_dir / "src" / "rakkib"
        package_dir.mkdir(parents=True)
        (repo_dir / ".git").mkdir()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        branch = MagicMock(returncode=0, stdout="main\n", stderr="")
        with patch("rakkib.cli.subprocess.run", side_effect=[branch, ok, ok]) as mock_run:
            result = runner.invoke(cli, ["update"], obj={"repo_dir": package_dir})

        assert result.exit_code == 0
        assert [call.kwargs["cwd"] for call in mock_run.call_args_list] == [repo_dir] * 3


class TestDoctor:
    def test_doctor_json_output(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "ok", True, "Ubuntu detected")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "ok", True, "daemon reachable")
            mock_compose.return_value = CheckResult("compose", "ok", True, "v2")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free 443=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
                CheckResult("cloudflare_auth", "ok", False, "browser_login"),
                CheckResult("cloudflare_creds", "ok", False, "present"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")

            result = runner.invoke(cli, ["doctor", "--json"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["summary"]["ok"] > 0
        assert len(data["checks"]) > 0

    def test_doctor_exit_code_on_failure(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "fail", True, "unsupported")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "ok", True, "daemon reachable")
            mock_compose.return_value = CheckResult("compose", "ok", True, "v2")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free 443=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
                CheckResult("cloudflare_auth", "ok", False, "browser_login"),
                CheckResult("cloudflare_creds", "ok", False, "present"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")

            result = runner.invoke(cli, ["doctor"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "fail" in result.output
        assert "os" in result.output

    def test_doctor_interactive_prompts_for_fix(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("rakkib.doctor.check_os") as mock_os, \
             patch("rakkib.doctor.check_arch") as mock_arch, \
             patch("rakkib.doctor.check_ram") as mock_ram, \
             patch("rakkib.doctor.check_disk") as mock_disk, \
             patch("rakkib.doctor.check_docker") as mock_docker, \
             patch("rakkib.doctor.check_compose") as mock_compose, \
             patch("rakkib.doctor.check_cloudflared_binary") as mock_cf, \
             patch("rakkib.doctor.check_public_ports") as mock_pp, \
             patch("rakkib.doctor.check_ssh_port") as mock_ssh, \
             patch("rakkib.doctor.check_domain_dns") as mock_dns, \
             patch("rakkib.doctor.check_cloudflare_readiness") as mock_cfr, \
             patch("rakkib.doctor.check_conflicts") as mock_conf, \
             patch("rakkib.cli.attempt_fix_docker") as mock_fix:
            from rakkib.doctor import CheckResult
            mock_os.return_value = CheckResult("os", "ok", True, "Ubuntu")
            mock_arch.return_value = CheckResult("architecture", "ok", False, "amd64")
            mock_ram.return_value = CheckResult("ram", "ok", False, "8192 MB")
            mock_disk.return_value = CheckResult("disk", "ok", False, "50 GB")
            mock_docker.return_value = CheckResult("docker", "fail", True, "missing")
            mock_compose.return_value = CheckResult("compose", "fail", True, "missing")
            mock_cf.return_value = CheckResult("cloudflared_cli", "ok", False, "on PATH")
            mock_pp.return_value = CheckResult("public_ports", "ok", True, "80=free")
            mock_ssh.return_value = CheckResult("ssh_port", "ok", False, "listening")
            mock_dns.return_value = CheckResult("dns", "ok", False, "resolves")
            mock_cfr.return_value = [
                CheckResult("cloudflare_zone", "ok", False, "active"),
            ]
            mock_conf.return_value = CheckResult("conflicts", "ok", False, "none")
            mock_fix.return_value = "installed"

            result = runner.invoke(
                cli,
                ["doctor", "--interactive"],
                input="y\ny\n",
                obj={"repo_dir": repo_dir},
            )

        assert result.exit_code == 1
        mock_fix.assert_called_once()


class TestPull:
    def test_pull_service_allows_unconfirmed_internal_state(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("")

        with (
            patch("rakkib.cli.ensure_prereqs", return_value=True),
            patch("rakkib.steps.services._ensure_service_runtime_env") as mock_runtime_env,
            patch("rakkib.cli._run_service_pull", return_value=True) as mock_run_service_pull,
        ):
            result = runner.invoke(cli, ["pull", "--service", "stirling-pdf"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_runtime_env.assert_called_once()
        mock_run_service_pull.assert_called_once()
        state = mock_run_service_pull.call_args.args[0]
        assert state.get("exposure_mode") == "internal"

    def test_pull_only_prints_links_for_installed_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "domain: example.com\n"
            "foundation_services:\n  - homepage\n"
            "selected_services:\n  - n8n\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "  hermes: hermes\n"
        )

        def fake_run_steps(state: State, repo_dir: Path) -> bool:
            _print_deployed_urls(state)
            return True

        with (
            patch("rakkib.cli.ensure_prereqs", return_value=True),
            patch("rakkib.cli._run_steps", side_effect=fake_run_steps),
        ):
            result = runner.invoke(cli, ["pull"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Deployed services:" in result.output
        assert "homepage" in result.output
        assert "https://home.example.com" in result.output
        assert "n8n" in result.output
        assert "https://n8n.example.com" in result.output
        assert "hermes" not in result.output
        assert "https://hermes.example.com" not in result.output

    def test_pull_prints_internal_direct_port_links(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "exposure_mode: internal\n"
            "lan_ip: 192.168.1.50\n"
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
        )

        def fake_run_steps(state: State, repo_dir: Path) -> bool:
            _print_deployed_urls(state)
            return True

        with (
            patch("rakkib.cli.ensure_prereqs", return_value=True),
            patch("rakkib.cli._run_steps", side_effect=fake_run_steps),
        ):
            result = runner.invoke(cli, ["pull"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "homepage" in result.output
        assert "http://192.168.1.50:13000/" in result.output


class TestAdd:
    def _make_registry(self, extra_services=None):
        services = [
            {
                "id": "postgres",
                "state_bucket": "always",
                "depends_on": [],
                "default_subdomain": None,
                "subdomain_placeholder": None,
                "notes": "Shared database backend.",
                "secrets": {"POSTGRES_PASSWORD": {"factory": "password"}},
            },
            {"id": "homepage", "state_bucket": "foundation_services", "depends_on": [], "default_subdomain": "home", "subdomain_placeholder": "HOMEPAGE_SUBDOMAIN", "notes": "Service dashboard."},
            {"id": "nocodb", "state_bucket": "foundation_services", "depends_on": ["postgres"], "default_subdomain": "nocodb", "subdomain_placeholder": "NOCODB_SUBDOMAIN", "notes": "No-code database UI.", "postgres": {"role": "nocodb", "db": "nocodb_db", "password_key": "NOCODB_DB_PASS"}},
            {"id": "n8n", "state_bucket": "selected_services", "depends_on": ["postgres"], "default_subdomain": "n8n", "subdomain_placeholder": "N8N_SUBDOMAIN", "notes": "Workflow automation.", "postgres": {"role": "n8n", "db": "n8n_db", "password_key": "N8N_DB_PASS"}, "homepage": {"category": "Automation"}},
            {"id": "hermes", "state_bucket": "selected_services", "depends_on": ["homepage"], "default_subdomain": "hermes", "subdomain_placeholder": "HERMES_SUBDOMAIN", "notes": "Internal assistant."},
            {"id": "openclaw", "state_bucket": "selected_services", "host_service": True, "depends_on": [], "default_subdomain": "claw", "subdomain_placeholder": "OPENCLAW_SUBDOMAIN", "notes": "AI assistant gateway.", "homepage": {"category": "AI"}},
        ]
        if extra_services:
            services.extend(extra_services)
        return {"services": services}

    def test_add_choices_group_selected_services_by_category(self):
        choices = _build_add_choices(
            State({"selected_services": ["n8n"]}), self._make_registry()
        )

        titles = [choice.title for choice in choices]
        assert "━━ Optional Services ━━" not in titles
        assert "━━ Automation ━━" in titles
        assert "━━ AI ━━" in titles
        assert "━━ Other ━━" in titles
        assert titles.index("━━ Automation ━━") < titles.index(
            "  n8n [Workflow automation]"
        )

    def test_postgres_sync_needed_only_for_postgres_service_delta(self):
        registry = self._make_registry()

        assert _postgres_sync_needed(registry, {"homepage", "nocodb"}, {"homepage", "nocodb", "openclaw"}) is False
        assert _postgres_sync_needed(registry, {"homepage"}, {"homepage", "n8n"}) is True
        assert _postgres_sync_needed(registry, {"homepage", "n8n"}, {"homepage"}) is True
        assert _postgres_sync_needed(registry, {"homepage", "n8n"}, {"homepage", "n8n"}) is True

    def test_add_rejects_invalid_dependency_selection(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text("confirmed: true\n")

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["hermes"]),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Invalid service selection" in result.output
        assert "hermes requires homepage" in result.output

    def test_add_no_changes_refreshes_selected_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
        )
        call_order: list[str] = []

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage"]),
            patch("rakkib.cli.prompt_confirm") as mock_confirm,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.postgres.run") as mock_postgres_run,
            patch("rakkib.steps.services.sync_shared_artifacts") as mock_sync_artifacts,
        ):
            mock_reg.return_value = self._make_registry()
            mock_secrets.side_effect = lambda state: call_order.append("secrets")
            mock_postgres_run.side_effect = lambda state: call_order.append("postgres")
            mock_sync_artifacts.side_effect = lambda *args, **kwargs: call_order.append("services")
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "No selection changes; refreshing selected services" in result.output
        assert "synced successfully" in result.output
        mock_confirm.assert_not_called()
        mock_secrets.assert_called_once()
        mock_postgres_run.assert_not_called()
        mock_sync_artifacts.assert_called_once()
        assert call_order == ["secrets", "services"]

        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage"]
        assert saved_state.get("selected_services") == []
        assert saved_state.get("subdomains") == {"homepage": "home"}
        assert saved_state.get("HOMEPAGE_SUBDOMAIN") == "home"

    def test_add_preserves_always_service_secrets(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "POSTGRES_PASSWORD: keep-postgres\n"
            "secrets:\n"
            "  values:\n"
            "    POSTGRES_PASSWORD: keep-postgres\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage"]),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.sync_shared_artifacts"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        saved_state = State.load(state_file)
        assert saved_state.get("POSTGRES_PASSWORD") == "keep-postgres"
        assert saved_state.get("secrets.values.POSTGRES_PASSWORD") == "keep-postgres"

    def test_add_backfills_host_gateway_for_host_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services: []\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["openclaw"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_postgres.assert_not_called()
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["openclaw"]
        assert saved_state.get("subdomains.openclaw") == "claw"
        assert saved_state.get("OPENCLAW_SUBDOMAIN") == "claw"
        assert saved_state.get("host_gateway") == "172.18.0.1"

    def test_add_service_argument_adds_service_without_checkbox(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "openclaw"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_postgres.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "openclaw"
        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage"]
        assert saved_state.get("selected_services") == ["openclaw"]
        assert saved_state.get("host_gateway") == "172.18.0.1"

    def test_add_host_service_argument_skips_postgres_with_existing_db_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n  - nocodb\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "openclaw"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_postgres.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "openclaw"

    def test_add_service_option_adds_service_without_checkbox(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "--service", "openclaw"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_postgres.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "openclaw"
        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage"]
        assert saved_state.get("selected_services") == ["openclaw"]
        assert saved_state.get("host_gateway") == "172.18.0.1"

    def test_add_rejects_conflicting_service_argument_and_option(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("confirmed: true\n")

        result = runner.invoke(
            cli,
            ["add", "openclaw", "--service", "n8n"],
            obj={"repo_dir": repo_dir},
        )

        assert result.exit_code == 1
        assert "Provide the service either as an argument or with --service" in result.output

    def test_add_immich_argument_runs_single_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "platform: linux\n"
            "foundation_services:\n  - homepage\n"
            "selected_services:\n  - n8n\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox") as mock_checkbox,
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run") as mock_postgres,
            patch("rakkib.steps.services.run") as mock_run,
            patch("rakkib.steps.services.run_single_service") as mock_run_single,
        ):
            mock_reg.return_value = self._make_registry(
                extra_services=[
                    {
                        "id": "immich",
                        "state_bucket": "selected_services",
                        "depends_on": [],
                        "default_subdomain": "immich",
                        "subdomain_placeholder": "IMMICH_SUBDOMAIN",
                        "notes": "Photo library.",
                    }
                ]
            )
            result = runner.invoke(cli, ["add", "immich"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_checkbox.assert_not_called()
        mock_postgres.assert_not_called()
        mock_run.assert_not_called()
        mock_run_single.assert_called_once()
        assert mock_run_single.call_args.args[1] == "immich"
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["n8n", "immich"]
        assert saved_state.get("subdomains.immich") == "immich"

    def test_add_service_argument_rejects_unknown_service(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("confirmed: true\n")

        with patch("rakkib.steps.services._load_registry") as mock_reg:
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add", "missing"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "Unknown service 'missing'" in result.output

    def test_add_aborts_when_not_confirmed(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - nocodb\n"
            "selected_services:\n  - n8n\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
            "NOCODB_SUBDOMAIN: nocodb\n"
            "N8N_SUBDOMAIN: n8n\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "nocodb"]),
            patch("rakkib.cli.prompt_confirm", return_value=False),
            patch("rakkib.steps.services.remove_single_service") as mock_remove,
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_remove.assert_not_called()

        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["n8n"]

    def test_add_syncs_selected_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n  - nocodb\n"
            "selected_services:\n  - n8n\n"
            "data_root: /srv\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "  n8n: n8n\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
            "NOCODB_SUBDOMAIN: nocodb\n"
            "N8N_SUBDOMAIN: n8n\n"
        )
        call_order: list[str] = []

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "nocodb"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.steps.services.remove_single_service") as mock_remove,
            patch("rakkib.steps.services._generate_missing_secrets") as mock_secrets,
            patch("rakkib.steps.postgres.run") as mock_postgres_run,
            patch("rakkib.steps.services.sync_shared_artifacts") as mock_sync_artifacts,
        ):
            mock_reg.return_value = self._make_registry()
            mock_secrets.side_effect = lambda state: call_order.append("secrets")
            mock_postgres_run.side_effect = lambda state: call_order.append("postgres")
            mock_sync_artifacts.side_effect = lambda *args, **kwargs: call_order.append("services")
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "synced successfully" in result.output
        assert [call.args[1] for call in mock_remove.call_args_list] == ["n8n"]
        mock_secrets.assert_called_once()
        mock_postgres_run.assert_called_once()
        mock_sync_artifacts.assert_called_once()
        assert call_order == ["secrets", "postgres", "services"]

        saved_state = State.load(state_file)
        assert saved_state.get("foundation_services") == ["homepage", "nocodb"]
        assert saved_state.get("selected_services") == []
        assert saved_state.get("subdomains") == {"homepage": "home", "nocodb": "nocodb"}
        assert saved_state.get("HOMEPAGE_SUBDOMAIN") == "home"
        assert saved_state.get("NOCODB_SUBDOMAIN") == "nocodb"
        assert saved_state.get("N8N_SUBDOMAIN") is None

    def test_add_uses_spinner_when_applying_changes(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "foundation_services:\n  - homepage\n"
            "selected_services: []\n"
            "domain: example.com\n"
            "subdomains:\n"
            "  homepage: home\n"
            "HOMEPAGE_SUBDOMAIN: home\n"
        )

        with (
            patch("rakkib.steps.services._load_registry") as mock_reg,
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "openclaw"]),
            patch("rakkib.cli.prompt_confirm", return_value=True),
            patch("rakkib.cli.progress_spinner", return_value=nullcontext()) as mock_spinner,
            patch("rakkib.steps.services._generate_missing_secrets"),
            patch("rakkib.steps.postgres.run"),
            patch("rakkib.steps.services.run_single_service"),
        ):
            mock_reg.return_value = self._make_registry()
            result = runner.invoke(cli, ["add"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_spinner.assert_called_once_with("Applying service changes...")
        saved_state = State.load(state_file)
        assert saved_state.get("selected_services") == ["openclaw"]


class TestUninstallPathBlock:
    def test_uninstall_removes_path_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create fake .bashrc with the marker block
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text(
            "some config\n"
            "# Added by Rakkib: user-local bin on PATH\n"
            'case ":$PATH:" in\n'
            '  *":$HOME/.local/bin:"*) ;;\n'
            '  *) export PATH="$HOME/.local/bin:$PATH" ;;\n'
            "esac\n"
            "more config\n"
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        content = bashrc.read_text()
        assert "# Added by Rakkib" not in content
        assert "some config" in content
        assert "more config" in content

    def test_uninstall_no_path_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("some config\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["uninstall"], input="y\n")
        assert result.exit_code == 0
        assert "No managed PATH block" in result.output


class TestAuth:
    def test_auth_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        runner = CliRunner()
        result = runner.invoke(cli, ["auth"])
        assert result.exit_code == 0
        assert "Authorization is ready" in result.output

    def test_auth_sudo_ready(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/sudo" if cmd == "sudo" else None)

        runner = CliRunner()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            result = runner.invoke(cli, ["auth"])
        assert result.exit_code == 0
        assert "Authorization is ready" in result.output

    def test_auth_sudo_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        monkeypatch.setattr(shutil, "which", lambda _cmd: None)
        runner = CliRunner()
        result = runner.invoke(cli, ["auth"])
        assert result.exit_code == 1
        assert "sudo is required" in result.output

    def test_auth_mac_missing_docker_installs_colima_backend(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        monkeypatch.setattr("rakkib.cli.platform.system", lambda: "Darwin")
        which_calls = {"count": 0}

        def fake_which(cmd: str):
            if cmd != "docker":
                return None
            which_calls["count"] += 1
            return "/usr/local/bin/docker" if which_calls["count"] > 1 else None

        monkeypatch.setattr("rakkib.cli.shutil.which", fake_which)
        monkeypatch.setattr("rakkib.cli.attempt_fix_docker", lambda: "Docker installed.")
        monkeypatch.setattr("rakkib.cli.docker_run", lambda _args: MagicMock(returncode=0, stdout="", stderr=""))

        runner = CliRunner()
        result = runner.invoke(cli, ["auth"], obj={"repo_dir": tmp_path})

        assert result.exit_code == 0
        assert "Preparing Docker" in result.output
        assert "Docker is ready" in result.output

    def test_auth_help(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0

    def test_auth_docker_prepares_access(self, tmp_path: Path, monkeypatch):
        from rakkib.docker import DockerError

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("admin_user: ubuntu\n")
        sudo_ok = MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        runner = CliRunner()
        with (
            patch("rakkib.cli.shutil.which", return_value="/usr/bin/docker"),
            patch(
                "rakkib.cli.docker_run",
                side_effect=DockerError(
                    "denied",
                    ["docker", "info"],
                    1,
                    "permission denied while trying to connect to /var/run/docker.sock",
                ),
            ),
            patch(
                "rakkib.cli.subprocess.run",
                side_effect=[sudo_ok, sudo_ok, sudo_ok, sudo_ok],
            ) as mock_run,
        ):
            result = runner.invoke(cli, ["auth"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Docker is ready for your user" in result.output
        assert ["sudo", "-n", "usermod", "-aG", "docker", "ubuntu"] in [
            call.args[0] for call in mock_run.call_args_list
        ]

    def test_auth_docker_already_ready(self, tmp_path: Path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        runner = CliRunner()
        sudo_ok = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch("rakkib.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("rakkib.cli.docker_run", return_value=MagicMock(returncode=0)),
            patch("rakkib.cli.subprocess.run", return_value=sudo_ok),
        ):
            result = runner.invoke(cli, ["auth"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Docker is ready" in result.output


class TestPrivileged:
    def test_privileged_check_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        runner = CliRunner()
        result = runner.invoke(cli, ["privileged", "check"])
        assert result.exit_code == 0
        assert "running as root" in result.output

    def test_privileged_check_non_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 1000)
        runner = CliRunner()
        result = runner.invoke(cli, ["privileged", "check"])
        assert result.exit_code == 1
        assert "root shell" in result.output

    def test_privileged_ensure_layout(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        data_root = tmp_path / "srv"
        state_file = tmp_path / ".fss-state.yaml"
        state_file.write_text("admin_user: testuser\n")

        runner = CliRunner()
        with patch("shutil.chown") as mock_chown:
            result = runner.invoke(
                cli,
                ["privileged", "ensure-layout", "--state", str(state_file), "--data-root", str(data_root)],
            )
        assert result.exit_code == 0
        assert data_root.exists()
        assert (data_root / "docker").exists()
        assert (data_root / "logs").exists()
        mock_chown.assert_called()

    def test_privileged_fix_repo_owner(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = tmp_path / ".fss-state.yaml"
        state_file.write_text("admin_user: testuser\n")

        runner = CliRunner()
        with patch("shutil.chown") as mock_chown:
            result = runner.invoke(
                cli,
                ["privileged", "fix-repo-owner", "--state", str(state_file), "--repo-dir", str(repo_dir)],
            )
        assert result.exit_code == 0
        mock_chown.assert_called()
class TestPullSnapshots:
    def test_pull_persists_deployed_selection_on_success(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "confirmed: true\n"
            "foundation_services:\n  - homepage\n"
            "selected_services:\n  - n8n\n"
        )

        with (
            patch("rakkib.cli.ensure_prereqs", return_value=True),
            patch("rakkib.cli._run_steps", return_value=True),
        ):
            result = runner.invoke(cli, ["pull"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        state = State.load(state_file)
        assert state.get("deployed.exists") is True
        assert state.get("deployed.foundation_services") == ["homepage"]
        assert state.get("deployed.selected_services") == ["n8n"]


class TestWeb:
    def test_web_prompt_yes_enables_lan_bind(self, tmp_path: Path):
        runner = CliRunner()

        with (
            patch("rakkib.cli._stdin_is_interactive", return_value=True),
            patch(
                "rakkib.cli.check_host_auth_readiness",
                return_value=HostAuthStatus(True, "ready", "ready", command=None),
            ),
            patch("rakkib.cli.prompt_confirm", return_value=True) as mock_prompt,
            patch("rakkib.cli._detect_lan_ip", return_value="192.168.1.50"),
            patch("rakkib.cli._show_qr"),
            patch("uvicorn.run") as mock_run,
        ):
            result = runner.invoke(
                cli,
                ["web", "--no-open", "--no-token"],
                obj={"repo_dir": tmp_path},
            )

        assert result.exit_code == 0
        mock_prompt.assert_called_once_with(
            "Do you want to set up your server from another machine on your network?",
            default=False,
        )
        assert mock_run.call_args.kwargs["host"] == "0.0.0.0"
        assert "LAN:" in result.output
        assert "http://192.168.1.50:8080" in result.output

    def test_web_prompt_no_keeps_local_bind(self, tmp_path: Path):
        runner = CliRunner()

        with (
            patch("rakkib.cli._stdin_is_interactive", return_value=True),
            patch(
                "rakkib.cli.check_host_auth_readiness",
                return_value=HostAuthStatus(True, "ready", "ready", command=None),
            ),
            patch("rakkib.cli.prompt_confirm", return_value=False),
            patch("rakkib.cli._detect_lan_ip") as mock_detect_lan_ip,
            patch("rakkib.cli._show_qr"),
            patch("uvicorn.run") as mock_run,
        ):
            result = runner.invoke(
                cli,
                ["web", "--no-open", "--no-token"],
                obj={"repo_dir": tmp_path},
            )

        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["host"] == "127.0.0.1"
        mock_detect_lan_ip.assert_not_called()
        assert "LAN:" not in result.output

    def test_web_local_skips_lan_prompt(self, tmp_path: Path):
        runner = CliRunner()

        with (
            patch("rakkib.cli._stdin_is_interactive", return_value=True),
            patch(
                "rakkib.cli.check_host_auth_readiness",
                return_value=HostAuthStatus(True, "ready", "ready", command=None),
            ),
            patch("rakkib.cli.prompt_confirm") as mock_prompt,
            patch("rakkib.cli._show_qr"),
            patch("uvicorn.run") as mock_run,
        ):
            result = runner.invoke(
                cli,
                ["web", "--local", "--no-open", "--no-token"],
                obj={"repo_dir": tmp_path},
            )

        assert result.exit_code == 0
        mock_prompt.assert_not_called()
        assert mock_run.call_args.kwargs["host"] == "127.0.0.1"

    def test_web_non_interactive_skips_lan_prompt(self, tmp_path: Path):
        runner = CliRunner()

        with (
            patch("rakkib.cli._stdin_is_interactive", return_value=False),
            patch(
                "rakkib.cli.check_host_auth_readiness",
                return_value=HostAuthStatus(True, "ready", "ready", command=None),
            ),
            patch("rakkib.cli.prompt_confirm") as mock_prompt,
            patch("rakkib.cli._show_qr"),
            patch("uvicorn.run") as mock_run,
        ):
            result = runner.invoke(
                cli,
                ["web", "--no-open", "--no-token"],
                obj={"repo_dir": tmp_path},
            )

        assert result.exit_code == 0
        mock_prompt.assert_not_called()
        assert mock_run.call_args.kwargs["host"] == "127.0.0.1"

    def test_web_prompts_for_host_auth_when_blocked(self, tmp_path: Path):
        runner = CliRunner()
        blocked = HostAuthStatus(False, "sudo_required", "Run `rakkib auth` first.")
        ready = HostAuthStatus(True, "ready", "ready", command=None)

        with (
            patch("rakkib.cli._stdin_is_interactive", return_value=True),
            patch("rakkib.cli.check_host_auth_readiness", side_effect=[blocked, ready]),
            patch("rakkib.cli.prompt_confirm", return_value=True) as mock_prompt,
            patch("rakkib.cli._run_auth_setup", return_value=True) as mock_auth,
            patch("rakkib.cli._show_qr"),
            patch("uvicorn.run") as mock_run,
        ):
            result = runner.invoke(
                cli,
                ["web", "--local", "--no-open", "--no-token"],
                obj={"repo_dir": tmp_path},
            )

        assert result.exit_code == 0
        mock_prompt.assert_called_once_with("Run `rakkib auth` now?", default=True)
        mock_auth.assert_called_once()
        assert "Host authorization is ready" in result.output
        assert mock_run.call_args.kwargs["host"] == "127.0.0.1"


class TestSyncServices:
    def test_sync_services_invokes_narrow_state_sync(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("confirmed: true\n")

        with patch("rakkib.cli._sync_services_to_state_selection", return_value=True) as mock_sync:
            result = runner.invoke(cli, ["sync-services"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        mock_sync.assert_called_once()


class TestRestart:
    def test_restart_without_args_prompts_for_deployed_services(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        state_file = repo_dir / ".fss-state.yaml"
        state_file.write_text(
            "deployed:\n"
            "  exists: true\n"
            "  foundation_services:\n"
            "    - homepage\n"
            "  selected_services:\n"
            "    - n8n\n"
        )

        registry = {
            "services": [
                {"id": "postgres", "state_bucket": "always", "notes": "Database."},
                {"id": "homepage", "state_bucket": "foundation_services", "notes": "Dashboard."},
                {
                    "id": "n8n",
                    "state_bucket": "selected_services",
                    "homepage": {"category": "Automation"},
                    "notes": "Workflow automation.",
                },
                {"id": "caddy", "state_bucket": "always", "notes": "Proxy."},
            ]
        }

        with (
            patch("rakkib.cli.load_service_registry", return_value=registry),
            patch("rakkib.cli.prompt_checkbox", return_value=["homepage", "caddy"]) as mock_prompt,
            patch("rakkib.cli.services_step.restart_service") as mock_restart,
        ):
            result = runner.invoke(cli, ["restart"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "Restarting selected services" in result.output
        choices = mock_prompt.call_args.kwargs["choices"]
        selectable = [choice for choice in choices if not choice.disabled]
        assert selectable
        assert all(choice.checked is False for choice in selectable)
        assert [call.args[1] for call in mock_restart.call_args_list] == ["homepage", "caddy"]

    def test_restart_without_args_aborts_when_nothing_deployed(self, tmp_path: Path):
        runner = CliRunner()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text("{}\n")

        with patch(
            "rakkib.cli.load_service_registry",
            return_value={"services": [{"id": "postgres", "state_bucket": "always", "notes": "Database."}]},
        ):
            result = runner.invoke(cli, ["restart"], obj={"repo_dir": repo_dir})

        assert result.exit_code == 1
        assert "No deployed services found" in result.output
