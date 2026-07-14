---
type: adr
number: 036
date: 2026-07-14
status: accepted
supersedes: none
---

# ADR-036 — Desktop App as Local FastAPI + Edge App Window (WP-011)

## Decision

QuantOS Desktop is a **local web app**: FastAPI + uvicorn (both
already in the locked environment) bound to `127.0.0.1:8742`, serving
one vanilla-HTML/JS page, opened in a chromeless Edge `--app=` window
by `tools/desktop_app.py` (desktop shortcut via
`tools/create_desktop_shortcut.ps1`). No Electron, no Tauri, no
Node/Rust toolchain, no packaging step.

Surfaces: Overview (derived system state, paper account, equity
chart), **Brokers** (connect Zerodha via the daily request-token
exchange, connect Angel One via TOTP — both verified read-only against
the real account), Orders (live holdings when connected + the
append-only journal), Strategy (registry + PIT snapshots), System
(kill switch + runbook).

## Constitutional position

- `api` binds local-only — exactly the Part III/Security default.
- ADR-028 permits exactly one write surface: the kill switch. The app
  exposes precisely that (`POST /api/killswitch`, reason mandatory);
  everything else is read-only. Order placement stays OUT of the UI —
  orders come from the strategy pipeline, never from a button.
- Broker credential policy (Part III/Secrets): secrets transit request
  bodies over loopback, live in process memory for the app's lifetime,
  are never persisted, logged, or echoed. Kite access tokens expire
  daily regardless. Upgrade path: Windows Credential Manager
  integration, its own ADR when wanted.
- ADR-035's static console remains — the scheduled daily run keeps
  generating it; both surfaces consume the same `api/collectors.py`
  read models (one source of truth, two renderings).

## Alternatives rejected

- **Electron/Tauri**: hundreds of MB of toolchain for a solo local
  tool; violates infrastructure minimalism (Part I).
- **pywebview**: new dependency for what Edge `--app` (present on
  every Windows 11 machine) already provides.
- **Buttons that trade**: rejected outright — the Constitution's
  pipeline is the only order source; a manual-order UI would create a
  second, ungated path to the broker.

## Consequences

- `tools/` remains a leaf: it imports `api`, never the reverse.
- The WP-005 boundary gate is unaffected (it polices `quantos_core`
  internals; `api` imports only `quantos_core` public surfaces).
- fastapi/uvicorn move from transitive-installed to pinned runtime
  dependencies of the project.
