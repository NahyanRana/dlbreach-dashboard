"""
dlbreach_batch.py
-----------------
Three things that deal with many runs or with files leaving the app:

  1. Scenario tables — a standard format for sensitivity runs
     (e.g. Runs 1-7), read from CSV or Excel.
  2. Batch packages — input files plus a Windows batch script, zipped,
     so that runs can be made on a machine with DLBreach and the outputs
     brought back. This is how the browser version handles any run.
  3. Breach geometry development exported as a text file.

Scenario table format
---------------------
One row per run. The first column is "Run", holding a label for the
run. Every other column is a parameter. Column headings may be any of:

  * the dashboard key            e.g.  sed_d50
  * the DLBreach card name       e.g.  Sediment_Diameter
  * the label shown in the app   e.g.  Grain diameter (m)

A blank cell means "use the base case value". Parameters not given a
column are taken from the base case on Model setup. Values are in the
model datum (metres above embankment base) and in the units of the
corresponding DLBreach card.
"""

from __future__ import annotations

import io
import re
import zipfile

import numpy as np
import pandas as pd

from dlbreach_io import DEFAULT_PARAMS, _CARD_MAP, parse_out, summarise
from dlbreach_mc import ALL_CANDIDATES

# Parameters a scenario may vary. Structural settings (breach mode,
# sediment type, stage-storage method) are included because sensitivity
# studies often switch them between runs.
SCENARIO_KEYS = sorted(set(ALL_CANDIDATES) | {
    "breach_mode", "overtopping_mode", "sediment_type", "breach_location",
    "sed_sg", "time_step", "sim_end", "res_AH", "res_H", "res_m",
    "wsl_down_initial", "ds_channel_width", "ds_channel_slope",
    "ds_channel_n", "pipe_head_loss", "headcut_model", "water_density",
})

INTEGER_KEYS = {"breach_mode", "overtopping_mode", "sediment_type",
                "headcut_model"}


def _alias_map() -> dict:
    """Every accepted heading, normalised, mapped to its dashboard key."""
    def norm(s):
        return re.sub(r"[^a-z0-9]+", "", str(s).lower())
    m = {}
    for k in SCENARIO_KEYS:
        m[norm(k)] = k
        if k in ALL_CANDIDATES:
            m[norm(ALL_CANDIDATES[k])] = k
    for card, (keys, _t) in _CARD_MAP.items():
        if len(keys) == 1 and keys[0] in SCENARIO_KEYS:
            m[norm(card)] = keys[0]
    return m


_ALIASES = _alias_map()


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def scenario_template(base: dict, keys: list[str] | None = None,
                      n_runs: int = 3) -> pd.DataFrame:
    """A starting table the user can fill in, pre-populated with the base
    values so that each run only needs the parameters it changes."""
    keys = keys or ["sed_d50", "manning_n", "hard_bottom_elev"]
    rows = []
    for i in range(1, n_runs + 1):
        row = {"Run": f"Run{i}"}
        for k in keys:
            row[k] = base.get(k, DEFAULT_PARAMS.get(k))
        rows.append(row)
    return pd.DataFrame(rows)


def read_scenario_table(data: bytes, filename: str) -> tuple[pd.DataFrame, dict]:
    """
    Read a scenario table from CSV or Excel bytes.

    Returns the parsed table (Run plus dashboard keys) and a report of
    what was recognised, ignored and rejected, so the user can see
    exactly how their headings were interpreted.
    """
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        raw = pd.read_excel(io.BytesIO(data))
    else:
        raw = pd.read_csv(io.BytesIO(data))
    raw = raw.dropna(how="all")
    if raw.empty:
        raise ValueError("The table is empty.")

    cols = list(raw.columns)
    run_col = next((c for c in cols if _norm(c) in ("run", "runid", "case",
                                                    "scenario", "name")),
                   cols[0])
    mapping, unknown = {}, []
    for c in cols:
        if c == run_col:
            continue
        key = _ALIASES.get(_norm(c))
        if key:
            mapping[c] = key
        else:
            unknown.append(str(c))

    out = pd.DataFrame({"Run": raw[run_col].astype(str).str.strip()})
    bad = []
    for c, key in mapping.items():
        vals = pd.to_numeric(raw[c], errors="coerce")
        nonblank = raw[c].notna() & (raw[c].astype(str).str.strip() != "")
        n_bad = int((vals.isna() & nonblank).sum())
        if n_bad:
            bad.append(f"{c}: {n_bad} value(s) not numeric")
        out[key] = vals.to_numpy()

    dup = out["Run"][out["Run"].duplicated()].tolist()
    report = {"run_column": str(run_col),
              "recognised": {str(c): k for c, k in mapping.items()},
              "unrecognised": unknown, "non_numeric": bad,
              "duplicate_runs": dup, "n_runs": len(out)}
    return out, report


