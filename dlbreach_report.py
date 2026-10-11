"""
dlbreach_report.py
------------------
Builds a PDF "report appendix" from the dashboard's results.

Drawn with matplotlib alone, so that it works both in the local install
and in the browser version, where no other PDF library is available.
The schematics are redrawn here rather than converted from the on-screen
SVG, which cannot be rasterised in a browser.

Every page carries the report title in its header and a page number in
its footer. Elevations are given in the display datum chosen in the app.
"""

from __future__ import annotations

import io
import math
import textwrap
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages       # noqa: E402
from matplotlib.patches import Polygon, Rectangle          # noqa: E402
import numpy as np                                         # noqa: E402
import pandas as pd                                        # noqa: E402

SECTIONS = {
    "title": "Title page",
    "inputs": "Model input summary",
    "section": "Dam cross-section",
    "hydrograph": "Breach outflow hydrograph",
    "development": "Breach development (widths, invert, reservoir level)",
    "face": "Final breach geometry (view from downstream)",
    "geomtable": "Breach geometry table",
    "tailings": "Tailings release summary",
    "scenarios": "Scenario runs",
    "mc": "Monte Carlo summary (minimum, average, maximum)",
    "mc_env": "Monte Carlo ensemble through time (outflow and breach geometry)",
    "mc_drivers": "How the sampled inputs drive the breach",
    "cases": "Comparison with case histories",
    "cards": "DLBreach input file",
}

A4 = (8.27, 11.69)
NAVY, RED, BLUE, GREY = "#17324D", "#B3402A", "#1B6AAE", "#77715F"
DAM, FOUND, WATER, TAIL, TAILM = "#CFC8B6", "#E3DCCC", "#A8CBE8", "#F2B46B", "#D9731F"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.titlesize": 10, "axes.labelsize": 9,
                     "axes.edgecolor": "#9AA7B3", "axes.grid": True,
                     "grid.color": "#E8ECF0", "grid.linewidth": 0.6})


class _Doc:
    def __init__(self, pdf, meta):
        self.pdf, self.meta, self.n = pdf, meta, 0

    def page(self):
        fig = plt.figure(figsize=A4)
        self.n += 1
        fig.text(0.07, 0.965, self.meta.get("title", ""), fontsize=9,
                 color=NAVY, weight="bold", va="top")
        fig.text(0.93, 0.965, self.meta.get("header_right", ""), fontsize=8,
                 color=GREY, ha="right", va="top")
        fig.add_artist(plt.Line2D([0.07, 0.93], [0.952, 0.952],
                                  color="#C9D6E2", lw=0.8))
        fig.text(0.07, 0.03, self.meta.get("footer", "DLBreach Dashboard"),
                 fontsize=7.5, color=GREY)
        fig.text(0.93, 0.03, f"Page {self.meta.get('page_prefix', '')}"
                 f"{self.n}", fontsize=7.5, color=GREY, ha="right")
        return fig

    def save(self, fig):
        self.pdf.savefig(fig)
        plt.close(fig)


def _heading(fig, text, y=0.92):
    fig.text(0.07, y, text, fontsize=12.5, weight="bold", color=NAVY, va="top")


def _table(ax, df: pd.DataFrame, col_w=None, fontsize=7.5):
    ax.axis("off")
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            if np.isnan(v):
                return ""
            if abs(v) >= 1000:
                return f"{v:,.0f}"
            return f"{v:,.4g}"
        if isinstance(v, (int, np.integer)):
            return f"{v:,d}"
        return str(v)
    cells = [[fmt(v) for v in row] for row in df.itertuples(index=False)]
    if col_w is None and len(df.columns) > 2:
        first = 0.30
        rest = (1.0 - first) / (len(df.columns) - 1)
        col_w = [first] + [rest] * (len(df.columns) - 1)
    t = ax.table(cellText=cells, colLabels=list(df.columns), loc="upper left",
                 cellLoc="left", colLoc="left", colWidths=col_w)
    t.auto_set_font_size(False)
    t.set_fontsize(fontsize)
    t.scale(1, 1.25)
    for (r, _c), cell in t.get_celld().items():
        cell.set_edgecolor("#DCE4EC")
        if r == 0:
            cell.set_facecolor("#EEF3F8")
            cell.set_text_props(weight="bold", color=NAVY)
    return t


# ---------------------------------------------------------------------
# Schematics
# ---------------------------------------------------------------------

def _legend_below(ax, ncol=4):
    """Legend under the axes, clear of the drawing; gridlines behind the
    drawing."""
    ax.set_axisbelow(True)
    h, lab = ax.get_legend_handles_labels()
    if h:
        ax.legend(h, lab, loc="upper center", bbox_to_anchor=(0.5, -0.16),
                  ncol=ncol, fontsize=7, frameon=False, handlelength=2.2)


