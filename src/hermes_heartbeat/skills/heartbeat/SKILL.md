---
name: heartbeat
description: "Heartbeat system — periodic background checks that report only when something's interesting"
---

# Heartbeat Plugin

The heartbeat plugin runs a background timer that periodically checks the environment. When something interesting is found, it injects a context alert into the next conversation turn.

**Off by default.** The plugin loads and registers the tools, but nothing runs until you explicitly enable it.

## Tools

- `heartbeat_configure` — set interval (ms) and enable/disable. Pass `enabled: true` to start.
- `heartbeat_status` — check current status
- `heartbeat_now` — fire an immediate heartbeat

## CLI

```bash
# Check status (off by default)
hermes heartbeat status

# Enable with 30min interval
hermes heartbeat start
hermes heartbeat configure --interval_ms 1800000

# Stop
hermes heartbeat stop

# Fire immediately
hermes heartbeat now
```

## Cron Pairing

For periodic wake-ups even when not actively chatting:

```bash
hermes cron create "every 30m" "Run heartbeat check. If nothing interesting, reply [SILENT]." --skill heartbeat
```

## How It Works

1. Plugin loads tools — **engine is off by default**
2. You explicitly enable: `heartbeat_configure(enabled=true)` or `hermes heartbeat start`
3. Background timer fires on the configured interval
4. Runs a check function (extensible via `set_check_fn()`)
5. If interesting → writes a pending alert file
6. Next time you message → `pre_llm_call` hook injects the alert context
7. Cron pairing → silent delivery when nothing's interesting (via `[SILENT]`)
