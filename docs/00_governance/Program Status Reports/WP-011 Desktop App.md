---
type: work-package
id: WP-011
date: 2026-07-14
status: complete
phase: ui-slice (ADR-036; local app layer, precursor to Phase 9)
---

# WP-011 — QuantOS Desktop (Local App: Accounts, Dashboard, Orders)

## Objective

Operator direction: the system as a desktop app — connect broker
accounts, see the dashboard, the orders, everything required. Built
per ADR-036: FastAPI + uvicorn (already-locked deps) on 127.0.0.1:8742,
one vanilla HTML/JS page, opened chromeless via Edge `--app` — no
Electron, no new toolchains.

## Delivered

- **`api/collectors.py`** — shared read models (paper state, kill
  switch, strategy registry, pinned equity curve, PIT universe,
  journal, project state); consumed by BOTH the desktop app and the
  WP-010 static console (one source of truth, two surfaces).
- **`api/server.py`** — local-only FastAPI: `/api/state`, broker
  connect/disconnect/status, Zerodha login-URL + request-token
  exchange, and the single write control `/api/killswitch`
  (reason mandatory). Broker credentials: in-memory only, never
  persisted/logged/echoed.
- **`quantos_core/brokers/zerodha.py`** — `kite_login_url()` +
  `exchange_request_token()` (Kite v3 daily flow, sha256 checksum;
  fail-closed, secret used transiently).
- **`api/app.html`** — five surfaces: Overview (derived state tiles,
  paper account, interactive equity chart), **Brokers** (guided
  Zerodha 2-step connect, Angel TOTP connect — both read-only account
  verification), Orders (live holdings when connected + append-only
  journal), Strategy (registry + PIT snapshots), System (kill switch
  with confirm + reason, runbook). Halt state tints the whole app red.
- **`tools/desktop_app.py`** launcher + `tools/create_desktop_shortcut.ps1`
  (Desktop "QuantOS.lnk").
- Dependencies pinned: `fastapi==0.136.3`, `uvicorn==0.49.0` (+
  starlette/httpx in the lock closure) — previously transitive.

## Live verification (real browser, running server)

- Zero console errors; Overview/Brokers/System screenshotted and
  eyeballed; state payload current (that day's scheduled run visible).
- **Kill-switch drill through the actual UI**: engage → whole app
  turned red, pill HALTED → cross-checked via the CLI (`ENGAGED`) →
  released via UI → CLI confirms released. UI and CLI agree on one
  persisted truth.
- Two defects found by the drill and fixed immediately: a selector
  that could hit a hidden button (scoped), and FastAPI validation
  errors rendering as `[object Object]` (now human-readable, e.g.
  "api_key: String should have at least 1 character").

## Gates

| Gate | Result |
|---|---|
| `ruff` / `format` | Clean |
| `mypy --strict -p quantos_core` | 39 files, clean |
| `pytest -m "not network"` | **188 passed** (10 new: endpoint tests via TestClient, token-exchange checksum, fail-closed blanks) |
| Static console | Still builds from the shared collectors |
| Six frozen scripts / determinism | Untouched / baseline unchanged |

## Notes

- Order placement is deliberately absent from the UI (ADR-036): the
  strategy pipeline is the only order source; a manual-order button
  would be a second, ungated path to the broker.
- WP numbering: the portfolio module shifts to WP-012, run_cycle to
  WP-013 (operator reprioritized UI first).

## Next

Operator: `.\tools\create_desktop_shortcut.ps1` once, then launch
QuantOS from the Desktop. Create the Zerodha key this week and connect
it on the Brokers tab. Engineering: WP-012 portfolio module (the
automation loop the operator ratified).
