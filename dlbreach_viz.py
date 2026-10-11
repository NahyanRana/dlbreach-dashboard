"""
dlbreach_viz.py
---------------
Two things the interface needs but that do not belong in it:

  1. HELP  -- a description for every input parameter, drawn from Wu's
             DLBreach technical documentation, shown on hover.
  2. cross_section_svg() -- an idealised cross-section of the embankment
             as currently configured, so the user can see the geometry
             rather than infer it from a column of numbers.

The schematic is drawn as plain SVG. That avoids adding a plotting
library to the requirements and keeps the drawing sharp at any size.

DLBreach approximates the embankment as a trapezoid. Upstream and
downstream toes sit at the same elevation, and all elevations are
referenced to the embankment base, positive upwards.
"""

from __future__ import annotations

import math

import numpy as np


# =====================================================================
# Parameter help text
# =====================================================================

# Help text lives in dlbreach_help, in the units the dashboard shows.
from dlbreach_help import HELP  # noqa: E402,F401


# =====================================================================
# Cross-section schematic
# =====================================================================

# Palette, kept consistent with the rest of the interface. Typeface as the
# interface; each drawing loads it itself, since it renders in its own frame.
FONT = "'IBM Plex Sans','Segoe UI',system-ui,-apple-system,Roboto,sans-serif"
FONT_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">')
C_BG        = "#FFFFFF"
C_PANEL     = "#F3F6F9"
C_FOUND     = "#E3DCCC"
C_FOUND_LN  = "#9A9280"
C_DAM       = "#CFC8B6"
C_DAM_LN    = "#6B6555"
C_WATER     = "#A8CBE8"
C_WATER_LN  = "#1B6AAE"
C_LIMIT     = "#B3402A"
C_BREACH    = "#1B6AAE"
C_TEXT      = "#17324D"
C_MUTED     = "#5E6B77"
C_TAIL      = "#F2B46B"   # stored solid waste: orange
C_TAIL_MOB  = "#D9731F"   # mobilised solid waste: deeper orange
C_POND_LN   = "#1B6AAE"



def breach_flow_depth(state: dict) -> float | None:
    """
    Flow depth at the breach, from the breach flow area DLBreach reports.

    The DLBreach output gives the flow area at the breach (Wu 2016, file
    format guide, output columns). For the trapezoidal breach with bottom
    width b and side slope s (V/H), A = b·h + h²/s, solved here for h.
    Returns None when the output carries no flow area.
    """
    try:
        A = float(state.get("breach_flow_area", float("nan")))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(A) or A <= 0:
        return None if not math.isfinite(A) else 0.0
    b = max(float(state.get("breach_bottom_width", 0.0)), 0.0)
    s = float(state.get("breach_side_slope", 0.0))
    if s <= 0.01:
        return A / b if b > 0 else None
    return (-b + math.sqrt(b * b + 4.0 * A / s)) / (2.0 / s)


C_TW_LN = "#17A2B8"     # tailwater (downstream water level)


def flow_regime(state: dict) -> str | None:
    """
    Which term sets the flow depth at the breach in DLBreach (Wu 2016,
    Eq. 3.5): the critical depth over a broad-crested weir, two-thirds of
    the pond's height above the invert, or the average of the pond and
    tailwater heights above the invert, whichever is larger.
    """
    try:
        zb = float(state["breach_bottom_elev"])
        hs = max(float(state["wsl_up"]) - zb, 0.0)
        ht = max(float(state.get("wsl_down", float("nan"))) - zb, 0.0)
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(ht) or hs <= 0:
        return None
    return "Tailwater" if 0.5 * (hs + ht) > (2.0 / 3.0) * hs else "Critical depth"


# ---------------------------------------------------------------------
# Section geometry shared by the on-screen and report drawings
#
# Distances run from the upstream toe, positive downstream; elevations are
# above the embankment base (Wu 2016, Embankment Dimensions).
# ---------------------------------------------------------------------
C_CORE      = "#A08566"   # clay core
C_CORE_LN   = "#6E5638"
C_COVER     = "#7D5F45"   # clay cover
C_ABUT      = "#B9B2A4"   # abutment (one-sided breach)
C_ABUT_LN   = "#8C8576"


def core_polygon(p: dict) -> list[tuple] | None:
    """
    The clay core as a trapezoid: (x, z) corners from the upstream base
    corner, clockwise. Core_Center_Location is the distance of the core
    crest centre from the embankment crest centre, positive downstream
    (Wu 2016, Clay Core Parameters). None when the case has no core.
    """
    if not p.get("has_core"):
        return None
    H = max(float(p.get("emb_height", 20.0)), 0.1)
    Su = max(float(p.get("emb_us_slope", 0.4)), 0.01)
    Wc = max(float(p.get("emb_crest_width", 10.0)), 0.0)
    hc = max(float(p.get("core_height", 0.0)), 0.0)
    wc = max(float(p.get("core_crest_width", 0.0)), 0.0)
    cu = max(float(p.get("core_us_slope", 4.0)), 0.01)
    cd = max(float(p.get("core_ds_slope", 4.0)), 0.01)
    xc = H / Su + Wc / 2 + float(p.get("core_center", 0.0))
    return [(xc - wc / 2 - hc / cu, 0.0), (xc - wc / 2, hc),
            (xc + wc / 2, hc), (xc + wc / 2 + hc / cd, 0.0)]


def core_outside(p: dict) -> list[str]:
    """Ways in which the core does not fit inside the embankment section."""
    poly = core_polygon(p)
    if not poly:
        return []
    H = max(float(p.get("emb_height", 20.0)), 0.1)
    Su = max(float(p.get("emb_us_slope", 0.4)), 0.01)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 0.01)
    Wc = max(float(p.get("emb_crest_width", 10.0)), 0.0)
    dam_w = H / Su + Wc + H / Sd
    tol = 1e-6
    msgs = []
    if poly[1][1] > H + tol:
        msgs.append(f"The core ({poly[1][1]:g} m) rises above the crest ({H:g} m).")
    lo = lambda z: z / Su                      # upstream face at elevation z
    hi = lambda z: dam_w - z / Sd              # downstream face at elevation z
    if any(x < lo(z) - tol for x, z in poly[:2]):
        msgs.append("The core's upstream face lies outside the embankment's "
                    "upstream face.")
    if any(x > hi(z) + tol for x, z in poly[2:]):
        msgs.append("The core's downstream face lies outside the embankment's "
                    "downstream face.")
    return msgs


_COVER_CARDS = {"CLAY_COVER_AT_UPSTREAM_SLOPE": "upstream slope",
                "CLAY_COVER_AT_BREACH_TOP": "crest",
                "CLAY_COVER_AT_DOWNSTREAM_SLOPE": "downstream slope"}


def clay_cover(p: dict) -> dict:
    """
    Clay cover thickness by segment, from the cover cards a loaded file
    carries: each has three entries, whether a cover exists (1 for yes),
    its Manning's n and its thickness in m (Wu 2016, Clay Cover Parameters).
    """
    out = {}
    for c in p.get("extra_cards") or []:
        toks = str(c).split("!")[0].replace(",", " ").split()
        if not toks or toks[0].upper() not in _COVER_CARDS:
            continue
        try:
            vals = [float(v) for v in toks[1:4]]
        except ValueError:
            continue
        if len(vals) == 3 and int(vals[0]) == 1 and vals[2] > 0:
            out[_COVER_CARDS[toks[0].upper()]] = vals[2]
    return out


def cover_polygons(p: dict) -> list[list[tuple]]:
    """
    The clay cover drawn as bands lining the embankment surface. Wu (2016)
    gives the cover thickness in m without saying how it is measured; it is
    drawn here normal to the face, inside the trapezoidal section.
    """
    cov = clay_cover(p)
    if not cov:
        return []
    H = max(float(p.get("emb_height", 20.0)), 0.1)
    Su = max(float(p.get("emb_us_slope", 0.4)), 0.01)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 0.01)
    Wc = max(float(p.get("emb_crest_width", 10.0)), 0.0)
    xu, xd = H / Su, H / Su + Wc
    dam_w = xd + H / Sd
    polys = []
    t = cov.get("upstream slope")
    if t:
        # vertical offset for a thickness t normal to a face of slope S (V/H)
        dz = min(t * math.sqrt(1 + Su ** 2), H)
        polys.append([(0.0, 0.0), (xu, H), (xu, H - dz), (dz / Su, 0.0)])
    t = cov.get("crest")
    if t:
        polys.append([(xu, H), (xd, H), (xd, H - min(t, H)), (xu, H - min(t, H))])
    t = cov.get("downstream slope")
    if t:
        dz = min(t * math.sqrt(1 + Sd ** 2), H)
        polys.append([(xd, H), (dam_w, 0.0), (dam_w - dz / Sd, 0.0), (xd, H - dz)])
    return polys


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))



def _nice_ticks(lo: float, hi: float, target: int = 8):
    """
    Choose round elevation values to label between lo and hi.

    Dividing a range into equal parts produces arbitrary labels such as
    4, 14, 24. Engineering drawings label round values, so a step is
    chosen from the 1, 2, 2.5, 5 sequence scaled by a power of ten, and
    ticks fall on multiples of that step. Zero is therefore always a tick
    when it lies within the range, and the interval refines automatically
    as the drawing is enlarged.
    """
    import math
    span = max(hi - lo, 1e-9)
    raw = span / max(target, 2)
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= m * mag:
            step = m * mag
            break
    else:
        step = 10.0 * mag
    first = math.ceil(lo / step) * step
    ticks, v = [], first
    while v <= hi + step * 1e-6:
        ticks.append(0.0 if abs(v) < step * 1e-6 else v)
        v += step
    return ticks, step


