"""
dlbreach_ui.py
--------------
Interface helpers shared by every page: section headings, callouts, stat
tiles, persistent widget state, and a chart with typed axis limits.

Charts are drawn as Vega-Lite specifications rather than Streamlit's
built-in charts, because the built-in charts cannot take explicit axis
limits or logarithmic axes, and zooming by dragging is awkward for
engineering plots where the reader wants a particular range.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

MODEL_SERIES = "This analysis"

# Series colours. Water is always blue and solid waste always orange, so a
# colour means the same thing on every chart. Other series take the
# palette in order; it leaves out orange, which is kept for solid waste.
WATER_BLUE = "#1F6FB2"
SOLID_ORANGE = "#D9731F"
FIXED_COLOURS = {
    "Breach outflow": WATER_BLUE, "Water (DLBreach)": WATER_BLUE,
    "Pond level": WATER_BLUE, "Stage-storage": WATER_BLUE,
    "Tailings": SOLID_ORANGE, "Total (bulked)": "#9C4A12",
    "Total, bulked": "#9C4A12",
    "Froehlich (2016a)": "#1F6FB2", "Xu and Zhang (2009)": "#C0392B",
    "Top width": "#17324D", "Bottom width": "#5B9BD5",
    "Breach invert": "#8A5A2B", "Breach depth": "#8A5A2B",
}
# Ordered so that neighbouring series differ in hue, not just in shade
PALETTE = ["#1F6FB2", "#C0392B", "#2E8B57", "#7A5AA6", "#C9A227",
           "#17A2B8", "#8A5A2B", "#D45087", "#5E6B77", "#17324D",
           "#7FB800", "#A0522D"]
LINE_STYLES = {"Solid": [1, 0], "Dashed": [7, 4], "Dotted": [1.5, 3.5],
               "Dash-dot": [8, 3, 1.5, 3]}


def seed(key: str, default):
    """Give a persistent widget its starting value, once."""
    if key not in st.session_state:
        st.session_state[key] = default


# Section titles drawn on the current page, in order, for the contents
# panel. Cleared at the start of every run.
RENDERED: list[tuple[str, str]] = []


def slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in str(text))
    while "--" in out:
        out = out.replace("--", "-")
    return "dlb-" + out.strip("-")


def anchor(title: str) -> str:
    """Record a section for the contents panel; return its anchor id."""
    a = slug(title)
    if a not in (x[1] for x in RENDERED):
        RENDERED.append((title, a))
    return a


def section(title: str, sub: str | None = None):
    a = anchor(title)
    # numbered steps ("1 · Choose ...") get a round badge for the number
    head = title
    if len(title) > 4 and title[0].isdigit() and title[1:4] == " · ":
        head = f'<span class="dlb-step">{title[0]}</span><span>{title[4:]}</span>'
    st.markdown(f'<div class="dlb-section" id="{a}">{head}</div>',
                unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="dlb-sub">{sub}</div>', unsafe_allow_html=True)


def group(label: str):
    st.markdown(f'<div class="dlb-group">{label}</div>', unsafe_allow_html=True)


def callout(kind: str, lead: str, body: str):
    """kind: info, note, warn or ok."""
    st.markdown(f'<div class="dlb-callout dlb-{kind}"><b>{lead}</b> {body}</div>',
                unsafe_allow_html=True)


def tiles(items: list[tuple], cols: int | None = None):
    """items: (label, value, sub or None, accent bool)."""
    cols = cols or max(len(items), 1)
    html = [f'<div class="dlb-tiles" style="grid-template-columns: '
            f'repeat({cols}, minmax(0, 1fr));">']
    for it in items:
        lab, val = it[0], it[1]
        sub = it[2] if len(it) > 2 else None
        acc = it[3] if len(it) > 3 else False
        html.append(f'<div class="dlb-tile"><p class="lab">{lab}</p>'
                    f'<p class="val{" accent" if acc else ""}">{val}</p>'
                    + (f'<p class="sub">{sub}</p>' if sub else "") + "</div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def _popover(label: str):
    """A popover where available, an expander on older Streamlit."""
    try:
        return st.popover(label)
    except AttributeError:
        return st.expander(label)


def chart(df: pd.DataFrame, x_title: str, y_title: str, key: str,
          kind: str = "line", log_x: bool = False, log_y: bool = False,
          one_to_one: bool = False, height: int = 340,
          colours: dict | None = None, highlight: str = MODEL_SERIES,
          dashed: list | None = None, x_auto_max: float | None = None,
          faint: list | None = None):
    """
    A chart with an "Axes" control holding min and max for each axis and
    log toggles. df is long-form with columns x, y, Series and optionally
    Event. kind is "line" for time series or "scatter" for case histories.
    Blank limits mean automatic.

    colours maps series names to colours (on top of FIXED_COLOURS); the
    remaining series take PALETTE in order. In a scatter, the series named
    `highlight` is drawn as a large black-edged diamond. Series listed in
    `dashed` are drawn dashed. For line charts the user can change the
    colour and line style of each series in the same control.

    In a scatter, series listed in `faint` (Monte Carlo realisations) are
    drawn as small, light points beneath the others.

    x_auto_max, when given, is the upper x limit used while "x max" is
    blank: for time series, the end of the active period rather than the
    end of the simulation.
    """
    if df is None or df.empty:
        st.caption("Nothing to plot yet.")
        return
    seed(f"keep_ax_{key}_lx", log_x)
    seed(f"keep_ax_{key}_ly", log_y)
    names = list(dict.fromkeys(df["Series"]))
    base_scale = _colour_scale(names, colours)
    base_col = dict(zip(base_scale["domain"], base_scale["range"]))
    styled = kind == "line" and len(names) <= 12
    with _popover("Chart options" if styled else "Axes"):
        st.markdown("**Axes**")
        c1, c2 = st.columns(2)
        xmin = c1.number_input("x min", value=None, key=f"keep_ax_{key}_x0",
                               format="%g", placeholder="auto")
        xmax = c2.number_input("x max", value=None, key=f"keep_ax_{key}_x1",
                               format="%g", placeholder="auto")
        ymin = c1.number_input("y min", value=None, key=f"keep_ax_{key}_y0",
                               format="%g", placeholder="auto")
        ymax = c2.number_input("y max", value=None, key=f"keep_ax_{key}_y1",
                               format="%g", placeholder="auto")
        lx = c1.toggle("Log x", key=f"keep_ax_{key}_lx")
        ly = c2.toggle("Log y", key=f"keep_ax_{key}_ly")
        if x_auto_max is not None:
            st.caption("With x max blank, the time axis ends shortly after the "
                       "outflow does.")
        line_col, line_dash = {}, {}
        if styled:
            st.markdown("**Lines**")
            for i, nm in enumerate(names):
                r1, r2, r3 = st.columns([3, 1, 2])
                r1.markdown(f"<div style='padding-top:.45rem;font-size:.88rem'>"
                            f"{nm}</div>", unsafe_allow_html=True)
                seed(f"keep_ls_{key}_{i}_c", base_col.get(nm, PALETTE[0]))
                seed(f"keep_ls_{key}_{i}_d",
                     "Dashed" if dashed and nm in dashed else "Solid")
                cval = r2.color_picker("Colour", key=f"keep_ls_{key}_{i}_c",
                                       label_visibility="collapsed")
                dval = r3.selectbox("Style", list(LINE_STYLES),
                                    key=f"keep_ls_{key}_{i}_d",
                                    label_visibility="collapsed")
                line_col[nm] = cval or base_col.get(nm)
                line_dash[nm] = dval or "Solid"
            if st.button("Reset lines", key=f"ls_reset_{key}"):
                for i in range(len(names)):
                    for suf in ("c", "d"):
                        st.session_state.pop(f"keep_ls_{key}_{i}_{suf}", None)
                st.rerun()

    d = df.copy()
    if lx:
        d = d[d["x"] > 0]
    if ly:
        d = d[d["y"] > 0]
    if "Event" not in d.columns:
        d["Event"] = ""

    def scale(lo, hi, log):
        s = {"type": "log", "nice": False} if log else {"zero": False}
        if lo is not None and hi is not None and hi > lo:
            s["domain"] = [lo, hi]
        elif lo is not None:
            s["domainMin"] = lo
        elif hi is not None:
            s["domainMax"] = hi
        return s

    enc = {
        "x": {"field": "x", "type": "quantitative", "title": x_title,
              "scale": scale(xmin, xmax if xmax is not None else
                             (x_auto_max if not lx else None), lx)},
        "y": {"field": "y", "type": "quantitative", "title": y_title,
              "scale": scale(ymin, ymax, ly)},
        "color": {"field": "Series", "type": "nominal", "title": None,
                  "scale": ({"domain": names,
                             "range": [line_col.get(n) or base_col.get(n) for n in names]}
                            if styled else base_scale),
                  "legend": {"orient": "bottom", "columns": 3,
                             "labelLimit": 320}},
        "tooltip": [{"field": "Event", "type": "nominal"},
                    {"field": "Series", "type": "nominal"},
                    {"field": "x", "type": "quantitative", "format": ",.4~g",
                     "title": x_title},
                    {"field": "y", "type": "quantitative", "format": ",.4~g",
                     "title": y_title}],
    }
    layers = []
    if kind == "line":
        enc_l = dict(enc)
        dash_of = {n: LINE_STYLES[line_dash.get(n, "Dashed" if dashed and n in dashed
                                                else "Solid")] for n in names}
        if any(v != [1, 0] for v in dash_of.values()):
            enc_l["strokeDash"] = {
                "field": "Series", "type": "nominal", "title": None,
                "scale": {"domain": names, "range": [dash_of[n] for n in names]},
                "legend": {"orient": "bottom", "columns": 3, "labelLimit": 320,
                           "symbolStrokeWidth": 2.5}}
        layers.append({"mark": {"type": "line", "strokeWidth": 1.9,
                                "strokeCap": "round", "clip": True},
                       "encoding": enc_l})
    else:
        layers.append({"transform": [{"filter": {"field": "Series",
                                                 "oneOf": [highlight]},
                                      }],
                       "mark": {"type": "point", "filled": True, "size": 330,
                                "shape": "diamond", "stroke": "black",
                                "strokeWidth": 1.4, "fillOpacity": 0.35,
                                "clip": True},
                       "encoding": enc})
        # each data set also gets its own marker shape (as in the PDF)
        shapes = ["circle", "triangle-up", "square", "triangle-down", "cross"]
        rng, k = [], 0
        for n in names:
            if n == highlight:
                rng.append("diamond")
            else:
                rng.append(shapes[k % len(shapes)])
                k += 1
        # same field, title and legend settings as the colour, so Vega-Lite
        # draws one legend with the right symbol for each data set
        enc_s = dict(enc, shape={"field": "Series", "type": "nominal",
                                 "title": None, "legend": enc["color"]["legend"],
                                 "scale": {"domain": names, "range": rng}})
        enc = dict(enc, shape=enc_s["shape"])
        faint = [n for n in (faint or []) if n in names]
        layers.insert(0, {"transform": [{"filter": {"not": {
            "field": "Series", "oneOf": [highlight] + faint}}}],
            "mark": {"type": "point", "filled": True, "size": 70,
                     "opacity": 0.85, "clip": True}, "encoding": enc_s})
        if faint:
            layers.insert(0, {"transform": [{"filter": {
                "field": "Series", "oneOf": faint}}],
                "mark": {"type": "point", "filled": True, "size": 22,
                         "opacity": 0.4, "clip": True}, "encoding": enc_s})
    if one_to_one:
        lo = float(min(d["x"].min(), d["y"].min()))
        hi = float(max(d["x"].max(), d["y"].max()))
        xy = {"x": {"field": "x", "type": "quantitative",
                    "scale": scale(xmin, xmax, lx)},
              "y": {"field": "y", "type": "quantitative",
                    "scale": scale(ymin, ymax, ly)}}
        layers.append({"data": {"values": [{"x": lo, "y": lo},
                                           {"x": hi, "y": hi}]},
                       "mark": {"type": "line", "color": "#555",
                                "strokeDash": [6, 4], "clip": True},
                       "encoding": xy})
        layers.append({"data": {"values": [{"x": hi, "y": hi, "t": "1:1"}]},
                       "mark": {"type": "text", "align": "right", "dx": -6,
                                "dy": -8, "fontSize": 12, "fontWeight": "bold",
                                "color": "#333"},
                       "encoding": {**xy, "text": {"field": "t"}}})
    # The data is embedded in the specification itself. Passed separately,
    # a changed DataFrame under an unchanged specification was not always
    # redrawn, so a re-run could leave the previous hydrograph on screen.
    rec = d[["x", "y", "Series", "Event"]].astype(object).where(
        d[["x", "y", "Series", "Event"]].notna(), None)
    values = [{"x": float(r[0]), "y": float(r[1]), "Series": str(r[2]),
               "Event": "" if r[3] is None else str(r[3])}
              for r in rec.itertuples(index=False, name=None)
              if r[0] is not None and r[1] is not None]
    spec = {"height": height, "layer": layers, "data": {"values": values},
            "config": {"font": "IBM Plex Sans, Segoe UI, system-ui, sans-serif",
                       "axis": {"labelFontSize": 11, "titleFontSize": 11.5,
                                "titleFontWeight": 600, "labelColor": "#33414E",
                                "titleColor": "#17324D", "gridColor": "#EEF2F6",
                                "domainColor": "#C9D3DD", "tickColor": "#C9D3DD"},
                       "legend": {"labelFontSize": 11, "labelColor": "#33414E",
                                  "symbolStrokeWidth": 2.5},
                       "view": {"stroke": "#E3EAF0"},
                       "background": "#FFFFFF"}}
    st.vega_lite_chart(spec=spec, use_container_width=True, theme=None)


def _colour_scale(names: list, extra: dict | None) -> dict:
    """Fixed colours for known series, the palette in order for the rest."""
    fixed = dict(FIXED_COLOURS, **(extra or {}))
    rng, k = [], 0
    for nm in names:
        if nm in fixed:
            rng.append(fixed[nm])
        else:
            rng.append(PALETTE[k % len(PALETTE)])
            k += 1
    return {"domain": names, "range": rng}


def series_long(frame: pd.DataFrame, x_col: str, cols: dict) -> pd.DataFrame:
    """Wide to long: cols maps column name to the series label shown."""
    parts = []
    for c, lab in cols.items():
        if c in frame.columns:
            parts.append(pd.DataFrame({"x": frame[x_col].to_numpy(),
                                       "y": frame[c].to_numpy(),
                                       "Series": lab}))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
