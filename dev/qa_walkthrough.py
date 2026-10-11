"""
dev/qa_walkthrough.py — a first-time user's path through the dashboard,
run end to end against the STAND-IN executable (not DLBreach).

What it does, in the order a new user would:

  About -> Project (point to the executable, load worked example T1)
  -> Model setup -> Single run (press Run) -> Sensitivity scenarios
  (press Run all) -> Monte Carlo (press Run, 20 realisations)
  -> Case histories -> Export (build PDF and Word)

Every step goes through the app's own buttons and code, with Streamlit
replaced by the stand-in from test_app_headless.py, so the real
run_case / run_monte_carlo / report paths are exercised, including the
subprocess calls and the parallel Monte Carlo workers.

It checks behaviour, not appearance or numbers. The numbers come from
dev/standin_dlbreach.py and mean nothing.

Linux and macOS only (the stand-in cannot run on Windows).

    python dev/qa_walkthrough.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dev"))
os.chdir(ROOT)

import test_app_headless as H        # noqa: E402  installs the Streamlit stand-in
from make_standin import make_exe    # noqa: E402

ST = H.ST
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def render(press: tuple[str, ...] = ()) -> list[str]:
    """One script run; buttons whose label or key is in `press` return True."""
    orig = H._Stub.button

    def button(self, label="", *a, key=None, **k):
        self._claim(key)
        return label in press or (key is not None and key in press)

    H._Stub.button = button
    try:
        ST.calls.clear()
        ST.keys_seen.clear()
        exec(compile(APP, "app.py", "exec"), {"__name__": "__main__",
                                              "__file__": str(ROOT / "app.py")})
        H._raise_contained()
    finally:
        H._Stub.button = orig
    return list(ST.calls)


def step(msg: str):
    print(f"  ok  {msg}")


def main() -> int:
    if os.name == "nt":
        sys.exit("Linux and macOS only: the stand-in cannot run on Windows.")
    exe = make_exe()
    pages = ["1. About", "2. Project", "3. Model setup", "4. Single run",
             "5. Sensitivity scenarios", "6. Monte Carlo", "7. Case histories",
             "8. Export"]
    ss = ST.session_state
    ss.clear()

    # a new user opens the dashboard
    render()
    assert ss["page"] == pages[0]
    step("first visit opens on About")

    # Project: point to the executable, then load a worked example
    ss["page"] = pages[1]
    ss["exe_path"] = str(exe)
    render()
    render(press=("load_example",))
    assert ss["params"]["case_name"].startswith("T1"), ss["params"]["case_name"]
    render()
    step(f"Project: stand-in found, example loaded ({ss['params']['case_name']})")

    ss["page"] = pages[2]
    render()
    step("Model setup drawn for the example")

    # Single run
    ss["page"] = pages[3]
    render(press=("Run DLBreach",))
    df = ss.get("result_df")
    assert df is not None and len(df) > 10, "single run produced no result"
    render()
    step(f"Single run: run completed, {len(df)} output rows read back")

    # Sensitivity scenarios: the default three runs
    ss["page"] = pages[4]
    render()
    n = int(ss.get("keep_scen_n", 3))
    render(press=(f"Run all {n} runs",))
    sc = ss.get("scen_store")
    assert sc and len(sc["summary"]) == n, "scenario runs missing"
    render()
    step(f"Sensitivity scenarios: {n} runs completed and compared")

    # Monte Carlo: 20 realisations around the base case
    ss["page"] = pages[5]
    ss["mc_nreal"] = 20
    render()
    render(press=("Run Monte Carlo",))
    mc = ss.get("mc_store") or {}
    assert mc, "Monte Carlo store empty"
    res = next(iter(mc.values()))["results"]
    assert int(res["ok"].sum()) == 20, res[["ok", "error"]].head()
    calls = render()
    assert calls.count("vega_lite_chart") >= 6
    step("Monte Carlo: 20 realisations run in parallel, results drawn")

    ss["page"] = pages[6]
    render()
    step("Case histories drawn with the run")

    # Export: build PDF and Word with every section that has content
    ss["page"] = pages[7]
    for k in ("mc", "mc_env", "mc_drivers", "cases", "scenarios"):
        ss[f"keep_rsec_{k}"] = True
    for fmt, magic in (("PDF", b"%PDF-"), ("Word", b"PK")):
        ss["keep_rep_fmt"] = fmt
        render()
        render(press=(f"Build {fmt}",))
        data, ext, _ = ss["report_file"]
        assert data[:len(magic)] == magic, f"{fmt} build failed"
        step(f"Export: {fmt} appendix built ({len(data) / 1024:.0f} kB)")

    print("\nWALKTHROUGH COMPLETE (stand-in executable; numbers are not DLBreach)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
