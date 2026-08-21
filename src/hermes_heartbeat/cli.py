"""Top-level `hermes heartbeat` command."""

from __future__ import annotations

import argparse
import json
import threading

from hermes_heartbeat.heartbeat import HeartbeatEngine


def setup_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "hb_action",
        nargs="?",
        choices=["status", "start", "stop", "configure", "now"],
        default="status",
        help="Action to perform (default: status)",
    )
    parser.add_argument(
        "--interval-ms",
        dest="interval_ms",
        type=int,
        default=1800000,
        help="Heartbeat interval in milliseconds (default: 1800000 = 30 min)",
    )


def heartbeat_command(args) -> int:
    engine = HeartbeatEngine.get_instance()
    action = str(getattr(args, "hb_action", "") or "status").strip().lower()

    if action == "status":
        print(json.dumps(engine.get_status(), indent=2))
        return 0

    if action == "start":
        engine.start()
        print("Heartbeat started")
        return 0

    if action == "stop":
        engine.stop()
        print("Heartbeat stopped")
        return 0

    if action == "configure":
        ms = int(getattr(args, "interval_ms", 1800000))
        engine.configure(interval_ms=ms)
        print(f"Configured: interval={HeartbeatEngine._format_interval(ms)}")
        return 0

    if action == "now":
        threading.Thread(target=engine._fire, daemon=True).start()
        print("Heartbeat fired")
        return 0

    print("Usage: hermes heartbeat [status|start|stop|configure|now]")
    return 1