def scenario_params(base: dict, row: pd.Series) -> dict:
    """Parameters for one scenario: the base case with the row applied."""
    p = dict(base)
    for k, v in row.items():
        if k == "Run" or pd.isna(v):
            continue
        p[k] = int(round(float(v))) if k in INTEGER_KEYS else float(v)
    return p


def safe_case_name(label: str, i: int) -> str:
    """A case name DLBreach will accept as a file stem."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", str(label)).strip("_")
    return s[:40] or f"case{i:03d}"


# ---------------------------------------------------------------------
# Batch packages
# ---------------------------------------------------------------------

def make_batch_zip(cases: list[tuple[str, str]],
                   extra: dict[str, str] | None = None,
                   exe_name: str = "DLBreach.exe") -> bytes:
    """
    Zip a set of input files with a Windows batch script that runs them.

    `cases` is a list of (case_name, input_text). DLBreach reads its input
    from the folder it runs in and asks for the case name on screen, so
    the script pipes each name to the executable in turn. The user copies
    their own DLBreach executable into the unzipped folder; it is not
    included.
    """
    lines = ["@echo off",
             "REM Runs every DLBreach case in this folder.",
             "REM Copy your DLBreach executable into this folder first and,",
             "REM if its name differs, change EXE below.",
             "cd /d \"%~dp0\"",
             f"set EXE={exe_name}",
             "if not exist \"%EXE%\" (",
             "  echo Could not find %EXE% in this folder.",
             "  pause",
             "  exit /b 1",
             ")"]
    for name, _ in cases:
        lines.append(f"echo Running {name} ...")
        lines.append(f"echo {name}| \"%EXE%\" > nul")
    lines += ["echo.", "echo All runs finished. Zip the .out files and upload them.",
              "pause"]
    readme = (
        "DLBreach batch\r\n"
        "==============\r\n\r\n"
        "1. Unzip this folder somewhere local (not a synced folder).\r\n"
        f"2. Copy your DLBreach executable into it ({exe_name}).\r\n"
        "3. Double-click run_all.bat and wait for it to finish.\r\n"
        "4. Select all the .out files, right-click, Send to > Compressed\r\n"
        "   (zipped) folder, and upload that zip back to the dashboard.\r\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in cases:
            z.writestr(f"{name}.txt", text.replace("\n", "\r\n"))
        z.writestr("run_all.bat", "\r\n".join(lines) + "\r\n")
        z.writestr("README.txt", readme)
        for fname, content in (extra or {}).items():
            parts = [x for x in str(fname).replace("\\", "/").split("/")
                     if x not in ("", ".")]
            if parts and ".." not in parts and ":" not in parts[0]:
                z.writestr("/".join(parts), content)
    return buf.getvalue()


def read_outputs(files: list[tuple[str, bytes]]) -> dict[str, pd.DataFrame]:
    """
    Parse DLBreach output files, given as (filename, bytes). A zip may be
    supplied among them and is expanded. Returns case name -> results.
    """
    import tempfile
    from pathlib import Path
    found: dict[str, bytes] = {}
    for fname, data in files:
        if fname.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.filename.lower().endswith(".out"):
                        found[Path(info.filename).stem] = z.read(info)
        elif fname.lower().endswith(".out"):
            found[Path(fname).stem] = data
    out = {}
    with tempfile.TemporaryDirectory() as td:
        for stem, data in found.items():
            f = Path(td) / f"{stem}.out"
            f.write_bytes(data)
            try:
                out[stem] = parse_out(f)
            except Exception:                         # noqa: BLE001
                continue
    return out


def summarise_cases(case_params: dict[str, dict],
                    outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One summary row per case that has an output."""
    rows = []
    for name, p in case_params.items():
        df = outputs.get(name)
        if df is None:
            rows.append({"Run": name, "ok": False})
            continue
        s = summarise(df, crest_elev=p.get("emb_height"))
        s.update({"Run": name, "ok": True})
        rows.append(s)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Breach geometry development as text
