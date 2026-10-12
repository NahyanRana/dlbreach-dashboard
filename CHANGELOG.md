# Changelog

Notable changes to the DLBreach Dashboard.

## [Unreleased]
- Zenodo DOI in `CITATION.cff`, the README (with a DOI badge) and the
  About page: 10.5281/zenodo.23307440 for all versions,
  10.5281/zenodo.23307441 for version 1.0.0.
- README *How it was built*: developed with an AI coding assistant, under
  the author's direction and engineering review, and how each release is
  checked.
- The related ICOLD 2027 lightning talk cited with its title, in the
  README and on the About page.
- Wu validation results recorded: Teton and Banqiao matched direct
  DLBreach runs (`docs/WU_VALIDATION.md`, `docs/QA_REPORT.md`).

## [1.0.0] — first public release (11 October 2026)

The first public release, for download and use on the user's own Windows
computer. It brings together the work of the development builds below:
structured DLBreach input in practitioner units with a live
cross-section (including clay cores), card-for-card loading of existing
input files, single runs, sensitivity scenarios and Monte Carlo ensembles
run in parallel, comparison with measured failures of water-retaining
dams, and PDF or Word report export.

- **Windows download** attached to the release: the dashboard with Python
  and its packages already installed. Unzip and double-click; DLBreach is
  obtained from Prof. Wu's page.
- **Citation:** software citation (2026, version 1.0.0) with ORCID in
  `CITATION.cff`, the README and the About page; the planned ICOLD 2027
  paper is listed separately, as in preparation. The Zenodo DOI follows
  the release.
- Tested on every push on Windows and Linux, Python 3.11 to 3.14; the
  Windows download is built and tested on Windows for every release.

## [0.16] — clay core inputs and clearer drawings (October 2026)

### Added
- **Clay core inputs** on a new *Clay core (optional)* tab of Model setup:
  geometry (height, crest width, slopes, offset from the crest centre),
  material, strength and erodibility, in practitioner units, for
  overtopping submode 3 (Wu 2016, Clay Core Parameters). A loaded core is
  read into these inputs and written back card for card; a partial set of
  core cards is written as loaded. Core inputs are offered for scenarios
  and Monte Carlo when the core is modelled, and Monte Carlo reports
  realisations that put the core outside the embankment.
- The cross-section draws the clay core, and a clay cover given in a loaded
  file, in the dashboard and in the PDF and Word reports.
- Breach views draw the abutments at both ends of the crest. A one-sided
  breach (Breach_Location 1) is drawn against the left-hand abutment,
  labelled as not erodible, and widens to the right only (Wu 2016,
  Section 4.3); the panel and caption state the breach location.
- Input checks: overtopping submode 3 without a core; a core above the
  crest or outside the embankment section; a core given for another mode.

### Fixed
- **The distance axis of the cross-section had no labels for overtopping
  cases** (the pilot channel drawing overwrote the axis range).
- The width check of a one-sided breach used two side slopes instead of one.
- A breach wider than the crest length was drawn over the abutments and
  out of the frame; it is now clipped at the crest ends.
- Low, wide embankments (barriers, levees) are drawn with enough vertical
  exaggeration to read (up to ×100), and the axis title is shortened when
  it would not fit.
- Cards for the failure mode not selected (for example a pipe head loss
  card in an overtopping file), both pipe head loss cards, and a
  lower-case adaptation length card are written back as loaded.
