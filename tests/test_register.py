"""Tests that register() wires everything correctly."""

from __future__ import annotations

import pathlib

import hermes_heartbeat as plugin


class FakeCtx:
    def __init__(self) -> None:
        self.tools: list[dict] = []
        self.cli: list[dict] = []
        self.hooks: list[dict] = []
        self.skills: list[dict] = []

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)

    def register_cli_command(self, **kwargs) -> None:
        self.cli.append(kwargs)

    def register_hook(self, name, handler) -> None:
        self.hooks.append({"name": name, "handler": handler})

    def register_skill(self, name, path, description="") -> None:
        self.skills.append({"name": name, "path": path, "description": description})


def test_register_wires_three_tools_and_cli_and_hooks_and_skill() -> None:
    ctx = FakeCtx()
    plugin.register(ctx)

    # 3 tools
    names = {t["name"] for t in ctx.tools}
    assert names == {"heartbeat_configure", "heartbeat_status", "heartbeat_now"}
    assert all(t["toolset"] == "hermes_heartbeat" for t in ctx.tools)
    assert all(callable(t["handler"]) for t in ctx.tools)

    # 1 CLI command
    assert len(ctx.cli) == 1
    cmd = ctx.cli[0]
    assert cmd["name"] == "heartbeat"
    assert callable(cmd["setup_fn"])
    assert callable(cmd["handler_fn"])

    # 3 hooks
    assert len(ctx.hooks) == 3
    hook_names = {h["name"] for h in ctx.hooks}
    assert hook_names == {"pre_llm_call", "on_session_start", "on_session_end"}
    assert all(callable(h["handler"]) for h in ctx.hooks)

    # 1 skill
    assert len(ctx.skills) == 1
    skill = ctx.skills[0]
    assert skill["name"] == "heartbeat"
    assert str(skill["path"]).endswith("skills/heartbeat/SKILL.md")
    assert pathlib.Path(skill["path"]).is_file()
    assert isinstance(skill["description"], str) and skill["description"]
