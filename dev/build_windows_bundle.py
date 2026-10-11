"""
dev/build_windows_bundle.py — build the ready-to-run Windows download.

The download holds the dashboard, the official embeddable Python from
python.org, and the exact packages in requirements.txt, already installed.
A user unzips it and double-clicks the launcher: no Python install and
no package download. (Streamlit keeps an empty credentials file in the
user's profile; everything else stays in the folder.) DLBreach itself is
NOT included (it comes from Prof. Wu's page).

    python dev/build_windows_bundle.py          # build dist/DLBreach-Dashboard-<ver>-Windows.zip
    python dev/build_windows_bundle.py --test   # test the built folder as a new user would meet it

Windows only, run by .github/workflows/windows-download.yml with the
Python version the download should carry (3.13). The functions that only
choose files and write text are tested on any system by test_core.py.

Layout of the download:

    DLBreach-Dashboard/
        Launch DLBreach Dashboard.bat    start here
        README-FIRST.txt
        app/                             the dashboard, worked examples, docs
        python/                          embeddable Python and the packages
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
NAME = "DLBreach-Dashboard"

MAX_REL_PATH = 150     # longest path inside the zip: extracting stays under
                       # Windows' 260-character limit for folders up to ~100

# Published files that are not needed to run the dashboard
_LEAVE_OUT = ("dev/", ".github/", "test_app_headless.py", "Launch DLBreach Dashboard.bat",
              "PUBLISHING.md", "CONTRIBUTING.md", ".gitignore", ".gitattributes")


def app_files(tracked: list[str]) -> list[str]:
    """The repository files that go into app/: everything published except
    developer tools, CI and the source launcher (which builds its own
    environment)."""
    return sorted(f for f in tracked
                  if not any(f == x or f.startswith(x) for x in _LEAVE_OUT))


def pth_text(minor: str) -> str:
    """
    The ._pth file of the embeddable Python. It fixes sys.path to the
    bundle itself (the standard library zip, the packages and the app),
    and runs site so that packages installed there are found. Nothing on
    the user's computer (PATH, PYTHONPATH, another Python) is consulted.
    """
    return "\n".join([f"python{minor}.zip", ".", r"Lib\site-packages", r"..\app",
                      "import site", ""])


def version_name(about_text: str, ref: str | None) -> str:
    """v1.0.0 from a release tag, else the version in dlbreach_about.py."""
    if ref and re.fullmatch(r"v\d+(\.\d+)*", ref):
        return ref
    m = re.search(r'VERSION_SHORT\s*=\s*"version ([\d.]+)', about_text)
    return f"v{m.group(1)}" if m else "dev"


LAUNCHER = r"""@echo off
REM ====================================================================
REM  DLBreach Dashboard - Windows download
REM
REM  Double-click to start. Python and every package are already in this
REM  folder; nothing is installed or downloaded. Keep the black window
REM  open while you use the dashboard.
REM ====================================================================

setlocal
pushd "%~dp0"
title DLBreach Dashboard

echo.
echo  ============================================
echo   DLBreach Dashboard
echo  ============================================
echo.

REM ---- opened from inside the zip? -------------------------------------
if not exist "%~dp0python\python.exe" (
    echo  This file has been opened from inside the zip.
    echo.
    echo  Close this window, right-click the downloaded zip, choose
    echo  "Extract All...", and run "Launch DLBreach Dashboard.bat" from the
    echo  extracted folder.
    echo.
    pause
    exit /b 1
)

REM ---- a synced folder can lock files while DLBreach runs --------------
echo "%~dp0" | "%SystemRoot%\System32\find.exe" /i "OneDrive" >nul
if not errorlevel 1 (
    echo  Note: this folder is inside OneDrive. If runs fail, move the
    echo  folder somewhere local, for example C:\Users\%USERNAME%\DLBreach-Dashboard
    echo.
)

REM ---- Streamlit asks for an email on its very first run unless this ---
REM  file exists; create it empty so the window never waits for input.
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
    >"%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >>"%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo  Starting the dashboard. A browser tab will open shortly.
echo.
echo  Keep this window open while you are using the dashboard.
echo  To stop it, close this window or press Ctrl+C.
echo.

pushd "%~dp0app"
REM  matplotlib keeps its font cache inside the folder, not the profile
set "MPLCONFIGDIR=%~dp0app\.matplotlib"
REM  If the server stops unexpectedly it is restarted (a new browser tab
REM  opens); inputs are autosaved and can be restored on the Project page.
set RESTARTS=0
:serve
"%~dp0python\python.exe" -m streamlit run app.py
if %ERRORLEVEL% EQU 0 goto stopped
if %RESTARTS% GEQ 5 goto stopped
set /a RESTARTS+=1
echo.
echo  The dashboard stopped unexpectedly. Restarting (%RESTARTS% of 5)...
echo.
"%SystemRoot%\System32\timeout.exe" /t 2 /nobreak >nul
goto serve