def _draw_section(ax, p, off, zlab, cone=None):
    from dlbreach_viz import (C_CORE, C_CORE_LN, C_COVER, clay_cover,
                              core_polygon, cover_polygons)
    H = float(p["emb_height"]); Wc = float(p["emb_crest_width"])
    Su, Sd = float(p["emb_us_slope"]), float(p["emb_ds_slope"])
    hb, wsl = float(p["hard_bottom_elev"]), float(p["wsl_up_initial"])
    wdn = float(p.get("wsl_down_initial", 0.0))
    ru, rd = H / Su, H / Sd
    dam_w = ru + Wc + rd
    res_w = max(dam_w * 0.55, 25.0)
    if cone:
        res_w = max(res_w, (cone["L"] - cone["z_invert"] / Su) * 1.12)
    x0, x1 = -res_w, dam_w + max(dam_w * 0.28, 18)
    ylo = min(hb, 0) - max(0.1 * H, 1)
    ax.add_patch(Rectangle((x0, ylo + off), x1 - x0, -ylo, color=FOUND, lw=0))
    curve = p.get("res_curve") or []
    bed = min(float(c[0]) for c in curve) if curve else (hb if hb > 0 else 0.0)
    top = min(wsl, H)
    if cone:
        zt, zi, s, L = cone["z_beach"], cone["z_invert"], cone["slope"], cone["L"]
        b0 = min(bed, zi)
        ax.add_patch(Polygon([(x0, b0 + off), (x0, zt + off), (zt / Su, zt + off),
                              (b0 / Su, b0 + off)], color=TAIL, lw=0,
                             label="Tailings"))
        xi, xb = zi / Su, max(zi / Su - L, x0)
        ax.add_patch(Polygon([(xi, zi + off), (xb, zi + s * (xi - xb) + off),
                              (xb, zt + off), (zt / Su, zt + off)],
                             color=TAILM, alpha=0.8, lw=0))
        ax.plot([xi, xb], [zi + off, zi + s * (xi - xb) + off], "--",
                color="#8A5A2B", lw=1.2, label="Post-failure surface")
        bed = max(bed, zt)
    if top > bed:
        ax.add_patch(Polygon([(x0, bed + off), (x0, top + off),
                              (top / Su, top + off), (bed / Su, bed + off)],
                             color=WATER, lw=0))
        ax.plot([x0, top / Su], [top + off] * 2, color=BLUE, lw=1.4,
                label="Pond level")
    if wdn > 0.01:
        zt_ = min(wdn, H)
        ax.add_patch(Polygon([(dam_w - zt_ / Sd, zt_ + off), (x1, zt_ + off),
                              (x1, off), (dam_w, off)], color=WATER, alpha=0.6,
                             lw=0, label="Initial tailwater"))
    ax.add_patch(Polygon([(0, off), (ru, H + off), (ru + Wc, H + off),
                          (dam_w, off)], facecolor=DAM, edgecolor="#6B6555",
                         lw=1.1, label="Embankment"))
    core = core_polygon(p)
    if core:
        ax.add_patch(Polygon([(x, z + off) for x, z in core], facecolor=C_CORE,
                             edgecolor=C_CORE_LN, lw=0.9, label="Clay core"))
    for i, c in enumerate(cover_polygons(p)):
        ax.add_patch(Polygon([(x, z + off) for x, z in c], color=C_COVER, lw=0.6,
                             label="Clay cover" if i == 0 else None))
    ax.axhline(hb + off, color=RED, ls="--", lw=1.1, label="Erosion limit")
    if int(p.get("breach_mode", 1)) == 2:
        zp = H - float(p.get("pipe_depth", 0))
        ax.plot([zp / Su, dam_w - zp / Sd], [zp + off] * 2, ls=(0, (4, 3)),
                color=BLUE, lw=0.9)
        ax.plot([ru + Wc / 2], [zp + off], "s", color=BLUE, ms=5,
                label="Initial pipe")
    else:
        zc = H - float(p.get("pilot_depth", 0))
        settle = p.get("ot_trigger") == "settlement"
        ax.add_patch(Rectangle((ru, zc + off), Wc, H - zc, facecolor="white",
                               edgecolor="none"))
        if wsl > zc:
            ax.add_patch(Rectangle((ru, zc + off), Wc, min(wsl, H) - zc,
                                   color=WATER, lw=0))
        ax.plot([ru, ru, ru + Wc, ru + Wc], [H + off, zc + off, zc + off, H + off],
                color=BLUE, lw=1.2,
                label="Crest settlement" if settle else "Pilot channel")
    ax.set_xlim(x0, x1)
    ax.set_ylim(ylo + off, max(H, wsl) * 1.12 + off)
    ax.set_xlabel("Distance from upstream toe (m)")
    ax.set_ylabel(f"Elevation ({zlab})")
    _legend_below(ax)


