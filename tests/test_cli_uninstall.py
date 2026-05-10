from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from rakkib.cli import cli
from rakkib.state import State


class TestAggressiveUninstall:
    def test_uninstall_removes_cloudflared_and_data_root(self, tmp_path: Path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        (home / ".cloudflared").mkdir()
        data_root = tmp_path / "srv"
        (data_root / "docker").mkdir(parents=True)
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".fss-state.yaml").write_text(f"data_root: {data_root}\nconfirmed: true\n")

        monkeypatch.setattr(Path, "home", lambda: home)

        runner = CliRunner()
        with (
            patch("rakkib.cli._run_remove_hooks"),
            patch("rakkib.cli._remove_rakkib_docker"),
            patch("rakkib.cli._remove_rakkib_cron_entries", return_value=False),
        ):
            result = runner.invoke(cli, ["uninstall"], input="y\n", obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert not (home / ".cloudflared").exists()
        assert not data_root.exists()

    def test_uninstall_does_not_remove_data_root_without_state(self, tmp_path: Path, monkeypatch):
        home = tmp_path / "home"
        home.mkdir()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        monkeypatch.setattr(Path, "home", lambda: home)

        runner = CliRunner()
        with (
            patch("rakkib.cli._run_remove_hooks"),
            patch("rakkib.cli._remove_rakkib_docker"),
            patch("rakkib.cli._remove_rakkib_cron_entries", return_value=False),
        ):
            result = runner.invoke(cli, ["uninstall"], input="y\n", obj={"repo_dir": repo_dir})

        assert result.exit_code == 0
        assert "No data_root recorded" in result.output

    def test_remove_rakkib_cron_entries_removes_marked_lines(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if cmd == ["crontab", "-l"]:
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout="0 1 * * * /keep\n*/5 * * * * /rakkib  # RAKKIB: backup-local\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("rakkib.cli.subprocess.run", side_effect=fake_run):
            from rakkib.cli import _remove_rakkib_cron_entries

            assert _remove_rakkib_cron_entries(None) is True

        assert calls[1][0] == ["crontab", "-"]
        assert calls[1][1]["input"] == "0 1 * * * /keep\n"

    def test_remove_rakkib_docker_cleans_compose_and_registry_containers(self, tmp_path: Path):
        data_root = tmp_path / "srv"
        compose_dir = data_root / "docker" / "demo"
        compose_dir.mkdir(parents=True)
        (compose_dir / "docker-compose.yml").write_text("services: {}\n")
        state = State({"data_root": str(data_root)})
        registry = {"services": [{"id": "demo", "container_name": "demo_container"}]}

        def fake_docker_run(cmd, **_kwargs):
            if cmd[:1] == ["inspect"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")
            if cmd[:3] == ["ps", "-aq", "--filter"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with (
            patch("rakkib.cli.shutil.which", return_value="docker"),
            patch("rakkib.cli.compose_down") as mock_compose_down,
            patch("rakkib.cli.docker_run", side_effect=fake_docker_run) as mock_docker_run,
        ):
            from rakkib.cli import _remove_rakkib_docker

            _remove_rakkib_docker(state, registry)

        mock_compose_down.assert_called_once()
        rm_calls = [call.args[0] for call in mock_docker_run.call_args_list if call.args[0][:1] == ["rm"]]
        assert ["rm", "-f", "-v", "demo"] in rm_calls
        assert ["rm", "-f", "-v", "demo_container"] in rm_calls
