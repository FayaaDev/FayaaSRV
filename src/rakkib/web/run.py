"""Background setup runner for the browser UI."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 form."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class RunRecord:
    """Current browser-triggered setup run state."""

    status: str = "idle"
    message: str = "No setup run has started yet."
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    command: list[str] = field(default_factory=list)
    log_path: str | None = None
    pid: int | None = None


class WebRunManager:
    """Manage one background `rakkib pull` process for the web UI."""

    def __init__(self, repo_dir: Path | str) -> None:
        self._repo_dir = Path(repo_dir)
        self._log_path = self._repo_dir / ".rakkib-web-run.log"
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._record = RunRecord(log_path=str(self._log_path))

    def start(self) -> dict[str, object]:
        """Start the setup run unless one is already active."""
        with self._lock:
            self._refresh_locked()
            if self._process is not None:
                return self._snapshot_locked()

            command = [sys.executable, "-m", "rakkib.cli", "pull"]
            started_at = _now_iso()
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = self._log_path.open("w", encoding="utf-8")
            log_handle.write(f"[{started_at}] Starting browser-triggered setup run\n")
            log_handle.write(f"$ {' '.join(shlex.quote(part) for part in command)}\n\n")
            log_handle.flush()

            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            try:
                process = subprocess.Popen(
                    command,
                    cwd=self._repo_dir,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                )
            except Exception as exc:
                message = f"Unable to start setup run: {exc}"
                log_handle.write(f"[{_now_iso()}] {message}\n")
                log_handle.close()
                self._record = RunRecord(
                    status="failed",
                    message=message,
                    started_at=started_at,
                    finished_at=_now_iso(),
                    exit_code=None,
                    command=command,
                    log_path=str(self._log_path),
                )
                raise RuntimeError(message) from exc

            self._process = process
            self._record = RunRecord(
                status="running",
                message="Setup run is in progress.",
                started_at=started_at,
                finished_at=None,
                exit_code=None,
                command=command,
                log_path=str(self._log_path),
                pid=process.pid,
            )

            watcher = threading.Thread(target=self._watch_process, args=(process, log_handle), daemon=True)
            watcher.start()
            return self._snapshot_locked()

    def snapshot(self) -> dict[str, object]:
        """Return the current run status plus a log tail."""
        with self._lock:
            self._refresh_locked()
            return self._snapshot_locked()

    def _watch_process(self, process: subprocess.Popen[str], log_handle) -> None:
        """Wait for the child process and persist the final status."""
        exit_code = process.wait()
        finished_at = _now_iso()
        status = "succeeded" if exit_code == 0 else "failed"
        message = "Setup run completed successfully." if exit_code == 0 else "Setup run exited with errors."

        try:
            log_handle.write(f"\n[{finished_at}] Setup run finished with exit code {exit_code}\n")
            log_handle.flush()
        finally:
            log_handle.close()

        with self._lock:
            if self._process is process:
                self._process = None
                self._record = RunRecord(
                    status=status,
                    message=message,
                    started_at=self._record.started_at,
                    finished_at=finished_at,
                    exit_code=exit_code,
                    command=list(self._record.command),
                    log_path=str(self._log_path),
                    pid=None,
                )

    def _refresh_locked(self) -> None:
        """Synchronize the stored record if the child exited between polls."""
        if self._process is None:
            return

        exit_code = self._process.poll()
        if exit_code is None:
            return

        finished_at = _now_iso()
        status = "succeeded" if exit_code == 0 else "failed"
        message = "Setup run completed successfully." if exit_code == 0 else "Setup run exited with errors."
        self._process = None
        self._record = RunRecord(
            status=status,
            message=message,
            started_at=self._record.started_at,
            finished_at=finished_at,
            exit_code=exit_code,
            command=list(self._record.command),
            log_path=str(self._log_path),
            pid=None,
        )

    def _snapshot_locked(self) -> dict[str, object]:
        """Build the API payload for the current run."""
        return {
            "status": self._record.status,
            "message": self._record.message,
            "started_at": self._record.started_at,
            "finished_at": self._record.finished_at,
            "exit_code": self._record.exit_code,
            "command": list(self._record.command),
            "log_path": self._record.log_path,
            "pid": self._record.pid,
            "running": self._record.status == "running",
            "can_start": self._record.status != "running",
            "log_tail": self._read_log_tail(),
        }

    def _read_log_tail(self, limit: int = 200) -> list[str]:
        """Return the last N lines from the current log file."""
        if not self._log_path.exists():
            return []

        with self._log_path.open("r", encoding="utf-8", errors="replace") as handle:
            return list(deque((line.rstrip("\n") for line in handle), maxlen=limit))
