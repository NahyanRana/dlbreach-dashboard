"""
dlbreach_mc.py
--------------
Monte Carlo sampling and batch execution for DLBreach.

The approach follows established practice for probabilistic breach
analysis: define distributions on uncertain input parameters, generate
one input card file per realisation, run them, and collect a result
value from each. Peak outflow is the usual choice, but breach depth,
top width and outflow volume are collected too, since peak discharge
does not always correspond to the worst downstream outcome.

Runs are executed in parallel across separate working directories,
because DLBreach expects its input file to sit beside the executable
and would otherwise overwrite itself.
"""

from __future__ import annotations

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from dlbreach_io import (build_input_text, run_case, parse_out, summarise,
                         write_data_file)


# ---------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------

DISTRIBUTIONS = ["fixed", "uniform", "triangular", "normal", "lognormal"]


def sample_parameter(spec: dict, n: int, rng: np.random.Generator) -> np.ndarray:
    """
    Draw n samples for one parameter.

    `spec` looks like:
        {"dist": "uniform", "low": 0.3, "high": 0.6}
        {"dist": "triangular", "low": 0.3, "mode": 0.4, "high": 0.6}
        {"dist": "normal", "mean": 0.4, "sd": 0.05}
        {"dist": "lognormal", "mean": 10.0, "sd": 3.0}   (mean/sd of the value)
        {"dist": "fixed", "value": 0.4}

    Samples are clipped to `min`/`max` when given, which is how you keep
    a normal distribution from producing a negative porosity.
    """
    d = spec.get("dist", "fixed")

    if d == "fixed":
        vals = np.full(n, float(spec["value"]))
    elif d == "uniform":
        vals = rng.uniform(float(spec["low"]), float(spec["high"]), n)
    elif d == "triangular":
        vals = rng.triangular(float(spec["low"]), float(spec["mode"]),
                              float(spec["high"]), n)
    elif d == "normal":
        vals = rng.normal(float(spec["mean"]), float(spec["sd"]), n)
    elif d == "lognormal":
        m, s = float(spec["mean"]), float(spec["sd"])
        if m <= 0:
            raise ValueError("lognormal mean must be positive")
        # convert mean/sd of the value to the underlying normal parameters
        sigma = np.sqrt(np.log(1.0 + (s / m) ** 2))
        mu = np.log(m) - 0.5 * sigma ** 2
        vals = rng.lognormal(mu, sigma, n)
    else:
        raise ValueError(f"Unknown distribution: {d}")

    lo, hi = spec.get("min"), spec.get("max")
    if lo is not None:
        vals = np.maximum(vals, float(lo))
    if hi is not None:
        vals = np.minimum(vals, float(hi))
    return vals


def build_sample_table(base_params: dict,
                       specs: dict[str, dict],
                       n: int,
                       seed: int | None = None) -> pd.DataFrame:
    """
    Build a table with one row per realisation and one column per
    sampled parameter. Parameters not listed in `specs` stay at their
    base value and are not included as columns.
    """
    rng = np.random.default_rng(seed)
    cols = {}
    for key, spec in specs.items():
        if spec.get("dist", "fixed") == "fixed":
            continue
        cols[key] = sample_parameter(spec, n, rng)
    df = pd.DataFrame(cols)
    df.insert(0, "realisation", np.arange(1, n + 1))
    return df


# ---------------------------------------------------------------------
# Batch execution
# ---------------------------------------------------------------------

HYDRO_POINTS = 320          # points retained per realisation hydrograph
GEOM_COLS = ["time_hr", "Q_breach", "wsl_up", "wsl_down", "breach_bottom_elev",
             "breach_bottom_width", "breach_top_width", "breach_side_slope",
             "breach_flow_area", "cum_volume"]