# ---------------------------------------------------------------------
# Display datum
#
# DLBreach works in metres above the embankment base, and inputs stay in
# that datum. For display only, an offset can be supplied in the params
# as "_z_off" with a label "_z_lab", so that axes and panel values read
# in site elevations (for example a mine grid RL, or geodetic).
# ---------------------------------------------------------------------
def _zoff(p: dict) -> float:
    return float(p.get("_z_off", 0.0) or 0.0)


def _zlab(p: dict) -> str:
    return str(p.get("_z_lab") or "m above embankment base")


def _ze(p: dict, z: float, dec: int = 2) -> str:
    """An elevation formatted in the display datum."""
    return f"{float(z) + _zoff(p):,.{dec}f} m"


def _nice_step(span: float, target_count: float) -> float:
    """
    Choose a round axis interval.

    Returns one of 1, 2, 2.5 or 5 times a power of ten, so that tick
    labels land on values a reader recognises rather than on arbitrary
    fractions of the data range.
    """
    if span <= 0 or target_count <= 0:
        return 1.0
    raw = span / target_count
    mag = 10.0 ** math.floor(math.log10(raw))
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= mult * mag:
            return mult * mag
    return 10.0 * mag


def _ticks(lo: float, hi: float, step: float) -> list[float]:
    """Tick values at multiples of the step spanning the range."""
    first = math.ceil(lo / step) * step
    out, v, guard = [], first, 0
    while v <= hi + 1e-9 and guard < 500:
        out.append(0.0 if abs(v) < 1e-9 else v)
        v += step
        guard += 1
    return out


# automatic vertical exaggeration steps; low, wide embankments such as
# coastal barriers need the larger ones
VE_STEPS = (1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 30, 40, 60, 80, 100)


def _ylabel(p: dict, plot_h: float) -> str:
    """The elevation axis title, shortened if it would not fit the axis."""
    full = f"Elevation ({_zlab(p)})"
    if len(full) * 6.0 <= plot_h:
        return full
    short = f"El. ({_zlab(p).replace('m above embankment base', 'm above base')})"
    return short if len(short) * 6.0 <= plot_h else "Elevation (m)"


def _fmt_tick(v: float, step: float) -> str:
    dec = 0 if step >= 1 else (1 if step >= 0.1 else 2)
    return f"{v:.{dec}f}"


def _legend_mark(kind: str, colour: str, x: float, y: float) -> str:
    """
    The legend sample for a panel row, drawn as the item is drawn: a filled
    square for areas, a short line for levels (solid, dashed or dotted), an
    outlined square for an opening.
    """
    if kind == "swatch":
        return (f'<rect x="{x}" y="{y - 8}" width="10" height="10" rx="1.5" '
                f'fill="{colour}" stroke="{C_DAM_LN}" stroke-width="0.6"/>')
    if kind == "outline":
        return (f'<rect x="{x + 0.8}" y="{y - 7.2}" width="8.4" height="8.4" '
                f'fill="#FFFFFF" stroke="{colour}" stroke-width="1.6"/>')
    dash = {"line": "", "dash": ' stroke-dasharray="4 2.5"',
            "dot": ' stroke-dasharray="1.2 2.4" stroke-linecap="round"'}.get(kind)
    if dash is None:
        return ""
    return (f'<line x1="{x - 1}" y1="{y - 3}" x2="{x + 11}" y2="{y - 3}" '
            f'stroke="{colour}" stroke-width="{1.6 if kind != "line" else 2}"{dash}/>')


def _panel(e: list, rows: list, ax: float, top: float, w: float, h: float,
           title: str, footer: tuple | None = None, ids: bool = False):
    """The labelled panel beside a drawing: one row per item, value right."""
    e.append(f'<rect x="{ax}" y="{top}" width="{w}" height="{h:.1f}" rx="4" '
             f'fill="{C_PANEL}" stroke="#DCE4EC" stroke-width="1"/>')
    e.append(f'<text x="{ax + 14}" y="{top + 24}" font-size="11.5" '
             f'font-weight="600" fill="{C_TEXT}">{_esc(title)}</text>')
    ty = top + 36
    for row in rows:
        kind, colour, label, value = row[:4]
        ty += 19
        if kind:
            e.append(_legend_mark(kind, colour, ax + 14, ty))
        e.append(f'<text x="{ax + 31}" y="{ty}" font-size="11" '
                 f'fill="{C_MUTED}">{_esc(label)}</text>')
        rid = f' id="f_{row[4]}"' if ids and len(row) > 4 else ""
        e.append(f'<text{rid} x="{ax + w - 14}" y="{ty}" font-size="11" '
                 f'text-anchor="end" fill="{C_TEXT}" font-weight="500">'
                 f'{_esc(value)}</text>')
    if footer:
        ty += 24
        e.append(f'<line x1="{ax + 14}" y1="{ty - 13}" x2="{ax + w - 14}" '
                 f'y2="{ty - 13}" stroke="#DCE4EC" stroke-width="1"/>')
        e.append(f'<text x="{ax + 14}" y="{ty}" font-size="11" '
                 f'fill="{C_MUTED}">{_esc(footer[0])}</text>')
        e.append(f'<text x="{ax + w - 14}" y="{ty}" font-size="11" '
                 f'text-anchor="end" fill="{C_TEXT}" font-weight="500">'
                 f'{_esc(footer[1])}</text>')


def _halo(colour: str = "#FFFFFF") -> str:
    """Attributes giving a text label a light outline, so it stays legible
    over lines and fills."""
    return (f' stroke="{colour}" stroke-width="3" stroke-linejoin="round" '
            f'paint-order="stroke"')


def failure_mode_text(p: dict) -> str:
    if int(p.get("breach_mode", 1)) == 2:
        return "Piping"
    return {1: "Overtopping, surface erosion", 2: "Overtopping, headcut",
            3: "Overtopping, clay core"}.get(int(p.get("overtopping_mode", 1)),
                                             "Overtopping")


ANN_W = 266          # width of the labelled panel beside each drawing

import itertools as _it
_IDS = _it.count(1)


def _uid(prefix: str) -> str:
    """An id unique to this drawing, so that two drawings on one page never
    share a pattern or clip path."""
    return f"{prefix}{next(_IDS)}"


