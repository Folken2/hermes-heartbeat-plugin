"""Heartbeat tool schemas and handlers."""

from __future__ import annotations

import json
import threading
from typing import Any

from hermes_heartbeat.heartbeat import HeartbeatEngine

HEARTBEAT_CONFIGURE = {
    "name": "heartbeat_configure",
    "description": (
        "Configure the heartbeat interval. The heartbeat runs as a background "
        "timer that periodically checks the environment and reports anything "
        "interesting. Use this to set how often the heartbeat fires and whether "
        "it is enabled."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "interval_ms": {
                "type": "integer",
                "description": (
                    "Interval in milliseconds between heartbeats "
                    "(min: 60000 = 1 min, max: 86400000 = 24 h, default: 1800000 = 30 min)"
                ),
                "default": 1800000,
            },
            "enabled": {
                "type": "boolean",
                "description": "Whether to enable the heartbeat (default: True)",
                "default": True,
            },
        },
    },
}

HEARTBEAT_STATUS = {
    "name": "heartbeat_status",
    "description": (
        "Get the current status of the heartbeat system — whether it is running, "
        "the configured interval, the last beat time, and the total beat count."
    ),
    "parameters": {"type": "object", "properties": {}},
}

HEARTBEAT_NOW = {
    "name": "heartbeat_now",
    "description": (
        "Trigger an immediate heartbeat check — run the check logic now and "
        "report anything interesting. Use this to force an on-demand heartbeat "
        "without waiting for the next scheduled interval."
    ),
    "parameters": {"type": "object", "properties": {}},
}

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_configure(args: dict[str, Any], **kwargs: Any) -> str:
    engine = HeartbeatEngine.get_instance()
    interval_ms = int(args.get("interval_ms", 1800000))
    enabled = bool(args.get("enabled", True))
    if enabled:
        engine.configure(interval_ms=interval_ms)
        engine.start()
    else:
        engine.stop()
    return json.dumps({"success": True, "status": engine.get_status()})


def _handle_status(args: dict[str, Any], **kwargs: Any) -> str:
    engine = HeartbeatEngine.get_instance()
    return json.dumps({"success": True, "status": engine.get_status()})


def _handle_now(args: dict[str, Any], **kwargs: Any) -> str:
    engine = HeartbeatEngine.get_instance()

    def _fire() -> None:
        try:
            result = engine._run_check()
            engine._record_beat(result)
            if result.get("interesting"):
                engine._on_interesting(result)
        except Exception as exc:
            import logging
            logging.getLogger("plugins.hermes_heartbeat").error(
                "heartbeat_now error: %s", exc
            )

    threading.Thread(target=_fire, daemon=True).start()
    return json.dumps({
        "success": True,
        "message": "Heartbeat fired. Check status for results.",
        "status": engine.get_status(),
    })