def _change_index(df: pd.DataFrame, n: int) -> np.ndarray:
    """
    Rows to keep, placed where the hydrograph and breach change fastest.

    Evenly spaced rows over a long simulation leave only a few points across
    a peak that lasts minutes, which draws the peak as a coarse polygon. The
    rows are instead spread evenly in cumulative change of discharge and
    breach geometry, with a small uniform share so quiet periods still
    appear, and the peak row is always kept.
    """
    m = len(df)
    if m <= n:
        return np.arange(m)
    change = np.zeros(m)
    for col, w in (("Q_breach", 1.0), ("breach_top_width", 0.5),
                   ("breach_bottom_elev", 0.5)):
        if col in df.columns:
            a = df[col].to_numpy(dtype=float)
            rng = a.max() - a.min()
            if rng > 1e-12:
                change += w * np.abs(np.diff(a, prepend=a[0])) / rng
    change += 0.2 / m
    cum = np.cumsum(change)
    idx = np.searchsorted(cum, np.linspace(0, cum[-1], n))
    idx = set(np.clip(idx, 0, m - 1).tolist())
    idx |= {0, m - 1, int(np.argmax(df["Q_breach"].to_numpy()))}
    return np.array(sorted(idx))


def _thin_hydrograph(df: pd.DataFrame, n: int = HYDRO_POINTS):
    """One realisation's hydrograph, thinned where it changes least."""
    keep = _change_index(df, n)
    return (df["time_hr"].to_numpy(dtype=float)[keep],
            df["Q_breach"].to_numpy(dtype=float)[keep])


def _thin_geometry(df: pd.DataFrame, n: int = 260) -> pd.DataFrame:
    """Breach geometry through time, thinned, for drawing and animation."""
    keep = _change_index(df, n)
    cols = [c for c in GEOM_COLS if c in df.columns]
    return df.iloc[keep][cols].reset_index(drop=True)


def _run_one(args):
    idx, params, exe_path, worker_dir, timeout = args
    try:
        text = build_input_text(params)
        res = run_case(exe_path, text,
                       case_name=f"mc{idx:06d}",
                       work_dir=worker_dir,
                       timeout=timeout)
        if not res["ok"]:
            return ({"realisation": idx, "ok": False,
                     "error": (res["stderr"] or "no output file")[:300]}, None, None)
        df = parse_out(res["out_path"])
        s = summarise(df, crest_elev=params.get('emb_height'))
        s.update({"realisation": idx, "ok": True, "error": ""})
        hydro = _thin_hydrograph(df)
        geom = _thin_geometry(df)
        # tidy up the per-run files, keep the directory for reuse
        try:
            res["out_path"].unlink(missing_ok=True)
            (Path(worker_dir) / f"mc{idx:06d}.txt").unlink(missing_ok=True)
        except OSError:
            pass
        return (s, hydro, geom)
    except Exception as exc:                     # noqa: BLE001
        return ({"realisation": idx, "ok": False,
                 "error": f"{type(exc).__name__}: {exc}"[:300]}, None, None)


def run_monte_carlo(base_params: dict,
                    sample_df: pd.DataFrame,
                    exe_path: str | Path,
                    n_workers: int = 4,
                    timeout: int = 600,
                    progress_callback=None) -> pd.DataFrame:
    """
    Run every realisation in `sample_df` and return a results table.

    A separate working directory is created for each worker, each with
    its own copy of the executable, so that concurrent runs cannot
    collide over input and output file names.

    `progress_callback(done, total)` is called after each completed run,
    which is what drives the progress bar in the interface.
    """
    exe_path = Path(exe_path).resolve()
    n = len(sample_df)
    sampled_cols = [c for c in sample_df.columns if c != "realisation"]

    import re as _re
    for fname in (base_params.get("data_files") or {}):
        if _re.fullmatch(r"mc\d{6}\.(txt|out)", Path(str(fname)).name, _re.I):
            raise ValueError(f"The data file {fname} has the same name as a "
                             "Monte Carlo run's own files.")

    root = Path(tempfile.mkdtemp(prefix="dlb_mc_"))
    worker_dirs = []
    for w in range(n_workers):
        wd = root / f"w{w}"
        wd.mkdir(parents=True, exist_ok=True)
        shutil.copy2(exe_path, wd / exe_path.name)
        for fname, content in (base_params.get("data_files") or {}).items():
            write_data_file(wd, fname, content)
        worker_dirs.append(wd)

    jobs = []
    for i, row in sample_df.iterrows():
        p = dict(base_params)
        for c in sampled_cols:
            p[c] = float(row[c])
        idx = int(row["realisation"])
        jobs.append((idx, p, exe_path, worker_dirs[i % n_workers], timeout))

    results = []
    hydrographs: dict[int, tuple] = {}
    geoms: dict[int, pd.DataFrame] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(_run_one, j) for j in jobs]
        for fut in as_completed(futures):
            summary, hydro, geom = fut.result()
            results.append(summary)
            if hydro is not None:
                hydrographs[int(summary["realisation"])] = hydro
                geoms[int(summary["realisation"])] = geom
            done += 1
            if progress_callback:
                progress_callback(done, n)

    res_df = pd.DataFrame(results).sort_values("realisation").reset_index(drop=True)
    out = sample_df.merge(res_df, on="realisation", how="left")

    try:
        shutil.rmtree(root, ignore_errors=True)
    except OSError:
        pass

    return out, hydrographs, geoms


