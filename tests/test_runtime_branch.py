from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "runtime-branch.sh"
RUNTIME_README = """# Rakkib - runtime branch

This branch is the slim install snapshot used by the public installer.

Allowed paths:
- `.gitignore`
- `README.md`
- `install.sh`
- `pyproject.toml`
- `src/rakkib/**`

Do not develop on this branch. Land changes on `main`, then regenerate `runtime`
with `scripts/runtime-branch.sh sync --push`.
"""


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _commit_all(repo: Path, message: str) -> None:
    env = os.environ | {
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    _run(["git", "add", "-A"], repo)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def _write_main_tree(repo: Path) -> None:
    (repo / "src" / "rakkib").mkdir(parents=True)
    (repo / ".gitignore").write_text(".venv/\n")
    (repo / "README.md").write_text("dev readme\n")
    (repo / "install.sh").write_text("#!/usr/bin/env bash\n")
    (repo / "pyproject.toml").write_text("[project]\nname = \"rakkib\"\n")
    (repo / "src" / "rakkib" / "__init__.py").write_text('__version__ = "0.0.0"\n')


def _create_runtime_branch(repo: Path, *, extra_path: str | None = None) -> None:
    assert _run(["git", "checkout", "--orphan", "runtime"], repo).returncode == 0
    for entry in repo.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()

    _write_main_tree(repo)
    (repo / "README.md").write_text(RUNTIME_README)
    if extra_path:
        extra = repo / extra_path
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("not allowed\n")
    _commit_all(repo, "runtime snapshot")


def test_runtime_branch_verify_ref_accepts_allowlisted_snapshot(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    assert _run(["git", "init", "-b", "main"], repo).returncode == 0
    _write_main_tree(repo)
    _commit_all(repo, "main snapshot")
    _create_runtime_branch(repo)

    result = _run(["bash", str(SCRIPT), "verify-ref", "--main-ref", "main", "--runtime-ref", "runtime"], repo)

    assert result.returncode == 0, result.stderr
    assert "matches the runtime allowlist" in result.stdout


def test_runtime_branch_verify_ref_rejects_disallowed_paths(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    assert _run(["git", "init", "-b", "main"], repo).returncode == 0
    _write_main_tree(repo)
    _commit_all(repo, "main snapshot")
    _create_runtime_branch(repo, extra_path="tests/test_cli.py")

    result = _run(["bash", str(SCRIPT), "verify-ref", "--main-ref", "main", "--runtime-ref", "runtime"], repo)

    assert result.returncode != 0
    assert "contains disallowed paths" in result.stderr
    assert "tests/test_cli.py" in result.stderr