def cross_section_svg(p: dict, width: int = 1000,
                      ve_override: float | None = None) -> str:
    """
    Draw an idealised cross-section of the embankment as configured.

    Design intent:

      * Labels live in a fixed panel on the right, so they can never
        collide with the geometry or with one another. Each row's sample
        is drawn as the item is: filled squares for areas, lines for
        levels.
      * Axis intervals snap to round numbers and grow denser as the
        vertical exaggeration increases, so zooming in reveals finer
        elevations rather than relabelling the same six values.
      * The canvas is sized to the drawing, so there is no large empty
        area above or below the section.
      * Horizontal and vertical scales differ. A dam is far wider than
        it is tall, so a true-scale section would be a sliver. The
        exaggeration applied is stated, and quoted slopes are always
        true slopes.
    """
    H = max(float(p.get("emb_height", 20.0)), 0.1)
    Wc = max(float(p.get("emb_crest_width", 10.0)), 0.1)
    Su = max(float(p.get("emb_us_slope", 0.4)), 0.01)
    Sd = max(float(p.get("emb_ds_slope", 0.4)), 0.01)
    hb = float(p.get("hard_bottom_elev", 0.0))
    wsl_u = float(p.get("wsl_up_initial", 0.0))
    wsl_d = float(p.get("wsl_down_initial", 0.0))
    mode = int(p.get("breach_mode", 1))
    settle = mode == 1 and p.get("ot_trigger") == "settlement"
    core = core_polygon(p)
    covers = cover_polygons(p)
    cov = clay_cover(p)

    run_u, run_d = H / Su, H / Sd
    dam_w = run_u + Wc + run_d
    res_w = max(dam_w * 0.55, 25.0)
    _cone = p.get("_cone") or {}
    if _cone:
        # backscarp measured from where the invert meets the upstream face
        _xf = float(_cone["z_invert"]) / Su
        res_w = max(res_w, (float(_cone["L"]) - _xf) * 1.12)
    tail_w = max(dam_w * 0.28, 18.0)

    PL, PT, PB = 78, 40, 62
    PR = ANN_W + 26
    plot_w = width - PL - PR

    x0, x1 = -res_w, dam_w + tail_w
    y_lo_raw = min(hb, 0.0) - max(H * 0.10, 1.0)
    y_hi_raw = max(H, wsl_u) + max(H * 0.10, 1.0)

    sx = plot_w / (x1 - x0)

    # --- vertical exaggeration -------------------------------------
    # Automatic mode aims for a section about 330 px tall, then rounds to
    # a value a reader can hold in mind.
    span_raw = y_hi_raw - y_lo_raw
    if ve_override and ve_override > 0:
        ve = float(ve_override)
    else:
        want = 330.0 / max(span_raw * sx, 1e-6)
        ve = min((v for v in VE_STEPS if v >= want), default=VE_STEPS[-1])
        ve = max(1.0, float(ve))
    sy = sx * ve

    # --- axis intervals, denser when zoomed in ---------------------
    draw_h_raw = span_raw * sy
    y_step = _nice_step(span_raw, max(3.0, draw_h_raw / 34.0))
    _off = _zoff(p)
    y_lo = math.floor((y_lo_raw + _off) / y_step) * y_step - _off
    y_hi = math.ceil((y_hi_raw + _off) / y_step) * y_step - _off
    yticks = [v - _off for v in _ticks(y_lo + _off, y_hi + _off, y_step)]

    draw_h = (y_hi - y_lo) * sy
    x_step = _nice_step(x1 - x0, max(3.0, plot_w / 90.0))
    xticks = _ticks(x0, x1, x_step)

    us_toe, crest_u = 0.0, run_u
    crest_d, ds_toe = run_u + Wc, dam_w

    curve = p.get("res_curve") or []
    res_bed = (min(float(z) for z, _ in curve) if curve
               else (hb if hb > 0 else 0.0))
    pond_top = min(wsl_u, H)

    # --- annotation rows, built before the panel is sized ----------
    # The panel must be tall enough for every row, otherwise entries are
    # silently dropped and the legend appears to change when the drawing
    # height changes.
    rows = [("swatch", C_DAM, "Crest elevation", _ze(p, H)),
            (None, None, "Crest width", f"{Wc:g} m"),
            (None, None, "Upstream slope", f"{1 / Su:.2f}H:1V"),
            (None, None, "Downstream slope", f"{1 / Sd:.2f}H:1V"),
            (None, None, "Base width (toe to toe)", f"{dam_w:,.0f} m"),
            (None, None, "Length along crest",
             f"{float(p.get('emb_length', 0)):,.0f} m")]
    if core:
        off_c = float(p.get("core_center", 0.0))
        rows.append(("swatch", C_CORE, "Clay core height", f"{core[1][1]:g} m"))
        rows.append((None, None, "Core crest width",
                     f"{float(p.get('core_crest_width', 0)):g} m"))
        rows.append((None, None, "Core offset",
                     "centred" if abs(off_c) < 1e-9 else
                     f"{abs(off_c):g} m {'downstream' if off_c > 0 else 'upstream'}"))
    if cov:
        segs = {"upstream slope": "u/s", "crest": "crest", "downstream slope": "d/s"}
        rows.append(("swatch", C_COVER, "Clay cover",
                     f"{next(iter(cov))}, {next(iter(cov.values())):g} m"
                     if len(cov) == 1 else
                     ", ".join(f"{segs[k]} {v:g} m" for k, v in cov.items())))
    if pond_top > res_bed:
        rows.append(("line", C_WATER_LN, "Pond level", _ze(p, wsl_u)))
        # With a cone drawn, the pond sits on the tailings beach, not on the
        # base of the storage curve.
        _floor = max(res_bed, float(_cone["z_beach"])) if _cone else res_bed
        rows.append((None, None, "Pond depth at dam",
                     f"{max(pond_top - _floor, 0.0):,.1f} m"))
        if res_bed > 0:
            rows.append(("dash", C_MUTED, "Storage curve base", _ze(p, res_bed)))
    if wsl_d > 0.01:
        rows.append(("swatch", C_WATER, "Initial tailwater", _ze(p, wsl_d)))
    rows.append(("dash", C_LIMIT, "Erosion limit", _ze(p, hb)))
    rows.append((None, None, "Max breach height", f"{H - hb:,.1f} m"))
    if _cone:
        rows.append(("swatch", C_TAIL, "Tailings surface",
                     _ze(p, _cone["z_beach"])))
        rows.append(("swatch", C_TAIL_MOB, "Post-failure slope",
                     f"{float(_cone['slope']) * 100:.1f} %"))
        rows.append((None, None, "Backscarp distance",
                     f"{float(_cone['L']):,.0f} m"
                     + (" (capped)" if _cone.get("truncated") else "")))
        rows.append((None, None, "Cone volume",
                     f"{float(_cone['volume']) / 1e6:,.2f} Mm³"))
    if mode == 1:
        rows.append(("outline", C_BREACH,
                     "Crest settlement, height × length" if settle
                     else "Pilot channel, depth × width",
                     f"{float(p.get('pilot_depth', 0)):g} × "
                     f"{float(p.get('pilot_width', 0)):g} m"))
    else:
        rows.append(("swatch", C_BREACH, "Initial pipe invert",
                     _ze(p, H - float(p.get('pipe_depth', 0)))))
        rows.append((None, None, "Pipe width (square)",
                     f"{float(p.get('pipe_width', 0)):g} m"))

    # --- canvas sized to content -----------------------------------
    # header + one line per row + divider and failure mode + padding
    ann_h = 36 + len(rows) * 19 + 44
    plot_h = draw_h
    height = int(PT + max(plot_h, ann_h) + PB)

    def X(x): return PL + (x - x0) * sx
    def Y(y): return PT + draw_h - (y - y_lo) * sy

    def poly(pts):
        return "M " + " L ".join(f"{X(a):.1f} {Y(b):.1f}" for a, b in pts) + " Z"

    e = []

    e.append(f'<text x="{PL}" y="24" font-size="13" font-weight="600" '
             f'fill="{C_TEXT}">Dam Cross-Section: Simplified Schematic</text>')

    # plot frame
    e.append(f'<rect x="{PL}" y="{PT}" width="{plot_w:.1f}" '
             f'height="{plot_h:.1f}" fill="#FFFFFF" stroke="#DCE4EC" '
             f'stroke-width="1"/>')

    # horizontal gridlines
    for v in yticks:
        yy = Y(v)
        is_zero = abs(v) < 1e-9
        e.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{PL + plot_w:.1f}" '
                 f'y2="{yy:.1f}" stroke="{"#C9D3DD" if is_zero else "#EEF2F6"}" '
                 f'stroke-width="{1.1 if is_zero else 0.8}"/>')

    # foundation
    if Y(0) < PT + plot_h:
        e.append(f'<rect x="{PL}" y="{Y(0):.1f}" width="{plot_w:.1f}" '
                 f'height="{PT + plot_h - Y(0):.1f}" fill="{C_FOUND}"/>')
        e.append(f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{PL + plot_w:.1f}" '
                 f'y2="{Y(0):.1f}" stroke="{C_FOUND_LN}" stroke-width="1.2"/>')

    # tailings and cone of depression, when supplied
    if _cone:
        zt, zi = float(_cone["z_beach"]), float(_cone["z_invert"])
        s_c, L_c = float(_cone["slope"]), float(_cone["L"])
        xf_i = zi / Su                   # invert meets upstream face
        xf_t = zt / Su                   # beach meets upstream face
        x_bs = xf_i - L_c                # backscarp, towards the reservoir
        z_bs = zi + s_c * L_c            # surface elevation at backscarp
        # tailings deposit between reservoir bed and beach
        bed = min(res_bed, zi)
        e.append(f'<path d="M {PL} {Y(bed):.1f} L {PL} {Y(zt):.1f} '
                 f'L {X(xf_t):.1f} {Y(zt):.1f} L {X(bed / Su):.1f} '
                 f'{Y(bed):.1f} Z" fill="{C_TAIL}" opacity="0.85"/>')
        # mobilised zone above the post-failure surface
        e.append(f'<path d="M {X(xf_i):.1f} {Y(zi):.1f} '
                 f'L {X(max(x_bs, x0)):.1f} '
                 f'{Y(zi + s_c * (xf_i - max(x_bs, x0))):.1f} '
                 f'L {X(max(x_bs, x0)):.1f} {Y(zt):.1f} '
                 f'L {X(xf_t):.1f} {Y(zt):.1f} Z" fill="{C_TAIL_MOB}" '
                 f'opacity="0.75"/>')
        e.append(f'<line x1="{X(xf_i):.1f}" y1="{Y(zi):.1f}" '
                 f'x2="{X(max(x_bs, x0)):.1f}" '
                 f'y2="{Y(zi + s_c * (xf_i - max(x_bs, x0))):.1f}" '
                 f'stroke="#8A5A2B" stroke-width="1.6" '
                 f'stroke-dasharray="7 4"/>')
        e.append(f'<line x1="{X(max(x_bs, x0)):.1f}" y1="{Y(zt):.1f}" '
                 f'x2="{X(max(x_bs, x0)):.1f}" y2="{Y(z_bs):.1f}" '
                 f'stroke="#8A5A2B" stroke-width="1.2"/>')
        res_bed = max(res_bed, zt)       # water only above the beach

    # impounded water
    if pond_top > res_bed:
        e.append(f'<path d="M {PL} {Y(res_bed):.1f} L {PL} {Y(pond_top):.1f} '
                 f'L {X(us_toe + pond_top / Su):.1f} {Y(pond_top):.1f} '
                 f'L {X(us_toe + res_bed / Su):.1f} {Y(res_bed):.1f} Z" '
                 f'fill="{C_WATER}" opacity="0.9"/>')
        e.append(f'<line x1="{PL}" y1="{Y(pond_top):.1f}" '
                 f'x2="{X(us_toe + pond_top / Su):.1f}" '
                 f'y2="{Y(pond_top):.1f}" stroke="{C_WATER_LN}" '
                 f'stroke-width="1.8"/>')
        if res_bed > 0:
            e.append(f'<line x1="{PL}" y1="{Y(res_bed):.1f}" '
                     f'x2="{X(us_toe + res_bed / Su):.1f}" '
                     f'y2="{Y(res_bed):.1f}" stroke="{C_MUTED}" '
                     f'stroke-width="1" stroke-dasharray="5 4"/>')

    if wsl_d > 0.01:
        # tailwater against the downstream face, up to its initial level
        zt_ = min(wsl_d, H)
        e.append(f'<path d="M {X(ds_toe - zt_ / Sd):.1f} {Y(zt_):.1f} '
                 f'L {PL + plot_w:.1f} {Y(zt_):.1f} L {PL + plot_w:.1f} {Y(0):.1f} '
                 f'L {X(ds_toe):.1f} {Y(0):.1f} Z" fill="{C_WATER}" opacity="0.6"/>')

    # embankment
    e.append(f'<path d="M {X(us_toe):.1f} {Y(0):.1f} '
             f'L {X(crest_u):.1f} {Y(H):.1f} L {X(crest_d):.1f} {Y(H):.1f} '
             f'L {X(ds_toe):.1f} {Y(0):.1f} Z" fill="{C_DAM}" '
             f'stroke="{C_DAM_LN}" stroke-width="1.4"/>')

    # clay core and cover, inside the embankment outline
    if core:
        e.append(f'<path d="{poly(core)}" fill="{C_CORE}" stroke="{C_CORE_LN}" '
                 f'stroke-width="1.2"/>')
    for c in covers:
        e.append(f'<path d="{poly(c)}" fill="{C_COVER}" stroke="{C_COVER}" '
                 f'stroke-width="1.2" stroke-linejoin="round"/>')

    # erosion limit
    e.append(f'<line x1="{PL}" y1="{Y(hb):.1f}" x2="{PL + plot_w:.1f}" '
             f'y2="{Y(hb):.1f}" stroke="{C_LIMIT}" stroke-width="1.6" '
             f'stroke-dasharray="8 5"/>')

    # initial breach
    mid = (crest_u + crest_d) / 2
    if mode == 1:
        pd_ = float(p.get("pilot_depth", 0.2))
        # In section a pilot channel lowers the crest by its depth across
        # the crest width: drawn as a cut, with the original crest dashed,
        # and water in it up to the pond level.
        zc = H - pd_
        xa, xb = X(crest_u), X(crest_d)
        e.append(f'<rect x="{xa:.1f}" y="{Y(H):.1f}" width="{xb - xa:.1f}" '
                 f'height="{max(Y(zc) - Y(H), 2.0):.1f}" fill="{C_BG}"/>')
        if wsl_u > zc:
            zw = min(wsl_u, H)
            e.append(f'<rect x="{xa:.1f}" y="{Y(zw):.1f}" width="{xb - xa:.1f}" '
                     f'height="{max(Y(zc) - Y(zw), 1.0):.1f}" fill="{C_WATER}"/>')
        e.append(f'<path d="M {xa:.1f} {Y(H):.1f} L {xa:.1f} {Y(zc):.1f} '
                 f'L {xb:.1f} {Y(zc):.1f} L {xb:.1f} {Y(H):.1f}" fill="none" '
                 f'stroke="{C_BREACH}" stroke-width="1.6"/>')
        e.append(f'<line x1="{xa:.1f}" y1="{Y(H):.1f}" x2="{xb:.1f}" y2="{Y(H):.1f}" '
                 f'stroke="{C_DAM_LN}" stroke-width="1" stroke-dasharray="3 3"/>')
    else:
        dep = float(p.get("pipe_depth", 5.0))
        pw = float(p.get("pipe_width", 0.5))
        z = H - dep
        w_px, h_px = max(pw * sx, 6.0), max(pw * sy, 6.0)
        # the pipe runs through the section, drawn at mid-crest with its
        # line to the downstream face
        x_out = ds_toe - max(z, 0.0) / Sd
        e.append(f'<line x1="{X(z / Su):.1f}" y1="{Y(z) - h_px / 2:.1f}" '
                 f'x2="{X(x_out):.1f}" y2="{Y(z) - h_px / 2:.1f}" stroke="{C_BREACH}" '
                 f'stroke-width="1.2" stroke-dasharray="4 3" opacity="0.8"/>')
        e.append(f'<rect x="{X(mid) - w_px / 2:.1f}" y="{Y(z) - h_px:.1f}" '
                 f'width="{w_px:.1f}" height="{h_px:.1f}" fill="{C_BREACH}" '
                 f'stroke="#0E4A80" stroke-width="1"/>')

    # --- vertical axis ---
    for v in yticks:
        yy = Y(v)
        bold = abs(v) < 1e-9
        e.append(f'<line x1="{PL - 5}" y1="{yy:.1f}" x2="{PL}" '
                 f'y2="{yy:.1f}" stroke="{C_MUTED}" stroke-width="1"/>')
        weight = ' font-weight="600"' if bold else ''
        e.append(f'<text x="{PL - 9}" y="{yy + 3.4:.1f}" text-anchor="end" '
                 f'font-size="10.5" fill="{C_TEXT if bold else C_MUTED}"'
                 f'{weight}>{_fmt_tick(v + _off, y_step)}</text>')
    e.append(f'<text x="20" y="{PT + plot_h / 2:.1f}" font-size="11" '
             f'fill="{C_MUTED}" text-anchor="middle" '
             f'transform="rotate(-90 20 {PT + plot_h / 2:.1f})">'
             f'{_esc(_ylabel(p, plot_h))}</text>')

    # --- horizontal axis ---
    ax_y = PT + plot_h
    for v in xticks:
        xx = X(v)
        if xx < PL - 0.5 or xx > PL + plot_w + 0.5:
            continue
        e.append(f'<line x1="{xx:.1f}" y1="{ax_y}" x2="{xx:.1f}" '
                 f'y2="{ax_y + 5}" stroke="{C_MUTED}" stroke-width="1"/>')
        e.append(f'<text x="{xx:.1f}" y="{ax_y + 18}" text-anchor="middle" '
                 f'font-size="10.5" fill="{C_MUTED}">'
                 f'{_fmt_tick(v, x_step)}</text>')
    e.append(f'<text x="{PL + plot_w / 2:.1f}" y="{ax_y + 35}" '
             f'text-anchor="middle" font-size="11" fill="{C_MUTED}">'
             f'Distance from upstream toe (m)</text>')

    ve_txt = (f"Vertical exaggeration ×{ve:g}."
              if ve > 1.001 else "True scale, no vertical exaggeration.")
    e.append(f'<text x="{PL}" y="{height - 12}" font-size="10.5" '
             f'fill="{C_MUTED}">{ve_txt} Quoted slopes are true slopes. '
             f'Section idealised as trapezoids, after DLBreach.</text>')

    # --- annotation panel ---
    _panel(e, rows, width - ANN_W - 14, PT, ANN_W, max(plot_h, ann_h),
           "Configuration", footer=("Failure mode", failure_mode_text(p)))

    # The drawing is capped at its natural width. Allowing the browser to
    # scale it up to fill the frame would make it taller than the height
    # the interface reserves, and the bottom of the section, the distance
    # axis and its label would be clipped.
    return (f'<div style="max-width:{width}px;margin:0;">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
            f'viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="xMinYMin meet" '
            f'style="display:block;height:auto;'
            f'font-family:{FONT}">'
            f'<rect width="{width}" height="{height}" fill="{C_BG}"/>'
            + "".join(e) + "</svg></div>")


