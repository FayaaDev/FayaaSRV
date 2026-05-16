from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish-runtime-repo.sh"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _commit_all(repo: Path, message: str) -> None:
    env = os.environ | {
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    assert _run(["git", "add", "-A"], repo).returncode == 0
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def _write_source_tree(repo: Path) -> None:
    (repo / "docs" / "public").mkdir(parents=True)
    (repo / "src" / "rakkib").mkdir(parents=True)
    (repo / ".gitignore").write_text(".venv/\n")
    (repo / "README.md").write_text("private dev readme\n")
    (repo / "docs" / "public" / "README.md").write_text("# Public Runtime\n")
    (repo / "LICENSE").write_text("MIT License\n")
    (repo / "install.sh").write_text("#!/usr/bin/env bash\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "rakkib"\n')
    (repo / "src" / "rakkib" / "__init__.py").write_text('__version__ = "0.0.0"\n')
    (repo / "tests").mkdir()
    (repo / "tests" / "internal_test.py").write_text("not public\n")


def test_publish_runtime_repo_syncs_allowlisted_public_snapshot(tmp_path: Path):
    source = tmp_path / "source"
    public_bare = tmp_path / "public.git"
    public_clone = tmp_path / "public-clone"
    source.mkdir()

    assert _run(["git", "init", "-b", "main"], source).returncode == 0
    _write_source_tree(source)
    _commit_all(source, "source snapshot")
    source_sha = _run(["git", "rev-parse", "HEAD"], source).stdout.strip()
    short_sha = _run(["git", "rev-parse", "--short", "HEAD"], source).stdout.strip()

    assert _run(["git", "init", "--bare", str(public_bare)], tmp_path).returncode == 0

    result = _run(
        ["bash", str(SCRIPT), "sync", "--public-repo", str(public_bare), "--push"],
        source,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert _run(["git", "clone", "--branch", "main", str(public_bare), str(public_clone)], tmp_path).returncode == 0

    files = _run(["git", "ls-files"], public_clone).stdout.splitlines()
    assert files == [
        ".gitignore",
        "LICENSE",
        "README.md",
        "install.sh",
        "pyproject.toml",
        "src/rakkib/__init__.py",
    ]
    assert (public_clone / "README.md").read_text() == "# Public Runtime\n"
    assert not (public_clone / "tests" / "internal_test.py").exists()

    log = _run(["git", "log", "-1", "--format=%s%n%b"], public_clone).stdout
    assert f"Publish runtime from {short_sha}" in log
    assert f"Source: FayaaDev/rakkib-dev@{source_sha}" in log


def test_publish_runtime_repo_verify_rejects_disallowed_public_files(tmp_path: Path):
    source = tmp_path / "source"
    public = tmp_path / "public"
    source.mkdir()
    public.mkdir()

    assert _run(["git", "init", "-b", "main"], source).returncode == 0
    _write_source_tree(source)
    _commit_all(source, "source snapshot")

    assert _run(["git", "init", "-b", "main"], public).returncode == 0
    (public / "src" / "rakkib").mkdir(parents=True)
    (public / ".gitignore").write_text(".venv/\n")
    (public / "README.md").write_text("# Public Runtime\n")
    (public / "LICENSE").write_text("MIT License\n")
    (public / "install.sh").write_text("#!/usr/bin/env bash\n")
    (public / "pyproject.toml").write_text('[project]\nname = "rakkib"\n')
    (public / "src" / "rakkib" / "__init__.py").write_text('__version__ = "0.0.0"\n')
    (public / "tests").mkdir()
    (public / "tests" / "internal_test.py").write_text("not public\n")
    _commit_all(public, "bad public snapshot")

    result = _run(
        ["bash", str(SCRIPT), "verify", "--source-ref", "main", "--public-dir", str(public)],
        source,
    )

    assert result.returncode != 0
    assert "contains disallowed paths" in result.stderr
    assert "tests/internal_test.py" in result.stderr
