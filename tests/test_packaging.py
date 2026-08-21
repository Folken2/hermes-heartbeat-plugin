"""Tests for packaging and entry points."""

from __future__ import annotations

import importlib.metadata as md


def test_entry_point_registered() -> None:
    eps = md.entry_points()
    group = eps.select(group="hermes_agent.plugins") if hasattr(eps, "select") else eps.get("hermes_agent.plugins", [])
    names = {ep.name: ep.value for ep in group}
    assert names.get("hermes_heartbeat") == "hermes_heartbeat"


def test_register_is_callable() -> None:
    import hermes_heartbeat
    assert callable(hermes_heartbeat.register)