# ---------------------------------------------------------------------
# Ensemble hydrographs
# ---------------------------------------------------------------------

def _active_end(series) -> float:
    """Latest time at which any realisation still discharges more than 1 %
    of its own peak. series: iterable of (t, q)."""
    end = 0.0
    for t, q in series:
        t, q = np.asarray(t, float), np.asarray(q, float)
        if len(q) and q.max() > 0:
            k = np.nonzero(q > 0.01 * q.max())[0]
            if k.size:
                end = max(end, float(t[k[-1]]))
    return end


def _ensemble_grid(t_max: float, t_act: float, n_grid: int) -> np.ndarray:
    """Common time grid, four fifths of its points in the active period, so
    peaks and the breach growth are resolved over a long simulation."""
    if not (0 < t_act < t_max):
        return np.linspace(0.0, t_max, n_grid)
    n1 = int(0.8 * n_grid)
    return np.unique(np.concatenate([np.linspace(0.0, t_act, n1),
                                     np.linspace(t_act, t_max, n_grid - n1 + 1)]))


def hydrograph_ensemble(hydrographs: dict[int, tuple],
                        n_grid: int = 400) -> tuple[np.ndarray, np.ndarray]:
    """
    Put every realisation's hydrograph onto a common time grid.

    Realisations end at different times, so each is interpolated onto a
    shared grid running from zero to the longest simulated duration.
    Beyond a realisation's own end time its discharge is taken as zero,
    which is physically what has happened: that breach has finished
    draining.

    Returns the time grid and an array of shape (realisations, n_grid).
    """
    if not hydrographs:
        return np.array([]), np.array([])
    t_max = max(float(t[-1]) for t, _ in hydrographs.values() if len(t))
    grid = _ensemble_grid(t_max, 1.2 * _active_end(hydrographs.values()), n_grid)
    rows = []
    for t, q in hydrographs.values():
        if len(t) < 2:
            continue
        rows.append(np.interp(grid, t, q, left=float(q[0]), right=0.0))
    return grid, np.asarray(rows)