- The erosion limit below the lowest level of a stage-storage table is a
  caution, not an input error (Prof. Wu's Teton input does this).
- `test_core.py` no longer leaves a `synthetic.out` file in the folder.

### Changed
- **Windows download with nothing to install.** Each release carries
  `DLBreach-Dashboard-<version>-Windows.zip`: the dashboard with the
  official embeddable Python and the pinned packages already installed,
  and its own launcher. Unzip and double-click; no Python install. It is
  built and tested on GitHub's Windows machines (no other Python on the
  path, the dashboard's checks, the server answering) by the new
  *Windows download* workflow, which attaches it to each release.
  DLBreach is not included. `test_core.py` now runs without the `dev`
  folder, as it does inside the download.
- **Download only.** The dashboard is published for download and run on
  the user's computer, where it runs DLBreach directly. The browser
  version (which could not run DLBreach, so needed output files uploaded
  by hand) is not published: `index.html`, `Preview browser version.bat`,
  the Pages workflow and the browser checklist are removed. The app's
  browser mode stays in the code, tested, but unused.
- Panel legends are drawn as the items are (filled squares for areas,
  lines for levels), with clearer labels: base width (toe to toe), length
  along crest, pilot channel depth × width, crest settlement height ×
  length, initial pipe invert. Piping readouts before the roof collapses
  show the pipe, not an opening.
- Report figures: legend below the drawing, gridlines behind it.
- Tests: card-for-card write-back of cores (full, partial, lower case);
  core geometry and cover thickness; the report figures; 9 more feature
  checks (98 in all).

## [0.15] — loading any DLBreach input file faithfully (October 2026)

### Fixed
- **Loading an input file dropped every card the dashboard does not edit**
  (clay core and cover, reservoir inflow, water level time series,
  downstream storage basin, spillways, waves, wind, breach phase options).
  They are now kept verbatim and written to every input file, and the
  Project page reports, card by card, that the file is written back
  unchanged.
- **A power-law reservoir (methods 2–4) became an empty table** when Model
  setup was opened, writing an empty `Upstream_Reservoir` card. Model setup
  now opens such cases on the power-law inputs, and a table shown is the
  table written.
- Unit conversion no longer rounds a value the user did not touch (for
  example a slope of 0.645 V/H came back as 0.6449999987).
- Numbers are written in full, not to six decimals.
- Loading an input file now sets the case name (from the file name) and the
  notes (from its leading comments), and replaces the previous inputs and
  results, as opening a project does.
- A case that prescribes its water levels or fills its reservoir by inflow
  is no longer blocked by the initial pond-level check.
- A DLBreach run that writes no results now says so, with DLBreach's
  messages, instead of showing an error.

### Added
- Data files a case names (for example wave and tide series) are attached
  once and placed next to the input for every run and run package.
- Prof. Wu's validation inputs, from his DLBreach page, are included in
  `test_cases/wu_2016` and appear under *Worked examples*;
  `docs/WU_VALIDATION.md` lists the values his report gives for each, and
  how to check them.
- Case histories: Froehlich (2016a) and Xu and Zhang (2009) now differ in
  colour and marker shape, in the dashboard and in the PDF; log axes that
  span less than two decades are labelled in plain numbers.
- Tests: card-for-card write-back of a synthetic levee case and of the Wu
  inputs; 16 more feature checks (89 in all).

### Changed
- The benchmark figures of the private project case are no longer given
  in the public documents.

### Fixed after independent review of 0.15
- kd and τc are written whenever the fill is cohesive, even if the loaded
  file left them out (switching a loaded case to cohesive ignored them).
- Opening *Edit table* on a power-law reservoir no longer changes it; the
  example table is used only once edited.
- Card names are matched without regard to case; a card given twice is
  reported; a card the dashboard has to add is a warning, not a success;
  `Breach_Manning_n_Segments` is not joined by a default
  `Breach_Manning_n`. Model setup lists differences from the loaded file.
- Scenario and Monte Carlo runs are blocked, like the single run, until the
  case's data files are attached; a scenario run without results no longer
  raises an error.
- Monte Carlo and scenarios offer only inputs that change the file DLBreach
  reads (for example not the reservoir volume when a water level series
  sets the upstream level).
- Data files: names in quotes, in sub-folders and in a different case are
  matched; absolute paths and `..` are refused; attached files can be
  removed.
- A loaded value outside a field's range is written unchanged and the field
  says so.
- Opening the power-law inputs on a case with a stage-storage table no
  longer replaces the table (the reverse of the earlier fix).
- Nothing after `END_PARAMETERS` is read. A file with both
  `Breach_Manning_n` and `Breach_Manning_n_Segments` keeps both, and the
  Manning's n field says when it is not used.
- Card names written in standard form, and data file references the
  dashboard cannot supply (outside the run folder, or named like the case's
  own files), are reported on loading; a run whose data file would be
  overwritten by its own input or output is refused.

## [0.14] — repository release preparation (October 2026)

### Added
- Public repository files: README, CITATION.cff, NOTICE, CONTRIBUTING,
  issue and pull request templates, `.gitignore`, `.gitattributes`.
- GitHub Actions: both test suites, a real-Streamlit smoke test and a
  first-time-user walkthrough, on Windows and Linux, Python 3.11 to 3.14.
  A separate, manually run workflow publishes the browser version to
  GitHub Pages.
- Developer tools in `dev/`: a stand-in executable for testing (not
  DLBreach), a public test fixture, the walkthrough and the smoke test.
- `dev/qa_features.py` (73 feature checks) and `dev/scan_confidential_names.py`
  (scans publishable files for confidential names kept in a private list).
- `docs/QA_REPORT.md`: testing, independent review and open items.
- Two more worked examples, so there are four 12 m water dam cases: T3
  (overtopping at a crest settlement, cohesive fill, headcut) and T4
  (piping near the base, cohesive fill). The paused solid waste cases are
  renamed S1 and S2.
- Browser version: the worked examples are now offered on the Project page,
  and the page footer names the Streamlit build in use.

### Fixed
- A scenario table downloaded from the dashboard (CSV or Excel) could not
  be uploaded back: the Unit column was read as the parameter name.

### Changed
- Checks pinned to project data (the benchmark and a practitioner run
  log) moved to `test_private_benchmarks.py`, kept out of the repository;
  the public tests use invented geometry. The in-situ Cv check now tests
  against the direct definition.
- `.gitignore` is an allowlist: only the files listed are published.
- Uploaded output files are read through a temporary folder that is
  deleted at once; run folders are deleted after single and scenario runs.
- The browser preview serves this computer only (127.0.0.1).
- The launcher reinstalls packages when `requirements.txt` changes, and
  creates an empty Streamlit credentials file so the first run never
  stops at Streamlit's email prompt.
- Browser version: openpyxl and python-docx pinned; usage statistics off.
- Local version serves `localhost` only (previously also the local network)
  and no longer sends Streamlit usage statistics (`.streamlit/config.toml`).
- `requirements.txt` pins exact versions. Supported Python is 3.11 to 3.14
  (3.13 recommended); the launcher checks this before the first setup.
- Batch files are kept with Windows (CRLF) line endings.
- The tests run without the project benchmark files; the benchmark checks
  are skipped, with a note, when those files are absent.
- LICENSE holds the MIT text only; the DLBreach and data notes moved to
  NOTICE.md.

## [0.13] — 5 October 2026
- Water-retaining dams only; solid waste (tailings, coal ash) paused behind
  `SOLID_WASTE_ENABLED` (open items in TAILINGS_TODO.md).
- Eight sections in a left contents panel: About, Project, Model setup,
  Single run, Sensitivity scenarios, Monte Carlo, Case histories, Export.
- Per-page error containment, launcher auto-restart, file-watch reloads
  off, local autosave of inputs with a restore offer.

## Earlier development builds — September and October 2026
- Shared as zip files during development. The input writer, executable
  runner and output parser were verified against a project benchmark,
  which they reproduce exactly.
