"""Tests for state schema versioning, migration, and crash-safe save."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from rakkib.state import STATE_VERSION, State, _migrate


def test_migrate_empty_dict_is_passthrough():
    # Empty load must not synthesise a schema_version key.
    assert _migrate({}) == {}


def test_migrate_legacy_state_stamps_current_version():
    raw = {"foo": "bar"}
    out = _migrate(raw)
    assert out is raw
    assert out["schema_version"] == STATE_VERSION
    assert out["foo"] == "bar"


def test_migrate_already_current_is_idempotent():
    raw = {"schema_version": STATE_VERSION, "foo": "bar"}
    snapshot = dict(raw)
    out = _migrate(raw)
    assert out == snapshot


def test_migrate_future_version_raises():
    raw = {"schema_version": STATE_VERSION + 99, "foo": "bar"}
    with pytest.raises(RuntimeError, match="newer than this rakkib supports"):
        _migrate(raw)


def test_save_stamps_schema_version(tmp_path: Path):
    path = tmp_path / ".fss-state.yaml"
    State({"server_name": "rkb"}).save(path)
    on_disk = yaml.safe_load(path.read_text())
    assert on_disk["schema_version"] == STATE_VERSION
    assert on_disk["server_name"] == "rkb"


def test_load_legacy_state_upgrades_silently(tmp_path: Path):
    path = tmp_path / ".fss-state.yaml"
    # Pre-versioning rakkib wrote no schema_version field.
    path.write_text(yaml.safe_dump({"server_name": "legacy"}))

    loaded = State.load(path)

    assert loaded.get("server_name") == "legacy"
    assert loaded.get("schema_version") == STATE_VERSION


def test_load_future_version_refuses(tmp_path: Path):
    path = tmp_path / ".fss-state.yaml"
    path.write_text(yaml.safe_dump({"schema_version": STATE_VERSION + 5, "x": 1}))

    with pytest.raises(RuntimeError, match="newer than this rakkib supports"):
        State.load(path)


def test_save_fsyncs_file_and_parent_directory(tmp_path: Path):
    # Crash-safety: a power loss between the data write and the directory
    # entry being flushed must not lose the rename.
    path = tmp_path / ".fss-state.yaml"

    real_fsync = __import__("os").fsync
    calls: list[int] = []

    def tracking_fsync(fd: int) -> None:
        calls.append(fd)
        return real_fsync(fd)

    with patch("rakkib.state.os.fsync", side_effect=tracking_fsync):
        State({"foo": "bar"}).save(path)

    # Two fsyncs expected: one on the data file, one on the parent directory.
    assert len(calls) >= 2, f"expected at least two fsync calls, got {len(calls)}"


def test_save_does_not_leak_tmp_file_on_success(tmp_path: Path):
    path = tmp_path / ".fss-state.yaml"
    State({"foo": "bar"}).save(path)
    assert not (tmp_path / ".fss-state.yaml.tmp").exists()
    assert path.exists()


def test_save_round_trip_preserves_data(tmp_path: Path):
    path = tmp_path / ".fss-state.yaml"
    State({"server_name": "alpha", "selected_services": ["a", "b"]}).save(path)
    loaded = State.load(path)
    assert loaded.get("server_name") == "alpha"
    assert loaded.get("selected_services") == ["a", "b"]