# ---------------------------------------------------------------------

def geometry_text(df: pd.DataFrame, p: dict, interval_min: float = 5.0,
                  z_off: float = 0.0, z_label: str = "m above embankment base",
                  case: str = "") -> str:
    """
    Breach geometry through time as a tab-delimited text file.

    Rows are taken at the requested interval, and the rows at peak
    discharge and at the end of the run are always included. Elevations
    are given in the display datum requested; widths, depths and flows
    are unaffected by the datum.
    """
    H = float(p.get("emb_height", 0.0))
    t = df["time_hr"].to_numpy(dtype=float)
    step_h = max(float(interval_min), 0.01) / 60.0
    targets = np.arange(t[0], t[-1] + 1e-9, step_h)
    idx = set(int(np.searchsorted(t, x)) for x in targets)
    idx |= {0, len(df) - 1, int(df["Q_breach"].idxmax())}
    idx = sorted(i for i in idx if 0 <= i < len(df))
    sub = df.iloc[idx]

    zsl = sub["breach_side_slope"].to_numpy(dtype=float)
    zb_all = sub["breach_bottom_elev"].to_numpy(dtype=float)
    if int(p.get("breach_mode", 1)) == 2:
        z_pipe0 = H - float(p.get("pipe_depth", 0.0))
        tol = max(0.02 * H, 0.10)
        stage = np.where(zb_all >= z_pipe0 - tol, "piping", "open")
    else:
        stage = np.full(len(sub), "open")
    out = pd.DataFrame({
        "stage": stage,
        "time_h": sub["time_hr"].to_numpy(),
        "time_min": sub["time_hr"].to_numpy() * 60.0,
        "Q_breach_m3s": sub["Q_breach"].to_numpy(),
        "reservoir_level": sub["wsl_up"].to_numpy() + z_off,
        "breach_invert": sub["breach_bottom_elev"].to_numpy() + z_off,
        "breach_depth_m": H - sub["breach_bottom_elev"].to_numpy(),
        "bottom_width_m": sub["breach_bottom_width"].to_numpy(),
        "top_width_m": sub["breach_top_width"].to_numpy(),
        "avg_width_m": (sub["breach_bottom_width"].to_numpy()
                        + sub["breach_top_width"].to_numpy()) / 2.0,
        "side_slope_H_per_V": np.where(zsl > 1e-6, 1.0 / np.maximum(zsl, 1e-6),
                                       np.nan),
        "cum_volume_m3": sub["cum_volume"].to_numpy(),
    })
    head = [
        "# DLBreach breach geometry development",
        f"# Case: {case or p.get('case_name', '')}",
        f"# Elevations (reservoir_level, breach_invert): {z_label}",
        f"# Crest elevation: {H + z_off:.3f}",
        f"# Output interval: {interval_min:g} min; peak and final rows included",
        "# Top width is referenced to crest level, as reported by DLBreach.",
        "# stage = piping: the pipe is still enlarging inside the embankment",
        "#   and the crest is intact; widths in those rows describe the",
        "#   equivalent trapezoid DLBreach reports, not an opening in the crest.",
        "# Columns are tab-delimited",
    ]
    body = out.to_csv(sep="\t", index=False, float_format="%.4f")
    return "\n".join(head) + "\n" + body


def ensemble_from_outputs(base: dict, sample_df: pd.DataFrame,
                          outputs: dict[str, pd.DataFrame],
                          name_fn=lambda i: f"mc{i:06d}"):
    """
    Rebuild a Monte Carlo results table from uploaded output files, in the
    same form the local runner produces, so the rest of the page is the
    same whichever way the runs were made.
    """
    from dlbreach_mc import _thin_geometry, _thin_hydrograph
    rows, hydros, geoms = [], {}, {}
    cols = [c for c in sample_df.columns if c != "realisation"]
    for _, r in sample_df.iterrows():
        i = int(r["realisation"])
        df = outputs.get(name_fn(i))
        if df is None:
            rows.append({"realisation": i, "ok": False,
                         "error": "no output file uploaded"})
            continue
        p = dict(base)
        for c in cols:
            p[c] = float(r[c])
        s = summarise(df, crest_elev=p.get("emb_height"))
        s.update({"realisation": i, "ok": True, "error": ""})
        rows.append(s)
        hydros[i] = _thin_hydrograph(df)
        geoms[i] = _thin_geometry(df)
    res = sample_df.merge(pd.DataFrame(rows), on="realisation", how="left")
    return res, hydros, geoms