def geometry_ensemble(geoms: dict, column: str, n_grid: int = 400,
                      crest: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """
    Put one breach geometry series of every realisation onto a common grid.

    `column` is a column of the stored geometry (for example
    breach_top_width), or "breach_depth" for crest minus invert, for which
    `crest` gives the embankment height of each realisation (keyed as
    geoms; a single value under the key None applies to all).

    Unlike discharge, breach geometry does not return to zero when a run
    ends: beyond a realisation's own end time its last value is held, which
    is the final breach it reached.
    """
    if not geoms:
        return np.array([]), np.array([])
    t_max = max(float(g["time_hr"].iloc[-1]) for g in geoms.values()
                if g is not None and len(g))
    t_act = _active_end((g["time_hr"], g["Q_breach"]) for g in geoms.values()
                        if g is not None and len(g) and "Q_breach" in g)
    grid = _ensemble_grid(t_max, 1.2 * t_act, n_grid)
    rows = []
    for k, g in geoms.items():
        if g is None or len(g) < 2:
            continue
        t = g["time_hr"].to_numpy(dtype=float)
        if column == "breach_depth":
            H = (crest or {}).get(k, (crest or {}).get(None))
            if H is None:
                continue
            y = float(H) - g["breach_bottom_elev"].to_numpy(dtype=float)
        elif column in g.columns:
            y = g[column].to_numpy(dtype=float)
        else:
            continue
        rows.append(np.interp(grid, t, y, left=float(y[0]), right=float(y[-1])))
    return grid, np.asarray(rows)


ENVELOPE_STATS = ["Min", "P05", "P10", "P25", "Median", "Mean",
                  "P75", "P90", "P95", "Max"]


def hydrograph_percentiles(grid: np.ndarray,
                           curves: np.ndarray,
                           stats=("P05", "Median", "P95")) -> pd.DataFrame:
    """
    Envelope of the ensemble at each time on the grid.

    Any combination of percentiles and summary statistics may be
    requested. Note that none of these curves is itself a model run: each
    traces a statistic of the ensemble through time, so a P95 curve peaks
    below the highest peak of any individual realisation.
    """
    if curves.size == 0:
        return pd.DataFrame()
    lookup = {
        "Min": lambda: curves.min(axis=0),
        "Max": lambda: curves.max(axis=0),
        "Mean": lambda: curves.mean(axis=0),
        "Median": lambda: np.percentile(curves, 50, axis=0),
    }
    data = {}
    for name in stats:
        if name in lookup:
            data[name] = lookup[name]()
        elif name.startswith("P"):
            try:
                data[name] = np.percentile(curves, float(name[1:]), axis=0)
            except ValueError:
                continue
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data, index=np.round(grid, 4))


# ---------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------

def ensemble_statistics(df: pd.DataFrame, column: str) -> dict:
    """Summary statistics and percentiles for one output quantity."""
    s = pd.to_numeric(df.loc[df["ok"] == True, column], errors="coerce").dropna()  # noqa: E712
    if s.empty:
        return {}
    return {
        "n": int(s.size),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)) if s.size > 1 else 0.0,
        "min": float(s.min()),
        "p05": float(s.quantile(0.05)),
        "p25": float(s.quantile(0.25)),
        "median": float(s.median()),
        "p75": float(s.quantile(0.75)),
        "p95": float(s.quantile(0.95)),
        "max": float(s.max()),
    }


def input_output_correlation(df: pd.DataFrame,
                             sampled_cols: list[str],
                             output_col: str) -> pd.DataFrame:
    """
    Rank correlation between each sampled input and a chosen output.

    This is the standard check for whether one parameter is exerting an
    inordinate influence on the result, and is usually more informative
    than the output distribution on its own.

    Spearman's coefficient is the Pearson correlation of the ranks, so it
    is computed directly here rather than through scipy, which keeps the
    package requirements to three.
    """
    ok = df[df["ok"] == True]  # noqa: E712
    rows = []
    for c in sampled_cols:
        x = pd.to_numeric(ok[c], errors="coerce")
        y = pd.to_numeric(ok[output_col], errors="coerce")
        m = x.notna() & y.notna()
        if m.sum() > 2:
            rx = x[m].rank()
            ry = y[m].rank()
            denom = rx.std(ddof=0) * ry.std(ddof=0)
            rho = float("nan") if denom == 0 else float(
                ((rx - rx.mean()) * (ry - ry.mean())).mean() / denom)
            rows.append({"parameter": c, "rank correlation": rho})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["abs"] = out["rank correlation"].abs()
        out = out.sort_values("abs", ascending=False).drop(columns="abs")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------
# Representative realisations
# ---------------------------------------------------------------------

