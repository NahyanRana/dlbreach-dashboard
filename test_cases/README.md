# Test cases

Four small water-retaining dam cases for checking the dashboard end to end:
two overtopping, two piping. All use the same 12 m embankment (crest 5 m,
upstream 3H:1V, downstream 2.5H:1V, 300 m long) and the same dummy
stage-storage curve (a power-law table, not a real facility).

| Case | Failure | Fill | Notes |
|---|---|---|---|
| T1_water_overtopping | Overtopping, 0.5 m × 2 m pilot channel, surface erosion | Non-cohesive, D50 1 mm | Pond 0.3 m above the channel invert |
| T2_water_piping | Piping at mid-height, 0.3 m pipe | Non-cohesive, D50 1 mm | 5 m of head on the pipe |
| T3_water_overtopping | Overtopping, 1 m × 10 m crest settlement, headcut erosion | Cohesive, 30 % clay | Pond 0.5 m above the settled crest |
| T4_water_piping | Piping 3 m above the base, 0.2 m pipe | Cohesive, 30 % clay | 8.5 m of head on the pipe |

**To use:** on the Project page, choose one under *Worked examples* and
press *Load example*, or use *Open project* with the `.json` file. The
`.txt` files are the matching DLBreach inputs and can be run directly with
DLBreach.

The cases are internally consistent (water above the breach, storage at the
pond level) but have not yet been run with DLBreach. Run each once and check
the hydrograph looks reasonable before relying on them for regression
testing. Real cases from Prof. Wu's DLBreach page can be added later.

## Prof. Wu's validation cases

`wu_2016/` holds eleven input files from Prof. Wu's validation of DLBreach
(Wu 2016, Chapters 6 and 7), with the four Mecox data files they name, as
published on his DLBreach page
(<https://webspace.clarkson.edu/~wwu/DLBreach.html>) and unchanged. They
appear under *Worked examples*. They remain Prof. Wu's work and are not
covered by the MIT licence (see `NOTICE.md`). See `docs/WU_VALIDATION.md`.

## Solid waste cases (paused)

The solid waste cases S1 (overtopping) and S2 (piping), for 25 m tailings
dams, are in `solid_waste_paused/` while solid waste support is switched
off; see `TAILINGS_TODO.md`.