def _draw_face(ax, p, state, off, zlab):
    from dlbreach_viz import C_ABUT, C_ABUT_LN, breach_flow_depth
    H, L = float(p["emb_height"]), float(p["emb_length"])
    bb = float(state["breach_bottom_width"])
    bt = max(float(state["breach_top_width"]), bb)
    zb = float(state["breach_bottom_elev"])
    wsl = float(state.get("wsl_up", zb))
    hb = float(p["hard_bottom_elev"])
    one = float(p.get("breach_location", 2.0)) < 1.5
    c = L / 2
    lb, rb = (0, bb) if one else (c - bb / 2, c + bb / 2)
    lt, rt = (0, bt) if one else (c - bt / 2, c + bt / 2)
    ylo = min(hb, zb, 0) - max(0.1 * H, 1)
    xa = -max(0.07 * L, 8.0) if one else -0.04 * L
    xb = 1.04 * L
    ax.add_patch(Rectangle((xa, ylo + off), xb - xa, -ylo, color=FOUND, lw=0))
    # abutments at both ends of the crest; with a one-sided breach the
    # left-hand one is the side that is not erodible (Wu 2016, Section 4.3)
    for i, (a, b) in enumerate(((xa, 0.0), (L, xb))):
        ax.add_patch(Rectangle((a, ylo + off), b - a, H * 1.06 - ylo,
                               facecolor=C_ABUT, edgecolor=C_ABUT_LN, hatch="////",
                               lw=0.8, label="Abutment" if i == 0 else None))
    if one:
        ax.text(xa / 2, (H * 0.5) + off, "abutment (not erodible)", rotation=90,
                ha="center", va="center", fontsize=7, color=NAVY,
                bbox=dict(facecolor=C_ABUT, edgecolor="none", pad=1.0))
    ax.add_patch(Rectangle((0, off), L, H, facecolor=DAM, edgecolor="#6B6555",
                           lw=1.1, label="Embankment"))
    clip = Rectangle((0, ylo + off), L, 10 * (H - ylo) + 1, transform=ax.transData)
    zp0 = H - float(p.get("pipe_depth", 0.0))
    piping = (int(p.get("breach_mode", 1)) == 2
              and zb >= zp0 - max(0.02 * H, 0.10))
    if piping:
        side = max(bb, 0.01)
        x_ = 0.0 if one else c - side / 2
        ax.add_patch(Rectangle((x_, zb + off), side, side, facecolor=WATER,
                               edgecolor=BLUE, lw=1.2, label="Pipe"))
    else:
        op = Polygon([(lt, H + off), (lb, zb + off), (rb, zb + off), (rt, H + off)],
                     facecolor="white", edgecolor=BLUE, lw=1.4, label="Breach opening")
        ax.add_patch(op)
        op.set_clip_path(clip)
        # water in the opening at the flow depth from DLBreach's breach flow
        # area; the pond level is drawn as a dashed line
        hf = breach_flow_depth(state)
        zw = min((zb + hf) if hf is not None else wsl, wsl, H)
        if zw > zb and H > zb:
            f = min((zw - zb) / (H - zb), 1)
            wp = Polygon([(lb, zb + off), (lb + (lt - lb) * f, zw + off),
                          (rb + (rt - rb) * f, zw + off), (rb, zb + off)],
                         color=WATER, lw=0, label="Flow in breach")
            ax.add_patch(wp)
            wp.set_clip_path(clip)
        x_lo = max(lt - 0.02 * L, 0.0)
        x_hi = min(rt + 0.02 * L, L)
        if wsl > zb:
            ax.plot([x_lo, x_hi], [wsl + off] * 2, "--",
                    color=BLUE, lw=1.0, label="Pond level")
        wdn = float(state.get("wsl_down", float("nan")))
        if np.isfinite(wdn) and wdn > zb:
            ax.plot([x_lo, x_hi], [wdn + off] * 2, ":",
                    color="#17A2B8", lw=1.3, label="Tailwater")
        oc, = ax.plot([lt, rt], [H + off] * 2, ":", color="#6B6555", lw=1,
                      label="Original crest")
        oc.set_clip_path(clip)
    ax.axhline(hb + off, color=RED, ls="--", lw=1.1, label="Erosion limit")
    ax.set_xlim(xa, xb)
    ax.set_ylim(ylo + off, H * 1.15 + off)
    ax.set_xlabel("Distance along crest (m)")
    ax.set_ylabel(f"Elevation ({zlab})")
    _legend_below(ax)


# ---------------------------------------------------------------------
# Ensemble, input-against-result and case-history figures
# ---------------------------------------------------------------------
ENV_COLOURS = {"Min": "#9DB9D3", "Max": "#9DB9D3", "P05": "#5B9BD5",
               "P95": "#5B9BD5", "P10": "#5B9BD5", "P90": "#5B9BD5",
               "P25": "#2F7BBF", "P75": "#2F7BBF", "Median": NAVY,
               "Mean": "#2E8B57"}
CASE_COLOURS = ["#1F6FB2", "#2E8B57", "#7A5AA6", "#B3402A", "#C9A227",
                "#5E6B77", "#3FA7D6"]
CASE_MARKERS = ["o", "^", "s", "v", "P", "X", "h"]
# the same colours as the dashboard's charts (dlbreach_ui.FIXED_COLOURS)
CASE_STYLE = {"Froehlich (2016a)": ("#1F6FB2", "o"),
              "Xu and Zhang (2009)": ("#C0392B", "^")}


def _draw_env(ax, panel: dict, sel_label: str, legend: bool = False):
    """One envelope panel: statistics through time, and the chosen
    realisation dashed in black."""
    t = panel["t"]
    for name, y in panel["curves"].items():
        ax.plot(t, y, lw=1.2, color=ENV_COLOURS.get(name, GREY), label=name)
    if panel.get("sel") is not None:
        ts, ys = panel["sel"]
        ax.plot(ts, ys, "--", lw=1.1, color="black", label=sel_label)
    ax.set_title(panel["title"], fontsize=9, loc="left")
    ax.set_xlabel("Time (h)", fontsize=8)
    ax.set_ylabel(panel["ylabel"], fontsize=8)
    ax.tick_params(labelsize=7.5)
    if legend:
        ax.legend(fontsize=7, ncol=3)


