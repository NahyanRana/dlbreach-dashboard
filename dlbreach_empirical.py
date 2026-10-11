"""
dlbreach_empirical.py
---------------------
Empirical breach equations, and the quantities needed to evaluate them
consistently from a DLBreach run.

Two distinct families are implemented and must not be conflated:

  * Peak discharge and breach parameter equations derived from
    WATER-RETAINING dam failures (Froehlich and others). No recorded
    peak outflow exists for any tailings dam failure, so for a tailings
    facility these provide a comparison against water-dam experience,
    not a validation.

  * Eroded dam volume equations (Adria et al.) derived from a combined
    set of water-retaining and TAILINGS dam failures, and intended for
    tailings application.

Every equation carries its published error statistic, so predictions can
be shown with the uncertainty the original authors reported rather than
as bare numbers. See dlbreach_data.CITATIONS for the sources.

All quantities are SI: metres, cubic metres, seconds unless stated.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

G = 9.807


# =====================================================================
# Quantities derived from a DLBreach configuration and result
# =====================================================================

def storage_at(p: dict, level: float) -> float | None:
    """
    Storage volume at a given water level, from the model's own
    stage-storage description.

    Using the model's curve rather than a separately entered figure is
    what keeps the empirical comparison internally consistent: the
    equations are then evaluated on the same impoundment the simulation
    routed.
    """
    method = int(p.get("reservoir_method", 2))
    curve = p.get("res_curve") or []

    if method == 0 and len(curve) >= 2:
        z = np.array([c[0] for c in curve], dtype=float)
        v = np.array([c[1] for c in curve], dtype=float)
        order = np.argsort(z)
        return float(np.interp(level, z[order], v[order]))

    if method == 1 and len(curve) >= 2:
        # stage-area table, integrated to a volume by the trapezoidal rule
        z = np.array([c[0] for c in curve], dtype=float)
        a = np.array([c[1] for c in curve], dtype=float)
        order = np.argsort(z)
        z, a = z[order], a[order]
        vol = np.concatenate([[0.0], np.cumsum(np.diff(z) * (a[1:] + a[:-1]) / 2)])
        return float(np.interp(level, z, vol))

    H = float(p.get("res_H", 0.0) or 0.0)
    if H <= 0:
        return None
    if method == 2:
        # volume and area known at H; exponent implied by the pair
        VH = float(p.get("res_VH", 0.0) or 0.0)
        AH = float(p.get("res_AH", 0.0) or 0.0)
        if VH <= 0 or AH <= 0:
            return None
        m = AH * H / VH                       # V = AH*H/(m+1) => m from pair
        m = max(m - 1.0, 0.1) if m > 1 else 1.0
        return VH * (level / H) ** (m + 1)
    if method == 3:
        VH = float(p.get("res_VH", 0.0) or 0.0)
        m = float(p.get("res_m", 2.0) or 2.0)
        return VH * (level / H) ** (m + 1) if VH > 0 else None
    if method == 4:
        AH = float(p.get("res_AH", 0.0) or 0.0)
        m = float(p.get("res_m", 2.0) or 2.0)
        if AH <= 0:
            return None
        return (AH * H / (m + 1)) * (level / H) ** (m + 1)
    return None


def average_embankment_width(p: dict) -> float:
    """
    Average embankment width in the upstream-downstream direction.

    Froehlich's W_avg is the mean of the crest width and the base width
    of the section.
    """
    H = float(p.get("emb_height", 0.0))
    Wc = float(p.get("emb_crest_width", 0.0))
    Su = max(float(p.get("emb_us_slope", 0.4)), 1e-6)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 1e-6)
    base = Wc + H * (1.0 / Su + 1.0 / Sd)
    return (Wc + base) / 2.0


def eroded_dam_volume(p: dict, bb: float, zb: float, zsl: float) -> float:
    """
    Volume of embankment removed by the breach, from the final geometry.

    The breach is integrated elevation by elevation: at each level the
    opening width is multiplied by the thickness of the embankment
    section at that level. This is the same geometric idea as the
    Washington Guidelines relations, evaluated numerically so that it
    holds for any combination of slopes and crest width.
    """
    H = float(p.get("emb_height", 0.0))
    Wc = float(p.get("emb_crest_width", 0.0))
    Su = max(float(p.get("emb_us_slope", 0.4)), 1e-6)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 1e-6)
    if H <= zb or bb < 0:
        return 0.0
    # Only embankment is counted: where the erosion limit lies below the
    # base (scour into the foundation), integrate from the base up. The
    # opening width at each level still follows from the invert.
    zs = np.linspace(max(zb, 0.0), H, 400)
    width = bb + 2.0 * (zs - zb) / max(zsl, 1e-6)          # opening width
    thick = Wc + (H - zs) * (1.0 / Su + 1.0 / Sd)          # section thickness
    return float(np.trapezoid(width * thick, zs))


def _onset_index(df: pd.DataFrame) -> int:
    """
    Row at which breach formation begins.

    Froehlich defines formation as starting when rapid downward erosion
    of the breach begins, after the initiation phase. For a piping
    failure the pipe may enlarge for some time before its roof collapses;
    that enlargement is initiation, not formation, so only downcutting of
    the invert is used as the trigger here. Widening alone does not start
    the clock.
    """
    zb = df["breach_bottom_elev"].to_numpy(dtype=float)
    z0 = zb[0]
    moved = np.where(zb < z0 - 0.02 * max(abs(z0), 1.0))[0]
    return int(moved[0]) if len(moved) else 0


def formation_time_hr(df: pd.DataFrame, tol: float = 1e-3) -> float | None:
    """
    Breach formation time taken from the simulation.

    Measured from the onset of downcutting to the first moment the breach
    reaches its final geometry, taken as the first time the top width is
    within `tol` of its final value. This follows the definition used by
    Froehlich (2008, 2016): the time from the start of rapid downward
    erosion to the end of significant lateral enlargement.
    """
    if "breach_top_width" not in df or "time_hr" not in df or len(df) < 3:
        return None
    bt = df["breach_top_width"].to_numpy(dtype=float)
    t = df["time_hr"].to_numpy(dtype=float)
    if bt[-1] <= 0:
        return None
    reached = np.where(bt >= bt[-1] * (1.0 - tol))[0]
    if len(reached) == 0:
        return None
    i_end, i_start = int(reached[0]), _onset_index(df)
    if i_end <= i_start:
        return None
    return float(t[i_end] - t[i_start])


def downcutting_time_hr(df: pd.DataFrame) -> float | None:
    """
    Time from the onset of downcutting until the invert reaches its lowest
    level. Reported alongside formation time because, in a breach that
    deepens quickly and then widens slowly, the two can differ greatly,
    and it is the deepening that governs how quickly the peak arrives.
    """
    if "breach_bottom_elev" not in df or len(df) < 3:
        return None
    zb = df["breach_bottom_elev"].to_numpy(dtype=float)
    t = df["time_hr"].to_numpy(dtype=float)
    i_start = _onset_index(df)
    floor = np.where(zb <= zb.min() + 0.01)[0]
    if len(floor) == 0 or floor[0] <= i_start:
        return None
    return float(t[floor[0]] - t[i_start])


WAVG_DEFINITIONS = {
    "mean": "Mean of crest width and base width",
    "base": "Base width, between upstream and downstream toes",
}


def average_embankment_width_by(p: dict, definition: str = "mean") -> float:
    """
    Embankment width for the Froehlich relations, under either reading.

    Froehlich (2016b) describes the variable as the "average width of the
    embankment (between toes of the downstream and upstream slopes)". That
    wording supports two readings — the mean of crest and base widths, or
    the base width itself — and the sources do not resolve which. Both are
    offered, and the choice is shown wherever the variable is used.
    """
    H = float(p.get("emb_height", 0.0))
    Wc = float(p.get("emb_crest_width", 0.0))
    Su = max(float(p.get("emb_us_slope", 0.4)), 1e-6)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 1e-6)
    base = Wc + H * (1.0 / Su + 1.0 / Sd)
    return base if definition == "base" else (Wc + base) / 2.0


def derive_inputs(p: dict, df: pd.DataFrame, wavg_def: str = "mean") -> dict:
    """
    Assemble the variables the empirical equations need, from the model
    configuration and its result.

      Vw    volume of water above the final breach invert
      Hw    height of water above the final breach invert
      Hb    height of the breach, crest to final invert
      Wavg  embankment width, under the selected definition
      tf    breach formation time, onset of downcutting to final geometry

    Froehlich defines Vw and Hw at the time of failure, meaning the
    reservoir level when breach formation begins. The level at the onset
    of downcutting is therefore used rather than the initial level, which
    matters where a long piping phase drains the reservoir first.
    """
    H = float(p.get("emb_height", 0.0))
    zb = float(df["breach_bottom_elev"].min())
    i0 = _onset_index(df)
    if "wsl_up" in df.columns:
        wsl_f = float(df["wsl_up"].iloc[i0])
    else:
        wsl_f = float(p.get("wsl_up_initial", 0.0))

    v_top = storage_at(p, wsl_f)
    v_bot = storage_at(p, zb)
    Vw = max(v_top - v_bot, 0.0) if (v_top is not None and v_bot is not None) else None

    return {
        "Vw": Vw,
        "Hw": max(wsl_f - zb, 0.0),
        "Hb": max(H - zb, 0.0),
        "Wavg": average_embankment_width_by(p, wavg_def),
        "wavg_def": wavg_def,
        "tf_hr": formation_time_hr(df),
        "tdown_hr": downcutting_time_hr(df),
        "invert": zb,
        "wsl_onset": wsl_f,
        "t_onset_hr": float(df["time_hr"].iloc[i0]),
        "overtopping": int(p.get("breach_mode", 1)) == 1,
    }


# =====================================================================
# Peak discharge — water-retaining dam equations
# =====================================================================

def froehlich_2016_peak(Vw, Hw, Hb, Wavg, overtopping):
    """Froehlich (2016) Eq. 2. RMSE of ln Qp = 0.277."""
    if min(Vw, Hw, Hb, Wavg) <= 0:
        return None
    kM = 1.85 if overtopping else 1.0
    kH = 1.0 if Hb <= 6.1 else (Hb / 6.1) ** 0.125
    return 0.0175 * kM * kH * math.sqrt(G * Vw * Hw * Hb ** 2 / Wavg)


def froehlich_1995_peak(Vw, Hw, **_):
    """Froehlich (1995). RMSE of ln Qp = 0.488."""
    if min(Vw, Hw) <= 0:
        return None
    return 0.607 * Vw ** 0.295 * Hw ** 1.24


# name -> (function, RMSE of ln Qp, citation key)
PEAK_EQUATIONS = {
    "Froehlich (2016), Eq. 2": (froehlich_2016_peak, 0.277, "froehlich2016"),
    "Froehlich (1995)": (froehlich_1995_peak, 0.488, "froehlich1995"),
}


def froehlich_factors(d: dict) -> dict:
    """
    The mode and height factors actually applied, so that the interface
    can state the assumptions rather than leaving them implicit.
    """
    Hb = d.get("Hb") or 0.0
    over = bool(d.get("overtopping"))
    return {
        "kM_2016": 1.85 if over else 1.0,
        "kH_2016": 1.0 if Hb <= 6.1 else (Hb / 6.1) ** 0.125,
        "kM_2008": 1.3 if over else 1.0,
        "mode_2008": 1.0 if over else 0.0,
        "side_slope_2008": 1.0 if over else 0.7,
        "mode_label": "overtopping" if over else "non-overtopping (piping)",
    }


def peak_predictions(d: dict) -> pd.DataFrame:
    """
    Evaluate every peak-discharge equation, with a band of plus and
    minus one RMSE applied in log space, which is how each error
    statistic was defined by its author.
    """
    rows = []
    for name, (fn, rmse, key) in PEAK_EQUATIONS.items():
        try:
            q = fn(Vw=d["Vw"], Hw=d["Hw"], Hb=d["Hb"],
                   Wavg=d["Wavg"], overtopping=d["overtopping"])
        except (TypeError, ValueError, ZeroDivisionError):
            q = None
        if q is None or not math.isfinite(q):
            continue
        rows.append({"Equation": name, "Qp (m3/s)": q,
                     "Lower (-1 RMSE)": q * math.exp(-rmse),
                     "Upper (+1 RMSE)": q * math.exp(rmse),
                     "RMSE of ln Qp": rmse, "_cite": key})
    return pd.DataFrame(rows)


# =====================================================================
# Breach geometry and formation time — Froehlich (2008)
# =====================================================================

def froehlich_2008_geometry(Vw: float, Hb: float, overtopping: bool) -> dict:
    """
    Froehlich (2008) average breach width, side slope and formation time.

    The average width follows the published regression
        ln(B/Hb) = -1.30 + 0.278*Mode + 0.316*ln(Vw/Hb^3)
    with a standard error of estimate of 0.4602 on the logarithm, which
    is carried through as a multiplicative band.

    Side slope is 1.0H:1V for overtopping and 0.7H:1V otherwise, and the
    formation time is tf = 63.2 * sqrt(Vw / (g*Hb^2)) in seconds.
    """
    if Vw is None or Vw <= 0 or Hb <= 0:
        return {}
    mode = 1.0 if overtopping else 0.0
    ln_bstar = -1.30 + 0.278 * mode + 0.316 * math.log(Vw / Hb ** 3)
    b_avg = math.exp(ln_bstar) * Hb
    sigma = 0.4602
    tf_s = 63.2 * math.sqrt(Vw / (G * Hb ** 2))
    return {
        "B_avg": b_avg,
        "B_avg_lower": b_avg * math.exp(-sigma),
        "B_avg_upper": b_avg * math.exp(sigma),
        "sigma_lnB": sigma,
        "side_slope_HV": 1.0 if overtopping else 0.7,
        "tf_hr": tf_s / 3600.0,
    }


# =====================================================================
# Eroded dam volume — Adria et al. (2023, 2024)
# =====================================================================

# The authors report an error of approximately half an order of
# magnitude on both relations.
ADRIA_BAND = 10 ** 0.5


def adria_eroded_volume(Hw: float, Vout: float) -> float | None:
    """Adria et al. (2023) Eq. 1: V_ED = 1.26 * Hw^1.803 * Vout^0.338."""
    if Hw is None or Vout is None or Hw <= 0 or Vout <= 0:
        return None
    return 1.26 * Hw ** 1.803 * Vout ** 0.338


def adria_erosion_rate(Hw: float, Vout: float) -> float | None:
    """Adria et al. (2023) Eq. 2: M = 415 * Hw^2.296 * Vout^-0.098 (m3/h)."""
    if Hw is None or Vout is None or Hw <= 0 or Vout <= 0:
        return None
    return 415.0 * Hw ** 2.296 * Vout ** -0.098


# =====================================================================
# Breach geometry and formation time — Froehlich (2016b)
# =====================================================================

def froehlich_2016b_geometry(Vw: float, Hb: float, Wavg: float,
                             overtopping: bool) -> dict:
    """
    Froehlich (2016b), "Empirical model of embankment dam breaching",
    fitted to 111 failures. The better-fitting forms are used:

      Eq. 2  Bavg = 0.28 kM kH Vw^(1/3) (Hb/Wavg)^(1/6)
             kM = 1.5 overtopping, 1.0 internal erosion
             kH = (Hb/6.1)^(1/2) for Hb < 6.1 m, else 1.0
             standard error of ln Bavg = 0.391
      Eq. 6  m = 1.0 overtopping, 0.6 internal erosion
             standard error of ln m = 0.771
      Eq. 8  tf = 50 sqrt(Vw / (g Hb^2)) (Wavg/Hb)^(1/4)   [seconds]
             standard error of ln tf = 0.210

    Bounds are plus and minus one standard error on the logarithm.
    """
    if not Vw or Vw <= 0 or Hb <= 0 or Wavg <= 0:
        return {}
    kM = 1.5 if overtopping else 1.0
    kH = (Hb / 6.1) ** 0.5 if Hb < 6.1 else 1.0
    b = 0.28 * kM * kH * Vw ** (1 / 3) * (Hb / Wavg) ** (1 / 6)
    m = 1.0 if overtopping else 0.6
    tf_s = 50.0 * math.sqrt(Vw / (G * Hb ** 2)) * (Wavg / Hb) ** 0.25
    sb, sm, st = 0.391, 0.771, 0.210
    return {
        "B_avg": b, "B_avg_lower": b * math.exp(-sb),
        "B_avg_upper": b * math.exp(sb),
        "side_slope_HV": m, "m_lower": m * math.exp(-sm),
        "m_upper": m * math.exp(sm),
        "tf_hr": tf_s / 3600.0, "tf_lower": tf_s / 3600.0 * math.exp(-st),
        "tf_upper": tf_s / 3600.0 * math.exp(st),
        "kM": kM, "kH": kH,
    }


def froehlich_2008_tf_bounds(Vw: float, Hb: float) -> tuple | None:
    """Froehlich (2008) formation time with its standard error of 0.2979."""
    if not Vw or Vw <= 0 or Hb <= 0:
        return None
    tf = 63.2 * math.sqrt(Vw / (G * Hb ** 2)) / 3600.0
    return tf, tf * math.exp(-0.2979), tf * math.exp(0.2979)


# =====================================================================
# Calibration range — Froehlich (2016a), Table 2
# =====================================================================

FROEHLICH_2016_RANGES = {
    "Wavg": (9.63, 250.0, "m", "Average embankment width"),
    "Vw": (0.0133e6, 701e6, "m³", "Volume of water above breach bottom"),
    "Hw": (1.68, 77.4, "m", "Height of water above breach bottom"),
    "Hb": (3.66, 86.9, "m", "Height of breach"),
}


def range_check(d: dict) -> pd.DataFrame:
    """
    Compare the case against the range of the data the peak-discharge
    relation was fitted to. Outside that range the relation is being
    extrapolated.
    """
    rows = []
    for key, (lo, hi, unit, label) in FROEHLICH_2016_RANGES.items():
        v = d.get(key)
        if v is None:
            continue
        inside = lo <= v <= hi
        scale = 1e6 if key == "Vw" else 1.0
        u = "Mm³" if key == "Vw" else unit
        rows.append({"Variable": label,
                     "This case": f"{v / scale:,.3g} {u}",
                     "Fitted range": f"{lo / scale:,.3g} – {hi / scale:,.3g} {u}",
                     "Within range": "Yes" if inside else "No — extrapolated"})
    return pd.DataFrame(rows)


# =====================================================================
# Diagnostics — what the simulated breach actually did
# =====================================================================

def breach_diagnostics(p: dict, df: pd.DataFrame) -> dict:
    """
    Quantities that explain a peak discharge, taken directly from the run.

    The broad-crested weir check tests whether the reported peak is
    consistent with the opening and head at that moment. If it is, any
    departure from an empirical estimate comes from the size and speed of
    the breach, not from the flow calculation.

    The weir expression is the standard trapezoidal form, in SI units,
        Q = 1.7 b h^1.5 + 1.35 z h^2.5
    with b the bottom width, h the head above the invert and z the side
    slope ratio (horizontal to vertical). It is an order-of-consistency
    check, not a replacement for the model's own hydraulics.
    """
    ipk = int(df["Q_breach"].idxmax())
    r = df.loc[ipk]
    head = max(float(r["wsl_up"]) - float(r["breach_bottom_elev"]), 0.0)
    zsl = float(r["breach_side_slope"])
    z_hv = 1.0 / zsl if zsl > 1e-6 else 0.0
    b = float(r["breach_bottom_width"])
    q_weir = 1.7 * b * head ** 1.5 + 1.35 * z_hv * head ** 2.5
    wsl0 = float(p.get("wsl_up_initial", df["wsl_up"].iloc[0]))
    zb_final = float(df["breach_bottom_elev"].min())
    i0 = _onset_index(df)
    return {
        "t_peak": float(r["time_hr"]),
        "q_peak": float(r["Q_breach"]),
        "head_at_peak": head,
        "bottom_width_at_peak": b,
        "top_width_at_peak": float(r["breach_top_width"]),
        "q_weir": q_weir,
        "weir_ratio": float(r["Q_breach"]) / q_weir if q_weir > 0 else None,
        "level_drop_at_peak": wsl0 - float(r["wsl_up"]),
        "available_drop": wsl0 - zb_final,
        "volume_at_peak": float(r["cum_volume"]) if "cum_volume" in df else None,
        "total_volume": float(df["cum_volume"].iloc[-1]) if "cum_volume" in df else None,
        "t_onset": float(df["time_hr"].iloc[i0]),
        "t_down": downcutting_time_hr(df),
        "depth_cut": float(df["breach_bottom_elev"].iloc[0]) - zb_final,
    }


# =====================================================================
# DLBreach input guidance — Wu (2016) technical report
# =====================================================================

def recommended_manning_n(p: dict, field: bool = True) -> float:
    """
    Manning's n recommended by the DLBreach technical report.

    Non-cohesive: n = d50^(1/6) / An, with An = 12 for field cases and 16
    for laboratory cases. Cohesive: 0.016, which the report specifies as
    the lowest value to be used.
    """
    if int(p.get("sediment_type", 1)) == 2:
        return 0.016
    d50 = max(float(p.get("sed_d50", 0.001)), 1e-9)
    return max(d50 ** (1 / 6) / (12.0 if field else 16.0), 0.016)


def dlbreach_guidance(p: dict, field: bool = True) -> list[dict]:
    """
    Compare the configuration against the recommendations Wu gives in the
    DLBreach technical report and input format document.

    Only recommendations the report actually states are checked. Each
    finding records what was entered, what is recommended, and why, so
    that a departure can be judged rather than simply flagged. Departures
    are not errors; the report notes the model was tested using these
    values, so a departure is a reason to confirm intent.
    """
    out = []
    cohesive = int(p.get("sediment_type", 1)) == 2
    n_in = float(p.get("manning_n", 0.0))
    n_rec = recommended_manning_n(p, field)
    if abs(n_in - n_rec) / n_rec > 0.15:
        basis = ("0.016, the value the report specifies for cohesive soils"
                 if cohesive else
                 f"d50^(1/6) / {12 if field else 16} with d50 = "
                 f"{float(p.get('sed_d50', 0)):g} m "
                 f"({'field' if field else 'laboratory'} case)")
        out.append({
            "Parameter": "Breach Manning n", "Entered": f"{n_in:.4f}",
            "Recommended": f"{n_rec:.4f}",
            "Basis": f"Wu (2016) recommends {basis}, noting the model was "
                     f"tested using these values.",
            "Effect": "Manning n enters both the flow and the bed shear "
                      "stress calculation in DLBreach, so the direction and "
                      "size of its effect on the peak are best established "
                      "by re-running with the recommended value."})

    if not cohesive:
        lam = float(p.get("adaptation_lambda", 6.0))
        lam_rec = 6.0 if field else 3.0
        if p.get("include_adaptation_lambda", True) and abs(lam - lam_rec) > 0.5:
            out.append({
                "Parameter": "Adaptation lambda", "Entered": f"{lam:g}",
                "Recommended": f"{lam_rec:g}",
                "Basis": "Wu (2016) suggests 6.0 for field and 3.0 for "
                         "laboratory cases.", "Effect": ""})
    else:
        d50 = float(p.get("sed_d50", 0.0))
        if abs(d50 - 0.00003) / 0.00003 > 0.5:
            out.append({
                "Parameter": "Grain diameter (cohesive)",
                "Entered": f"{d50:g} m", "Recommended": "0.00003 m",
                "Basis": "For cohesive soils Wu (2016) suggests a "
                         "representative floc diameter of 0.03 mm.",
                "Effect": ""})
        kd = float(p.get("kd", 0.0))
        if not (2.5 <= kd <= 30.0):
            out.append({
                "Parameter": "Erodibility kd", "Entered": f"{kd:g}",
                "Recommended": "2.5 – 30 cm³/N·s",
                "Basis": "The range used in the 35 cohesive test cases in "
                         "Wu (2016). The report identifies kd as the most "
                         "important parameter for cohesive embankments and "
                         "recommends sensitivity analysis on it.",
                "Effect": ""})

    if int(p.get("breach_mode", 1)) == 2:
        hl = float(p.get("pipe_head_loss", 0.05))
        if abs(hl - 0.05) > 0.02:
            out.append({
                "Parameter": "Pipe entrance head loss", "Entered": f"{hl:g}",
                "Recommended": "0.05",
                "Basis": "Suggested value in Wu (2016).", "Effect": ""})
    return out
