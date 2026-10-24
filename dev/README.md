# Developer tools

> **Nothing in this folder is DLBreach.** The stand-in below imitates the
> DLBreach executable's *interface* so the dashboard can be tested on
> machines without the model. Its numbers are made up and must never be
> reported or compared with DLBreach results.

| File | What it is |
|---|---|
| `standin_dlbreach.py` | Stand-in for testing. Reads the case name from standard input and `<case>.txt` from the working folder, and writes `<case>.out` with DLBreach's 13 columns. The values come from a toy weir-and-erosion rule. Every output starts with a `STAND-IN OUTPUT - NOT DLBREACH` banner. |
| `make_standin.py` | Wraps the stand-in as `dev/bin/STANDIN_not_DLBreach.exe` so the dashboard will run it (Linux and macOS only). `--fixture` also rebuilds `fixtures/standin_T1.out`. |
| `qa_walkthrough.py` | A first-time user's path through all eight sections, pressing the real buttons: load example T1, single run, three scenario runs, 20 Monte Carlo realisations, PDF and Word export. Uses the stand-in executable and the Streamlit stand-in from `test_app_headless.py`. |
| `scan_confidential_names.py` | Scans every file that would be published for the confidential names listed in `dev/private_terms.txt` (never published). Run it before each commit; works on Windows. |
| `qa_features.py` | Feature-by-feature QA: for each worked example (T1–T4), the local run, scenarios, Monte Carlo, case histories and export, and the browser round trip (download inputs, run, upload outputs); project save and open, input-file loading, templates, stage-storage and scenario-table uploads, autosave and restore; loading input files card for card (with Prof. Wu's validation inputs in `test_cases/wu_2016`); the clay core tab and the drawings (axis labels, core, cover, abutments); and the security settings. 97 checks; prints a table. |
| `build_windows_bundle.py` | Builds the ready-to-run Windows download: the official embeddable Python from python.org with the packages in `requirements.txt` installed, the dashboard in `app/`, a launcher and a README; `--test` checks it as a new user would meet it. Windows only; run by `.github/workflows/windows-download.yml`. DLBreach is not included. |
| `apptest_smoke.py` | Opens every page in real Streamlit (`streamlit.testing`) and fails on any error shown on screen. It catches version changes in Streamlit that the stand-in cannot. |
| `fixtures/standin_T1.out` | Stand-in output for test case T1. The test suites use it when the Run4 benchmark is absent (as on GitHub). |

## Running them

```bash
python test_core.py                 # calculations; private benchmarks and name scan if their files are present
python test_app_headless.py         # every page, local and browser modes, PDF and Word
python dev/qa_walkthrough.py        # Linux/macOS: end-to-end with the stand-in
python dev/qa_features.py           # Linux/macOS: every feature, all four cases
python dev/apptest_smoke.py         # needs streamlit installed
```

GitHub Actions runs them on every push (`.github/workflows/tests.yml`): the
first three on Windows and Linux, the two that use the stand-in on Linux only.

## Project benchmarks (private)

Regression checks pinned to project data live in
`test_private_benchmarks.py`, which is **not** in the repository
(`.gitignore` excludes it, with `Run4_v3.*` and `SampleRunLog.xlsx`). Keep
it in your local dashboard folder; `python test_core.py` runs it when it
is present and notes that it was skipped when it is not.