def _draw_driver(ax, x, y, sel, xlabel, ylabel):
    """Sampled input against a result, one point per realisation, with the
    Spearman rank correlation in the title."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    ax.scatter(x[m], y[m], s=9, color="#5B9BD5", alpha=0.75, lw=0)
    if sel is not None and np.any(sel & m):
        ax.scatter(x[sel & m], y[sel & m], s=60, marker="D", color="black")
    rho = np.nan
    if m.sum() > 2:
        rx, ry = pd.Series(x[m]).rank(), pd.Series(y[m]).rank()
        den = rx.std(ddof=0) * ry.std(ddof=0)
        rho = np.nan if den == 0 else float(((rx - rx.mean()) * (ry - ry.mean())).mean() / den)
    ax.set_title(f"Spearman ρ = {rho:+.2f}" if np.isfinite(rho)
                 else "No variation in this result", fontsize=8, loc="left")
    ax.set_xlabel(xlabel, fontsize=7.5)
    ax.set_ylabel(ylabel, fontsize=7.5)
    ax.tick_params(labelsize=7)


def _draw_case(ax, panel: dict):
    """Measured case histories, with this analysis as a black-edged diamond."""
    d = panel["data"]
    k = 0
    for name, g in d.groupby("Series", sort=False):
        g = g[(g["x"] > 0) & (g["y"] > 0)] if (panel["logx"] or panel["logy"]) else g
        if name == panel.get("model", "This analysis"):
            ax.scatter(g["x"], g["y"], s=90, marker="D", color="#FFFFFF",
                       edgecolor="black", lw=1.4, zorder=5, label=name)
        else:
            # each data set has its own colour and marker shape, so they stay
            # distinct in print and for colour-blind readers
            col, mk = CASE_STYLE.get(name, (CASE_COLOURS[k % len(CASE_COLOURS)],
                                            CASE_MARKERS[k % len(CASE_MARKERS)]))
            ax.scatter(g["x"], g["y"], s=22, color=col, marker=mk, alpha=0.85,
                       edgecolor="white", lw=0.4, label=name)
            k += 1
    if panel["logx"]:
        ax.set_xscale("log")
    if panel["logy"]:
        ax.set_yscale("log")
    # on a log axis spanning less than a decade matplotlib labels the minor
    # ticks as 6×10^0; plain numbers read better
    from matplotlib.ticker import FuncFormatter, NullFormatter

    def _minor(v, _):
        if v <= 0:
            return ""
        lead = round(v / 10 ** math.floor(math.log10(v)))
        return f"{v:g}" if lead in (2, 3, 5) else ""

    ax.autoscale_view()
    for on, axis, lim in ((panel["logx"], ax.xaxis, ax.get_xlim()),
                          (panel["logy"], ax.yaxis, ax.get_ylim())):
        if on and lim[0] > 0:
            narrow = lim[1] / lim[0] < 100         # two decades or less
            axis.set_minor_formatter(FuncFormatter(_minor) if narrow
                                     else NullFormatter())
    ax.set_title(panel["title"], fontsize=8.5, loc="left")
    ax.set_xlabel(panel["xlabel"], fontsize=7.5)
    ax.set_ylabel(panel["ylabel"], fontsize=7.5)
    ax.tick_params(which="both", labelsize=7)
    ax.legend(fontsize=6.5, loc="best")


def _env_tmax(panels: list) -> float | None:
    """End of the active period: where the upper outflow envelope falls
    below 1 % of its peak, plus a margin. None if there is no outflow panel."""
    if not panels or not panels[0].get("curves"):
        return None
    t = np.asarray(panels[0]["t"], float)
    top = np.max(np.vstack([np.asarray(v, float) for v in panels[0]["curves"].values()]),
                 axis=0)
    if top.size == 0 or top.max() <= 0:
        return None
    last = np.nonzero(top > 0.01 * top.max())[0]
    return float(min(t[-1], t[last[-1]] * 1.3)) if last.size else None


def _env_axes(fig, rect=(0.1, 0.08, 0.83, 0.78)):
    """Outflow across the top, the four geometry panels below."""
    gs = fig.add_gridspec(3, 2, left=rect[0], right=rect[0] + rect[2],
                          bottom=rect[1], top=rect[1] + rect[3],
                          hspace=0.55, wspace=0.3)
    return [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]),
            fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[2, 0]),
            fig.add_subplot(gs[2, 1])]


DRIVER_ROWS = 4


def _driver_axes(fig, n_rows, n_cols, rect=(0.1, 0.08, 0.83, 0.78)):
    gs = fig.add_gridspec(n_rows, n_cols, left=rect[0], right=rect[0] + rect[2],
                          bottom=rect[1], top=rect[1] + rect[3],
                          hspace=0.7, wspace=0.4)
    return [[fig.add_subplot(gs[r, c]) for c in range(n_cols)]
            for r in range(n_rows)]


# ---------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------

def build_report(sections: list[str], meta: dict, p: dict,
                 df: pd.DataFrame | None = None,
                 extras: dict | None = None) -> bytes:
    """
    Assemble the PDF and return its bytes.

    meta:   title, subtitle, prepared_by, organisation, date, notes,
            header_right, footer, page_prefix
    extras: z_off, z_lab, cone, input_text, geom_interval_min,
            scenario_summary (DataFrame), scenario_hydros (dict),
            mc_stats (DataFrame), mc_envelope (DataFrame),
            empirical_peak (DataFrame), empirical_geom (DataFrame),
            inputs_table (DataFrame)
    """
    ex = extras or {}
    off, zlab = float(ex.get("z_off", 0.0)), ex.get("z_lab", "m above embankment base")
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        d = _Doc(pdf, meta)
        info = pdf.infodict()
        info["Title"] = meta.get("title", "DLBreach report appendix")
        info["Author"] = meta.get("prepared_by", "")

        for sec in sections:
            if sec == "title":
                fig = d.page()
                fig.text(0.07, 0.72, meta.get("title", ""), fontsize=22,
                         weight="bold", color=NAVY, wrap=True)
                if meta.get("subtitle"):
                    fig.text(0.07, 0.665, meta["subtitle"], fontsize=13,
                             color="#3A4A5A")
                y = 0.58
                for lab, key in (("Prepared by", "prepared_by"),
                                 ("Organisation", "organisation"),
                                 ("Date", "date")):
                    if meta.get(key):
                        fig.text(0.07, y, f"{lab}: {meta[key]}", fontsize=10.5)
                        y -= 0.03
                if meta.get("notes"):
                    wrapped = "\n".join(textwrap.wrap(meta["notes"], 95))
                    fig.text(0.07, y - 0.03, wrapped, fontsize=9, va="top",
                             color="#2E3A46")
                fig.text(0.07, 0.12, "\n".join(textwrap.wrap(
                    "Results were produced with DLBreach (Wu 2013, 2016), "
                    "executed unaltered through the DLBreach Dashboard. The "
                    "dashboard writes model input, runs the model and reports "
                    "its output; it adds no physics. DLBreach routes the "
                    "impoundment as clear water.", 105)),
                    fontsize=8, color=GREY, va="top")
                d.save(fig)

            elif sec == "inputs" and ex.get("inputs_table") is not None:
                fig = d.page(); _heading(fig, "Model input summary")
                ax = fig.add_axes([0.07, 0.08, 0.86, 0.8])
                _table(ax, ex["inputs_table"], col_w=[0.30, 0.15, 0.15, 0.40],
                       fontsize=7)
                d.save(fig)

            elif sec == "section":
                fig = d.page(); _heading(fig, "Dam cross-section")
                ax = fig.add_axes([0.1, 0.5, 0.83, 0.38])
                _draw_section(ax, p, off, zlab, ex.get("cone"))
                from dlbreach_viz import clay_cover, failure_mode_text
                fig.text(0.07, 0.395, textwrap.fill(
                    "Idealised section after DLBreach (trapezoidal embankment"
                    + (" and clay core" if p.get("has_core") else "")
                    + (", clay cover from the loaded file" if clay_cover(p) else "")
                    + "). Vertical scale exaggerated. Failure mode: "
                    + failure_mode_text(p) + ".", 115), fontsize=8, color=GREY,
                    va="top")
                d.save(fig)

            elif sec == "hydrograph" and df is not None:
                fig = d.page(); _heading(fig, "Breach outflow hydrograph")
                ax = fig.add_axes([0.1, 0.52, 0.83, 0.36])
                ax.plot(df["time_hr"], df["Q_breach"], color=BLUE, lw=1.4,
                        label="Water (DLBreach)")
                if ex.get("q_total") is not None:
                    ax.plot(df["time_hr"], ex["q_total"], color="#C58B4E", lw=1.3,
                            label="Total, bulked")
                    ax.legend(fontsize=7.5)
                i = int(df["Q_breach"].idxmax())
                ax.plot(df["time_hr"].iloc[i], df["Q_breach"].iloc[i], "o",
                        color=RED)
                ax.annotate(f"Peak {df['Q_breach'].iloc[i]:,.0f} m³/s at "
                            f"{df['time_hr'].iloc[i]:.2f} h",
                            (df["time_hr"].iloc[i], df["Q_breach"].iloc[i]),
                            xytext=(10, -4), textcoords="offset points",
                            fontsize=8, color=RED)
                ax.set_xlabel("Time (h)"); ax.set_ylabel("Discharge (m³/s)")
                d.save(fig)

            elif sec == "development" and df is not None:
                fig = d.page(); _heading(fig, "Breach development")
                a1 = fig.add_axes([0.1, 0.55, 0.83, 0.32])
                a1.plot(df["time_hr"], df["breach_top_width"], label="Top width",
                        color=NAVY)
                a1.plot(df["time_hr"], df["breach_bottom_width"],
                        label="Bottom width", color=BLUE)
                a1.set_ylabel("Width (m)"); a1.legend(fontsize=7.5)
                a2 = fig.add_axes([0.1, 0.13, 0.83, 0.32])
                a2.plot(df["time_hr"], df["wsl_up"] + off, label="Reservoir level",
                        color=BLUE)
                a2.plot(df["time_hr"], df["breach_bottom_elev"] + off,
                        label="Breach invert", color=RED)
                a2.set_xlabel("Time (h)"); a2.set_ylabel(f"Elevation ({zlab})")
                a2.legend(fontsize=7.5)
                d.save(fig)

            elif sec == "face" and df is not None:
                fig = d.page()
                _heading(fig, "Final breach geometry, looking upstream")
                ax = fig.add_axes([0.1, 0.5, 0.83, 0.38])
                _draw_face(ax, p, df.iloc[-1].to_dict(), off, zlab)
                last = df.iloc[-1]
                from dlbreach_viz import location_text
                fig.text(0.07, 0.372, textwrap.fill(
                    "Breach location: " + location_text(p)
                    + (". One side of the breach is not erodible, so it widens "
                       "one way only (Wu 2016)."
                       if float(p.get("breach_location", 2.0)) < 1.5 else "."), 115),
                    fontsize=8, color=GREY, va="top")
                fig.text(0.07, 0.385,
                         f"Top width {last['breach_top_width']:,.1f} m · bottom "
                         f"width {last['breach_bottom_width']:,.1f} m · invert "
                         f"{last['breach_bottom_elev'] + off:,.2f} ({zlab}) · "
                         f"depth {float(p['emb_height']) - last['breach_bottom_elev']:,.2f} m",
                         fontsize=8.5)
                d.save(fig)

            elif sec == "geomtable" and df is not None:
                interval = float(ex.get("geom_interval_min", 10))
                tab = _geom_rows(df, off, interval)
                per = 42
                for k in range(0, len(tab), per):
                    fig = d.page()
                    _heading(fig, "Breach geometry table"
                             + (" (continued)" if k else ""))
                    fig.text(0.07, 0.895, f"Elevations in {zlab}. Interval "
                             f"{interval:g} min, to the end of outflow; peak and "
                             f"final rows included.", fontsize=8, color=GREY)
                    ax = fig.add_axes([0.07, 0.07, 0.86, 0.81])
                    _table(ax, tab.iloc[k:k + per], fontsize=7)
                    d.save(fig)

            elif sec == "scenarios" and ex.get("scenario_summary") is not None:
                fig = d.page(); _heading(fig, "Scenario comparison")
                hy = ex.get("scenario_hydros") or {}
                if hy:
                    ax = fig.add_axes([0.1, 0.56, 0.83, 0.32])
                    for name, (tt, qq) in hy.items():
                        ax.plot(tt, qq, lw=1.2, label=str(name))
                    ax.set_xlabel("Time (h)"); ax.set_ylabel("Discharge (m³/s)")
                    ax.legend(fontsize=7, ncol=2)
                ax2 = fig.add_axes([0.07, 0.07, 0.86, 0.4])
                _table(ax2, ex["scenario_summary"], fontsize=7)
                d.save(fig)

            elif sec == "mc" and ex.get("mc_table") is not None:
                fig = d.page(); _heading(fig, "Monte Carlo summary")
                fig.text(0.07, 0.895, "Minimum, average and maximum over the "
                         "realisations of each run.", fontsize=8, color=GREY)
                ax = fig.add_axes([0.07, 0.08, 0.86, 0.8])
                _table(ax, ex["mc_table"], fontsize=6.8)
                d.save(fig)

            elif sec == "mc_env" and ex.get("mc_env"):
                for ent in ex["mc_env"]:
                    fig = d.page()
                    _heading(fig, f"Monte Carlo ensemble through time — {ent['name']}")
                    fig.text(0.07, 0.895, "Each curve is a statistic across the "
                             "realisations at every moment, not a model run. "
                             f"Dashed black: {ent['sel_label']}.", fontsize=8,
                             color=GREY)
                    axs = _env_axes(fig, (0.1, 0.07, 0.83, 0.78))
                    tmax = _env_tmax(ent["panels"])
                    for k, (ax, pan) in enumerate(zip(axs, ent["panels"])):
                        _draw_env(ax, pan, ent["sel_label"], legend=(k == 0))
                        if tmax:
                            ax.set_xlim(0, tmax)
                    d.save(fig)

            elif sec == "mc_drivers" and ex.get("mc_drivers"):
                for ent in ex["mc_drivers"]:
                    ins, outs = ent["inputs"], ent["outputs"]
                    for k in range(0, len(ins), DRIVER_ROWS):
                        chunk = ins[k:k + DRIVER_ROWS]
                        fig = d.page()
                        _heading(fig, "How the sampled inputs drive the breach — "
                                 f"{ent['name']}" + (" (continued)" if k else ""))
                        fig.text(0.07, 0.895, "One point per realisation. Black "
                                 f"diamond: {ent['sel_label']}.", fontsize=8,
                                 color=GREY)
                        h = 0.78 * len(chunk) / DRIVER_ROWS
                        grid = _driver_axes(fig, len(chunk), len(outs),
                                            (0.1, 0.85 - h, 0.83, h))
                        for r, (xl, xv) in enumerate(chunk):
                            for c, (yl, yv) in enumerate(outs):
                                _draw_driver(grid[r][c], xv, yv, ent.get("sel"),
                                             xl, yl)
                        d.save(fig)

            elif sec == "cases" and ex.get("cases"):
                cs = ex["cases"]
                fig = d.page(); _heading(fig, "Comparison with case histories")
                fig.text(0.07, 0.895, "\n".join(textwrap.wrap(cs["note"], 120)),
                         fontsize=7.5, color=GREY, va="top")
                gs = fig.add_gridspec(2, 2, left=0.1, right=0.95, bottom=0.2,
                                      top=0.8, hspace=0.42, wspace=0.32)
                for k, pan in enumerate(cs["panels"][:4]):
                    _draw_case(fig.add_subplot(gs[k // 2, k % 2]), pan)
                fig.text(0.07, 0.15, "\n".join(
                    "\n".join(textwrap.wrap(r, 125)) for r in cs["refs"]),
                    fontsize=7, va="top", color="#2E3A46")
                d.save(fig)

            elif sec == "tailings" and ex.get("tailings") is not None:
                fig = d.page(); _heading(fig, "Tailings release summary")
                fig.text(0.07, 0.895, "Estimated outside DLBreach, which routes "
                         "the impoundment as clear water. The bulking factor "
                         "is applied uniformly to the water hydrograph.",
                         fontsize=8, color=GREY)
                ax = fig.add_axes([0.07, 0.5, 0.86, 0.37])
                _table(ax, ex["tailings"], col_w=[0.6, 0.4], fontsize=8)
                d.save(fig)

            elif sec == "cards" and ex.get("input_text"):
                lines = ex["input_text"].splitlines()
                per = 78
                for k in range(0, len(lines), per):
                    fig = d.page()
                    _heading(fig, "DLBreach input file"
                             + (" (continued)" if k else ""))
                    fig.text(0.07, 0.89, "\n".join(lines[k:k + per]),
                             family="DejaVu Sans Mono", fontsize=6.6, va="top")
                    d.save(fig)
    return buf.getvalue()


# =====================================================================
# Word document
# =====================================================================

def _fig_png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _geom_rows(df, off, interval):
    t = df["time_hr"].to_numpy()
    idx = sorted(set(int(np.searchsorted(t, x)) for x in
                     np.arange(t[0], t[-1] + 1e-9, interval / 60))
                 | {int(df["Q_breach"].idxmax()), len(df) - 1})
    sub = df.iloc[[i for i in idx if i < len(df)]]
    # stop listing once nothing changes any more
    q = sub["Q_breach"].to_numpy()
    last = max(np.nonzero(q > 0)[0].max() + 2 if (q > 0).any() else 2, 2)
    sub = sub.iloc[:last]
    return pd.DataFrame({
        "Time (h)": sub["time_hr"].round(3),
        "Q (m³/s)": sub["Q_breach"].round(1),
        "Pond level": (sub["wsl_up"] + off).round(2),
        "Invert": (sub["breach_bottom_elev"] + off).round(2),
        "Bottom W (m)": sub["breach_bottom_width"].round(1),
        "Top W (m)": sub["breach_top_width"].round(1)})


def build_docx(sections: list[str], meta: dict, p: dict,
               df: pd.DataFrame | None = None, extras: dict | None = None) -> bytes:
    """
    The same appendix as build_report, as an editable Word document: real
    tables, figures as images, and the title and page numbers in the header
    and footer.
    """
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    ex = extras or {}
    off, zlab = float(ex.get("z_off", 0.0)), ex.get("z_lab", "m above embankment base")
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10)

    hp = sec.header.paragraphs[0]
    hp.text = f"{meta.get('title', '')}\t\t{meta.get('header_right', '')}"
    hp.runs[0].font.size = Pt(8)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = fp.add_run(f"Page {meta.get('page_prefix', '')}")
    run.font.size = Pt(8)
    r2 = fp.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve")
            el.text = text
        r2._r.append(el)
    r2.font.size = Pt(8)

    def heading(text):
        h = doc.add_heading(text, level=1)
        for rn in h.runs:
            rn.font.color.rgb = RGBColor(0x17, 0x32, 0x4D)

    def table(frame, widths=None, size=8):
        t = doc.add_table(rows=1, cols=len(frame.columns))
        t.style = "Light Grid Accent 1"
        for j, c in enumerate(frame.columns):
            t.rows[0].cells[j].text = str(c)
        for row in frame.itertuples(index=False):
            cells = t.add_row().cells
            for j, v in enumerate(row):
                if isinstance(v, (float, np.floating)):
                    v = "" if np.isnan(v) else (f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.4g}")
                cells[j].text = str(v)
        for rw in t.rows:
            for c in rw.cells:
                for para in c.paragraphs:
                    for rn in para.runs:
                        rn.font.size = Pt(size)
        if widths:
            for rw in t.rows:
                for j, w in enumerate(widths):
                    rw.cells[j].width = Cm(w)
        doc.add_paragraph()

    def figure(fig, caption=None, width=16):
        doc.add_picture(_fig_png(fig), width=Cm(width))
        if caption:
            c = doc.add_paragraph(caption)
            c.runs[0].font.size = Pt(8)
            c.runs[0].italic = True

    first = True
    for s in sections:
        if not first and s != "title":
            doc.add_page_break()
        first = False
        if s == "title":
            t = doc.add_heading(meta.get("title", ""), level=0)
            for rn in t.runs:
                rn.font.color.rgb = RGBColor(0x17, 0x32, 0x4D)
            if meta.get("subtitle"):
                doc.add_paragraph(meta["subtitle"]).runs[0].font.size = Pt(13)
            for lab, key in (("Prepared by", "prepared_by"),
                             ("Organisation", "organisation"), ("Date", "date")):
                if meta.get(key):
                    doc.add_paragraph(f"{lab}: {meta[key]}")
            if meta.get("notes"):
                doc.add_paragraph(meta["notes"])
            n = doc.add_paragraph(
                "Results were produced with DLBreach (Wu 2013, 2016), executed "
                "unaltered through the DLBreach Dashboard. DLBreach routes the "
                "impoundment as clear water.")
            n.runs[0].font.size = Pt(8)
            n.runs[0].italic = True
        elif s == "inputs" and ex.get("inputs_table") is not None:
            heading("Model input summary")
            table(ex["inputs_table"], widths=[5, 3, 2.5, 6.5])
        elif s == "section":
            heading("Dam cross-section")
            fig, ax = plt.subplots(figsize=(8, 4))
            _draw_section(ax, p, off, zlab, ex.get("cone"))
            figure(fig, "Idealised trapezoidal section after DLBreach; vertical "
                        "scale exaggerated.")
        elif s == "hydrograph" and df is not None:
            heading("Breach outflow hydrograph")
            fig, ax = plt.subplots(figsize=(8, 3.8))
            ax.plot(df["time_hr"], df["Q_breach"], color=BLUE, lw=1.4,
                    label="Water (DLBreach)")
            if ex.get("q_total") is not None:
                ax.plot(df["time_hr"], ex["q_total"], color="#C58B4E", lw=1.3,
                        label="Total, bulked")
            ax.set_xlabel("Time (h)"); ax.set_ylabel("Discharge (m³/s)")
            ax.legend(fontsize=8)
            figure(fig)
        elif s == "development" and df is not None:
            heading("Breach development")
            fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
            a1.plot(df["time_hr"], df["breach_top_width"], label="Top width", color=NAVY)
            a1.plot(df["time_hr"], df["breach_bottom_width"], label="Bottom width",
                    color=BLUE)
            a1.set_ylabel("Width (m)"); a1.legend(fontsize=8)
            a2.plot(df["time_hr"], df["wsl_up"] + off, label="Pond level", color=BLUE)
            a2.plot(df["time_hr"], df["breach_bottom_elev"] + off, label="Breach invert",
                    color=RED)
            a2.set_xlabel("Time (h)"); a2.set_ylabel(f"Elevation ({zlab})")
            a2.legend(fontsize=8)
            figure(fig)
        elif s == "face" and df is not None:
            heading("Final breach geometry, looking upstream")
            fig, ax = plt.subplots(figsize=(8, 4))
            _draw_face(ax, p, df.iloc[-1].to_dict(), off, zlab)
            figure(fig)
        elif s == "geomtable" and df is not None:
            heading("Breach geometry table")
            doc.add_paragraph(f"Elevations in {zlab}. Interval "
                              f"{float(ex.get('geom_interval_min', 10)):g} min, "
                              f"to the end of outflow; peak and final rows included.")
            table(_geom_rows(df, off, float(ex.get("geom_interval_min", 10))), size=7.5)
        elif s == "mc_env" and ex.get("mc_env"):
            heading("Monte Carlo ensemble through time")
            doc.add_paragraph("Each curve is a statistic across the realisations "
                              "at every moment, not a model run.")
            for ent in ex["mc_env"]:
                fig = plt.figure(figsize=(8, 8.5))
                axs = _env_axes(fig, (0.09, 0.06, 0.86, 0.88))
                tmax = _env_tmax(ent["panels"])
                for k, (ax, pan) in enumerate(zip(axs, ent["panels"])):
                    _draw_env(ax, pan, ent["sel_label"], legend=(k == 0))
                    if tmax:
                        ax.set_xlim(0, tmax)
                figure(fig, f"{ent['name']}. Dashed black: {ent['sel_label']}.")
        elif s == "mc_drivers" and ex.get("mc_drivers"):
            heading("How the sampled inputs drive the breach")
            doc.add_paragraph("One point per realisation, with the Spearman rank "
                              "correlation of each pair.")
            for ent in ex["mc_drivers"]:
                ins, outs = ent["inputs"], ent["outputs"]
                for k in range(0, len(ins), DRIVER_ROWS):
                    chunk = ins[k:k + DRIVER_ROWS]
                    fig = plt.figure(figsize=(8, 2.3 * len(chunk) + 0.6))
                    grid = _driver_axes(fig, len(chunk), len(outs),
                                        (0.09, 0.08, 0.87, 0.86))
                    for r, (xl, xv) in enumerate(chunk):
                        for c, (yl, yv) in enumerate(outs):
                            _draw_driver(grid[r][c], xv, yv, ent.get("sel"), xl, yl)
                    figure(fig, f"{ent['name']}. Black diamond: {ent['sel_label']}.")
        elif s == "cases" and ex.get("cases"):
            cs = ex["cases"]
            heading("Comparison with case histories")
            doc.add_paragraph(cs["note"])
            fig, axs = plt.subplots(2, 2, figsize=(8, 7))
            for ax, pan in zip(axs.flat, cs["panels"][:4]):
                _draw_case(ax, pan)
            fig.tight_layout()
            figure(fig)
            for r in cs["refs"]:
                pr = doc.add_paragraph(r)
                pr.runs[0].font.size = Pt(8)
        elif s == "tailings" and ex.get("tailings") is not None:
            heading("Tailings release summary")
            doc.add_paragraph("Estimated outside DLBreach, which routes the "
                              "impoundment as clear water.")
            table(ex["tailings"], widths=[9, 6])
        elif s == "scenarios" and ex.get("scenario_summary") is not None:
            heading("Sensitivity scenarios")
            hy = ex.get("scenario_hydros") or {}
            if hy:
                fig, ax = plt.subplots(figsize=(8, 3.8))
                for name, (tt, qq) in hy.items():
                    ax.plot(tt, qq, lw=1.2, label=str(name))
                ax.set_xlabel("Time (h)"); ax.set_ylabel("Discharge (m³/s)")
                ax.legend(fontsize=7, ncol=3)
                figure(fig)
            table(ex["scenario_summary"], size=7)
        elif s == "mc" and ex.get("mc_table") is not None:
            heading("Monte Carlo summary")
            doc.add_paragraph("Minimum, average and maximum over the realisations "
                              "of each run.")
            table(ex["mc_table"], size=7.5)
        elif s == "cards" and ex.get("input_text"):
            heading("DLBreach input file")
            para = doc.add_paragraph()
            rn = para.add_run(ex["input_text"])
            rn.font.name, rn.font.size = "Courier New", Pt(7)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
