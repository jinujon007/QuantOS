"""QuantOS Operator Console generator (WP-010).

    python tools/build_dashboard.py [--open]

Reads the system's real artifacts -- paper account state, the strategy
registry, the pinned backtest equity curve, the PIT universe store,
the order journal, the production kill switch -- and writes ONE
self-contained, read-only HTML page to dashboard/index.html. No
server, no network, no build step: refresh = re-run this script.

Read-only by constitutional design (ADR-028): the single write
control, the kill switch, lives in tools/kill_switch.py, not in a
web page.
"""

import argparse
import html
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Collectors are shared with the desktop app (api/collectors.py) --
# one set of read models feeds both surfaces (WP-011).
from api.collectors import (  # noqa: E402
    REPO,
    collect_daily_run,
    collect_equity,
    collect_journal,
    collect_kill_switch,
    collect_paper_state,
    collect_project_state,
    collect_strategy,
    collect_universe,
)

# ── rendering ─────────────────────────────────────────────────────────────


def inr(value: float) -> str:
    """Indian-grouping rupee format: 583819 -> ₹5,83,819."""
    negative = value < 0
    digits = f"{abs(value):.0f}"
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return ("-₹" if negative else "₹") + digits


def outcome_tag(outcome: str) -> str:
    cls = {"FILLED": "fill", "OPEN": "wait", "BLOCKED": "block", "FAILED": "block", "UNKNOWN": "block"}.get(
        outcome, "wait"
    )
    return f'<span class="tag {cls}">{html.escape(outcome)}</span>'


