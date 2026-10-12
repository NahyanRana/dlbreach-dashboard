# DLBreach Dashboard — setup

Questions and feedback: nahyan.rana@geosyntec.com

An interface to the DLBreach dam and levee breach model (Wu, 2013, 2016),
providing structured input, a cross-section schematic, results
visualisation, Monte Carlo capability, and comparison with measured
failures of water-retaining dams.

The dashboard runs the published DLBreach executable and reads its output.
It adds no physics of its own.

---

## What you need

**1. The dashboard.** The Windows download from the
[Releases page](https://github.com/NahyanRana/dlbreach-dashboard/releases)
(`DLBreach-Dashboard-<version>-Windows.zip`) needs nothing else: Python
and the packages are inside it. To run from the source instead, install
**Python 3.13** (3.11 to 3.14 work) from
[python.org](https://www.python.org/downloads/), ticking **"Add python.exe
to PATH"** on the installer's first screen; the source launcher checks the
version before its first setup.

**2. The DLBreach executable.** From Professor Wu's page:
[webspace.clarkson.edu/~wwu/DLBreach.html](https://webspace.clarkson.edu/~wwu/DLBreach.html).
It is not distributed with this dashboard.

---

## Running it

1. Extract the Windows download (or the source zip, **Code → Download ZIP**)
   somewhere local — **not** inside OneDrive or another synced folder. Your
   user folder works, e.g. `C:\Users\<you>\DLBreach-Dashboard`.
2. Double-click **Launch DLBreach Dashboard.bat**. The Windows download
   starts in seconds. From the source, the first run sets up an environment
   and takes a couple of minutes; later runs start in seconds.
   If Windows shows "Windows protected your PC", click **More info → Run anyway**.
3. A browser tab opens. Leave the black window open while you work.

**Updating the Windows download:** extract the new release to a new
folder; save your project first and open it there.

**Updating from the source:** replace every file in the folder,
including the hidden `.streamlit` folder and `test_cases`, but keep `.venv`.
Then start it with the launcher as usual: from v0.8 it checks for missing
packages and installs them, so no manual `pip install` is needed.

---

## Using it

Version 1.0.0 covers water-retaining dams. Solid waste (tailings, coal ash)
support is paused; see `TAILINGS_TODO.md`.

Work through the sections in the contents panel on the left, in order.
A tick marks a section that is done, and the open section lists its
headings. The strip under the header shows what is done (executable,
inputs, run, scenarios, Monte Carlo), and each page opens with a line on
what it is for. Hover the **?** beside any field for its meaning, unit and
source. The About page has a fuller *Getting started*.

1. **Project** — DLBreach executable, a worked example to start from, case
   name, open a project or load an input file, site datum.
2. **Model setup** — inputs in practitioner units, live cross-section, input
   checks, and the exact input file.
3. **Single run** — hydrograph, breach widths and levels, breach view and
   animation, downloads. Results are flagged if inputs change after the run.
4. **Sensitivity scenarios** — runs as columns, run all, compare outflow,
   widths, depth and pond level, play any run.
5. **Monte Carlo** — ensembles around chosen runs; summary, envelopes for
   outflow and breach geometry, input-against-result charts, and any single
   realisation to inspect, play and download.
6. **Case histories** — your result among measured water-dam failures.
7. **Export** — PDF or Word report appendix, including Monte Carlo
   envelopes, input-against-result charts and the case-history comparison.

Every chart has a **Chart options** button: axis limits and log scales, and
for line charts the colour and line style of each series. Time axes end
shortly after the outflow does; clear or set *x max* to change that.

On its first run the launcher also creates an empty
`%USERPROFILE%\.streamlit\credentials.toml`, so Streamlit never stops to ask
for an email address. Model runs use folders in your Windows temporary
folder, deleted after each run; nothing else is written outside the
dashboard folder.

If the server stops unexpectedly, the launcher restarts it and the browser
tab reconnects. Inputs are autosaved locally (`.dlbreach_autosave.json`);
after a refresh, the About and Project pages offer to restore them.
Results are not kept between sessions.

**Templates:** the Project page has a template for every file the dashboard
reads (annotated DLBreach input file, stage-storage table, scenario runs,
project file), singly or as one zip with a README.

---

## Test cases

The `test_cases` folder holds four 12 m water-retaining dam cases: T1 and
T3 (overtopping), T2 and T4 (piping). Load one from *Worked examples* on
the Project page. The solid waste cases S1 and S2 are in
`test_cases/solid_waste_paused`. See `test_cases/README.md`.

## Files

| File | Purpose |
|---|---|
| `app.py` | The interface |
| `dlbreach_io.py` | Writes input cards, runs the executable, parses output |
| `dlbreach_mc.py` | Sampling, batch execution, ensemble statistics |
| `dlbreach_viz.py` | Cross-section, breach view, animation, help text |
| `dlbreach_empirical.py` | Froehlich and Adria relations, diagnostics, input guidance |
| `dlbreach_units.py` | Practitioner units and porosity from unit weight |
| `dlbreach_cases.py` | Case-history comparison data |
| `dlbreach_ui.py` | Shared page elements and charts with axis controls |
| `dlbreach_batch.py` | Scenario tables, batch packages, geometry text export |
| `dlbreach_tailings.py` | Cone of depression and stage-storage construction |
| `dlbreach_report.py` | PDF report appendix |
| `dlbreach_help.py` | Help text for every field |
| `dlbreach_templates.py` | Templates for every file the dashboard reads |
| `dlbreach_data.py` | Case-history data and citations |
| `dlbreach_about.py` | About page text and disclaimer |
| `test_core.py` | Checks the calculations; also runs the private project benchmarks when `test_private_benchmarks.py` is present |
| `test_app_headless.py` | Executes every page without a browser, to catch run-time errors |
| `dev/` | Developer tools: a stand-in executable for testing (**not DLBreach**), a walkthrough and a Streamlit smoke test. See `dev/README.md`. |

To check an installation, open a command prompt in the folder and run
`.venv\Scripts\python test_core.py` then `.venv\Scripts\python test_app_headless.py`.
The project benchmark checks run too if `test_private_benchmarks.py`,
`Run4_v3.txt` and `Run4_v3.out` are in the folder. They are project data:
`.gitignore` keeps them out of the repository.

---

## Verification

Loading a project benchmark input and running it reproduces the original
DLBreach results exactly. The benchmark files and their checks
(`test_private_benchmarks.py`) are project data and stay out of the
repository.

---

## Attribution

DLBreach was developed by Professor Weiming Wu, Clarkson University.
Please cite the model, and the dashboard where it was used. Full
references are on the About page and on the Case histories page.
