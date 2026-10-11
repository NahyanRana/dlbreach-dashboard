"""
dlbreach_tailings.py
--------------------
Cone of depression for a tailings impoundment, after CDA (2021),
Appendix A, and its optional use to adjust the stage-storage relation
passed to DLBreach.

What the Bulletin states
    CDA (2021) describes estimating mobilised tailings volumes by drawing
    a cone of depression back from the breach at a post-failure slope,
    shown schematically in its Figure A.1 (plan view and section A-A,
    with the breach width at the dam and a final backscarp). It reports
    average post-liquefaction slopes in past failures of 2 to 5 degrees
    (3.5 to 9 %), citing Lucia et al. (1981) and Blight and Fourie
    (2003), and states that practitioners should make their own
    professional judgement based on site-specific information.

What this module adds, and which is therefore interpretation
    The Bulletin gives the method as a schematic, not as a formula. The
    geometry here is the construction that follows most directly from
    Figure A.1:

      * in section, the post-failure surface rises from the breach invert
        at the chosen slope until it meets the tailings surface; the
        horizontal distance to that point is the backscarp distance
            L = (z_tailings - z_invert) / slope
      * in plan, the evacuated zone is a half-cone (a semicircular fan)
        centred on the breach, with the breach width at its apex, so that
            V = (pi L^2 h / 6) + (b L h / 2),   h = z_tailings - z_invert
      * the backscarp may be capped at a maximum distance where the
        impoundment is smaller than the cone.

    Treating the cone contents as storage in DLBreach, which routes the
    impoundment as clear water, is a bounding simplification, not a
    representation of tailings flow. The Bulletin applies the cone to
    liquefied (Process II) and slumped tailings volumes, not to the
    water routed by a breach model.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# Range quoted by CDA (2021), Appendix A.
SLOPE_RANGE_PCT = (3.5, 9.0)


def cone_geometry(z_beach: float, z_invert: float, slope_pct: float,
                  b_apex: float, l_max: float | None = None,
                  n: int = 240) -> dict:
    """
    Stage-area and stage-volume of the half-cone of depression.

    Elevations are in the model datum (metres above embankment base).
    The evacuated plan area at elevation z is the fan of radius
    r(z) = (z - z_invert) / slope, capped at l_max if given:
        A(z) = pi r^2 / 2 + b r
    and the volume below z is the integral of A from the invert.
    """
    s = float(slope_pct) / 100.0
    h = float(z_beach) - float(z_invert)
    if s <= 0 or h <= 0:
        return {}
    L_full = h / s
    L = min(L_full, float(l_max)) if l_max and l_max > 0 else L_full
    z = np.linspace(z_invert, z_beach, n)
    r = np.clip((z - z_invert) / s, 0.0, L)
    area = math.pi * r ** 2 / 2.0 + max(b_apex, 0.0) * r
    vol = np.concatenate([[0.0], np.cumsum(np.diff(z) * (area[1:] + area[:-1]) / 2)])
    closed = (math.pi * L_full ** 2 * h / 6.0 + max(b_apex, 0.0) * L_full * h / 2.0)
    return {
        "h": h, "slope": s, "L_full": L_full, "L": L,
        "truncated": L < L_full - 1e-9,
        "volume": float(vol[-1]), "volume_closed_form_untruncated": closed,
        "z": z, "area": area, "vol": vol,
        "z_beach": float(z_beach), "z_invert": float(z_invert),
        "b_apex": float(b_apex),
    }


def cone_volume_below(cone: dict, z: float) -> float:
    """Cone volume between the invert and elevation z."""
    if not cone:
        return 0.0
    return float(np.interp(z, cone["z"], cone["vol"],
                           left=0.0, right=cone["volume"]))


def combined_stage_storage(p: dict, cone: dict, factor: float,
                           storage_fn, n_levels: int = 30) -> list[tuple]:
    """
    Stage-storage table combining the cone with the pond above the beach.

    Below the tailings surface, storage is `factor` times the cone volume
    below each level. Above it, the existing stage-storage relation is
    taken as the pond, and its increments above the beach are added.
    `factor` = 1 treats the whole cone as releasable, which is the
    bounding assumption; smaller values reduce it proportionally.

    Returns (level, volume) pairs in the model datum, for DLBreach
    stage-storage method 0.
    """
    if not cone:
        return []
    zb, zt = cone["z_invert"], cone["z_beach"]
    top = max(float(p.get("wsl_up_initial", zt)), float(p.get("emb_height", zt)))
    curve = p.get("res_curve") or []
    if curve:
        top = max(top, max(float(c[0]) for c in curve))
    v_beach = storage_fn(p, zt) or 0.0
    below = np.linspace(zb, zt, max(n_levels // 2, 6))
    above = np.linspace(zt, top, max(n_levels // 2, 6))[1:]
    rows = []
    for z in below:
        rows.append((round(float(z), 3),
                     round(factor * cone_volume_below(cone, z), 1)))
    base = factor * cone["volume"]
    for z in above:
        pond = max((storage_fn(p, z) or 0.0) - v_beach, 0.0)
        rows.append((round(float(z), 3), round(base + pond, 1)))
    return rows


# =====================================================================
# Tailings release volume — three methods, and bulking
# =====================================================================

def insitu_cv(pond_m3: float, flood_m3: float, solids_t: float,
              dry_density: float, sg: float, saturation: float = 1.0) -> dict:
    """
    Solids concentration if the whole impoundment were mixed: pond, flood
    water and all stored tailings (solids and pore water).

    Phase relations, with rho_w = 1 t/m3:
        tailings volume   VT = Ms / rho_d
        interstitial water     (VT - Ms/rho_s) * S        (rho_w = 1 t/m3)
        water content     WC = (pond + flood + interstitial) / Ms
        Cw = 1 / (WC + 1)
        Cv = Cw / (SG + (1 - SG) Cw)
    This is an upper bound on Cv for a breach flow; the release would not
    normally include the entire tailings mass.
    """
    if solids_t <= 0 or dry_density <= 0 or sg <= 0:
        return {}
    vt = solids_t / dry_density
    vs = solids_t / sg
    iw = max(vt - vs, 0.0) * saturation
    water = pond_m3 + flood_m3 + iw
    wc = water / solids_t
    cw = 1.0 / (wc + 1.0)
    cv = cw / (sg + (1.0 - sg) * cw)
    return {"tailings_m3": vt, "solids_m3": vs, "interstitial_m3": iw,
            "water_content": wc, "Cw": cw, "Cv": cv}


def cw_from_cv(cv: float, sg: float) -> float:
    """Solids content by weight from solids concentration by volume."""
    return cv * sg / (1.0 + cv * (sg - 1.0))


def cv_from_cw(cw: float, sg: float) -> float:
    return cw / (sg + (1.0 - sg) * cw)


def fontaine_martin(solids_t: float, dry_density: float, sg: float,
                    saturation: float, water_m3: float,
                    solids_content: float) -> dict:
    """
    Fontaine and Martin (2015), Eqs. 2 to 17.

    solids_t        mass of tailings solids stored, MS-INIT (t)
    dry_density     average dry density rho_D (t/m3)
    sg              solids specific gravity (rho_S = sg t/m3)
    saturation      degree of saturation S (fraction)
    water_m3        free water VW: supernatant pond plus any flood (m3)
    solids_content  %s, gravimetric solids content of the outflow (fraction)

    The mobilised solids are capped at the solids stored (their limiting
    condition), and Eq. 13 is valid only for %w < 1/%s - 1.
    """
    rho_s, rho_w = sg, 1.0
    vt = solids_t / dry_density                          # (2)
    vs = solids_t / rho_s                                # (3)
    vv = vt - vs                                         # (4)
    n = vv / vt                                          # (5)
    e = vv / vs                                          # (6)
    viw = saturation * vv                                # (7)
    miw = viw * rho_w                                    # (8)
    pw = miw / solids_t                                  # (9)  %w
    rho_bulk = (solids_t + miw) / vt                     # (10)
    mw = water_m3 * rho_w                                # (11)
    valid = pw < (1.0 / solids_content) - 1.0
    ms_mob = mw / ((1.0 / solids_content) - 1.0 - pw) if valid else float("nan")  # (13)
    capped = valid and ms_mob > solids_t
    if capped:
        ms_mob = solids_t
    miw_mob = ((ms_mob / dry_density) - (ms_mob / rho_s)) * saturation * rho_w   # (14)
    vt_mob = (ms_mob + miw_mob) / rho_bulk               # (15)
    vout = water_m3 + vt_mob                             # (16)
    pct_out = vout / (water_m3 + vt)                     # (17)
    solids_v = ms_mob / rho_s
    return {"VT": vt, "VS": vs, "VV": vv, "n": n, "e": e, "VIW": viw,
            "pct_w": pw, "rho_bulk": rho_bulk, "MS_MOB": ms_mob,
            "MIW_MOB": miw_mob, "VT_MOB": vt_mob, "VOUT": vout,
            "pct_VOUT": pct_out, "valid": valid, "capped": capped,
            "release_solids_m3": solids_v,
            "release_interstitial_m3": miw_mob / rho_w,
            "Cv_release": solids_v / vout if vout > 0 else float("nan")}


def cone_volume_practice(h: float, slope_deg: float, b_apex: float) -> dict:
    """
    Cone of depression in the form used in practice for tailings release
    (half-cone with the breach width at the apex):

        L         = h / tan(beta)
        V_central = 0.5 * B * L * h
        V_cones   = pi h^3 / (6 tan^2 beta)
        V         = V_central + V_cones

    h is the height of the cone (crest or tailings surface down to the
    breach invert, by the user's choice) and B the breach width at the
    apex (top or bottom width, by the user's choice). This is the same
    geometry as cone_geometry(); it is stated here in the form practitioners
    use so that values can be checked against existing calculations.
    """
    t = math.tan(math.radians(slope_deg))
    if h <= 0 or t <= 0:
        return {}
    L = h / t
    vc = 0.5 * b_apex * L * h
    ve = math.pi * h ** 3 / (6.0 * t ** 2)
    return {"L": L, "V_central": vc, "V_cones": ve, "V": vc + ve}


def bulking_factor(water_m3: float, tailings_release_m3: float) -> float:
    """
    Ratio of total release (water plus mobilised tailings) to free water.
    Applied uniformly to the water hydrograph, it gives a bulked hydrograph
    of the same shape. A uniform factor is the constant-concentration
    simplification described in CDA (2021); concentration in a real breach
    varies through the event.
    """
    if water_m3 <= 0:
        return 1.0
    return (water_m3 + max(tailings_release_m3, 0.0)) / water_m3


# =====================================================================
# Tailings release through time, for any of the three methods
# =====================================================================

def _open_stage(df: pd.DataFrame, p: dict) -> np.ndarray:
    """True where the breach is open to the crest (after any pipe collapse)."""
    zb = df["breach_bottom_elev"].to_numpy(dtype=float)
    if int(p.get("breach_mode", 1)) != 2:
        return np.ones(len(zb), dtype=bool)
    H = float(p.get("emb_height", 0.0))
    z0 = H - float(p.get("pipe_depth", 0.0))
    return zb < z0 - max(0.02 * H, 0.10)


def cone_timeseries(df: pd.DataFrame, p: dict, beach: float, slope_deg: float,
                    width: str = "bottom", l_max: float | None = None) -> dict:
    """
    Cone of depression following the breach as DLBreach develops it.

    At each time step the cone's apex sits at the breach invert and its
    width at the apex is the breach width reported by DLBreach, so the cone
    height is h(t) = tailings beach - breach invert(t). The mobilised volume
    is the cone volume at that geometry; it is not allowed to decrease,
    since tailings once mobilised are not restored. Before a piping breach
    opens to the crest no cone is formed.

    The rate at which the cone grows is taken as the tailings release rate.
    That link between cone growth and release rate is this dashboard's
    construction, not a published method.
    """
    t = df["time_hr"].to_numpy(dtype=float)
    zb = df["breach_bottom_elev"].to_numpy(dtype=float)
    bcol = "breach_top_width" if width == "top" else "breach_bottom_width"
    b = df[bcol].to_numpy(dtype=float)
    open_ = _open_stage(df, p)
    tan_b = math.tan(math.radians(slope_deg))
    vol = np.zeros(len(t))
    for i in range(len(t)):
        h = beach - zb[i]
        if not open_[i] or h <= 0 or tan_b <= 0:
            continue
        L = h / tan_b
        if l_max and L > l_max:
            vol[i] = cone_geometry(beach, zb[i], tan_b * 100, b[i], l_max)["volume"]
        else:
            vol[i] = 0.5 * b[i] * L * h + math.pi * h ** 3 / (6 * tan_b ** 2)
    vol = np.maximum.accumulate(vol)
    dt = np.gradient(t * 3600.0)
    q = np.where(dt > 0, np.gradient(vol) / np.where(dt > 0, dt, 1), 0.0)
    return {"t": t, "V": vol, "Q": np.maximum(q, 0.0)}


def tailings_for_run(df: pd.DataFrame, p: dict, cfg: dict) -> dict:
    """
    Tailings released with one DLBreach run, by the configured method.

    Free water is the DLBreach release volume of the run unless the
    configuration supplies a pond and flood volume instead. The result
    includes a tailings release hydrograph aligned with the run: for the
    cone method it follows the cone's growth; for the other methods it is
    the water hydrograph scaled by (bulking factor - 1), the uniform
    constant-concentration simplification described in CDA (2021).
    """
    qw = df["Q_breach"].to_numpy(dtype=float)
    if cfg.get("water_source", "run") == "run" and "cum_volume" in df:
        free_w = float(df["cum_volume"].iloc[-1])
    else:
        free_w = float(cfg.get("pond_m3", 0.0)) + float(cfg.get("flood_m3", 0.0))
    rho_d = float(cfg.get("dry_density", 1.4))
    sg = float(cfg.get("sg", 2.7))
    sat = float(cfg.get("sat_pct", 100.0)) / 100.0
    n_t = max(1.0 - rho_d / sg, 0.0)
    method = cfg.get("method", "ratio")
    note = ""
    qt = None
    if method == "fm":
        cw = float(cfg.get("fm_cw", 50.0)) / 100.0
        fm = fontaine_martin(float(cfg.get("solids_t", 1e7)), rho_d, sg, sat,
                             free_w, cw)
        if not fm["valid"]:
            return {"ok": False, "free_water_m3": free_w,
                    "note": "Solids content below that of the stored tailings: "
                            "Fontaine and Martin Eq. 13 does not apply."}
        vt, vs, vi = fm["VT_MOB"], fm["release_solids_m3"], fm["release_interstitial_m3"]
        note = "capped at stored tailings" if fm["capped"] else ""
    elif method == "cone":
        cs = cone_timeseries(df, p, float(cfg.get("beach_level", 0.0)),
                             float(cfg.get("cone_slope_deg", 4.0)),
                             cfg.get("cone_width", "bottom"),
                             float(cfg.get("cone_lmax", 0.0)) or None)
        vt = float(cs["V"][-1])
        vs, vi = vt * (1 - n_t), vt * n_t * sat
        qt = cs["Q"]
    else:
        vt = float(cfg.get("ratio", 0.30)) * free_w
        vs, vi = vt * (1 - n_t), vt * n_t * sat
    bf = bulking_factor(free_w, vt)
    if qt is None:
        qt = qw * (bf - 1.0)
    total = free_w + vt
    return {"ok": free_w > 0, "method": method, "free_water_m3": free_w,
            "tailings_m3": vt, "solids_m3": vs, "interstitial_m3": vi,
            "total_m3": total, "bulking": bf,
            "Cv": vs / total if total > 0 else 0.0,
            "Q_tailings": qt, "Q_total": qw + qt,
            "peak_total": float(np.max(qw + qt)) if len(qw) else 0.0,
            "note": note if free_w > 0 else
                    "No free water was released, so no tailings can be "
                    "mobilised. Check the pond level against the breach."}
