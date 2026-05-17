"""Tests for install.sh bootstrap helpers."""

from __future__ import annotations

import os
import shlex
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _q(value: Path | str) -> str:
    return shlex.quote(str(value))


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip())
    path.chmod(0o755)


def _run_install_script(script: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_path)
    return subprocess.run(
        ["bash", "-lc", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_quiet_uses_portable_mktemp_template(tmp_path: Path):
    log_path = tmp_path / "rakkib-install.ABC123"

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    mktemp() {{
      case "$1" in
        *XXXXXX) printf '%s\n' {_q(log_path)} ;;
        *) printf 'bad template: %s\n' "$1" >&2; return 1 ;;
      esac
    }}
    run_quiet noop true
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def _source_install(extra: str = "") -> str:
    return f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    {extra}
    """


class TestValidateRepoUrl:
    def test_accepts_public_https(self, tmp_path: Path):
        for url in (
            "https://github.com/FayaaDev/rakkib",
            "https://github.com/FayaaDev/rakkib.git",
            "https://github.com/FayaaDev/rakkib-dev",
            "https://github.com/FayaaDev/rakkib-dev.git",
        ):
            result = _run_install_script(_source_install(f"validate_repo_url {_q(url)}"), tmp_path)
            assert result.returncode == 0, f"rejected legitimate URL {url}: {result.stderr}"

    def test_accepts_ssh_forms(self, tmp_path: Path):
        for url in (
            "git@github.com:FayaaDev/rakkib.git",
            "git@github.com:FayaaDev/rakkib-dev.git",
            "ssh://git@github.com/FayaaDev/rakkib.git",
            "ssh://git@github.com/FayaaDev/rakkib-dev.git",
        ):
            result = _run_install_script(_source_install(f"validate_repo_url {_q(url)}"), tmp_path)
            assert result.returncode == 0, f"rejected legitimate URL {url}: {result.stderr}"

    def test_rejects_untrusted_urls(self, tmp_path: Path):
        for url in (
            "https://attacker.example/rakkib.git",
            "https://github.com/FayaaDev/Rakkib",  # legacy uppercase; old origin migrates but install rejects
            "https://github.com/evil/rakkib.git",
            "file:///tmp/local-rakkib",
            "https://github.com/FayaaDev/rakkib-fork.git",
        ):
            result = _run_install_script(_source_install(f"validate_repo_url {_q(url)}"), tmp_path)
            assert result.returncode != 0, f"accepted untrusted URL {url}"
            assert "untrusted repo" in result.stderr


class TestValidateBranch:
    def test_accepts_typical_names(self, tmp_path: Path):
        for branch in ("main", "Claudify", "v2.0.0a1", "release/1.0", "feature_x", "x"):
            result = _run_install_script(
                _source_install(f"validate_branch {_q(branch)}"), tmp_path
            )
            assert result.returncode == 0, f"rejected legitimate branch {branch}: {result.stderr}"

    def test_rejects_injection(self, tmp_path: Path):
        for branch in (
            "",
            "--upload-pack=evil",
            "-rf",
            ".hidden",
            "/abs",
            "main; rm -rf /",
            "main$(id)",
            "main`id`",
            "main\nrm",
        ):
            result = _run_install_script(
                _source_install(f"validate_branch {_q(branch)}"), tmp_path
            )
            assert result.returncode != 0, f"accepted dangerous branch {branch!r}"


def test_update_mode_default_is_skip(tmp_path: Path):
    # Defense against curl|bash silently destroying local checkout edits.
    script = _source_install('printf "%s" "$UPDATE_MODE"')
    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "skip", f"default UPDATE_MODE drifted: {result.stdout!r}"


def test_macos_tooling_installs_clt_homebrew_and_git(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    clt_ready = tmp_path / "clt-ready"
    git_ready = tmp_path / "git-ready"
    calls = tmp_path / "calls"

    _write_executable(
        fakebin / "softwareupdate",
        f"""
        #!/usr/bin/env bash
        if [[ "$1" == "-l" ]]; then
          printf '   * Label: Command Line Tools for Xcode-16.4\n'
          exit 0
        fi
        if [[ "$1" == "-i" ]]; then
          [[ -f /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress ]] || exit 2
          : > {_q(clt_ready)}
          exit 0
        fi
        exit 1
        """,
    )
    _write_executable(
        fakebin / "sudo",
        """
        #!/usr/bin/env bash
        exec "$@"
        """,
    )

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    PATH={_q(fakebin)}:/usr/bin:/bin
    xcode_clt_installed() {{ [[ -f {_q(clt_ready)} ]]; }}
    select_xcode_command_line_tools() {{ [[ -f {_q(clt_ready)} ]]; }}
    git_usable() {{ [[ -f {_q(git_ready)} ]]; }}
    ensure_homebrew() {{ printf 'homebrew\n' >> {_q(calls)}; }}
    ensure_brew_package() {{ printf '%s %s %s\n' "$1" "$2" "${{3:-0}}" >> {_q(calls)}; : > {_q(git_ready)}; }}
    command_exists() {{
      case "$1" in
        curl|softwareupdate|sudo) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    ensure_tooling
    test -f {_q(clt_ready)}
    test -f {_q(git_ready)}
    [[ "$(cat {_q(calls)})" == $'homebrew\ngit git 1' ]]
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_macos_clt_install_selects_command_line_tools(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    clt_ready = tmp_path / "clt-ready"
    selected = tmp_path / "selected"

    _write_executable(
        fakebin / "softwareupdate",
        f"""
        #!/usr/bin/env bash
        if [[ "$1" == "-l" ]]; then
          printf '   * Label: Command Line Tools for Xcode-16.4\n'
          exit 0
        fi
        if [[ "$1" == "-i" ]]; then
          [[ -f /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress ]] || exit 2
          : > {_q(clt_ready)}
          exit 0
        fi
        exit 1
        """,
    )
    _write_executable(
        fakebin / "sudo",
        """
        #!/usr/bin/env bash
        exec "$@"
        """,
    )

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    PATH={_q(fakebin)}:/usr/bin:/bin
    xcode_clt_installed() {{ [[ -f {_q(selected)} ]]; }}
    select_xcode_command_line_tools() {{ [[ -f {_q(clt_ready)} ]] && : > {_q(selected)}; }}
    command_exists() {{
      case "$1" in
        softwareupdate|sudo) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    install_xcode_command_line_tools
    test -f {_q(selected)}
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_macos_python_installs_homebrew_python(tmp_path: Path):
    python_ready = tmp_path / "python-ready"
    calls = tmp_path / "calls"

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    ensure_homebrew() {{ printf 'homebrew\n' >> {_q(calls)}; }}
    select_python_cmd() {{
      if [[ -f {_q(python_ready)} ]]; then
        PYTHON_CMD=/opt/homebrew/bin/python3
        return 0
      fi
      return 1
    }}
    brew() {{
      printf '%s %s\n' "$1" "$2" >> {_q(calls)}
      [[ "$1" == "install" && "$2" == "python" ]] && : > {_q(python_ready)}
    }}
    command_exists() {{
      case "$1" in
        apt-get|dnf|pacman) return 1 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    ensure_python3_and_venv
    [[ "$PYTHON_CMD" == /opt/homebrew/bin/python3 ]]
    [[ "$(cat {_q(calls)})" == $'homebrew\ninstall python' ]]
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_prepare_repo_requires_git_without_archive_fallback(tmp_path: Path):
    install_dir = tmp_path / "Rakkib"

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    INSTALL_DIR={_q(install_dir)}
    git_usable() {{ return 1; }}
    if ( prepare_repo ) >/tmp/rakkib-prepare.out 2>&1; then
      exit 1
    fi
    if ! [[ "$(cat /tmp/rakkib-prepare.out)" == *"git is required"* ]]; then
      cat /tmp/rakkib-prepare.out >&2
      exit 1
    fi
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_install_defaults_to_public_runtime_repo():
    install_text = (REPO_ROOT / "install.sh").read_text()

    assert 'DEFAULT_REPO_URL="https://github.com/FayaaDev/rakkib.git"' in install_text
    assert 'DEFAULT_BRANCH="main"' in install_text


def test_existing_checkout_migrates_legacy_origin_to_public_repo(tmp_path: Path):
    install_dir = tmp_path / "Rakkib"

    script = f"""
    set -euo pipefail
    git init -b runtime {_q(install_dir)} >/dev/null
    git -C {_q(install_dir)} remote add origin https://github.com/FayaaDev/Rakkib.git
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    INSTALL_DIR={_q(install_dir)}
    ensure_origin_url
    [[ "$(git -C {_q(install_dir)} remote get-url origin)" == "https://github.com/FayaaDev/rakkib.git" ]]
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_linux_tooling_still_requires_git(tmp_path: Path):
    script = """
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=linux
    git_usable() { return 1; }
    command_exists() {
      case "$1" in
        curl) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }
    if ( ensure_tooling ) >/tmp/rakkib-tooling.out 2>&1; then
      exit 1
    fi
    if ! [[ "$(cat /tmp/rakkib-tooling.out)" == *"git is required"* ]]; then
      cat /tmp/rakkib-tooling.out >&2
      exit 1
    fi
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_removed_macos_archive_and_python_pkg_fallbacks():
    install_text = (REPO_ROOT / "install.sh").read_text()
    assert "prepare_repo_archive" not in install_text
    assert "codeload.github.com" not in install_text
    assert "python.org/ftp" not in install_text