def render(page: dict) -> str:
    template = (REPO / "dashboard" / "template.html").read_text(encoding="utf-8")
    for key, value in page.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def build_page() -> str:
    paper = collect_paper_state()
    switch = collect_kill_switch()
    strategy = collect_strategy()
    equity = collect_equity()
    universe = collect_universe()
    journal = collect_journal()
    state = collect_project_state()

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    phase = state.get("current_phase", {})
    metrics = state.get("metrics", {})

    # -- derived system state (one label, not raw flags) --
    halted = switch["engaged"]
    holdings = paper.get("holdings") or {}
    if halted:
        system_state, system_cls, system_note = "HALTED", "crit", "kill switch engaged — no order passes the gate"
    elif paper.get("available") and not holdings:
        system_state, system_cls, system_note = "ACTIVE — IN CASH", "wait", "paper mode · regime filter holding cash"
    else:
        system_state, system_cls, system_note = "ACTIVE — INVESTED", "ok", f"paper mode · {len(holdings)} positions"

    # -- last unattended run (data/daily_run.log) --
    run = collect_daily_run()
    if run.get("available"):
        run_status = str(run["status"])
        run_cls = {"OK": "ok", "HALTED": "wait", "DEGRADED": "crit", "INCOMPLETE": "crit"}.get(run_status, "wait")
        run_note = f"last unattended run · {html.escape(str(run.get('when', '')))}"
        failed_steps = [s["step"] for s in run.get("steps", []) if s["status"] != "OK"]
        if failed_steps:
            run_note = f"{html.escape(failed_steps[0])} · {html.escape(str(run.get('when', '')))}"
    else:
        run_status, run_cls, run_note = "NEVER RUN", "wait", "no daily_run.log yet — scheduled task hasn't fired"

    tiles = f"""
      <div class="cell state {system_cls}"><div class="v">{system_state}</div><div class="k">{system_note}</div></div>
      <div class="cell state {run_cls}"><div class="v">{run_status}</div><div class="k">{run_note}</div></div>
      <div class="cell"><div class="v">{inr(paper.get("portfolio_value", 0.0))}</div><div class="k">paper portfolio (virtual)</div></div>
      <div class="cell"><div class="v" data-age-of="{html.escape(str(paper.get("last_updated", "")))}" data-warn-hours="30" data-crit-hours="96">—</div><div class="k">paper state freshness</div></div>
      <div class="cell"><div class="v" data-age-of="{html.escape(universe[0]["date"] if universe else "")}" data-warn-hours="192" data-crit-hours="360">—</div><div class="k">universe snapshot freshness</div></div>"""

    # -- chips --
    switch_chip = (
        '<span class="chip crit">KILL SWITCH ENGAGED — trading blocked</span>'
        if halted
        else '<span class="chip ok">kill switch: not engaged</span>'
    )
    chips = f"""{switch_chip}
      <span class="chip">phase {html.escape(str(phase.get("number", "?")))}: <b>{html.escape(str(phase.get("name", "")))}</b></span>
      <span class="chip">strategy: <b>Momentum v{html.escape(strategy["version"])}, frozen</b></span>
      <span class="chip">tests: <b>{html.escape(str(metrics.get("test_count", "—")))}</b> · coverage <b>100%</b> (quantos_core)</span>"""

    # -- paper account --
    if paper.get("available"):
        holdings_note = (
            f"{len(holdings)} positions" if holdings else "no positions — regime filter holding 100% cash (bear market)"
        )
        paper_html = f"""
      <div class="proof">
        <div class="cell"><div class="v">{inr(paper["portfolio_value"])}</div><div class="k">portfolio value (virtual)</div></div>
        <div class="cell"><div class="v">{inr(paper["cash"])}</div><div class="k">cash</div></div>
        <div class="cell"><div class="v">{len(holdings)}</div><div class="k">open positions</div></div>
        <div class="cell"><div class="v">{html.escape(str(paper.get("last_updated", "—")))}</div><div class="k">last updated</div></div>
      </div>
      <p class="mut">Since {html.escape(str(paper.get("start_date", "?")))} · {holdings_note}. This account is the
      Prospective Validation record — run <code>python paper_trader.py</code> after 15:30 IST daily.</p>"""
    else:
        paper_html = '<p class="mut">paper_state.json not found — run paper_trader.py to initialize.</p>'

    # -- strategy --
    params = strategy["params"]
    strategy_html = f"""
      <table><thead><tr><th>Parameter</th><th class="r">Value</th></tr></thead><tbody>
      <tr><td>Universe</td><td class="r">Nifty 500 (point-in-time store)</td></tr>
      <tr><td>Momentum window</td><td class="r">{params["lookback_months"]}M − {params["skip_months"]}M</td></tr>
      <tr><td>Positions</td><td class="r">top {params["top_n"]}, equal weight</td></tr>
      <tr><td>Stop loss</td><td class="r">{params["stop_loss_pct"] * 100:.0f}% from entry</td></tr>
      <tr><td>Regime filter</td><td class="r">cash when Nifty &lt; {params["trend_ma_days"]}-day MA</td></tr>
      <tr><td>Rebalance</td><td class="r">weekly (Friday)</td></tr>
      </tbody></table>
      <p class="mut">Registry: <code>strategies_registry/momentum_v1.yaml</code> — the single source of truth.
      Editing any value is a new strategy version and <b>restarts the 13-week validation clock</b>.
      Signal math is parity-proven byte-equal to the frozen script.</p>"""

    # -- equity chart --
    if equity["available"]:
        stats_html = f"""
      <div class="proof">
        <div class="cell"><div class="v">{inr(equity["final"])}</div><div class="k">end value (from {inr(equity["initial"])})</div></div>
        <div class="cell"><div class="v">{equity["cagr"] * 100:.1f}%</div><div class="k">CAGR</div></div>
        <div class="cell"><div class="v">{equity["sharpe"]:.2f}</div><div class="k">Sharpe (weekly, ann.)</div></div>
        <div class="cell"><div class="v">{equity["max_dd"] * 100:.1f}%</div><div class="k">max drawdown</div></div>
      </div>"""
        chart_data = json.dumps(equity["points"])
        chart_html = f"""{stats_html}
      <div class="chartwrap"><svg id="equity" viewBox="0 0 900 320" role="img"
        aria-label="Backtest equity curve {equity["start"]} to {equity["end"]}"></svg>
        <div id="tip" class="tip" hidden></div></div>
      <p class="mut">Regime-filtered backtest, accurate Zerodha delivery cost model, {equity["start"]} → {equity["end"]},
      computed live from <code>data/results/equity_curve.csv</code> (the determinism-gated artifact, sha-pinned in CI).
      Past performance ≠ future results.</p>
      <script>const EQUITY = {chart_data};</script>"""
    else:
        chart_html = '<p class="mut">No equity curve found — run momentum_backtest.py.</p>'

    # -- journal --
    if journal:
        rows = "".join(
            f"<tr><td>{html.escape(e['id'])}</td><td>{html.escape(e['side'])} {e['quantity']} {html.escape(e['ticker'])}"
            f"</td><td class='r'>{e['limit_price']:,.2f}</td><td>{outcome_tag(e['outcome'])}</td></tr>"
            for e in journal
        )
        journal_html = f"""
      <div class="tablewrap"><table>
      <thead><tr><th>Journal ID</th><th>Order</th><th class="r">Limit ₹</th><th>Outcome</th></tr></thead>
      <tbody>{rows}</tbody></table></div>
      <p class="mut">Append-only: every attempt is recorded — filled, open, blocked, failed — from
      <code>data/demo/journal.db</code>. Newest first, last {len(journal)}.</p>"""
    else:
        journal_html = '<p class="mut">No orders journaled yet — run tools/demo_pipeline.py.</p>'

    # -- universe --
    if universe:
        urows = "".join(f"<tr><td>{html.escape(u['date'])}</td><td class='r'>{u['count']}</td></tr>" for u in universe)
        universe_html = f"""
      <table><thead><tr><th>Snapshot date</th><th class="r">Members</th></tr></thead><tbody>{urows}</tbody></table>
      <p class="mut">Point-in-time history accumulates from the first snapshot forward — seed weekly on Fridays:
      <code>python tools/seed_universe_snapshot.py &lt;date&gt;</code>.</p>"""
    else:
        universe_html = '<p class="mut">No snapshots yet — run tools/seed_universe_snapshot.py.</p>'

    return render(
        {
            "generated": generated,
            "body_class": "halted" if halted else "paper",
            "tiles": tiles,
            "chips": chips,
            "paper": paper_html,
            "strategy": strategy_html,
            "chart": chart_html,
            "journal": journal_html,
            "universe": universe_html,
            "strategy_version": html.escape(strategy["version"]),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="open the console in the default browser")
    args = parser.parse_args()

    out = REPO / "dashboard" / "index.html"
    out.write_text(build_page(), encoding="utf-8")
    print(f"Operator console written: {out}")
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
