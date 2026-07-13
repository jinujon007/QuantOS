"""Determinism verification for momentum_backtest.py (Phase 0, deliverable 5).

Runs the full script (`python momentum_backtest.py`, main mode — not
--selftest) N times as separate subprocesses, hashes the two result CSVs
each run produces, and fails loudly on any mismatch. Separate processes,
not repeated in-process calls, is the deliberately harder bar: it also
catches nondeterminism sources a single process could hide (e.g. hash-seed
randomization — already fixed upstream per momentum_backtest.py's own
comments, but this is what proves the fix holds under the condition it
actually matters: a fresh process each time, exactly how a real daily/CI
run would invoke it).

CSV bytes are compared after normalizing line endings (\\r\\n -> \\n) — see
tools/capture_golden.py's docstring for why raw bytes aren't the right
comparison unit on Windows (verified: it's a platform newline-translation
artifact, not strategy nondeterminism).

Usage: python tools/verify_determinism.py [N]   (default N=10)
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
RESULT_FILES = ["data/results/equity_curve.csv", "data/results/equity_comparison.csv"]


def _hash_normalized(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_once(run_index: int) -> dict[str, str]:
    result = subprocess.run(
        [PYTHON, "momentum_backtest.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Run {run_index}: FAILED (exit {result.returncode})")
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise SystemExit(1)
    hashes = {f: _hash_normalized(ROOT / f) for f in RESULT_FILES}
    print(f"Run {run_index}: " + ", ".join(f"{Path(f).name}={h[:12]}" for f, h in hashes.items()))
    return hashes


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"Determinism verification: {n} independent subprocess runs of momentum_backtest.py\n")

    all_hashes = [run_once(i + 1) for i in range(n)]

    reference = all_hashes[0]
    mismatches = []
    for i, hashes in enumerate(all_hashes[1:], start=2):
        for f in RESULT_FILES:
            if hashes[f] != reference[f]:
                mismatches.append((i, f, reference[f], hashes[f]))

    print()
    checkpoints = [c for c in (3, 5, 10) if c <= n]
    for c in checkpoints:
        subset = all_hashes[:c]
        ok = all(h == subset[0] for h in subset)
        status = "PASS - byte-identical" if ok else "FAIL - divergence detected"
        print(f"  [{c}x] {status}")

    if mismatches:
        print(f"\nFAIL: {len(mismatches)} mismatch(es) found.")
        for i, f, ref_h, got_h in mismatches:
            print(f"  run {i}, {f}: expected {ref_h[:16]}, got {got_h[:16]}")
        raise SystemExit(1)

    print(f"\nPASS: all {n} runs byte-identical (after line-ending normalization).")
    for f, h in reference.items():
        print(f"  {f}: sha256={h}")


if __name__ == "__main__":
    main()