# ---------------------------------------------------------------------
# Scenario grid: runs as columns, parameters as rows (Run Log layout)
# ---------------------------------------------------------------------
import dlbreach_units as U

GROUP_ROW = "Scenario group"


# Phrasings seen in practitioner run logs and DBA input tables.
SYNONYMS = {
    "emb_height": ["height", "height from ground", "dam height",
                   "embankment height", "height above ground"],
    "emb_length": ["length", "crest length", "embankment length", "dam length"],
    "emb_crest_width": ["crest width", "crest"],
    "sed_d50": ["d50", "psd median d50", "median d50", "particle size distribution median d50",
                "median grain size", "grain size"],
    "sed_sg": ["specific gravity", "gs", "sg"],
    "sed_clay": ["clay size fraction", "clay content", "clay fraction", "clay"],
    "sed_friction": ["internal friction angle", "friction angle", "phi"],
    "sed_cohesion": ["cohesion", "c"],
    "wsl_up_initial": ["peak pond level", "pond level", "initial pond level",
                       "reservoir level", "initial water level"],
    "beach_level": ["tailings beach level", "beach level", "tailings surface",
                    "tailings level"],
    "hard_bottom_elev": ["hard bottom", "hard bottom elevation", "erosion limit"],
    "manning_n": ["manning n", "mannings n", "breach manning n"],
    "pilot_depth": ["pilot channel height", "pilot channel depth"],
    "pilot_width": ["pilot channel width"],
}


def _strip_units(s: str) -> str:
    return re.sub(r"\(.*?\)", "", str(s)).strip()


def _grid_aliases() -> dict:
    m = {}
    for k in U.CATALOGUE:
        for name in (k, U.label(k), U.label_unit(k)):
            m[_norm(name)] = k
            m[_norm(_strip_units(name))] = k
    for k, names in SYNONYMS.items():
        for name in names:
            m[_norm(name)] = k
    for card, (keys, _t) in _CARD_MAP.items():
        if len(keys) == 1 and keys[0] in U.CATALOGUE:
            m[_norm(card)] = keys[0]
    return m


_GRID_ALIASES = _grid_aliases()


def grid_template(base: dict, keys: list[str], runs: list[str],
                  groups: dict[str, str] | None = None) -> pd.DataFrame:
    """
    A scenario grid pre-filled with the base case, in display units.
    First row holds an optional group label per run (e.g. Sunny day).
    """
    groups = groups or {}
    rows = [{"Parameter": GROUP_ROW, "Unit": "",
             **{r: groups.get(r, "") for r in runs}}]
    for k in keys:
        if k == "bulk_unit_weight":
            v = base.get("bulk_unit_weight", 20.0)
        elif k == "sed_saturation":
            v = U.from_model(k, base.get("sed_saturation", 1.0))
        else:
            v = U.from_model(k, base.get(k, DEFAULT_PARAMS.get(k)))
        rows.append({"Parameter": U.label(k), "Unit": U.unit(k),
                     **{r: (round(v, 6) if isinstance(v, float) else v)
                        for r in runs}})
    return pd.DataFrame(rows)