def representative_realisation(results: pd.DataFrame,
                               column: str,
                               statistic: str) -> int | None:
    """
    Find the realisation that best represents a statistic of the ensemble.

    A percentile of the ensemble is not itself a model run. Taking the
    95th percentile of each geometric quantity independently would
    produce a breach that no realisation produced, and whose widths need
    not even be consistent with its own side slope and depth.

    Instead the run whose value of `column` lies closest to the requested
    statistic is returned. That geometry is real, internally consistent,
    and traceable to a specific set of sampled inputs.

    Returns the index into `results`, or None if nothing is available.
    """
    ok = results[results["ok"] == True]  # noqa: E712
    if ok.empty or column not in ok.columns:
        return None
    vals = pd.to_numeric(ok[column], errors="coerce").dropna()
    if vals.empty:
        return None

    if statistic == "Min":
        target = vals.min()
    elif statistic == "Max":
        target = vals.max()
    elif statistic == "Mean":
        target = vals.mean()
    elif statistic == "Median":
        target = vals.median()
    elif statistic.startswith("P"):
        try:
            target = vals.quantile(float(statistic[1:]) / 100.0)
        except ValueError:
            return None
    else:
        return None

    return int((vals - target).abs().idxmin())


def realisation_state(results: pd.DataFrame, idx: int) -> dict:
    """
    Build the final breach state of one realisation, in the form the
    face-view drawing expects.
    """
    r = results.loc[idx]
    return {
        "breach_bottom_width": float(r.get("final_bottom_width_m", 0.0) or 0.0),
        "breach_top_width": float(r.get("final_top_width_m", 0.0) or 0.0),
        "breach_bottom_elev": float(r.get("final_bottom_elev_m", 0.0) or 0.0),
        "breach_side_slope": float(r.get("final_side_slope", 0.0) or 0.0),
        "wsl_up": float(r.get("final_bottom_elev_m", 0.0) or 0.0),
        "time_hr": float(r.get("simulated_duration_hr", 0.0) or 0.0),
        "Q_breach": float(r.get("peak_outflow_m3s", 0.0) or 0.0),
    }


def realisation_params(base_params: dict,
                       results: pd.DataFrame,
                       idx: int,
                       sampled_cols: list[str]) -> dict:
    """
    Rebuild the parameter set used by one realisation.

    Sampled parameters vary between realisations, so the dam geometry
    that frames the drawing must come from that run rather than from the
    base configuration.
    """
    p = dict(base_params)
    r = results.loc[idx]
    for c in sampled_cols:
        if c in results.columns and pd.notna(r.get(c)):
            p[c] = float(r[c])
    return p


# ---------------------------------------------------------------------
# Guarding against samples that cannot matter or cannot be valid
# ---------------------------------------------------------------------

ALL_CANDIDATES = {
    "emb_height": "Embankment height (m)",
    "emb_crest_width": "Crest width (m)",
    "emb_us_slope": "Upstream slope (V/H)",
    "emb_ds_slope": "Downstream slope (V/H)",
    "emb_length": "Base length (m)",
    "manning_n": "Breach Manning n",
    "hard_bottom_elev": "Hard bottom elevation (m)",
    "sed_d50": "Grain diameter (m)",
    "sed_porosity": "Porosity",
    "sed_clay": "Clay content",
    "sed_cohesion": "Cohesion (Pa)",
    "sed_friction": "tan(phi)",
    "adaptation_lambda": "Adaptation lambda",
    "kd": "Erodibility kd",
    "tauc": "Critical shear stress (Pa)",
    "headcut_coef": "Headcut coefficient",
    "res_VH": "Reservoir volume at H (m3)",
    "wsl_up_initial": "Initial upstream WSL (m)",
    "pilot_depth": "Pilot breach depth (m)",
    "pilot_width": "Pilot breach width (m)",
    "pipe_depth": "Pipe depth below crest (m)",
    "pipe_width": "Initial pipe width (m)",
    "core_center": "Core offset from crest centre (m)",
    "core_d50": "Core grain diameter (m)",
    "core_cohesion": "Core cohesion (Pa)",
    "core_friction": "Core tan(phi)",
    "core_kd": "Core erodibility kd",
    "core_tauc": "Core critical shear stress (Pa)",
}
CORE_KEYS = {k for k in ALL_CANDIDATES if k.startswith("core_")}


