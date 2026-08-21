"""Heartbeat standalone plugin for Hermes Agent.

register(ctx) registers 3 tools into the ``hermes_heartbeat`` toolset, 3
lifecycle hooks, and a top-level ``hermes heartbeat`` CLI command. Discovered
via the ``hermes_agent.plugins`` entry point; enable with
``hermes plugins enable hermes_heartbeat``.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from hermes_heartbeat.heartbeat import HeartbeatEngine
from hermes_heartbeat.tools import (
    HEARTBEAT_CONFIGURE,
    HEARTBEAT_NOW,
    HEARTBEAT_STATUS,
    _handle_configure,
    _handle_now,
    _handle_status,
)

logger = logging.getLogger("plugins.hermes_heartbeat")
_SKILL = pathlib.Path(__file__).parent / "skills" / "heartbeat" / "SKILL.md"

_TOOLS: tuple[tuple[str, dict[str, Any], Any, str], ...] = (
    ("heartbeat_configure", HEARTBEAT_CONFIGURE, _handle_configure, "⚙️"),
    ("heartbeat_status", HEARTBEAT_STATUS, _handle_status, "❤️"),
    ("heartbeat_now", HEARTBEAT_NOW, _handle_now, "🔔"),
)


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def _on_pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    """Inject pending heartbeat alerts into the next conversation turn."""
    from hermes_heartbeat.heartbeat import HEARTBEAT_HOME as _hb_home
    alert_file = _hb_home / "pending_alert.json"
    if not alert_file.exists():
        return None
    try:
        alert = json.loads(alert_file.read_text())
        if alert.get("dismissed", False):
            return None
        text = f"[Heartbeat Alert]\n{alert.get('summary', 'Something needs attention')}\n"
        if alert.get("details"):
            text += "Details:\n" + "\n".join(f"- {item}" for item in alert["details"])
        alert["dismissed"] = True
        alert_file.write_text(json.dumps(alert))
        return {"context": text}
    except Exception as exc:
        logger.error("pre_llm_call heartbeat error: %s", exc)
        return None


def _on_session_start(session_id: str | None = None, **kwargs: Any) -> None:
    """Heartbeat is off by default; no auto-start."""


def _on_session_end(**kwargs: Any) -> None:
    """Stop the heartbeat timer when the session ends."""
    engine = HeartbeatEngine.get_instance()
    if engine._running:
        engine.stop()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Register the heartbeat plugin with Hermes."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="hermes_heartbeat",
            schema=schema,
            handler=handler,
            emoji=emoji,
        )

    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)

    from hermes_heartbeat.cli import heartbeat_command, setup_cli

    ctx.register_cli_command(
        name="heartbeat",
        help="Manage the background heartbeat timer",
        setup_fn=setup_cli,
        handler_fn=heartbeat_command,
        description=(
            "Background heartbeat timer that periodically checks the environment "
            "and reports only when something interesting is found. Off by default. "
            "Actions: status, start, stop, configure, now."
        ),
    )

    if _SKILL.is_file():
        ctx.register_skill(
            "heartbeat",
            str(_SKILL),
            description="Background heartbeat timer — periodic checks that report only when interesting.",
        )
