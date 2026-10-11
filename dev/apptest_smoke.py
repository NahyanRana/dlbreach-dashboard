"""
dev/apptest_smoke.py — open every page in real Streamlit and fail on any
error shown on screen.

test_app_headless.py replaces Streamlit with a stand-in, which is fast and
needs nothing installed, but cannot notice when a Streamlit release changes
or removes something the app uses. This test uses Streamlit's own test
runner (streamlit.testing.v1.AppTest), with the installed version, for
that. It does not run DLBreach; the "with results" pass loads the stand-in
fixture (dev/fixtures/standin_T1.out, NOT DLBreach output).

    python dev/apptest_smoke.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from streamlit.testing.v1 import AppTest    # noqa: E402

from dlbreach_io import parse_out           # noqa: E402

PAGES = ["1. About", "2. Project", "3. Model setup", "4. Single run",
         "5. Sensitivity scenarios", "6. Monte Carlo", "7. Case histories",
         "8. Export"]
CONTAINED = "Something went wrong on"       # the app's on-screen error callout


def _check(at: AppTest, where: str):
    if at.exception:
        raise AssertionError(f"{where}: {at.exception[0].value}")
    shown = [m.value for m in at.markdown if CONTAINED in str(m.value)]
    if shown:
        raise AssertionError(f"{where}: {shown[0][:200]}")


def main() -> int:
    import streamlit
    print(f"  streamlit {streamlit.__version__}")
    fixture = parse_out(ROOT / "dev" / "fixtures" / "standin_T1.out")
    for label, results in (("empty session", None), ("with a loaded output", fixture)):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
        at.run()
        _check(at, f"first load ({label})")
        for page in PAGES:
            at.session_state["page"] = page
            if results is not None:
                at.session_state["result_df"] = results
            at.run()
            _check(at, f"{page} ({label})")
        print(f"  ok  all {len(PAGES)} pages, {label}")
    print("\nALL PAGES OPEN IN STREAMLIT WITHOUT ERROR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
