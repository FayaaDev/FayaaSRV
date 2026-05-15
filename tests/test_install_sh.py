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


def test_macos_without_git_uses_archive_checkout(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    install_dir = tmp_path / "Rakkib"

    _write_executable(
        fakebin / "curl",
        """
        #!/usr/bin/env bash
        out=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -o) out="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        : > "$out"
        """,
    )
    _write_executable(
        fakebin / "tar",
        """
        #!/usr/bin/env bash
        target=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -C) target="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        mkdir -p "$target/Rakkib-MacSupport/src/rakkib"
        printf '[project]\nname = "rakkib"\n' > "$target/Rakkib-MacSupport/pyproject.toml"
        : > "$target/Rakkib-MacSupport/src/rakkib/__init__.py"
        """,
    )

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    INSTALL_DIR={_q(install_dir)}
    REPO_URL=https://github.com/FayaaDev/Rakkib.git
    BRANCH=MacSupport
    UPDATE_MODE=reset
    PATH={_q(fakebin)}:$PATH
    command_exists() {{
      case "$1" in
        git) return 1 ;;
        curl|tar) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    prepare_repo
    test -f "$INSTALL_DIR/.rakkib-archive-install"
    test -f "$INSTALL_DIR/pyproject.toml"
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_macos_xcode_git_shim_uses_archive_checkout(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    install_dir = tmp_path / "Rakkib"

    _write_executable(
        fakebin / "curl",
        """
        #!/usr/bin/env bash
        out=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -o) out="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        : > "$out"
        """,
    )
    _write_executable(
        fakebin / "tar",
        """
        #!/usr/bin/env bash
        target=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -C) target="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        mkdir -p "$target/Rakkib-MacSupport/src/rakkib"
        printf '[project]\nname = "rakkib"\n' > "$target/Rakkib-MacSupport/pyproject.toml"
        : > "$target/Rakkib-MacSupport/src/rakkib/__init__.py"
        """,
    )
    _write_executable(
        fakebin / "xcode-select",
        """
        #!/usr/bin/env bash
        exit 2
        """,
    )
    _write_executable(
        fakebin / "git",
        """
        #!/usr/bin/env bash
        printf 'git should not be called\n' >&2
        exit 99
        """,
    )

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    INSTALL_DIR={_q(install_dir)}
    REPO_URL=https://github.com/FayaaDev/Rakkib.git
    BRANCH=MacSupport
    UPDATE_MODE=reset
    PATH={_q(fakebin)}:$PATH
    git_path() {{ printf '/usr/bin/git\n'; }}
    command_exists() {{
      case "$1" in
        git|curl|tar|xcode-select) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    prepare_repo
    test -f "$INSTALL_DIR/.rakkib-archive-install"
    test -f "$INSTALL_DIR/pyproject.toml"
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_macos_python_fallback_installs_python_org_pkg(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()

    _write_executable(
        fakebin / "curl",
        """
        #!/usr/bin/env bash
        out=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -o) out="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        printf 'pkg' > "$out"
        """,
    )
    _write_executable(
        fakebin / "shasum",
        """
        #!/usr/bin/env bash
        printf '%s  %s\n' "$MAC_PYTHON_SHA256" "${@: -1}"
        """,
    )
    _write_executable(
        fakebin / "sudo",
        """
        #!/usr/bin/env bash
        exec "$@"
        """,
    )
    _write_executable(
        fakebin / "installer",
        f"""
        #!/usr/bin/env bash
        cat > {_q(fakebin / 'python3')} <<'PY'
        #!/usr/bin/env bash
        exit 0
        PY
        chmod +x {_q(fakebin / 'python3')}
        """,
    )

    script = f"""
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    export MAC_PYTHON_SHA256
    PLATFORM=mac
    PATH={_q(fakebin)}:/usr/bin:/bin
    command_exists() {{
      case "$1" in
        python3) [[ -x {_q(fakebin / 'python3')} ]] ;;
        apt-get|dnf|pacman|brew|sha256sum) return 1 ;;
        curl|shasum|sudo|installer) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }}
    ensure_python3_and_venv
    [[ "$PYTHON_CMD" == {_q(fakebin / 'python3')} ]]
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout


def test_macos_tooling_allows_missing_git_when_archive_tools_exist(tmp_path: Path):
    script = """
    set -euo pipefail
    export RAKKIB_INSTALL_TEST_MODE=1
    source ./install.sh
    PLATFORM=mac
    command_exists() {
      case "$1" in
        git) return 1 ;;
        curl|tar) return 0 ;;
        *) command -v "$1" >/dev/null 2>&1 ;;
      esac
    }
    ensure_tooling
    """

    result = _run_install_script(script, tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