def svg_height(svg: str, default: int = 470) -> int:
    """
    Read the drawing height back out of a generated schematic.

    The canvas is sized to its content, so the interface reads the height
    rather than assuming one and clipping the section.
    """
    try:
        vb = svg.split('viewBox="', 1)[1].split('"', 1)[0].split()
        return int(float(vb[3]))
    except (IndexError, ValueError):
        return default


# =====================================================================
# Post-breach face view, looking upstream from downstream
# =====================================================================

def _abutments(e: list, X, Y, L: float, H: float, x0: float, x1: float,
               y_lo: float, one_sided: bool, sx: float) -> str:
    """
    The valley sides at the two ends of the crest, hatched. With a
    one-sided breach the left-hand abutment is the side of the breach that
    is not erodible (Wu 2016, Section 4.3), and is labelled so.
    """
    top = H * 1.06
    pid, cid = _uid("abut"), _uid("crest")
    # the breach is clipped to the crest length: the abutments do not erode
    e.append(f'<defs><pattern id="{pid}" width="7" height="7" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<rect width="7" height="7" fill="{C_ABUT}"/>'
             f'<line x1="0" y1="0" x2="0" y2="7" stroke="{C_ABUT_LN}" '
             'stroke-width="1.2"/></pattern>'
             f'<clipPath id="{cid}"><rect x="{X(0) - 1.5:.1f}" y="0" '
             f'width="{X(L) - X(0) + 3:.1f}" height="100000"/></clipPath></defs>')
    for a, b in ((x0, 0.0), (L, x1)):
        if X(b) - X(a) < 2:
            continue
        e.append(f'<rect x="{X(a):.1f}" y="{Y(top):.1f}" width="{X(b) - X(a):.1f}" '
                 f'height="{Y(y_lo) - Y(top):.1f}" fill="url(#{pid})"/>')
        edge = b if a == x0 else a
        e.append(f'<line x1="{X(edge):.1f}" y1="{Y(top):.1f}" x2="{X(edge):.1f}" '
                 f'y2="{Y(y_lo):.1f}" stroke="{C_ABUT_LN}" stroke-width="1.2"/>')
    if one_sided and X(0) - X(x0) >= 14:
        xm = (X(x0) + X(0)) / 2 + 4
        ym = (Y(top) + Y(0)) / 2
        e.append(f'<text x="{xm:.1f}" y="{ym:.1f}" font-size="10.5" '
                 f'font-weight="600" fill="{C_TEXT}" text-anchor="middle" '
                 f'transform="rotate(-90 {xm:.1f} {ym:.1f})"'
                 f'{_halo(C_ABUT)}>abutment (not erodible)</text>')
    return cid


def _limit_label(e: list, PL, plot_w, PT, plot_h, y: float, text: str,
                 x_right: float | None = None):
    """Erosion limit label at the right, below the line where there is
    room (in the foundation), otherwise above it."""
    yy = y + 13 if y + 15 < PT + plot_h else y - 5
    xr = min(PL + plot_w, x_right if x_right is not None else PL + plot_w) - 6
    e.append(f'<text x="{xr:.1f}" y="{yy:.1f}" text-anchor="end" '
             f'font-size="10.5" fill="{C_LIMIT}"{_halo()}>{_esc(text)}</text>')


