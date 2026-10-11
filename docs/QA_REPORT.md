# QA report — v0.16 (9 October 2026)

How this release was checked, what was found, and what still has to be
verified on a Windows computer and in a real browser.

## 1. Automated tests (all pass)

| Test | Scope | Result |
|---|---|---|
| `test_core.py` | Calculations; input files written back card for card (a made-up levee case, a made-up cored case with a clay cover, and Prof. Wu's eleven validation inputs); clay core read, written, switched off, partial sets, geometry and fit; clay cover thickness; report figures; data file paths; inputs offered for sampling | Pass |
| `test_app_headless.py` | All eight pages × four worked examples, local and browser modes (64 page runs); scenario and Monte Carlo results; PDF and Word export | Pass |
| `dev/qa_walkthrough.py` | A first-time user's path through all eight sections, pressing the real buttons | Pass |
| `dev/qa_features.py` | 98 feature checks, below | 98 of 98 |
| Private project benchmarks | Benchmark reproduced exactly; its input written back card for card; practitioner run log read (kept out of the repository) | Pass |
| Confidential-name scan | The 82 files that would be published | None found |

`dev/qa_features.py` covers, for each worked example T1–T4: the input file
round trip; Model setup in three datums; local single run, scenarios and
Monte Carlo; case histories; PDF and Word export; and the browser round
trip (download inputs, run, upload outputs). It also covers project save
and open, templates, uploads, autosave, the security settings, loading
input files (every Wu case loaded, written back card for card and run;
data files), and, new in this release, the clay core tab and the drawings:

- distance-axis labels on overtopping and piping sections;
- a loaded core (Banqiao) read into the inputs and drawn;
- a core added to a case, written, drawn and removed;
- a loaded non-cohesive core made cohesive writes kd and τc;
- submode 3 without a core, and a core outside the dam, flagged (the
  warning clears on the same screen as the toggle);
- core inputs offered for scenarios only in submode 3;
- the clay cover of Yahekou drawn;
- Teton's one-sided breach drawn against a labelled abutment;
- an erosion limit below the storage table shown as a caution.

Runs use a stand-in for DLBreach, so these tests check the dashboard's
behaviour, not DLBreach's numbers.

**Visual review.** Every drawing (cross-section in two datums, two breach
views and the animation) was rendered for T1–T4 and all eleven Wu cases
and inspected, with the PDF pages for four of them. This found the missing
axis labels, a breach drawn over the abutments, labels cut off at the
frame, crowded animation readouts, and barrier sections too flat to read;
all fixed.

## 2. Independent review of this release

| Problem | Now |
|---|---|
| **Clay cover drawn 1/S times too thick** (2.5× on a 2.5H:1V face) | Drawn at the given thickness normal to the face; test added |
| A partial set of core cards was completed with starting values | Written as loaded; a field edited on the tab is then written |
| A lower-case adaptation length card was dropped; a comment naming it added one | Card names matched without regard to case |
| A file with both pipe head loss cards lost one | Both written |
| "Submode 3 needs a clay core" lagged one screen behind the toggle | Read before the tabs are drawn; test added |
| Help and labels said more than Wu (2016) does (core height "above base"; core erosion sequence; "the model would extrapolate") | Reworded to Wu's text; the drawing's assumption that the core stands on the base is stated |
| No check on sampled core geometry | Monte Carlo reports realisations that put the core outside the section |
| Minor drawing cases (erosion limit above the crest off the canvas; missing values in an output row; the breach outline at an abutment half hidden) | Fixed |

The reviewer confirmed: core position and sign, slope and unit conversions,
the card-for-card round trip of all Wu files and T1–T4 (also lower-case
core names, tabbed cards, cores with other modes, duplicates), state across
loading a new case, unique drawing ids, the clip path, and the one-sided
width check.

## 3. Security, as checked

- No client data published: allowlist `.gitignore`; confidential-name scan
  of every publishable file (needs your private list).
- Local version serves this computer only, sends no usage statistics, keeps
  no uploads, deletes run folders.
- Browser version: no server or shared storage; during every browser-mode
  page run, the QA recorded any process start or file written in the
  dashboard folder: none.
- Data files are written only inside the run folder; absolute paths and
  `..` are refused.

## 4. Not yet verified (Stage 4)

- Package versions installing on Windows (first GitHub Actions run).
- Real Streamlit (`dev/apptest_smoke.py`, first GitHub Actions run).
- A clean install by a new user on Windows.
- The browser version in Chrome and Edge (`docs/BROWSER_CHECKLIST.md`).
- Worked examples T1–T4 and Prof. Wu's cases run with DLBreach itself
  (`docs/WU_VALIDATION.md`), including a cored case edited on the Clay core
  tab.