:stopped
echo.
echo  The dashboard has stopped.
pause
popd
popd
endlocal
"""


def readme_first(version: str, py: str) -> str:
    return f"""DLBreach Dashboard {version} - Windows download
==================================================

An interactive Monte Carlo companion to DLBreach (Wu 2016). It runs on
this computer and runs DLBreach directly; nothing is sent anywhere.

Start
-----
1. Extract the whole zip (right-click > Extract All...) to a local folder,
   for example C:\\Users\\<you>\\DLBreach-Dashboard. Avoid OneDrive and
   other synced folders.
2. Get DLBreach.exe from Prof. Wu's page (it is not included):
   https://webspace.clarkson.edu/~wwu/DLBreach.html
   You can put it in the "app" folder, or anywhere and point to it.
3. Double-click "Launch DLBreach Dashboard.bat". If Windows shows
   "Windows protected your PC", click More info > Run anyway.
4. A browser tab opens. Keep the black window open while you work.
   On the Project page, point to DLBreach.exe and load worked example T1.

No Python installation is needed: Python {py} and the packages the
dashboard uses are in the "python" folder. To update, download the new
zip and extract it to a new folder; save your project first (Project
page > Save project) and open it in the new version.

Contents
--------
app\\     the dashboard, worked examples (test_cases), documentation
python\\  Python {py} (embeddable distribution from python.org) with the
         packages listed in app\\requirements.txt

Licences
--------
The dashboard: MIT (app\\LICENSE); see app\\NOTICE.md for DLBreach, the
validation inputs and the case-history data. Python: PSF licence
(python\\LICENSE.txt). Each package keeps its own licence, in its
*.dist-info folder under python\\Lib\\site-packages. The Microsoft C++
runtime files in the python folder are redistributed under the Visual
C++ Redistributable terms.