def _face_frame(L: float, one_sided: bool):
    """Horizontal extent of a face view: the crest plus room for the
    abutments, wider on the left for a one-sided breach (to be labelled)."""
    m = max(L * 0.04, 5.0)
    return (-max(L * 0.07, 8.0) if one_sided else -m), L + m


def location_text(p: dict) -> str:
    return ("One-sided (at abutment)" if float(p.get("breach_location", 2.0)) < 1.5
            else "Two-sided (centred)")


def breach_face_svg(p: dict, state: dict, width: int = 1000,
                    ve_override: float | None = None) -> str:
    """
    Draw the breach opening as seen looking upstream from downstream.

    This is the elevation view of the dam face, showing the trapezoidal
    breach cut through it. It answers the question the cross-section
    cannot: how wide is the opening relative to the dam, and how much of
    the embankment is gone.

    `state` is one row of the DLBreach output, as a dictionary, and must
    carry breach_bottom_width, breach_top_width, breach_bottom_elev and
    breach_side_slope. Passing an intermediate row rather than the final
    one shows the breach part-formed at that moment.

    A two-sided breach is centred on the crest and widens both ways. A
    one-sided breach has one side that is not erodible (Wu 2016, Section
    4.3); it is drawn against the left-hand abutment and widens to the
    right only.
    """
    H = max(float(p.get("emb_height", 20.0)), 0.1)
    L = max(float(p.get("emb_length", 300.0)), 1.0)
    one_sided = float(p.get("breach_location", 2.0)) < 1.5

    def num(k, d=0.0):
        try:
            v = float(state.get(k, d))
        except (TypeError, ValueError):
            return d
        return v if math.isfinite(v) else d

    bb = max(num("breach_bottom_width"), 0.0)
    bt = max(num("breach_top_width", bb), bb)
    zb = num("breach_bottom_elev")
    zsl = num("breach_side_slope")
    wsl = num("wsl_up")
    t_hr = num("time_hr")
    q = num("Q_breach")

    depth = max(H - zb, 0.0)

    # Piping phase detection.
    #
    # Before the roof of a pipe collapses, the opening is an internal
    # conduit, not a notch cut down from the crest. DLBreach still
    # reports a top width in that phase, but it is the width the
    # equivalent trapezoid would have at crest level, not a hole in the
    # crest. Drawing it literally would show the dam open to the sky
    # before anything has actually happened to the crest.
    #
    # The test is whether downcutting has begun: while the invert sits at
    # the initial pipe elevation, the pipe is still enlarging in place.
    piping_phase = False
    if int(p.get("breach_mode", 1)) == 2:
        z_pipe0 = H - float(p.get("pipe_depth", 0.0))
        # The invert erodes by a fraction of a millimetre from the first
        # time step, so an exact comparison never matches. The phase ends
        # when meaningful downcutting has occurred.
        tol = max(0.02 * H, 0.10)
        piping_phase = zb >= z_pipe0 - tol

    PL, PT, PB = 78, 40, 76
    PR = ANN_W + 26
    plot_w = width - PL - PR

    hb = float(p.get("hard_bottom_elev", 0.0))
    x0, x1 = _face_frame(L, one_sided)
    y_lo_raw = min(zb, hb, 0.0) - max(H * 0.10, 1.0)
    y_hi_raw = max(H, wsl, hb) + max(H * 0.10, 1.0)

    sx = plot_w / (x1 - x0)
    span_raw = y_hi_raw - y_lo_raw
    if ve_override and ve_override > 0:
        ve = float(ve_override)
    else:
        want = 300.0 / max(span_raw * sx, 1e-6)
        ve = min((v for v in VE_STEPS if v >= want), default=VE_STEPS[-1])
        ve = max(1.0, float(ve))
    sy = sx * ve

    draw_h_raw = span_raw * sy
    y_step = _nice_step(span_raw, max(3.0, draw_h_raw / 34.0))
    _off = _zoff(p)
    y_lo = math.floor((y_lo_raw + _off) / y_step) * y_step - _off
    y_hi = math.ceil((y_hi_raw + _off) / y_step) * y_step - _off
    yticks = [v - _off for v in _ticks(y_lo + _off, y_hi + _off, y_step)]
    draw_h = (y_hi - y_lo) * sy

    x_step = _nice_step(x1 - x0, max(3.0, plot_w / 90.0))
    xticks = [v for v in _ticks(x0, x1, x_step) if -1e-9 <= v <= L + 1e-9]

    # breach position along the crest
    if one_sided:
        b_lo_bot, b_hi_bot = 0.0, bb
        b_lo_top, b_hi_top = 0.0, bt
    else:
        c = L / 2
        b_lo_bot, b_hi_bot = c - bb / 2, c + bb / 2
        b_lo_top, b_hi_top = c - bt / 2, c + bt / 2

    wdn = float(state.get("wsl_down", float("nan")))
    if piping_phase:
        rows = [(None, None, "Stage", "Piping, pre-collapse"),
                (None, None, "Breach location", location_text(p)),
                ("swatch", C_WATER, "Pipe width (square)", f"{bb:,.2f} m"),
                (None, None, "Pipe invert", _ze(p, zb)),
                (None, None, "Depth below crest", f"{depth:,.2f} m"),
                ("swatch", C_DAM, "Crest elevation", _ze(p, H)),
                (None, None, "Crest length", f"{L:,.0f} m")]
    else:
        rows = [(None, None, "Stage", "Open breach"),
                (None, None, "Breach location", location_text(p)),
                ("outline", C_BREACH, "Breach top width", f"{bt:,.1f} m"),
                (None, None, "Breach bottom width", f"{bb:,.1f} m"),
                (None, None, "Breach invert", _ze(p, zb)),
                (None, None, "Breach height", f"{depth:,.2f} m"),
                (None, None, "Side slope",
                 f"{(1 / zsl):.2f}H:1V" if zsl > 0.01 else "vertical"),
                ("swatch", C_DAM, "Crest elevation", _ze(p, H)),
                (None, None, "Crest length", f"{L:,.0f} m"),
                (None, None, "Breached fraction",
                 f"{min(bt / L, 1.0) * 100:,.1f} %")]
    rows.append(("dash", C_LIMIT, "Erosion limit", _ze(p, hb)))
    if not piping_phase:
        rows.append((None, None, "Invert above erosion limit",
                     f"{max(zb - hb, 0.0):,.1f} m"))
    hflow = None if piping_phase else breach_flow_depth(state)
    if hflow is not None and hflow > 0:
        rows.append(("swatch", C_WATER, "Flow depth in breach", f"{hflow:,.2f} m"))
        reg = flow_regime(state)
        if reg:
            rows.append((None, None, "Depth set by", reg))
    if wsl > zb:
        rows.append(("dash", C_POND_LN, "Pond level", _ze(p, wsl)))
    if math.isfinite(wdn) and not piping_phase:
        rows.append(("dot", C_TW_LN, "Tailwater",
                     _ze(p, wdn) + (", below invert" if wdn <= zb else "")))
    rows.append((None, None, "Hydrograph time", f"{t_hr:,.2f} h"))
    rows.append((None, None, "Discharge", f"{q:,.0f} m³/s"))

    ann_h = 36 + len(rows) * 19 + 20
    plot_h = draw_h
    height = int(PT + max(plot_h, ann_h) + PB)

    def X(x): return PL + (x - x0) * sx
    def Y(y): return PT + draw_h - (y - y_lo) * sy

    e = []
    e.append(f'<text x="{PL}" y="24" font-size="13" font-weight="600" '
             f'fill="{C_TEXT}">Post-Breach Face: View Looking Upstream '
             f'from Downstream</text>')
    e.append(f'<rect x="{PL}" y="{PT}" width="{plot_w:.1f}" '
             f'height="{plot_h:.1f}" fill="#FFFFFF" stroke="#DCE4EC" '
             f'stroke-width="1"/>')

    for v in yticks:
        yy = Y(v)
        zero = abs(v) < 1e-9
        e.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{PL + plot_w:.1f}" '
                 f'y2="{yy:.1f}" '
                 f'stroke="{"#C9D3DD" if zero else "#EEF2F6"}" '
                 f'stroke-width="{1.1 if zero else 0.8}"/>')

    if Y(0) < PT + plot_h:
        e.append(f'<rect x="{PL}" y="{Y(0):.1f}" width="{plot_w:.1f}" '
                 f'height="{PT + plot_h - Y(0):.1f}" fill="{C_FOUND}"/>')
    clip = _abutments(e, X, Y, L, H, x0, x1, y_lo, one_sided, sx)
    cl = f' clip-path="url(#{clip})"'

    # The dam is drawn whole and the opening is then removed from it.
    # Drawing two side panels instead leaves a sliver running the full
    # height of the dam, because the panel edges follow the breach sides
    # even below the invert, where the embankment is in fact intact.
    e.append(f'<rect x="{X(0):.1f}" y="{Y(H):.1f}" '
             f'width="{L * sx:.1f}" height="{(H - 0) * sy:.1f}" '
             f'fill="{C_DAM}" stroke="{C_DAM_LN}" stroke-width="1.3"/>')

    px_lo, px_hi = X(0), X(L)          # level lines stay within the crest
    if piping_phase:
        # a square conduit within the embankment, not open to the crest
        side = max(bb, 0.01)
        w_px = max(side * sx, 7.0)
        h_px = max(side * sy, 7.0)
        # against the abutment for a one-sided breach, else mid-crest
        rx = X(0) if one_sided else X(L / 2) - w_px / 2
        e.append(f'<rect x="{rx:.1f}" '
                 f'y="{Y(zb) - h_px:.1f}" width="{w_px:.1f}" '
                 f'height="{h_px:.1f}" fill="{C_WATER}" '
                 f'stroke="{C_BREACH}" stroke-width="1.6"/>')
    else:
        # cut the trapezoidal opening out of the face
        void = (f'M {X(b_lo_top):.1f} {Y(H):.1f} '
                f'L {X(b_lo_bot):.1f} {Y(zb):.1f} '
                f'L {X(b_hi_bot):.1f} {Y(zb):.1f} '
                f'L {X(b_hi_top):.1f} {Y(H):.1f} Z')
        e.append(f'<path d="{void}" fill="#FFFFFF"{cl}/>')

        # Water in the opening is drawn at the flow depth implied by the
        # breach flow area DLBreach reports, not at the pond level: flow
        # passing the breach is shallower than the pond behind it.
        zw = (zb + hflow) if hflow is not None else wsl
        zw = min(zw, wsl, H)
        if zw > zb and depth > 0:
            frac = min(max((zw - zb) / depth, 0.0), 1.0)
            wl_lo = b_lo_bot + (b_lo_top - b_lo_bot) * frac
            wl_hi = b_hi_bot + (b_hi_top - b_hi_bot) * frac
            e.append(f'<path d="M {X(b_lo_bot):.1f} {Y(zb):.1f} '
                     f'L {X(wl_lo):.1f} {Y(zw):.1f} '
                     f'L {X(wl_hi):.1f} {Y(zw):.1f} '
                     f'L {X(b_hi_bot):.1f} {Y(zb):.1f} Z" '
                     f'fill="{C_WATER}" opacity="0.9"{cl}/>')
            e.append(f'<line x1="{X(wl_lo):.1f}" y1="{Y(zw):.1f}" '
                     f'x2="{X(wl_hi):.1f}" y2="{Y(zw):.1f}" '
                     f'stroke="{C_WATER_LN}" stroke-width="1.8"{cl}/>')
        lx0 = max(X(b_lo_top) - 18, px_lo)
        lx1 = min(X(b_hi_top) + 18, px_hi)
        if wsl > zb:
            e.append(f'<line x1="{lx0:.1f}" y1="{Y(wsl):.1f}" x2="{lx1:.1f}" '
                     f'y2="{Y(wsl):.1f}" stroke="{C_POND_LN}" stroke-width="1.3" '
                     f'stroke-dasharray="5 4"/>')
            e.append(f'<text x="{lx1 - 4:.1f}" y="{Y(wsl) - 4:.1f}" '
                     f'text-anchor="end" font-size="10.5" '
                     f'fill="{C_POND_LN}"{_halo()}>pond</text>')
        if math.isfinite(wdn) and wdn > zb:
            e.append(f'<line x1="{lx0:.1f}" y1="{Y(wdn):.1f}" x2="{lx1:.1f}" '
                     f'y2="{Y(wdn):.1f}" stroke="{C_TW_LN}" stroke-width="1.5" '
                     f'stroke-dasharray="1.5 3" stroke-linecap="round"/>')
            e.append(f'<text x="{lx0 + 4:.1f}" y="{Y(wdn) - 4:.1f}" '
                     f'font-size="10.5" fill="{C_TW_LN}"{_halo()}>tailwater</text>')

        e.append(f'<path d="M {X(b_lo_top):.1f} {Y(H):.1f} '
                 f'L {X(b_lo_bot):.1f} {Y(zb):.1f} '
                 f'L {X(b_hi_bot):.1f} {Y(zb):.1f} '
                 f'L {X(b_hi_top):.1f} {Y(H):.1f}" fill="none" '
                 f'stroke="{C_BREACH}" stroke-width="1.8"{cl}/>')
        e.append(f'<line x1="{X(b_lo_top):.1f}" y1="{Y(H):.1f}" '
                 f'x2="{X(b_hi_top):.1f}" y2="{Y(H):.1f}" '
                 f'stroke="{C_DAM_LN}" stroke-width="1" '
                 f'stroke-dasharray="6 4"{cl}/>')

    # erosion limit
    e.append(f'<line x1="{PL}" y1="{Y(hb):.1f}" x2="{PL + plot_w:.1f}" '
             f'y2="{Y(hb):.1f}" stroke="{C_LIMIT}" stroke-width="1.5" '
             f'stroke-dasharray="8 5"/>')
    _limit_label(e, PL, plot_w, PT, plot_h, Y(hb), f"erosion limit {_ze(p, hb)}",
                 X(L))

    # axes
    for v in yticks:
        yy = Y(v)
        bold = abs(v) < 1e-9
        weight = ' font-weight="600"' if bold else ''
        e.append(f'<line x1="{PL - 5}" y1="{yy:.1f}" x2="{PL}" y2="{yy:.1f}" '
                 f'stroke="{C_MUTED}" stroke-width="1"/>')
        e.append(f'<text x="{PL - 9}" y="{yy + 3.4:.1f}" text-anchor="end" '
                 f'font-size="10.5" fill="{C_TEXT if bold else C_MUTED}"'
                 f'{weight}>{_fmt_tick(v + _off, y_step)}</text>')
    e.append(f'<text x="20" y="{PT + plot_h / 2:.1f}" font-size="11" '
             f'fill="{C_MUTED}" text-anchor="middle" '
             f'transform="rotate(-90 20 {PT + plot_h / 2:.1f})">'
             f'{_esc(_ylabel(p, plot_h))}</text>')

    ax_y = PT + plot_h
    for v in xticks:
        xx = X(v)
        if xx < PL - 0.5 or xx > PL + plot_w + 0.5:
            continue
        e.append(f'<line x1="{xx:.1f}" y1="{ax_y}" x2="{xx:.1f}" '
                 f'y2="{ax_y + 5}" stroke="{C_MUTED}" stroke-width="1"/>')
        e.append(f'<text x="{xx:.1f}" y="{ax_y + 18}" text-anchor="middle" '
                 f'font-size="10.5" fill="{C_MUTED}">'
                 f'{_fmt_tick(v, x_step)}</text>')
    e.append(f'<text x="{PL + plot_w / 2:.1f}" y="{ax_y + 35}" '
             f'text-anchor="middle" font-size="11" fill="{C_MUTED}">'
             f'Distance along crest (m)</text>')

    ve_txt = (f"Vertical exaggeration ×{ve:g}."
              if ve > 1.001 else "True scale.")
    note = ("Pipe still enlarging within the embankment; the crest is intact."
            if piping_phase else
            "Grey dashed: original crest.")
    loc = ("One-sided breach: the left side is not erodible, so the breach "
           "widens to the right only."
           if one_sided else "Two-sided breach: centred, widening both ways.")
    e.append(f'<text x="{PL}" y="{height - 26}" font-size="10.5" '
             f'fill="{C_MUTED}">{ve_txt} {loc} {note}</text>')
    e.append(f'<text x="{PL}" y="{height - 11}" font-size="10.5" '
             f'fill="{C_MUTED}">Blue fill: flow depth from the breach flow area. '
             f'Dashed blue: pond. Dotted: tailwater. Red dashed: erosion limit. '
             f'Hatched: abutments.</text>')

    _panel(e, rows, width - ANN_W - 14, PT, ANN_W, max(plot_h, ann_h),
           "Breach geometry")

    return (f'<div style="max-width:{width}px;margin:0;">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
            f'viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="xMinYMin meet" '
            f'style="display:block;height:auto;'
            f'font-family:{FONT}">'
            f'<rect width="{width}" height="{height}" fill="{C_BG}"/>'
            + "".join(e) + "</svg></div>")


