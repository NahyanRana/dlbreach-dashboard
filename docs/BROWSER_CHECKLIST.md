# Browser version: feasibility review and test checklist

The browser version runs the dashboard in the visitor's browser with
**stlite** (Streamlit compiled to WebAssembly through Pyodide), served from
GitHub Pages. DLBreach cannot run in a browser, so each run page prepares
input files to download and reads the `.out` files back.

## 1. Review of the code (October 2026, v0.14)

Done by reading the code and running every page in browser mode with
`test_app_headless.py`, which sets `sys.platform = "emscripten"` as stlite
does. It was not run in a real browser; part 2 does that.

| Feature | Finding | Risk | If it fails |
|---|---|---|---|
| **Run paths** (subprocess, tkinter file dialog, parallel workers, autosave) | Never reached in the browser: every call is behind `BROWSER`. All eight pages pass in browser mode. | Low | — |
| **Input download, batch zip, output upload, results** | Use `st.download_button` and `st.file_uploader` with in-memory zips, which stlite supports. Results pages use the same code as the local version. | Low | Release local-only first |
| **Worked examples** | **Fixed in v0.14.** The example `.json` files were not mounted, so the Project page had no examples in the browser. `index.html` now mounts them. | — | — |
| **Contents panel styling** | Uses `st.container(key="toc")` and Streamlit's `st-key-…` classes for the numbered circles, ticks and current-section highlight. They depend on the Streamlit version bundled in stlite. If `key=` is not accepted, the code falls back to a plain container: navigation still works, unstyled. The footer now shows the Streamlit version in use. | Medium (cosmetic) | Accept for release; restyle later |
| **Google Fonts** (IBM Plex Sans) | Loaded by CSS `@import` and by a `<link>` in each drawing. Needs internet access; otherwise falls back to Segoe UI or the system font. | Low (cosmetic) | Accept |
| **Drawings and animation** (`components.html`) | Static HTML and SVG with inline script in an iframe, which stlite supports. Custom components are not used. | Low | Release local-only first if the animation fails |
| **python-docx** (Word export) | Pure Python. Its dependency `lxml` is in the Pyodide distribution. It is installed when the page loads, so a failure stops the whole app from starting. | **Medium (whole app)** | Remove `python-docx` from `index.html` and offer PDF only in the browser (one small change) |
| **openpyxl** (Excel run logs and stage-storage) | Pure Python, installed when the page loads. | Low | As above |
| **matplotlib** (PDF export) | In the Pyodide distribution; the report uses the Agg backend. | Low | — |
| **`st.color_picker`, popovers** | Core widgets. Popovers fall back to expanders on older Streamlit. | Low | — |
| **stlite version** | `index.html` loads `@stlite/browser@0.85.1` from jsDelivr. The version could not be confirmed from this build environment. A wrong version gives a blank page with a 404 in the console. | Medium | Change the version in the two places in `index.html` |
| **Large Monte Carlo batches** | The input zip is rebuilt on every interaction, in the browser. Expect slower response above about 1,000 realisations. | Low | Note in the README |

**Release rule:** cosmetic differences (fonts, contents-panel styling) do
not block release. If the page fails to start, or downloading inputs,
uploading outputs or any results page fails, publish the local version
only, and add the browser version in a later release.

## 2. Test in a real browser (about 15 minutes)

You need: Python on PATH, Chrome or Edge, and one `.out` file from a real
DLBreach run of worked example **T1** (run it once in the local version
and keep `T1_water_overtop.out`).

1. Double-click **Preview browser version.bat**. A tab opens at
   `http://127.0.0.1:8000` (served to this computer only). Wait for the first load (about a minute).
   - [ ] The page loads. *If it stays blank: F12 → Console, copy the red text.*
   - [ ] The footer reads *browser version, Streamlit x.y.z*. Note the version.
2. **Look**
   - [ ] Header, status strip and page guides look as in the local version.
   - [ ] Contents panel: numbered circles, ticks for done sections, current
     section highlighted, *On this page* links work.
   - [ ] IBM Plex Sans font (compare with the local version).
3. **Project**
   - [ ] *Browser version* note in place of the executable box.
   - [ ] Worked examples: load **T1**.
   - [ ] Templates: download the zip and open it.
4. **Model setup**
   - [ ] Cross-section draws, and redraws when you change the embankment
     height.
   - [ ] A **?** tooltip and a *Chart options* popover open.
5. **Single run**
   - [ ] *Download input file* gives `T1_water_overtop.txt`.
   - [ ] Upload your real `T1_water_overtop.out`: tiles, hydrograph, widths,
     levels and the breach view appear; the animation plays; step buttons work.
   - [ ] In *Chart options*, change a line colour (colour picker).
6. **Sensitivity scenarios**
   - [ ] *Download 3 input files (.zip)*. Unzip, add DLBreach.exe, run
     `run_all.bat`, zip the `.out` files, upload: comparison tabs appear.
7. **Monte Carlo** (20 realisations is enough)
   - [ ] Download the zip, run `run_all.bat`, upload the outputs: summary,
     envelopes and input-against-result charts appear.
8. **Case histories**
   - [ ] Your T1 point among the case histories.
9. **Export**
   - [ ] Build **PDF**, download, open.
   - [ ] Build **Word**, download, open.
10. **Edge**: repeat steps 1 and 5 in Edge.

Send the ticked list (and any console errors) and we decide together:
publish the browser version with v1.0.0, or local-only first.
