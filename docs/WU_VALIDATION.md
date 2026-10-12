# Checking the dashboard against Prof. Wu's validation cases

Prof. Wu validated DLBreach against laboratory, field and historical cases
(Wu 2016, Chapters 6 and 7), and the input files for several of them
come from him. These files exercise far more of DLBreach than the dashboard edits:
clay cores and covers, reservoir inflow, prescribed water level series,
downstream storage basins, spillways, waves and wind. They are a strong
test that the dashboard passes a case to DLBreach unchanged.

The input files, from Prof. Wu's DLBreach page
(<https://webspace.clarkson.edu/~wwu/DLBreach.html>), are in
`test_cases\wu_2016\` with the data files they name, unchanged. They appear
under *Worked examples* on the Project page.

## 1. What the dashboard guarantees, and how it is tested

- **Every card is written back.** On loading, the dashboard reads the cards
  it edits into its inputs and keeps every other card verbatim, and writes
  every card back with the same values. The Project page checks this for
  each file loaded and warns of any exception: a card the dashboard has to
  add, a card given twice, a card name written in standard form, or a data
  file it cannot supply. All eleven of Prof. Wu's files load with nothing added.
  Model setup lists any differences from the loaded file that later edits
  make.
- **Boundaries are left as the file gives them.** If the file prescribes
  the upstream water level (a time series or a data file) or the downstream
  boundary another way, the dashboard does not add its own reservoir or
  channel card.
- **Data files travel with the case.** Files a case names (for example the
  Mecox wave and tide files) are attached once and placed next to the input
  for every run, scenario, Monte Carlo realisation and run package.

`test_core.py` checks the first two for all eleven files, and for a made-up levee case that is always present;
`dev/qa_features.py` loads each through the Project page, opens Model
setup, checks the input file written card for card, and runs it.

## 2. Check on your computer (about 30 minutes for all)

For each case:

1. **Run it directly.** Copy `<case>.txt` (and any data files it names)
   into a scratch folder with DLBreach.exe, run DLBreach and give the case
   name. Keep `<case>.out`. This is the reference.
2. **Run it through the dashboard.** Project → *Worked examples* → the case
   → **Load example** → Single run → **Run DLBreach**. Note the tiles.
3. **Compare.** On the same page, load the reference `.out` from step 1
   under *Or load an existing .out file*. The tiles must be identical.
4. **Compare with Wu (2016)** using the table below. The report does not
   say which input file or DLBreach version produced each value, so treat
   it as a reference, not a pass mark; step 3 is the test of the
   dashboard.

### Results so far

| Case | Dashboard against a direct DLBreach run | Checked |
|---|---|---|
| `Teton_cards` | Matched | Owner, October 2026 |
| `Banqiao_cards` | Matched | Owner, October 2026 |

The other nine cases are still to be run.

## 3. Values reported by Wu (2016)

From the technical report's Tables 6.2, 6.4, 6.7 and 6.9 and Sections 7.1
and 7.4. Qp peak outflow, B breach width (top, or average where marked
"avg"), Tp time to peak, Tf failure time. Only values the report states are
listed. Measured times for field cases are failure times and for
laboratory cases times to peak, as the report explains in Section 6.1.

| File | Case (report section) | Wu (2016) calculated | Measured |
|---|---|---|---|
| `Teton_cards` | Teton Dam, piping (6.4, case 50) | Qp 64,272.7 m³/s; B 138.83 m avg; Tp 1.455 h; Tf 5.333 h | Qp 65,120 m³/s; B 151 m avg; Tf 4.0 h |
| `BigBay_cards` | Big Bay Dam, piping (6.4, case 26) | Qp 4,853.49 m³/s; B 101.54 m; Tp 0.717 h; Tf 1.319 h | Qp 4,160 m³/s; B 96.0 m; Tf 1.0 h |
| `Banqiao_cards` | Banqiao Dam, clay core (6.3, case 23) | Qp 71,782.9 m³/s; B 430.5 m; Tp 2.314 h; Tf 4.160 h | Qp 78,100 m³/s; B 372 m; Tf 5.5 h |
| `HansonE1S1_cards` | USDA-ARS E1S1, headcut (6.2, case 14) | Qp 5.897 m³/s; B 6.810 m; Tp 0.672 h | Qp 6.53 m³/s; B 6.90 m; Tp 0.666 h |
| `Impactfld03_cards` | IMPACT field test 3, moraine core (6.3, case 22) | Qp 225.9 m³/s | Qp 242 m³/s |
| `Yigong_cards` | Yigong landslide dam (6.1, case 8) | Qp 98,824.7 m³/s; B 314.04 m; Tp 6.909 h; Tf 12.91 h | Qp 94,013 m³/s; B 432 m; Tf 6.17 h |
| `Zwin_cards` | Zwin sea dike (7.1) | Maximum top width 39.2 m; scour depth 3.72 m | Top width 41.0 m |
| `Sutter_cards_BasinVolume` | Sutter Bypass levee (7.4) | Final width 270.4 m (regular basin curve) or 277.9 m (curve with roads) | 274 m |
| `Yahekou_cards`, `Yahekou_R_cards` | Yahekou fuse plug (7.3) | Figures 7.22–7.24 only | Figures 7.22–7.24 |
| `Mecox_cards_WSLbay` | Mecox Inlet (7.2) | Figures 7.15–7.19 only | Figures 7.15–7.19 |

Which basin curve the Sutter file uses is not stated in the file name
alone; check its `Downstream_Storage_Basin` table against the report's
Table 7.3.

## 4. Limits

- The dashboard was built for water-retaining dams. Clay cores are now
  inputs (Model setup, *Clay core* tab) and are drawn, and a clay cover
  given in the file is drawn. For levee and barrier cases it runs the file
  faithfully, but its input checks and case-history comparison do not
  represent covers, water level series, basins or waves.
- Sutter starts at 583,200 s (day 6.75), so its times are reported from
  that origin, as DLBreach writes them.

## Reference

Wu, W. (2016). *Introduction to DLBreach: A Simplified Physically-Based
Dam/Levee Breach Model*, version 2016.4. Technical report, Clarkson
University.