def read_grid(df: pd.DataFrame) -> tuple[dict, dict]:
    """
    Read a scenario grid (from the editor or an uploaded file).

    Returns ({run: {key: model value}}, report). Unrecognised rows and
    non-numeric cells are reported rather than silently dropped; blank
    cells are omitted so the base value applies.
    """
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    pcol = next((c for c in df.columns if _norm(c) in ("parameter", "inputparameter")),
                df.columns[0])
    skip = {pcol} | {c for c in df.columns if _norm(c) in ("unit", "units", "")}
    runs = [c for c in df.columns if c not in skip and not c.lower().startswith("unnamed")]
    out = {r: {} for r in runs}
    groups, unknown, bad = {}, [], []
    for _, row in df.iterrows():
        name = str(row[pcol]).strip()
        if not name or name.lower() == "nan":
            continue
        if _norm(name) == _norm(GROUP_ROW):
            groups = {r: ("" if pd.isna(row[r]) else str(row[r])) for r in runs}
            continue
        key = (_GRID_ALIASES.get(_norm(name))
               or _GRID_ALIASES.get(_norm(_strip_units(name))))
        if not key:
            unknown.append(name)
            continue
        for r in runs:
            val = row[r]
            if val is None or (isinstance(val, float) and np.isnan(val)) or \
                    str(val).strip() in ("", "N/A", "n/a", "-", "—"):
                continue
            s = str(val).strip()
            m = re.match(r"^\s*([\d.]+)\s*H\s*:\s*([\d.]+)\s*V\s*$", s, re.I)
            if m:                                   # "3H:1V"
                num = float(m.group(1)) / float(m.group(2))
            else:
                try:
                    num = float(s.replace(",", ""))
                except ValueError:
                    bad.append(f"{name} / {r}: '{s}'")
                    continue
            if key == "bulk_unit_weight":
                out[r][key] = num
            else:
                out[r][key] = U.to_model(key, num)
    report = {"runs": runs, "groups": groups, "unrecognised": unknown,
              "non_numeric": bad}
    return out, report


def grid_params(base: dict, values: dict) -> dict:
    """Base case with one run's values applied, porosity derived if asked."""
    p = dict(base)
    p.update(values)
    if "bulk_unit_weight" in values:
        p["porosity_from_bulk"] = True
    return U.apply_derived(p)


def read_grid_file(data: bytes, filename: str) -> pd.DataFrame:
    """
    Load a scenario grid from CSV or Excel, including report-style sheets
    such as a run log with a title row, a row of run names, a row of
    scenario descriptions and parameter labels spread over two columns.

    The run-name row is found as the first row in which several cells
    look like run labels (Run 1, Sensitivity 2, Case 3, ...). Parameter
    labels are taken from the right-most text cell before the first run
    column. A row directly below the run names holding text only is read
    as the scenario group row.
    """
    import io as _io
    if filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raw = pd.read_excel(_io.BytesIO(data), header=None)
    else:
        raw = pd.read_csv(_io.BytesIO(data), header=None)
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    pat = re.compile(r"^(run|sensitivity|case|scenario|sens)\s*[-_ ]?\s*\w+", re.I)
    hdr_i, run_cols = None, []
    for i in range(min(len(raw), 15)):
        hits = [j for j, v in enumerate(raw.iloc[i]) if isinstance(v, str)
                and pat.match(v.strip())]
        if len(hits) >= 1 and (len(hits) >= 2 or i < 3):
            hdr_i, run_cols = i, hits
            break
    if hdr_i is None:                       # already in simple column form
        df = raw.copy()
        df.columns = [str(c) for c in df.iloc[0]]
        return df.iloc[1:].reset_index(drop=True)
    first_run = run_cols[0]
    names = [str(raw.iat[hdr_i, j]).strip() for j in run_cols]
    # columns headed "Unit" or "Units" (as in the dashboard's own download)
    # hold units, not parameter labels
    label_cols = [j for j in range(first_run)
                  if _norm(str(raw.iat[hdr_i, j])) not in ("unit", "units")]
    rows = []
    for i in range(hdr_i + 1, len(raw)):
        labels = [str(raw.iat[i, j]).strip() for j in label_cols
                  if isinstance(raw.iat[i, j], str) and str(raw.iat[i, j]).strip()]
        vals = [raw.iat[i, j] for j in run_cols]
        if not labels:
            if i == hdr_i + 1 and any(isinstance(v, str) for v in vals):
                rows.append([GROUP_ROW] + ["" if pd.isna(v) else v for v in vals])
            continue
        if i == hdr_i + 1 and all((isinstance(v, str) or pd.isna(v)) for v in vals) \
                and any(isinstance(v, str) for v in vals):
            rows.append([GROUP_ROW] + ["" if pd.isna(v) else v for v in vals])
            continue
        if all(pd.isna(v) for v in vals):
            continue                        # notes and section headings
        rows.append([labels[-1]] + list(vals))
    df = pd.DataFrame(rows, columns=["Parameter"] + names)
    # carry a scenario group forward across merged cells
    g = df[df["Parameter"] == GROUP_ROW]
    if not g.empty:
        last = ""
        for c in names:
            v = str(g.iloc[0][c]).strip()
            last = v if v and v.lower() != "nan" else last
            df.loc[g.index[0], c] = last
    return df
