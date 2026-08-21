"""Heartbeat engine — background timer that periodically checks state."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("plugins.hermes_heartbeat")

HEARTBEAT_HOME = Path.home() / ".hermes" / "heartbeat"
STATE_FILE = HEARTBEAT_HOME / "state.json"
HISTORY_FILE = HEARTBEAT_HOME / "history.jsonl"


class HeartbeatEngine:
    """Background heartbeat engine. Runs a timer thread that fires on interval."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._timer: threading.Timer | None = None
        self._running = False
        self._interval_ms = 1800000  # 30 min default
        self._check_fn = None
        self._last_beat: str | None = None
        self._beat_count = 0
        self._session_id: str | None = None
        HEARTBEAT_HOME.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> HeartbeatEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def configure(self, interval_ms: int = 1800000) -> None:
        """Configure heartbeat interval (clamped 1 min – 24 h)."""
        self._interval_ms = max(60000, min(interval_ms, 86400000))
        self._save_state()
        if self._running:
            self.stop()
            self.start()

    def start(self, session_id: str | None = None) -> None:
        """Start the heartbeat timer."""
        if session_id:
            self._session_id = session_id
        if self._running:
            return
        self._running = True
        self._last_beat = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._schedule_next()
        logger.info("Heartbeat started: interval=%dms", self._interval_ms)

    def stop(self) -> None:
        """Stop the heartbeat timer."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._save_state()
        logger.info("Heartbeat stopped")

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._interval_ms / 1000.0, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self) -> None:
        """Fired when the heartbeat interval elapses."""
        if not self._running:
            return
        try:
            self._beat_count += 1
            self._last_beat = datetime.now(timezone.utc).isoformat()
            result = self._run_check()
            self._record_beat(result)
            self._save_state()
            if result and result.get("interesting"):
                self._on_interesting(result)
        except Exception as exc:
            logger.error("Heartbeat error: %s", exc)
        finally:
            if self._running:
                self._schedule_next()

    def _run_check(self) -> dict:
        """Run the heartbeat check. Override via set_check_fn()."""
        findings: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "interesting": False,
            "items": [],
        }
        if self._check_fn:
            try:
                custom = self._check_fn()
                if custom:
                    findings.update(custom)
            except Exception as exc:
                logger.error("Check fn error: %s", exc)
        return findings

    def _on_interesting(self, result: dict) -> None:
        """Write a pending alert for the pre_llm_call hook to inject."""
        alert_file = HEARTBEAT_HOME / "pending_alert.json"
        alert_file.write_text(
            json.dumps({
                "timestamp": result.get("timestamp"),
                "summary": result.get("summary", "Something needs attention"),
                "details": result.get("items", []),
                "dismissed": False,
            })
        )

    def _record_beat(self, result: dict) -> None:
        """Record a heartbeat to the history log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "beat_number": self._beat_count,
            "interval_ms": self._interval_ms,
            "interesting": result.get("interesting", False),
            "summary": result.get("summary", ""),
            "item_count": len(result.get("items", [])),
        }
        with open(HISTORY_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _save_state(self) -> None:
        """Persist current state to disk."""
        state = {
            "running": self._running,
            "interval_ms": self._interval_ms,
            "last_beat": self._last_beat,
            "beat_count": self._beat_count,
            "session_id": self._session_id,
        }
        STATE_FILE.write_text(json.dumps(state, indent=2))

    def get_status(self) -> dict:
        """Return current heartbeat status."""
        return {
            "running": self._running,
            "interval_ms": self._interval_ms,
            "interval_display": self._format_interval(self._interval_ms),
            "last_beat": self._last_beat,
            "beat_count": self._beat_count,
            "session_id": self._session_id,
        }

    def set_check_fn(self, fn) -> None:
        """Set a custom check function. fn() should return a dict."""
        self._check_fn = fn

    @staticmethod
    def _format_interval(ms: int) -> str:
        s = ms / 1000
        if s < 60:
            return f"{int(s)}s"
        if s < 3600:
            return f"{int(s / 60)}m"
        return f"{int(s / 3600)}h{int((s % 3600) / 60)}m"