def relevant_candidates(p: dict) -> dict:
    """
    Parameters that actually influence a run in the current configuration.

    Sampling a parameter the model ignores costs run time and, worse,
    suggests uncertainty has been explored when it has not. Erodibility
    kd and critical shear stress apply only to cohesive fill; the
    adaptation length only to non-cohesive; pilot notch dimensions only
    to overtopping; pipe dimensions only to piping; the headcut
    coefficient only to headcut erosion; and a single reference volume
    only where the stage-storage relation is defined by one.
    """
    cohesive = int(p.get("sediment_type", 1)) == 2
    piping = int(p.get("breach_mode", 1)) == 2
    headcut = (not piping) and int(p.get("overtopping_mode", 1)) == 2
    rm = int(p.get("reservoir_method", 2))
    drop = set()
    drop |= {"adaptation_lambda"} if cohesive else {"kd", "tauc"}
    drop |= {"pilot_depth", "pilot_width"} if piping else {"pipe_depth", "pipe_width"}
    if not headcut:
        drop.add("headcut_coef")
    if rm not in (2, 3):
        drop.add("res_VH")
    # the core is used only for overtopping submode 3 (Wu 2016)
    core = (p.get("has_core") and not piping
            and int(p.get("overtopping_mode", 1)) == 3)
    if not core:
        drop |= CORE_KEYS
    elif int(p.get("core_sed_type", 2)) != 2:
        drop |= {"core_kd", "core_tauc"}
    return {k: v for k, v in ALL_CANDIDATES.items()
            if k not in drop and affects_input(p, k)}


def affects_input(p: dict, key: str) -> bool:
    """
    Whether changing this parameter changes the input file DLBreach reads.
    A loaded case can make an input inert (a water level series replaces the
    reservoir, a card the file omitted stays omitted); sampling such an
    input would wrongly suggest the result is insensitive to it.
    """
    try:
        v = float(p.get(key))
    except (TypeError, ValueError):
        return True
    base = build_input_text(p)
    return build_input_text(dict(p, **{key: v * 1.37 + 0.011})) != base


def constraint_violations(base_params: dict,
                          sample_df: pd.DataFrame) -> list[str]:
    """
    Check sampled realisations for physically inconsistent combinations
    before any are run, and describe how many are affected.
    """
    msgs = []
    n = len(sample_df)
    if n == 0:
        return msgs

    def col(name):
        if name in sample_df.columns:
            return sample_df[name].astype(float).to_numpy()
        return np.full(n, float(base_params.get(name, 0.0)))

    H, wsl, hb = col("emb_height"), col("wsl_up_initial"), col("hard_bottom_elev")
    k = int(np.sum(wsl > H))
    if k:
        msgs.append(f"{k} of {n} realisations place the initial water level "
                    f"above the crest.")
    if int(base_params.get("breach_mode", 1)) == 2:
        k = int(np.sum(col("pipe_depth") >= H))
        if k:
            msgs.append(f"{k} of {n} realisations place the pipe at or below "
                        f"the embankment base.")
    curve = base_params.get("res_curve") or []
    if int(base_params.get("reservoir_method", 2)) in (0, 1) and curve:
        lo = min(z for z, _ in curve)
        k = int(np.sum(hb < lo - 1e-6))
        if k:
            msgs.append(f"{k} of {n} realisations place the erosion limit "
                        f"below the lowest level of the stage-storage table "
                        f"({lo:g} m); if the pond falls that far, DLBreach works "
                        f"outside the table.")
    k = int(np.sum(hb >= H))
    if k:
        msgs.append(f"{k} of {n} realisations place the erosion limit at or "
                    f"above the crest, so no breach can form.")
    if (base_params.get("has_core") and int(base_params.get("breach_mode", 1)) == 1
            and int(base_params.get("overtopping_mode", 1)) == 3):
        from dlbreach_viz import core_outside
        keys = [c for c in sample_df.columns if c in base_params]
        k = sum(1 for _, r in sample_df.iterrows()
                if core_outside(dict(base_params, **{c: float(r[c]) for c in keys})))
        if k:
            msgs.append(f"{k} of {n} realisations place the clay core above the "
                        f"crest or outside the embankment section.")
    return msgs