def check_breach_consistency(p: dict, state: dict) -> str | None:
    """
    Verify the reported widths against the reported side slope.

    Top width should equal bottom width plus the horizontal run over the
    breach depth on each erodible side (two, or one for a one-sided
    breach). A mismatch means the top width is referenced
    to something other than crest level, and any area or volume derived
    from these numbers would be wrong.
    """
    H = float(p.get("emb_height", 0.0))
    bb = float(state.get("breach_bottom_width", 0.0))
    bt = float(state.get("breach_top_width", 0.0))
    zb = float(state.get("breach_bottom_elev", 0.0))
    zsl = float(state.get("breach_side_slope", 0.0))
    depth = H - zb
    if depth <= 0 or zsl <= 0.01 or bb <= 0:
        return None
    # one side slope for a one-sided breach, two otherwise (Wu 2016,
    # Section 4.3: n_loc = 1 or 2)
    n_loc = 1.0 if float(p.get("breach_location", 2.0)) < 1.5 else 2.0
    expected = bb + n_loc * depth / zsl
    if expected <= 0:
        return None
    err = abs(bt - expected) / expected
    if err > 0.05:
        return (f"Reported top width ({bt:,.1f} m) differs by "
                f"{err * 100:.0f}% from the value implied by the bottom "
                f"width, breach depth and side slope ({expected:,.1f} m).")
    return None


# =====================================================================
# Animated breach development
# =====================================================================