Source, issues and documentation:
https://github.com/NahyanRana/dlbreach-dashboard
"""


# ---------------------------------------------------------------------
# Windows only from here
# ---------------------------------------------------------------------

def _run(*cmd, **kw):
    print(">", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True, **kw)


def build() -> Path:
    if os.name != "nt":
        sys.exit("Builds on Windows only (the download carries Windows Python).")
    py = platform.python_version()                 # e.g. 3.13.7
    minor = "".join(py.split(".")[:2])             # 313
    out = DIST / NAME
    if DIST.exists():
        shutil.rmtree(DIST)
    pydir = out / "python"
    pydir.mkdir(parents=True)

    # 1. the official embeddable Python, the same version as this one
    url = f"https://www.python.org/ftp/python/{py}/python-{py}-embed-amd64.zip"
    print("Downloading", url, flush=True)
    emb = DIST / "embed.zip"
    urllib.request.urlretrieve(url, emb)
    with zipfile.ZipFile(emb) as z:
        z.extractall(pydir)
    emb.unlink()
    (pydir / f"python{minor}._pth").write_text(pth_text(minor))

    # 2. the exact packages, as binary wheels for this Python and Windows
    site = pydir / "Lib" / "site-packages"
    _run(sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
         "--no-warn-script-location", "--only-binary=:all:", "--no-compile",
         "--target", site, "-r", ROOT / "requirements.txt")
    # the exact versions installed, including dependencies, for the record
    frz = subprocess.run([sys.executable, "-m", "pip", "list", "--path", str(site),
                          "--format=freeze"], check=True, capture_output=True,
                         text=True).stdout
    (pydir / "BUNDLED-PACKAGES.txt").write_text(frz)
    # not needed to run, and the longest paths: package test suites, C
    # headers, and console scripts tied to the build computer's Python
    for d in [*site.glob("*/tests"), *site.glob("*/*/tests"), *site.glob("*/testing/tests"),
              site / "pyarrow" / "include", site / "bin"]:
        if d.is_dir():
            shutil.rmtree(d)

    # 3. tkinter (the "Browse" button for DLBreach.exe), which the
    #    embeddable Python leaves out: copied from this Python
    base = Path(sys.base_prefix)
    shutil.copytree(base / "Lib" / "tkinter", site / "tkinter")
    for pat in ("_tkinter.pyd", "tcl*.dll", "tk*.dll", "zlib*.dll"):
        for f in (base / "DLLs").glob(pat):
            shutil.copy2(f, pydir / f.name)
    shutil.copytree(base / "tcl", pydir / "tcl")

    # 4. the C++ runtime some packages need, so a computer without the
    #    Visual C++ Redistributable can run it
    sysdir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    for name in ("msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
                 "vcruntime140.dll", "vcruntime140_1.dll", "concrt140.dll"):
        if not (pydir / name).exists() and (sysdir / name).exists():
            shutil.copy2(sysdir / name, pydir / name)

    # 5. the dashboard: the published files, from git
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], check=True,
                             capture_output=True, text=True).stdout.splitlines()
    for f in app_files(tracked):
        dst = out / "app" / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, dst)

    # compiled once here and checked by content, not by file time, so the
    # first start is fast whatever time zone the zip is extracted in
    _run(sys.executable, "-m", "compileall", "-q", "-j0",
         "--invalidation-mode", "unchecked-hash", site, out / "app")

    version = version_name((ROOT / "dlbreach_about.py").read_text(encoding="utf-8"),
                           os.environ.get("GITHUB_REF_NAME"))
    (out / "Launch DLBreach Dashboard.bat").write_bytes(
        LAUNCHER.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))
    (out / "README-FIRST.txt").write_bytes(
        readme_first(version, py).replace("\n", "\r\n").encode("utf-8"))

    # 6. the zip, with one top-level folder
    longest = max((f.relative_to(DIST) for f in out.rglob("*") if f.is_file()),
                  key=lambda f: len(str(f)))
    print(f"Longest path in the zip ({len(str(longest))}): {longest}", flush=True)
    assert len(str(longest)) <= MAX_REL_PATH, "a path is too long for Windows extraction"
    zpath = DIST / f"{NAME}-{version}-Windows.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DIST))
    print(f"Built {zpath.name}: {zpath.stat().st_size / 1e6:.0f} MB", flush=True)
    return zpath


def test() -> None:
    """
    Test the extracted download the way a new user meets it: from a fresh
    copy, with no other Python on PATH, nothing from the build computer on
    sys.path, the self-tests passing and the server answering.
    """
    if os.name != "nt":
        sys.exit("Tests on Windows only.")
    zips = sorted(DIST.glob(f"{NAME}-*-Windows.zip"))
    assert zips, "build first"
    fresh = DIST / "fresh"
    if fresh.exists():
        shutil.rmtree(fresh)
    with zipfile.ZipFile(zips[-1]) as z:
        z.extractall(fresh)
    top = fresh / NAME
    py, app = top / "python" / "python.exe", top / "app"
    sysroot = os.environ.get("SystemRoot", r"C:\Windows")
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("PYTHON", "PIP", "VIRTUAL_ENV", "TCL", "TK"))}
    env["PATH"] = rf"{sysroot}\System32;{sysroot}"     # no other Python
    env["MPLBACKEND"] = "Agg"
    env["PYTHONUTF8"] = "1"            # ignored by an isolated Python; harmless

    def py_run(*args, **kw):
        print(">", *args, flush=True)
        r = subprocess.run([str(py), "-X", "utf8", *args], cwd=app, env=env,
                           capture_output=True, encoding="utf-8", errors="replace",
                           timeout=600, **kw)
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:], flush=True)
            r.check_returncode()
        return r

    # sys.path holds the bundle only
    r = py_run("-c", "import sys, json; print(json.dumps(sys.path))")
    import json
    paths = json.loads(r.stdout)
    outside = [p for p in paths if p and not Path(p).resolve().is_relative_to(top.resolve())]
    assert not outside, f"sys.path reaches outside the download: {outside}"

    # every package imports, tkinter works, matplotlib draws
    r = py_run("-c", (
        "import streamlit, pandas, numpy, matplotlib, openpyxl, docx, tkinter;"
        "import matplotlib.pyplot as plt; plt.plot([0, 1]); plt.savefig('t.png');"
        "tcl = tkinter.Tcl(); tk = tcl.eval('package require Tk');"
        "print('tcl', tcl.eval('info patchlevel'), 'tk', tk, 'streamlit', streamlit.__version__)"))
    print(r.stdout.strip())
    (app / "t.png").unlink()

    # the dashboard's own calculation tests, with the bundled Python
    r = py_run("test_core.py")
    assert "ALL CHECKS PASSED" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
    print("test_core.py: all checks passed", flush=True)

    # the server starts and answers, as the launcher starts it
    import urllib.error
    port = "8599"
    log = open(DIST / "server.log", "w", encoding="utf-8")
    proc = subprocess.Popen([str(py), "-X", "utf8", "-m", "streamlit", "run", "app.py",
                             "--server.headless=true", f"--server.port={port}"],
                            cwd=app, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        t0, ok = time.time(), False
        while time.time() - t0 < 120 and not ok:
            time.sleep(2)
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/_stcore/health",
                                            timeout=5) as h:
                    ok = h.read().decode().strip() == "ok"
                with urllib.request.urlopen(f"http://localhost:{port}/", timeout=5) as h:
                    ok = ok and h.status == 200
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                pass
        assert ok, "the dashboard did not answer within 2 minutes"
        print(f"server answered after {time.time() - t0:.0f} s", flush=True)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log.close()
        print((DIST / "server.log").read_text(encoding="utf-8", errors="replace")[-3000:],
              flush=True)
    print("DOWNLOAD TESTED OK", flush=True)


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        build()
