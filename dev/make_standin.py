"""
dev/make_standin.py — wrap the stand-in as an "executable" the dashboard can run.

THE RESULT IS NOT DLBREACH. It exists so the run, scenario and Monte Carlo
paths can be tested without the real model (see dev/standin_dlbreach.py).

    python dev/make_standin.py            # writes dev/bin/STANDIN_not_DLBreach.exe

Linux and macOS only: the file is a Python script with a ".exe" name,
because the dashboard looks for that suffix. Windows will not run it; on
Windows, test with the real DLBreach.exe.

It also rebuilds the public test fixture used by the test suites when the
Run4 benchmark files are not present:

    python dev/make_standin.py --fixture  # writes dev/fixtures/standin_T1.out
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

DEV = Path(__file__).resolve().parent
ROOT = DEV.parent
EXE = DEV / "bin" / "STANDIN_not_DLBreach.exe"
FIXTURE = DEV / "fixtures" / "standin_T1.out"


def make_exe() -> Path:
    if os.name == "nt":
        sys.exit("The stand-in runs on Linux and macOS only. On Windows, "
                 "test with the real DLBreach.exe.")
    EXE.parent.mkdir(exist_ok=True)
    EXE.write_text(
        f"#!{sys.executable}\n"
        "# STAND-IN FOR TESTING. THIS IS NOT DLBREACH.\n"
        "import runpy, sys\n"
        f"sys.argv[0] = {str(DEV / 'standin_dlbreach.py')!r}\n"
        f"runpy.run_path({str(DEV / 'standin_dlbreach.py')!r}, run_name='__main__')\n",
        encoding="utf-8")
    EXE.chmod(EXE.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return EXE


def make_fixture() -> Path:
    """Run the stand-in on test case T1 and keep its output as a fixture."""
    sys.path.insert(0, str(ROOT))
    from dlbreach_io import run_case
    exe = make_exe()
    text = (ROOT / "test_cases" / "T1_water_overtopping.txt").read_text()
    with tempfile.TemporaryDirectory() as tmp:
        res = run_case(exe, text, case_name="standin_T1", work_dir=tmp)
        if not res["ok"]:
            sys.exit(f"stand-in failed:\n{res['stdout']}\n{res['stderr']}")
        FIXTURE.parent.mkdir(exist_ok=True)
        FIXTURE.write_bytes(Path(res["out_path"]).read_bytes())
    return FIXTURE


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        print(f"Wrote {make_fixture()} (stand-in output, not DLBreach)")
    else:
        print(f"Wrote {make_exe()} (stand-in, not DLBreach)")
