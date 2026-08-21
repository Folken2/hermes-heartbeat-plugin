# hermes-heartbeat-plugin

Background heartbeat timer for the [Hermes Agent](https://github.com/NousResearch/hermes-agent),
distributed as a standalone plugin.

It runs a configurable background timer that periodically checks the environment
and reports back **only when something interesting is found** — otherwise it stays
silent. The heartbeat is **off by default**; you enable it explicitly when you want it.

> Hermes' contribution guidelines ask that third-party product integrations ship
> as their own repositories rather than being merged into the core tree. This
> project follows that guidance: it is installed alongside Hermes and loaded via
> the `hermes_agent.plugins` entry point.

## Requirements

- Hermes Agent installed and importable in the same Python environment.
- Python 3.11–3.13.

## Installation

Install the package into the same environment as Hermes:

```bash
pip install hermes-heartbeat
```

Standalone plugins are opt-in, so enable it once:

```bash
hermes plugins enable hermes_heartbeat
```

## Usage

The heartbeat is **off by default**. Enable it when you want it:

```bash
# Check status
hermes heartbeat status

# Enable with 30-minute interval
hermes heartbeat start
# or with a custom interval:
hermes heartbeat configure --interval_ms 1800000

# Fire an immediate check
hermes heartbeat now

# Disable when done
hermes heartbeat stop
```

The agent can also manage the heartbeat directly through conversation:

> "Enable the heartbeat every 30 minutes and tell me if anything interesting happens."

Or pair it with a cron job for autonomous wake-ups:

```bash
hermes cron create "every 30m" "Run heartbeat check. If nothing interesting, reply [SILENT]." --skill heartbeat
```

The `[SILENT]` prefix suppresses delivery entirely — you only get a message when
something genuinely needs attention.

## How it works

1. A background `threading.Timer` fires on the configured interval
2. Runs a pluggable check function (extensible via `set_check_fn()`)
3. If interesting → writes a pending alert to `~/.hermes/heartbeat/pending_alert.json`
4. The `pre_llm_call` hook injects the alert context into the next conversation turn
5. If nothing's interesting → stays silent, no context injected

## Tools

| Tool | What it does |
|------|-------------|
| `heartbeat_configure` | Set interval (ms) and enable/disable the heartbeat |
| `heartbeat_status` | Show current status (running, interval, last beat, beat count) |
| `heartbeat_now` | Trigger an immediate heartbeat check |

## Hooks

| Hook | Purpose |
|------|---------|
| `pre_llm_call` | Injects pending heartbeat alerts into the conversation |
| `on_session_start` | Registers the engine with the session ID (does NOT auto-start) |
| `on_session_end` | Stops the heartbeat timer when the session ends |

## Skill

The plugin ships a Hermes skill, `heartbeat`, that documents the plugin's
usage and cron-pairing pattern. It auto-surfaces when the plugin is enabled.

## Development

```bash
git clone https://github.com/Folken2/hermes-heartbeat-plugin
cd hermes-heartbeat-plugin
pip install -e ".[dev]"      # into an environment that also has hermes-agent
pytest
```

## License

MIT License. Copyright (c) 2026 Albert Folch. See [LICENSE](LICENSE).