def breach_animation_html(p: dict, df, width: int = 1000,
                          ve_override: float | None = None,
                          max_frames: int = 220) -> str:
    """
    Animate the breach forming, as a self-contained playable widget.

    Every frame is drawn in Python and the resulting path geometry is
    embedded as data. The browser only swaps attributes, so playback is
    smooth and needs no round trip to the server, which a Streamlit
    slider could not provide.

    The static parts of the drawing — axes, embankment, annotation panel
    — are rendered once; only the opening, the water and the readouts
    change between frames.
    """
    import json as _json

    n = len(df)
    if n == 0:
        return "<div>No results to animate.</div>"

    # Frames are chosen by how much the breach is changing, not by equal
    # time steps. A run that develops in the first hour and then sits
    # unchanged for twenty-three more would otherwise spend almost every
    # frame on a static picture, and skip through the collapse in two.
    if n <= max_frames:
        idx = list(range(n))
    else:
        def _norm(col):
            a = df[col].to_numpy(dtype=float)
            rng = a.max() - a.min()
            return (a - a.min()) / rng if rng > 1e-12 else np.zeros_like(a)

        change = np.zeros(n)
        for col, wgt in (("breach_top_width", 1.0),
                         ("breach_bottom_elev", 1.0),
                         ("Q_breach", 0.6),
                         ("breach_flow_area", 0.5),
                         ("wsl_down", 0.5)):
            if col in df.columns:
                change += wgt * np.abs(np.diff(_norm(col), prepend=0.0))
        # a small uniform component keeps the quiet tail from vanishing
        change += 0.15 / n
        cum = np.cumsum(change)
        if cum[-1] <= 0:
            idx = list(range(0, n, max(1, n // max_frames)))
        else:
            # Two thirds of the frames follow the change, the rest are evenly
            # spaced in time steps, so that a fast collapse is resolved and
            # no stretch of the run is skipped in one jump. Frames that land
            # on the same step are topped up with evenly spaced ones.
            n_chg = int(round(max_frames * 2 / 3))
            targets = np.linspace(0, cum[-1], n_chg)
            chosen = {min(int(np.searchsorted(cum, t)), n - 1) for t in targets}
            chosen |= set(np.linspace(0, n - 1, max_frames - n_chg).astype(int).tolist())
            if len(chosen) < max_frames:
                spare = [i for i in np.linspace(0, n - 1, 2 * max_frames).astype(int)
                         if i not in chosen]
                step = max(1, len(spare) // max(max_frames - len(chosen), 1))
                chosen |= set(spare[::step][:max_frames - len(chosen)])
            idx = sorted(chosen)
    if idx[-1] != n - 1:
        idx.append(n - 1)

    H = max(float(p.get("emb_height", 20.0)), 0.1)
    _zp0 = H - float(p.get("pipe_depth", 0.0))
    _tolp = max(0.02 * H, 0.10)
    if int(p.get("breach_mode", 1)) == 2 and "breach_bottom_elev" in df.columns:
        # The pipe enlarges slowly and changes little, so a purely
        # change-weighted selection skips almost all of it. Give the phase
        # enough frames to be seen before the roof collapses.
        pipe_rows = np.where(
            df["breach_bottom_elev"].to_numpy(dtype=float) >= _zp0 - _tolp)[0]
        if len(pipe_rows) > 2:
            have = sum(1 for i in idx if i <= pipe_rows[-1])
            want_min = max(10, int(0.10 * max_frames))
            if have < want_min:
                extra = np.linspace(pipe_rows[0], pipe_rows[-1],
                                    want_min).astype(int)
                idx = sorted(set(idx) | set(int(i) for i in extra))
    L = max(float(p.get("emb_length", 300.0)), 1.0)
    hb = float(p.get("hard_bottom_elev", 0.0))
    one_sided = float(p.get("breach_location", 2.0)) < 1.5
    mode = int(p.get("breach_mode", 1))
    z_pipe0 = H - float(p.get("pipe_depth", 0.0))
    tol_pipe = max(0.02 * H, 0.10)

    # rows with missing values are drawn as the row before them
    _geo = [c for c in ("breach_bottom_width", "breach_top_width",
                        "breach_bottom_elev", "wsl_up", "Q_breach", "time_hr")
            if c in df.columns]
    df = df.copy()
    df[_geo] = df[_geo].ffill().fillna(0.0)
    sub = df.iloc[idx]
    wsl_max = float(sub["wsl_up"].max()) if "wsl_up" in sub else H
    zb_min = float(sub["breach_bottom_elev"].min())

    PL, PT, PB = 78, 40, 84
    ctrl_h = 52
    PR = ANN_W + 26
    plot_w = width - PL - PR
    x0, x1 = _face_frame(L, one_sided)
    y_lo_raw = min(zb_min, hb, 0.0) - max(H * 0.10, 1.0)
    y_hi_raw = max(H, wsl_max, hb) + max(H * 0.10, 1.0)

    sx = plot_w / (x1 - x0)
    span = y_hi_raw - y_lo_raw
    if ve_override and ve_override > 0:
        ve = float(ve_override)
    else:
        want = 300.0 / max(span * sx, 1e-6)
        ve = max(1.0, float(min((v for v in VE_STEPS if v >= want),
                                default=VE_STEPS[-1])))
    sy = sx * ve
    y_step = _nice_step(span, max(3.0, span * sy / 34.0))
    _off = _zoff(p)
    y_lo = math.floor((y_lo_raw + _off) / y_step) * y_step - _off
    y_hi = math.ceil((y_hi_raw + _off) / y_step) * y_step - _off
    yticks = [v - _off for v in _ticks(y_lo + _off, y_hi + _off, y_step)]
    draw_h = (y_hi - y_lo) * sy
    x_step = _nice_step(x1 - x0, max(3.0, plot_w / 90.0))
    xticks = [v for v in _ticks(x0, x1, x_step) if -1e-9 <= v <= L + 1e-9]

    plot_h = draw_h
    ann_h = 36 + 14 * 19 + 20
    height = int(PT + max(plot_h, ann_h) + PB + ctrl_h)

    def X(x): return PL + (x - x0) * sx
    def Y(y): return PT + draw_h - (y - y_lo) * sy

    # ---- per-frame geometry ----
    frames = []
    for i in idx:
        r = df.iloc[i]
        bb = max(float(r["breach_bottom_width"]), 0.0)
        bt = max(float(r["breach_top_width"]), bb)
        zb = float(r["breach_bottom_elev"])
        wsl = float(r.get("wsl_up", 0.0))
        depth = max(H - zb, 0.0)
        piping = (mode == 2) and (zb >= z_pipe0 - tol_pipe)

        if one_sided:
            lb, hbw, lt, ht = 0.0, bb, 0.0, bt
        else:
            c = L / 2
            lb, hbw, lt, ht = c - bb / 2, c + bb / 2, c - bt / 2, c + bt / 2

        if piping:
            side = max(bb, 0.01)
            w_px, h_px = max(side * sx, 7.0), max(side * sy, 7.0)
            rx = X(0) if one_sided else X(L / 2) - w_px / 2
            d_void = (f"M {rx:.1f} {Y(zb) - h_px:.1f} "
                      f"h {w_px:.1f} v {h_px:.1f} h {-w_px:.1f} Z")
            d_water, d_out = d_void, ""
        else:
            d_void = (f"M {X(lt):.1f} {Y(H):.1f} L {X(lb):.1f} {Y(zb):.1f} "
                      f"L {X(hbw):.1f} {Y(zb):.1f} L {X(ht):.1f} {Y(H):.1f} Z")
            d_out = (f"M {X(lt):.1f} {Y(H):.1f} L {X(lb):.1f} {Y(zb):.1f} "
                     f"L {X(hbw):.1f} {Y(zb):.1f} L {X(ht):.1f} {Y(H):.1f}")
            hf = breach_flow_depth(r.to_dict())
            zw = min((zb + hf) if hf is not None else wsl, wsl, H)
            if zw > zb and depth > 0:
                f_ = min(max((zw - zb) / depth, 0.0), 1.0)
                wl, wh = lb + (lt - lb) * f_, hbw + (ht - hbw) * f_
                d_water = (f"M {X(lb):.1f} {Y(zb):.1f} "
                           f"L {X(wl):.1f} {Y(zw):.1f} "
                           f"L {X(wh):.1f} {Y(zw):.1f} "
                           f"L {X(hbw):.1f} {Y(zb):.1f} Z")
            else:
                d_water = ""
        hf_txt = "-"
        if not piping:
            _h = breach_flow_depth(r.to_dict())
            hf_txt = f"{_h:,.2f} m" if _h is not None else "-"
        # level lines span the opening and stay within the crest
        lx0, lx1 = max(X(lt) - 18, X(0)), min(X(ht) + 18, X(L))
        if wsl > zb and not piping:
            d_pond = f"M {lx0:.1f} {Y(wsl):.1f} L {lx1:.1f} {Y(wsl):.1f}"
        else:
            d_pond = ""
        wdn = float(r.get("wsl_down", float("nan")))
        if math.isfinite(wdn) and wdn > zb and not piping:
            d_tw = f"M {lx0:.1f} {Y(wdn):.1f} L {lx1:.1f} {Y(wdn):.1f}"
        else:
            d_tw = ""
        tw_txt = ((_ze(p, wdn) + (", below invert" if wdn <= zb and not piping
                                  else "")) if math.isfinite(wdn) else "-")
        rg_txt = (flow_regime(r.to_dict()) or "-") if not piping else "-"

        frames.append({
            "v": d_void, "w": d_water, "o": d_out, "p": 1 if piping else 0,
            "pl": d_pond, "hf": hf_txt, "tw": d_tw, "twl": tw_txt, "rg": rg_txt,
            "t": f"{float(r['time_hr']):,.2f} h",
            "q": f"{float(r['Q_breach']):,.0f} m\u00b3/s",
            # before the roof collapses the crest is intact: the pipe's
            # width and invert are shown, not an opening's
            "bt": "-" if piping else f"{bt:,.1f} m",
            "bb": f"{bb:,.2f} m (pipe)" if piping else f"{bb:,.1f} m",
            "zb": _ze(p, zb), "dp": "-" if piping else f"{depth:,.2f} m",
            "wl": _ze(p, wsl),
            "fr": "-" if piping else f"{min(bt / L, 1.0) * 100:,.1f} %",
            "st": "Piping, pre-collapse" if piping else "Open breach",
        })

    # ---- static scene ----
    e = []
    e.append(f'<text x="{PL}" y="24" font-size="13" font-weight="600" '
             f'fill="{C_TEXT}">Breach Development: View Looking Upstream '
             f'from Downstream</text>')
    e.append(f'<rect x="{PL}" y="{PT}" width="{plot_w:.1f}" '
             f'height="{plot_h:.1f}" fill="#FFFFFF" stroke="#DCE4EC" '
             f'stroke-width="1"/>')
    for v in yticks:
        yy = Y(v)
        z = abs(v) < 1e-9
        e.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{PL + plot_w:.1f}" '
                 f'y2="{yy:.1f}" stroke="{"#C9D3DD" if z else "#EEF2F6"}" '
                 f'stroke-width="{1.1 if z else 0.8}"/>')
    if Y(0) < PT + plot_h:
        e.append(f'<rect x="{PL}" y="{Y(0):.1f}" width="{plot_w:.1f}" '
                 f'height="{PT + plot_h - Y(0):.1f}" fill="{C_FOUND}"/>')
    clip = _abutments(e, X, Y, L, H, x0, x1, y_lo, one_sided, sx)
    cl = f' clip-path="url(#{clip})"'
    e.append(f'<rect x="{X(0):.1f}" y="{Y(H):.1f}" width="{L * sx:.1f}" '
             f'height="{H * sy:.1f}" fill="{C_DAM}" stroke="{C_DAM_LN}" '
             f'stroke-width="1.3"/>')
    e.append(f'<path id="dvoid" d="" fill="#FFFFFF"{cl}/>')
    e.append(f'<path id="dwater" d="" fill="{C_WATER}" opacity="0.9"{cl}/>')
    e.append(f'<path id="dout" d="" fill="none" stroke="{C_BREACH}" '
             f'stroke-width="1.8"{cl}/>')
    e.append(f'<path id="dpond" d="" fill="none" stroke="{C_POND_LN}" '
             f'stroke-width="1.3" stroke-dasharray="5 4"/>')
    e.append(f'<path id="dtw" d="" fill="none" stroke="{C_TW_LN}" '
             f'stroke-width="1.5" stroke-dasharray="1.5 3" stroke-linecap="round"/>')
    e.append(f'<line x1="{PL}" y1="{Y(hb):.1f}" x2="{PL + plot_w:.1f}" '
             f'y2="{Y(hb):.1f}" stroke="{C_LIMIT}" stroke-width="1.5" '
             f'stroke-dasharray="8 5"/>')
    _limit_label(e, PL, plot_w, PT, plot_h, Y(hb), f"erosion limit {_ze(p, hb)}",
                 X(L))
    for v in yticks:
        yy, bold = Y(v), abs(v) < 1e-9
        wgt = ' font-weight="600"' if bold else ''
        e.append(f'<line x1="{PL - 5}" y1="{yy:.1f}" x2="{PL}" y2="{yy:.1f}" '
                 f'stroke="{C_MUTED}" stroke-width="1"/>')
        e.append(f'<text x="{PL - 9}" y="{yy + 3.4:.1f}" text-anchor="end" '
                 f'font-size="10.5" fill="{C_TEXT if bold else C_MUTED}"'
                 f'{wgt}>{_fmt_tick(v + _off, y_step)}</text>')
    e.append(f'<text x="20" y="{PT + plot_h / 2:.1f}" font-size="11" '
             f'fill="{C_MUTED}" text-anchor="middle" '
             f'transform="rotate(-90 20 {PT + plot_h / 2:.1f})">'
             f'{_esc(_ylabel(p, plot_h))}</text>')
    ax_y = PT + plot_h
    for v in xticks:
        xx = X(v)
        if xx < PL - 0.5 or xx > PL + plot_w + 0.5:
            continue
        e.append(f'<line x1="{xx:.1f}" y1="{ax_y}" x2="{xx:.1f}" '
                 f'y2="{ax_y + 5}" stroke="{C_MUTED}" stroke-width="1"/>')
        e.append(f'<text x="{xx:.1f}" y="{ax_y + 18}" text-anchor="middle" '
                 f'font-size="10.5" fill="{C_MUTED}">'
                 f'{_fmt_tick(v, x_step)}</text>')
    e.append(f'<text x="{PL + plot_w / 2:.1f}" y="{ax_y + 35}" '
             f'text-anchor="middle" font-size="11" fill="{C_MUTED}">'
             f'Distance along crest (m)</text>')
    ve_txt = (f"Vertical exaggeration \u00d7{ve:g}."
              if ve > 1.001 else "True scale.")
    loc = ("One-sided breach: the left side is not erodible, so the breach "
           "widens to the right only."
           if one_sided else "Two-sided breach: centred, widening both ways.")
    y_cap = PT + max(plot_h, ann_h) + 54
    e.append(f'<text x="{PL}" y="{y_cap:.1f}" font-size="10.5" '
             f'fill="{C_MUTED}">{ve_txt} {loc} {len(frames)} of {n:,} time '
             f'steps shown.</text>')
    e.append(f'<text x="{PL}" y="{y_cap + 15:.1f}" font-size="10.5" '
             f'fill="{C_MUTED}">Blue fill: flow depth from the breach flow area. '
             f'Dashed blue: pond. Dotted: tailwater. Red dashed: erosion limit. '
             f'Hatched: abutments.</text>')

    rows = [(None, None, "Stage", "-", "st"),
            (None, None, "Breach location", location_text(p)),
            ("outline", C_BREACH, "Top width", "-", "bt"),
            (None, None, "Bottom width", "-", "bb"),
            (None, None, "Invert", "-", "zb"),
            (None, None, "Breach height", "-", "dp"),
            (None, None, "Breached fraction", "-", "fr"),
            ("swatch", C_WATER, "Flow depth in breach", "-", "hf"),
            (None, None, "Depth set by", "-", "rg"),
            ("dash", C_POND_LN, "Pond level", "-", "wl"),
            ("dot", C_TW_LN, "Tailwater", "-", "twl"),
            ("dash", C_LIMIT, "Erosion limit", _ze(p, hb)),
            (None, None, "Hydrograph time", "-", "t"),
            (None, None, "Discharge", "-", "q")]
    _panel(e, rows, width - ANN_W - 14, PT, ANN_W, max(plot_h, ann_h),
           "Breach geometry", ids=True)

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
           f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" '
           f'style="display:block;height:auto;font-family:{FONT}">'
           f'<rect width="{width}" height="{height}" fill="{C_BG}"/>'
           + "".join(e) + "</svg>")

    data = _json.dumps(frames)
    btn = ("padding:6px 14px;border:1px solid #C9D6E2;border-radius:6px;"
           "background:#FFFFFF;cursor:pointer;font-size:12.5px;"
           "font-family:inherit;color:#17324D;")
    return f"""
<div style="max-width:{width}px;font-family:{FONT};">
{svg}
<div style="display:flex;align-items:center;gap:9px;margin-top:-46px;
            padding:0 0 0 {PL}px;">
  <button id="pp" style="{btn}font-weight:600;min-width:74px;">&#9654; Play</button>
  <select id="sp" style="{btn}">
    <option value="0.25">0.25&times;</option>
    <option value="0.5">0.5&times;</option>
    <option value="1" selected>1&times;</option>
    <option value="2">2&times;</option>
    <option value="4">4&times;</option>
    <option value="8">8&times;</option>
  </select>
  <input id="sc" type="range" min="0" max="{len(frames) - 1}" value="0"
         style="flex:1;accent-color:#1D5C83;"/>
  <span id="cnt" style="font-size:11.5px;color:#5E6B77;min-width:74px;
        text-align:right;">1 / {len(frames)}</span>
</div>
<script>
(function(){{
  const F = {data};
  const g = id => document.getElementById(id);
  let i = 0, timer = null;
  function draw(k){{
    const f = F[k];
    g('dvoid').setAttribute('d', f.v);
    g('dwater').setAttribute('d', f.w);
    g('dout').setAttribute('d', f.o);
    g('dpond').setAttribute('d', f.pl);
    g('dtw').setAttribute('d', f.tw);
    g('dvoid').setAttribute('fill', f.p ? '{C_WATER}' : '#FFFFFF');
    g('dvoid').setAttribute('stroke', f.p ? '{C_BREACH}' : 'none');
    g('dvoid').setAttribute('stroke-width', f.p ? '1.6' : '0');
    ['st','bt','bb','zb','dp','fr','hf','rg','wl','twl','t','q'].forEach(
        key => g('f_'+key).textContent = f[key]);
    g('sc').value = k;
    g('cnt').textContent = (k+1) + ' / ' + F.length;
  }}
  function stop(){{ if(timer){{clearInterval(timer); timer=null;}}
                    g('pp').innerHTML = '&#9654; Play'; }}
  function play(){{
    stop();
    if(i >= F.length-1) i = 0;
    const ms = Math.max(16, 55 / parseFloat(g('sp').value));
    timer = setInterval(function(){{
      i++;
      if(i >= F.length){{ i = F.length-1; draw(i); stop(); return; }}
      draw(i);
    }}, ms);
    g('pp').innerHTML = '&#10073;&#10073; Pause';
  }}
  g('pp').onclick = () => timer ? stop() : play();
  g('sp').onchange = () => {{ if(timer) play(); }};
  g('sc').oninput = e => {{ stop(); i = +e.target.value; draw(i); }};
  draw(0);
}})();
</script>
</div>"""


def animation_height(html: str, default: int = 640) -> int:
    """Frame height for the animation, read from its viewBox."""
    try:
        vb = html.split('viewBox="', 1)[1].split('"', 1)[0].split()
        return int(float(vb[3])) + 16
    except (IndexError, ValueError):
        return default
