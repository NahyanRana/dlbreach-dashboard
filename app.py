"""
app.py — DLBreach Dashboard
---------------------------
An interface to the DLBreach dam/levee breach model (Wu 2013, 2016).

    streamlit run app.py

Every run is executed by the published DLBreach executable; the dashboard
writes its input, runs it, and presents the output. It adds no physics to
the model itself. Calculations that sit outside DLBreach (tailings release
volumes, bulking, porosity from unit weight, the cone of depression) are
stated with their sources on the page where they are used.

Pages
    About, Project, Model setup, Single run, Sensitivity scenarios,
    Monte Carlo, Case histories, Export. A Tailings release page appears for
    solid waste dams when SOLID_WASTE_ENABLED is set (paused in v0.8; see
    TAILINGS_TODO.md).

Only the active page runs on each interaction.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import dlbreach_about as ABOUT
import dlbreach_batch as BATCH
import dlbreach_cases as CASES
import dlbreach_data as DATA
import dlbreach_help as HLP
import dlbreach_templates as TPL
import dlbreach_units as U
import dlbreach_mc as MCX
from dlbreach_empirical import (case_values, derive_inputs, dlbreach_guidance,
                                eroded_dam_volume, recommended_manning_n,
                                storage_at)
from dlbreach_io import (DEFAULT_PARAMS, browse_for_executable,
                         build_input_text, card_differences, check_stage_storage,
                         find_executable, guess_columns, parse_out,
                         read_input_file, read_table_file, run_case,
                         save_config, stage_storage_from_table, summarise)
from dlbreach_mc import (DISTRIBUTIONS, ENVELOPE_STATS, _thin_hydrograph,
                         build_sample_table, constraint_violations,
                         ensemble_statistics, hydrograph_ensemble,
                         hydrograph_percentiles, realisation_params,
                         representative_realisation, run_monte_carlo)
from dlbreach_report import SECTIONS as REPORT_SECTIONS, build_docx, build_report
from dlbreach_tailings import (bulking_factor, combined_stage_storage,
                               tailings_for_run,
                               cone_geometry, cone_volume_practice,
                               cv_from_cw, cw_from_cv, fontaine_martin,
                               insitu_cv)
import dlbreach_ui as UI
from dlbreach_ui import (anchor, callout, chart, group, section, seed,
                         series_long, tiles)
from dlbreach_viz import (FONT_LINK, HELP, animation_height, breach_animation_html,
                          breach_face_svg, check_breach_consistency,
                          clay_cover, core_outside, core_polygon,
                          cross_section_svg, svg_height)

# Solid waste dams (tailings, coal ash) are paused while the water-dam
# workflow is finalised. Their code is kept and works when this is True;
# the open items before it is switched back on are in TAILINGS_TODO.md.
SOLID_WASTE_ENABLED = False

st.set_page_config(page_title="DLBreach Dashboard", page_icon="🌊",
                   layout="wide", initial_sidebar_state="expanded")

# Running in a browser (stlite / Pyodide) rather than a local install. The
# executable cannot run in a browser, so runs are packaged for the user's
# own machine and the outputs uploaded back.
BROWSER = sys.platform == "emscripten"

# Keep widget values when their page is not displayed: Streamlit discards
# the state of widgets not drawn on a run, so persistent keys are
# re-assigned here. They are seeded once and never given value=.
for _k in list(st.session_state.keys()):
    if isinstance(_k, str) and _k.startswith(("mc_", "keep_")):
        st.session_state[_k] = st.session_state[_k]

# ---------------------------------------------------------------------
# Styling: light only, no sidebar
# ---------------------------------------------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
  :root {--dlb-font: "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, Roboto, sans-serif;}
  /* One typeface everywhere, except Streamlit's icon font and code */
  .stApp, .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre):not(.material-symbols-rounded) {
      font-family: var(--dlb-font) !important;}
  .dlb-tile .val, [data-testid="stDataFrame"], .dlb-case {font-variant-numeric: tabular-nums;}
  html, body, .stApp, [data-testid="stAppViewContainer"] {
      background: #FFFFFF !important; color: #17324D !important;}
  .stMarkdown p, .stMarkdown li, label, .stCaption, [data-testid="stCaptionContainer"] {
      color: #24323F;}
  [data-testid="stCaptionContainer"] p {color: #4A5866 !important;}
  .block-container {padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}
  h1, h2, h3, h4 {color: #17324D !important; letter-spacing: -0.01em;}
  .dlb-hero {background: linear-gradient(115deg, #0E2638 0%, #15405F 58%, #1D5C83 100%);
      border-radius: 12px; padding: 1.45rem 1.8rem 1.35rem; margin: 0 0 .9rem 0;
      position: relative; overflow: hidden;}
  .dlb-hero .motif {position: absolute; right: 1.4rem; top: 50%; transform: translateY(-50%);
      width: 420px; max-width: 42%; opacity: .95; pointer-events: none;}
  .dlb-hero .txt {position: relative; max-width: 60%;}
  @media (max-width: 1100px) {.dlb-hero .motif {display: none;} .dlb-hero .txt {max-width: 100%;}}
  .dlb-hero p {margin: 0;}
  .dlb-hero .kicker {font-size: .78rem; letter-spacing: .08em; text-transform: uppercase;
      color: #A9C7DF !important;}
  .dlb-hero .title {font-size: 1.9rem; font-weight: 600; color: #FFFFFF !important;
      line-height: 1.25; letter-spacing: -0.015em;}
  .dlb-hero .lede {font-size: .96rem; color: #DCE8F1 !important; margin-top: .45rem;
      max-width: 1000px; line-height: 1.5;}
  .dlb-hero .title .ver {font-size: 1.0rem; font-weight: 500; color: #A9C7DF !important;
      margin-left: .45rem; letter-spacing: 0;}
  .dlb-hero .meta {font-size: .84rem; color: #C3D8E8 !important; margin-top: .55rem;}
  .dlb-hero .meta + .meta {margin-top: .1rem;}
  /* ---- contents panel (sidebar), read like the contents of a book ---- */
  section[data-testid="stSidebar"] {background: #F3F6F9 !important;
      border-right: 1px solid #DCE4EC;}
  section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {background: #F3F6F9;}
  .dlb-toc-head {padding: .2rem .2rem .8rem .2rem; border-bottom: 1px solid #DCE4EC;
      margin-bottom: .7rem;}
  .dlb-toc-head p {margin: 0;}
  .dlb-toc-head .t {font-size: 1.05rem; font-weight: 700; color: #17324D;}
  .dlb-toc-head .c {font-size: .82rem; color: #4A5866; margin-top: .15rem;}
  .dlb-prog {height: 5px; border-radius: 3px; background: #DCE4EC; margin-top: .6rem;
      overflow: hidden;}
  .dlb-prog > div {height: 100%; background: #2E7D4F;}
  .dlb-prog-lab {font-size: .78rem !important; color: #4A5866 !important;
      margin-top: .35rem !important; line-height: 1.3 !important;}
  .dlb-toc-head .c {font-size: .82rem !important;}
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {height: 2.2rem; padding-top: .6rem;}
  section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top: .3rem;}
  .st-key-toc {gap: 0 !important;}
  .st-key-toc .stButton {position: relative;}
  .st-key-toc .stButton button {justify-content: flex-start; text-align: left;
      border: 1px solid transparent; background: transparent; box-shadow: none;
      padding: .42rem .6rem .42rem 2.55rem; min-height: 2.35rem; border-radius: 7px;
      position: relative; z-index: 1;}
  .st-key-toc .stButton button > div, .st-key-toc .stButton button [data-testid="stMarkdownContainer"] {
      justify-content: flex-start !important; text-align: left !important; width: 100%;}
  .st-key-toc .stButton button p {font-size: .92rem; font-weight: 500; color: #24323F;
      text-align: left !important; margin: 0;}
  .st-key-toc .stButton button:hover {background: #E6EDF4; border-color: transparent;}
  .st-key-toc .stButton button:focus:not(:active) {border-color: transparent;}
  .st-key-toc .stButton button::before {position: absolute; left: .55rem; top: 50%;
      transform: translateY(-50%); width: 1.45rem; height: 1.45rem; border-radius: 50%;
      display: flex; align-items: center; justify-content: center; font-size: .74rem;
      font-weight: 700; border: 1.5px solid #9DB0C2; background: #FFFFFF; color: #4A5866;
      box-sizing: border-box;}
  .st-key-toc .stButton::after {content: ""; position: absolute; left: 1.23rem; top: 50%;
      height: 100%; border-left: 1.5px solid #C9D6E2; z-index: 0;}
  .dlb-toc-sub {margin: 0 0 .15rem 1.23rem; border-left: 1.5px solid #C9D6E2;
      padding: .05rem 0 .45rem 1.25rem;}
  .dlb-toc-sub p {margin: 0; font-size: .8rem; color: #4A5866; line-height: 1.65;}
  .dlb-toc-sub a {color: #1D5C83 !important; text-decoration: none;}
  .dlb-toc-sub a:hover {text-decoration: underline;}
  .dlb-toc-sub .lab {font-size: .74rem; color: #77818B; margin-bottom: .1rem;}
  .dlb-case {margin-top: 1.1rem; padding: .7rem .8rem; background: #FFFFFF;
      border: 1px solid #DCE4EC; border-radius: 8px;}
  .dlb-case p {margin: 0; font-size: .82rem; color: #33414E; line-height: 1.5;}
  .dlb-case .n {font-weight: 700; color: #17324D; font-size: .9rem;}
  [id^="dlb-"] {scroll-margin-top: 4rem;}
  .st-key-navbar div[role="radiogroup"] {gap: .45rem; flex-wrap: wrap;}
  .st-key-navbar div[role="radiogroup"] > label {border: 1px solid #C9D6E2;
      border-radius: 999px; background: #FFFFFF; padding: .32rem .95rem; margin: 0;}
  .st-key-navbar div[role="radiogroup"] > label > div:first-child {display: none;}
  .st-key-navbar div[role="radiogroup"] > label p {font-size: .9rem; font-weight: 600;
      color: #17324D !important;}
  .st-key-navbar div[role="radiogroup"] > label:has(input:checked) {
      background: #17324D; border-color: #17324D;}
  .st-key-navbar div[role="radiogroup"] > label:has(input:checked) p {
      color: #FFFFFF !important;}
  div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 10px !important;
      background: #FFFFFF; border-color: #DCE4EC !important;}
  .dlb-section {font-size: 1.12rem; font-weight: 600; color: #17324D; margin: .2rem 0 .2rem 0;
      letter-spacing: -0.005em; display: flex; align-items: center; gap: .55rem;}
  .dlb-step {display: inline-flex; align-items: center; justify-content: center;
      width: 1.55rem; height: 1.55rem; border-radius: 50%; background: #17324D;
      color: #FFFFFF; font-size: .8rem; font-weight: 600; flex: none;}
  .dlb-sub {font-size: .9rem; color: #4A5866; margin: 0 0 .7rem 0; line-height: 1.5;}
  .dlb-group {font-size: .86rem; font-weight: 600; letter-spacing: 0;
      color: #3F5F7A; border-bottom: 1px solid #E3EAF0;
      padding-bottom: .3rem; margin: .2rem 0 .7rem 0;}
  .dlb-callout {border-radius: 8px; padding: .8rem 1.0rem; margin: .5rem 0 .8rem 0;
      line-height: 1.55; font-size: .93rem;}
  .dlb-info {background: #EEF5FB; border-left: 4px solid #1D5C83; color: #13222F;}
  .dlb-note {background: #FFF7EA; border-left: 4px solid #D98A1A; color: #2E220E;}
  .dlb-warn {background: #FDF0EE; border-left: 4px solid #B3402A; color: #33150F;}
  .dlb-ok   {background: #EEF7F1; border-left: 4px solid #2E7D4F; color: #12271A;}
  .dlb-tiles {display: grid; gap: .6rem; margin: .3rem 0 .8rem 0;}
  .dlb-tile {background: #F5F8FB; border: 1px solid #E1E8EF; border-radius: 8px;
      padding: .6rem .8rem;}
  .dlb-tile p {margin: 0;}
  .dlb-tile .lab {font-size: .76rem; color: #4A5866;}
  .dlb-tile .val {font-size: 1.35rem; font-weight: 600; color: #17324D; margin-top: .15rem;
      letter-spacing: -0.01em;}
  .dlb-tile .val.accent {color: #B3402A;}
  .dlb-tile .sub {font-size: .74rem; color: #5E6B77; margin-top: .15rem;}
  .dlb-cite p, .dlb-cite li {color: #111 !important; font-weight: 600;}
  .dlb-note {background: #F3F6F9; border-left: 3px solid #5B9BD5; border-radius: 4px;
      padding: .55rem .8rem; margin: .1rem 0 .7rem 0; font-size: .86rem; line-height: 1.5;
      color: #33414E; max-width: 1050px;}
  .dlb-tpl {font-size: .9rem; line-height: 1.45; color: #24323F; padding: .15rem 0 .5rem 0;}
  .dlb-tpl span {color: #4A5866; font-size: .85rem;}
  .dlb-contact {background: #EEF5FB; border: 1px solid #CFE0EE; border-radius: 10px;
      padding: 1rem 1.15rem; margin-bottom: 1rem;}
  .dlb-contact p {margin: 0; font-size: .92rem; color: #24323F; line-height: 1.5;}
  .dlb-contact .h {font-weight: 600; color: #17324D; font-size: 1.02rem; margin-bottom: .3rem;}
  .dlb-contact .e {margin-top: .55rem; font-size: 1.0rem;}
  .dlb-contact .e a {color: #1D5C83 !important; font-weight: 600; text-decoration: none;}
  .dlb-contact .e a:hover {text-decoration: underline;}
  .dlb-foot {text-align: center; color: #4A5866; font-size: .86rem; padding-top: .45rem;}
  .dlb-status {display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; margin: .1rem 0 .9rem 0;
      font-size: .84rem; color: #33414E;}
  .dlb-status span {white-space: nowrap;}
  .dlb-status i {display: inline-block; width: .55rem; height: .55rem; border-radius: 50%;
      margin-right: .35rem; vertical-align: .05rem;}
  .dlb-status .g {background: #2E7D4F;} .dlb-status .a {background: #D9A21A;}
  .dlb-status .r {background: #B3402A;} .dlb-status .n {background: #B8C3CE;}
  .dlb-guide {border-left: 3px solid #1D5C83; padding: .15rem 0 .15rem .9rem;
      margin: 0 0 1rem 0; max-width: 1100px;}
  .dlb-guide p {margin: 0; line-height: 1.5; font-size: .95rem; color: #24323F;}
  .dlb-guide p.need {font-size: .86rem; color: #4A5866; margin-top: .2rem;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# State
# ---------------------------------------------------------------------
# A new session starts from a small, internally consistent dam, so that
# pressing Run straight away releases water. DLBreach's own defaults put
# the pond below the pilot channel.
STARTER = {"case_name": "example_dam", "wsl_up_initial": 19.5,
           "pilot_depth": 1.0, "pilot_width": 2.0, "res_H": 20.0,
           "sim_end": 43200.0}
EXAMPLES = {
    "T1_water_overtopping": "12 m water dam, overtopping from a pilot channel",
    "T2_water_piping": "12 m water dam, piping at mid-height",
    "T3_water_overtopping": "12 m water dam, cohesive fill, overtopping at a crest settlement",
    "T4_water_piping": "12 m water dam, cohesive fill, piping near the base",
}
if "params" not in st.session_state:
    st.session_state.params = dict(DEFAULT_PARAMS, **STARTER)
for _k, _v in {"result_df": None, "mc_store": {}, "scen_store": None,
               "scen_grid": None, "tl_result": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
P = st.session_state.params
P.setdefault("dam_type", "water")
if P["dam_type"] in ("tailings", "ccr"):
    P["dam_type"] = "solid"
if not SOLID_WASTE_ENABLED and P["dam_type"] != "water":
    P["dam_type"] = "water"
    st.session_state["solid_coerced"] = True
P.setdefault("sed_saturation", 1.0)
P.setdefault("bulk_unit_weight", 20.0)
P.setdefault("basis", {})


def resync_inputs():
    """Forget input widget states so they re-read the parameters, after a
    file is loaded or a value is changed from elsewhere."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(("keep_in_", "_model_keep_in_",
                                                "_clamped_keep_in_")):
            del st.session_state[k]


def num_u(key: str, lo=None, hi=None, step=None, fmt=None, label=None,
          help_=None):
    """Number input in the practitioner unit, stored in the DLBreach unit."""
    wk = f"keep_in_{key}"
    mk = f"_model_{wk}"
    if wk not in st.session_state:
        m0 = P.get(key, DEFAULT_PARAMS.get(key, 0.0))
        v = U.from_model(key, m0)
        v = float(v) if v is not None else 0.0
        v_in = v
        if lo is not None:
            v = max(v, lo)
        if hi is not None:
            v = min(v, hi)
        st.session_state[wk] = round(v, 8)
        if v != v_in:
            # a loaded value outside the field's range: shown at the limit,
            # written unchanged unless the user edits the field
            st.session_state[f"_clamped_{wk}"] = v_in
        # remember the exact model value shown, so an untouched field writes
        # it back unchanged (no rounding from the unit conversion)
        st.session_state[mk] = (st.session_state[wk], m0)
    v = st.number_input(label or U.label_unit(key), min_value=lo, max_value=hi,
                        step=step, format=fmt, key=wk,
                        help=help_ or HELP.get(key))
    shown = st.session_state.get(mk)
    if shown is not None and shown[0] == v and shown[1] is not None:
        P[key] = shown[1]
        cl = st.session_state.get(f"_clamped_{wk}")
        if cl is not None:
            st.caption(f"The loaded value, {cl:g}, is outside this field's range. "
                       "It is written unchanged unless you edit the field.")
    else:
        P[key] = U.to_model(key, v) if key in U.CATALOGUE else v
    return P[key]


def choice(label: str, key: str, options: list, fmt=None, horizontal=True,
           help_=None, radio=True):
    """Radio or selectbox bound to a parameter."""
    wk = f"keep_in_{key}"
    if wk not in st.session_state:
        cur = P.get(key, options[0])
        st.session_state[wk] = cur if cur in options else options[0]
    w = st.radio if radio else st.selectbox
    kw = {"horizontal": horizontal} if radio else {}
    P[key] = w(label, options, key=wk, format_func=fmt or str, help=help_, **kw)
    return P[key]


def datum() -> tuple[float, str]:
    base = float(P.get("datum_base_rl", 0.0))
    shift = float(P.get("datum_bench_geo", 0.0)) - float(P.get("datum_bench_site", 0.0))
    d = P.get("datum_display", "model")
    if d == "site":
        return base, str(P.get("datum_label") or "site RL")
    if d == "geo":
        return base + shift, str(P.get("datum_geo_label") or "geodetic")
    return 0.0, "m above embankment base"


def PD(extra: dict | None = None) -> dict:
    off, lab = datum()
    d = dict(P, _z_off=off, _z_lab=lab)
    if extra:
        d.update(extra)
    return d


def zdisp(z: float) -> str:
    off, lab = datum()
    return f"{float(z) + off:,.2f} ({lab})"


def exe_status() -> tuple[str, bool]:
    if BROWSER:
        return "", False
    if "exe_path" not in st.session_state:
        st.session_state.exe_path = find_executable() or ""
    p = Path(st.session_state.exe_path) if st.session_state.exe_path else None
    if p and p.is_file() and p.suffix.lower() == ".exe":
        return str(p), True
    if p and p.is_dir():
        found = sorted(p.glob("*.exe"))
        if found:
            return str(found[0]), True
    return st.session_state.exe_path, False


@st.cache_data(show_spinner=False)
def thin(df: pd.DataFrame, max_points: int = 1200) -> pd.DataFrame:
    """Fewer rows for plotting; the peak row is always kept."""
    if len(df) <= max_points:
        return df
    stride = max(1, len(df) // max_points)
    keep = set(range(0, len(df), stride)) | {len(df) - 1}
    if "Q_breach" in df.columns:
        keep.add(int(df["Q_breach"].idxmax()))
    return df.iloc[sorted(keep)]


def is_tailings() -> bool:
    """Solid waste: tailings, or coal combustion residuals such as fly ash.
    Always False while SOLID_WASTE_ENABLED is off."""
    return SOLID_WASTE_ENABLED and P.get("dam_type") in ("solid", "tailings", "ccr")


def input_signature(p: dict | None = None) -> str:
    """The DLBreach input text a run was made from, for spotting results that
    no longer match the inputs."""
    try:
        return build_input_text(p or P)
    except Exception:                                  # noqa: BLE001
        return ""


def result_state() -> str:
    """none, current, stale or loaded (an .out file read from disk)."""
    if st.session_state.get("result_df") is None:
        return "none"
    sig = st.session_state.get("result_sig")
    if sig is None:
        return "loaded"
    return "current" if sig == input_signature() else "stale"


def stale_notice():
    """Say so when the results on screen no longer match the inputs."""
    rs = result_state()
    if rs == "stale":
        callout("note", "Inputs have changed since this run.",
                "The results below are from the earlier inputs. Run the model "
                "again on Single run to update them." if PAGE != "Single run" else
                "The results below are from the earlier inputs. Run the model "
                "again to update them.")
    elif rs == "loaded":
        callout("note", "Results loaded from an output file.",
                "They may not match the inputs on Model setup.")


def t_view(series) -> float | None:
    """Default end of a time axis: 30 % past the moment the last of the
    given hydrographs, (t, q) pairs, falls below 1 % of its peak."""
    try:
        e = MCX._active_end(series)
    except Exception:                                  # noqa: BLE001
        return None
    return round(1.3 * e, 2) if e > 0 else None


AUTOSAVE = Path(globals().get("__file__", "app.py")).resolve().with_name(
    ".dlbreach_autosave.json")


def _autosave():
    """Keep the inputs on disk, so a refreshed or restarted session can
    restore them. Written only when they change, and not before the user
    has answered the restore offer of a new session."""
    if BROWSER or (st.session_state.get("_fresh")
                   and not st.session_state.get("_restore_done")):
        return
    try:
        import json as _json
        data = {k: v for k, v in P.items() if not k.startswith("_")}
        txt = _json.dumps(data, default=float, sort_keys=True)
        if st.session_state.get("_autosaved") != txt:
            AUTOSAVE.write_text(txt, encoding="utf-8")
            st.session_state["_autosaved"] = txt
    except Exception:                                  # noqa: BLE001
        pass


def restore_offer():
    """After a refresh or restart, offer the inputs of the last session."""
    if PAGE not in ("About", "Project"):
        # moving on to the analysis means starting afresh
        st.session_state["_restore_done"] = True
    if BROWSER or st.session_state.get("_restore_done") or not AUTOSAVE.is_file():
        return
    try:
        import json as _json
        import datetime as _dt
        data = _json.loads(AUTOSAVE.read_text(encoding="utf-8"))
        cur = {k: v for k, v in P.items() if not k.startswith("_")}
        if _json.dumps(data, default=float, sort_keys=True) == \
                _json.dumps(cur, default=float, sort_keys=True):
            st.session_state["_restore_done"] = True
            return
        when = _dt.datetime.fromtimestamp(AUTOSAVE.stat().st_mtime)
    except Exception:                                  # noqa: BLE001
        st.session_state["_restore_done"] = True
        return
    with st.container(border=True):
        r1, r2, r3 = st.columns([5, 1.3, 1])
        r1.markdown(f"**Inputs from your last session are available** "
                    f"({data.get('case_name', 'case')}, saved "
                    f"{when:%d %b %Y %H:%M}). Results are not kept between "
                    f"sessions; run again after restoring.")
        if r2.button("Restore inputs", type="primary", key="restore_yes",
                     use_container_width=True):
            st.session_state["_restore_done"] = True
            _open_project(data, "the inputs of your last session")
        if r3.button("Dismiss", key="restore_no", use_container_width=True):
            st.session_state["_restore_done"] = True
            st.rerun()


def page_intro(name: str):
    """One line on what the page is for, and what it needs first."""
    g = ABOUT.PAGE_GUIDE.get(name)
    if not g:
        return
    need = f'<p class="need">{g[1]}</p>' if g[1] else ""
    st.markdown(f'<div class="dlb-guide"><p>{g[0]}</p>{need}</div>',
                unsafe_allow_html=True)


def tl_bulking() -> float | None:
    """Bulking factor of the latest run, for solid waste dams."""
    r = tl_for(st.session_state.get("result_df"))
    return r["bulking"] if (r and r.get("ok")) else None


def cone_overlay():
    """Cone of depression for the cross-section, at the final breach of the
    latest run (or the erosion limit before any run)."""
    tl = P.get("tl", {})
    if not (is_tailings() and tl.get("method") == "cone" and tl.get("show_cone")):
        return None
    df = st.session_state.get("result_df")
    if df is not None:
        inv = float(df["breach_bottom_elev"].min())
        col = "breach_top_width" if tl.get("cone_width") == "top" else "breach_bottom_width"
        b = float(df[col].iloc[-1])
    else:
        inv, b = float(P["hard_bottom_elev"]), 0.0
    slope_pct = float(np.tan(np.radians(float(tl.get("cone_slope_deg", 4.0))))) * 100
    return cone_geometry(float(tl.get("beach_level", 0.0)), inv, slope_pct, b,
                         float(tl.get("cone_lmax", 0.0)) or None) or None


# ---------------------------------------------------------------------
# Header and navigation
# ---------------------------------------------------------------------
HERO_MOTIF = ('<svg class="motif" viewBox="0 0 420 150" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M20 58 L404 58" stroke="rgba(255,255,255,.18)" stroke-width="1"/><path d="M 20.0 58.0 L 23.2 57.6 L 26.4 56.2 L 29.6 54.0 L 32.8 51.2 L 36.0 48.0 L 39.2 44.5 L 42.4 41.0 L 45.6 37.4 L 48.8 34.0 L 52.0 30.8 L 55.2 27.8 L 58.4 25.0 L 61.6 22.6 L 64.8 20.5 L 68.0 18.6 L 71.2 17.2 L 74.4 16.0 L 77.6 15.1 L 80.8 14.5 L 84.0 14.1 L 87.2 14.0 L 90.4 14.1 L 93.6 14.4 L 96.8 14.9 L 100.0 15.5 L 103.2 16.3 L 106.4 17.2 L 109.6 18.2 L 112.8 19.3 L 116.0 20.4 L 119.2 21.6 L 122.4 22.9 L 125.6 24.2 L 128.8 25.5 L 132.0 26.8 L 135.2 28.1 L 138.4 29.4 L 141.6 30.7 L 144.8 31.9 L 148.0 33.2 L 151.2 34.4 L 154.4 35.6 L 157.6 36.8 L 160.8 37.9 L 164.0 39.0 L 167.2 40.0 L 170.4 41.0 L 173.6 42.0 L 176.8 42.9 L 180.0 43.8 L 183.2 44.6 L 186.4 45.4 L 189.6 46.2 L 192.8 46.9 L 196.0 47.6 L 199.2 48.3 L 202.4 48.9 L 205.6 49.5 L 208.8 50.0 L 212.0 50.6 L 215.2 51.0 L 218.4 51.5 L 221.6 51.9 L 224.8 52.4 L 228.0 52.7 L 231.2 53.1 L 234.4 53.4 L 237.6 53.8 L 240.8 54.1 L 244.0 54.3 L 247.2 54.6 L 250.4 54.8 L 253.6 55.1 L 256.8 55.3 L 260.0 55.5 L 263.2 55.7 L 266.4 55.8 L 269.6 56.0 L 272.8 56.1 L 276.0 56.3 L 279.2 56.4 L 282.4 56.5 L 285.6 56.6 L 288.8 56.7 L 292.0 56.8 L 295.2 56.9 L 298.4 57.0 L 301.6 57.1 L 304.8 57.2 L 308.0 57.2 L 311.2 57.3 L 314.4 57.3 L 317.6 57.4 L 320.8 57.4 L 324.0 57.5 L 327.2 57.5 L 330.4 57.6 L 333.6 57.6 L 336.8 57.6 L 340.0 57.7 L 343.2 57.7 L 346.4 57.7 L 349.6 57.7 L 352.8 57.8 L 356.0 57.8 L 359.2 57.8 L 362.4 57.8 L 365.6 57.8 L 368.8 57.8 L 372.0 57.8 L 375.2 57.9 L 378.4 57.9 L 381.6 57.9 L 384.8 57.9 L 388.0 57.9 L 391.2 57.9 L 394.4 57.9 L 397.6 57.9 L 400.8 57.9 L 404.0 57.9" fill="none" stroke="#8FC5EE" stroke-width="2"/><circle cx="87.2" cy="14.0" r="3.2" fill="#FFFFFF"/><path d="M20 78 L404 78 L404 136 L20 136 Z M178 78 L196 122 L232 122 L250 78 Z" fill="rgba(255,255,255,.10)" fill-rule="evenodd" stroke="rgba(255,255,255,.45)" stroke-width="1.2"/><path d="M196 122 L188 102 L240 102 L232 122 Z" fill="#6FB1E6" opacity=".85"/><path d="M14 136 L410 136" stroke="rgba(255,255,255,.35)" stroke-width="1"/><path d="M20 128 L404 128" stroke="#E07A5F" stroke-width="1" stroke-dasharray="5 4" opacity=".75"/></svg>')
st.markdown(
    f'<div class="dlb-hero">{HERO_MOTIF}<div class="txt">'
    f'<p class="title">{ABOUT.TITLE}<span class="ver">({ABOUT.VERSION_SHORT})</span></p>'
    f'<p class="lede">{ABOUT.SUBTITLE}</p>'
    f'<p class="meta">{ABOUT.PREPARED_BY}</p>'
    f'<p class="meta">{ABOUT.ALGORITHM_BY}</p></div></div>',
    unsafe_allow_html=True)

_names = ["About", "Project", "Model setup"]
if is_tailings():
    _names.append("Tailings release")
_names += ["Single run", "Sensitivity scenarios", "Monte Carlo",
           "Case histories", "Export"]
PAGES = [f"{i + 1}. {n}" for i, n in enumerate(_names)]
_by_name = {p.split(". ", 1)[1]: p for p in PAGES}
if st.session_state.get("page") not in PAGES:
    _prev = str(st.session_state.get("page", "")).split(". ", 1)[-1]
    st.session_state.page = _by_name.get(_prev, PAGES[0])


def _go(delta: int):
    i = PAGES.index(st.session_state.page)
    st.session_state.page = PAGES[max(0, min(len(PAGES) - 1, i + delta))]


def _go_to(target: str):
    st.session_state.page = target


# The page is chosen in the contents panel on the left (and with the
# previous and next buttons at the foot of each page).
page = st.session_state.page
PAGE = page.split(". ", 1)[1]
st.session_state.setdefault("visited", set()).add(PAGE)
UI.RENDERED.clear()
# Both filled at the end of the run, so they reflect anything the page did.
_toc_slot = st.sidebar.empty()
_status_slot = st.empty()


def _status_strip():
    """Where the analysis stands, so a user can see what is still to do."""
    _, exe_ok = exe_status()
    if BROWSER:
        exe = ("n", "DLBreach runs on your computer")
    else:
        exe = ("g", "DLBreach.exe found") if exe_ok else ("r", "DLBreach.exe not set")
    issues = water_checks()
    inp = ("g", "Inputs ready") if not issues else ("a", "Inputs need attention")
    rs = result_state()
    run = {"none": ("n", "No run yet"), "current": ("g", "Run up to date"),
           "stale": ("a", "Inputs changed since run"),
           "loaded": ("g", "Output file loaded")}[rs]
    sc = st.session_state.get("scen_store")
    scen = ("g", f"{len(sc['summary'])} scenario runs") if sc else ("n", "No scenarios")
    mc = st.session_state.get("mc_store") or {}
    mcs = ("g", f"{len(mc)} Monte Carlo ensemble{'s' if len(mc) != 1 else ''}") \
        if mc else ("n", "No Monte Carlo")
    items = "".join(f'<span><i class="{c}"></i>{t}</span>'
                    for c, t in (exe, inp, run, scen, mcs))
    st.markdown(f'<div class="dlb-status">{items}</div>', unsafe_allow_html=True)


# =====================================================================
# ABOUT
# =====================================================================
def _about_block(title: str, md: str, html: str | None = None):
    with st.container(border=True):
        st.markdown(f'<div id="{anchor(title)}"></div>', unsafe_allow_html=True)
        st.markdown(md)
        if html:
            st.markdown(html, unsafe_allow_html=True)


def page_about():
    a1, a2 = st.columns([3, 2], gap="large")
    with a1:
        _about_block("The algorithm", ABOUT.ABOUT_MODEL)
        _about_block("This dashboard", ABOUT.ABOUT_DASHBOARD)
        _about_block("Foundational methodology", ABOUT.FOUNDATIONS)
        _about_block("Getting started", ABOUT.GETTING_STARTED)
    with a2:
        st.markdown(f'<div id="{anchor("Questions and feedback")}"></div>'
                    + ABOUT.CONTACT_HTML, unsafe_allow_html=True)
        _about_block("Limitations", ABOUT.LIMITATIONS)
        _about_block("How to cite", ABOUT.HOW_TO_CITE,
                     f'<div class="dlb-cite">{ABOUT.CITATIONS_HTML}</div>')
        _about_block("Disclaimer", ABOUT.DISCLAIMER)


# =====================================================================
# PROJECT
# =====================================================================
# Validation cases from Prof. Wu's DLBreach page, offered as worked examples
# from test_cases/wu_2016. Labels follow Wu (2016), Chapters 6 and 7.
WU_LABELS = {
    "Teton_cards": "Teton Dam, piping (Wu 2016 validation case)",
    "BigBay_cards": "Big Bay Dam, piping (Wu 2016 validation case)",
    "Banqiao_cards": "Banqiao Dam, clay core, overtopping (Wu 2016 validation case)",
    "HansonE1S1_cards": "USDA-ARS E1S1 laboratory dam, headcut (Wu 2016 validation case)",
    "Impactfld03_cards": "IMPACT field test 3, moraine core (Wu 2016 validation case)",
    "Yigong_cards": "Yigong landslide dam, overtopping (Wu 2016 validation case)",
    "Zwin_cards": "Zwin sea dike, water level series (Wu 2016 validation case)",
    "Yahekou_cards": "Yahekou fuse plug, measured tailwater (Wu 2016 validation case)",
    "Yahekou_R_cards": "Yahekou fuse plug, variant R (Wu 2016 validation case)",
    "Sutter_cards_BasinVolume": "Sutter Bypass levee, piping (Wu 2016 validation case)",
    "Mecox_cards_WSLbay": "Mecox Inlet barrier, waves and tide (Wu 2016 validation case)",
}


def wu_cases(ex_dir: Path) -> dict:
    """Wu validation input files present locally: key -> (label, path)."""
    d = ex_dir / "wu_2016"
    if not d.is_dir():
        return {}
    return {f"wu:{f.stem}": (WU_LABELS.get(f.stem, f"{f.stem} (Wu 2016)"), f)
            for f in sorted(d.glob("*_cards*.txt"))}


def load_input_text(text: str, filename: str, data_files: dict | None = None):
    """Replace every input with those of a DLBreach input file. Cards the
    dashboard does not edit are kept and written back unchanged; the case
    name comes from the file name and the notes from its leading comments."""
    loaded = read_input_file(text)
    keep = {k: v for k, v in P.items() if k.startswith("datum_")}
    stem = Path(filename).stem
    data = dict(keep, **loaded)
    data["case_name"] = BATCH.safe_case_name(stem, 0)
    data["notes"] = loaded.get("notes") or f"Loaded from {filename}."
    data["data_files"] = dict(data_files or {})
    # a data file named like the case's own input or output would be
    # overwritten by it in the run folder
    own = {f"{data['case_name']}.txt".lower(), f"{data['case_name']}.out".lower()}
    clash = [r for r in data.get("data_file_refs", [])
             if Path(str(r).replace("\\", "/")).name.lower() in own]
    if clash:
        data["data_file_refs"] = [r for r in data["data_file_refs"] if r not in clash]
        data["data_file_refused"] = list(data.get("data_file_refused", [])) + clash
    p_new = dict(DEFAULT_PARAMS, **data)
    p_new["res_curve"] = [tuple(x) for x in p_new.get("res_curve") or []]
    diff = card_differences(text, build_input_text(p_new))
    st.session_state.loaded_text = (filename, text)
    st.session_state.load_report = {
        "file": filename, "n": diff["n"], "missing": diff["missing"],
        "changed": diff["changed"], "added": diff["added"],
        "duplicates": diff["duplicates"],
        "kept": [c.split(None, 1)[0] for c in loaded.get("extra_cards", [])],
        "renamed": loaded.get("renamed_cards", []),
        "refused": data.get("data_file_refused", []),
        "reservoir": loaded.get("write_reservoir", True),
        "downstream": loaded.get("downstream_mode", "channel")}
    _open_project(data, filename, keep_report=True)


def load_report():
    """What happened to the cards of the last loaded input file."""
    r = st.session_state.get("load_report")
    if not r:
        return
    kept, n = r["kept"], r["n"]
    if r.get("duplicates"):
        callout("warn", f"{r['file']} gives some cards more than once.",
                ", ".join(r["duplicates"]) + ". The dashboard uses the last one; "
                "DLBreach may read either. Correct the file and load it again.")
    if r["missing"] or r["changed"]:
        callout("warn", f"Not every card of {r['file']} is written back as it was.",
                "Missing: " + (", ".join(r["missing"]) or "none") + ". Changed: "
                + (", ".join(r["changed"]) or "none") + ". Check the Input file "
                "tab on Model setup before running.")
    elif r["added"]:
        callout("warn", f"Read {n} cards from {r['file']}; the dashboard adds "
                f"{len(r['added'])}.",
                "All the file's cards are written back unchanged, but these are "
                "added with the dashboard's default values: " + ", ".join(r["added"])
                + ". Without them DLBreach would use its own defaults. Check "
                "them on Model setup.")
    else:
        callout("ok", f"Read {n} cards from {r['file']}.",
                f"All {n} are written back unchanged, and nothing is added: "
                f"{n - len(kept)} through the dashboard's inputs"
                + (f", {len(kept)} kept as written." if kept else "."))
    if r.get("renamed"):
        callout("note", "Card names written in standard form.",
                ", ".join(r["renamed"]) + ". If your DLBreach version matches card "
                "names exactly, the original file may not have used these values.")
    if r.get("refused"):
        callout("warn", "Data files the dashboard cannot supply.",
                ", ".join(r["refused"]) + ". They are outside the run folder or "
                "share the case's own file name. DLBreach looks for them itself; "
                "rename them in the file to let the dashboard attach them.")
    if kept:
        callout("note", "Cards the dashboard keeps but does not edit.",
                ", ".join(kept) + ". They are written to every input file "
                "(single run, scenarios, Monte Carlo) exactly as loaded. "
                + ("The cross-section shows the clay cover they describe; the "
                   if clay_cover(P) else "The cross-section, ")
                + "input checks and case-history comparison do not account for "
                  "them.")


def data_files_card():
    """Data files the loaded case reads by name (water levels, waves)."""
    refs = P.get("data_file_refs") or []
    if not refs:
        return
    have = dict(P.get("data_files") or {})          # never edit the default in place
    missing = [r for r in refs if r not in have]
    if not missing:
        callout("ok", "Data files attached.", ", ".join(refs) + ". They are "
                "placed next to the input file for every run and included in "
                "run packages.")
        if st.button("Remove attached data files", key="data_files_clear"):
            P["data_files"] = {}
            st.rerun()
        return
    callout("warn", "This case reads data files.",
            "Add " + ", ".join(missing) + " (from the same folder as the input "
            "file). Runs are blocked until they are attached.")
    ups = st.file_uploader("Data files", type=None, accept_multiple_files=True,
                           key="data_files_up", label_visibility="collapsed")
    added = False
    for u in ups or []:
        # matched on the bare file name, ignoring case; stored under the
        # name the input uses (which may include a sub-folder)
        for r in missing:
            if Path(str(r).replace("\\", "/")).name.lower() == u.name.lower():
                have[r] = u.getvalue().decode("utf-8", "replace")
                added = True
    if added:
        P["data_files"] = have
        st.rerun()


def data_files_missing(p: dict | None = None) -> list[str]:
    p = p or P
    return [r for r in (p.get("data_file_refs") or [])
            if r not in (p.get("data_files") or {})]


def page_project():
    if st.session_state.pop("solid_coerced", False):
        callout("note", "Opened as a water-retaining dam.",
                "This version covers water-retaining dams only, so the solid "
                "waste settings in the file were set aside.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if SOLID_WASTE_ENABLED:
            with st.container(border=True):
                section("Dam type", "Changes the pages and comparisons offered. "
                        "Solid waste facilities add a Tailings release page and are "
                        "compared with tailings dam case histories.")
                choice("Dam type", "dam_type", ["water", "solid"],
                       fmt=lambda k: {"water": "Water-retaining",
                                      "solid": "Solid waste (tailings, coal ash / fly ash)"}[k])
        ex_dir = Path(globals().get("__file__", "app.py")).resolve().with_name("test_cases")
        avail_ex = {k: v for k, v in EXAMPLES.items()
                    if (ex_dir / f"{k}.json").is_file()}
        wu = wu_cases(ex_dir)
        avail_ex.update({k: v[0] for k, v in wu.items()})
        if avail_ex:
            with st.container(border=True):
                section("Worked examples",
                        "Small test cases supplied with the dashboard. Loading one "
                        "replaces the current inputs.")
                e1, e2 = st.columns([3, 1])
                seed("keep_example", list(avail_ex)[0])
                exk = e1.selectbox("Example", list(avail_ex), key="keep_example",
                                   format_func=lambda k: avail_ex[k],
                                   label_visibility="collapsed",
                                   help="Small test cases supplied with the dashboard.")
                if e2.button("Load example", type="primary", use_container_width=True,
                             key="load_example"):
                    if exk in wu:
                        f = wu[exk][1]
                        refs = read_input_file(f.read_text(errors="replace")).get(
                            "data_file_refs", [])
                        companions = {r: (f.parent / r).read_text(errors="replace")
                                      for r in refs if (f.parent / r).is_file()}
                        load_input_text(f.read_text(errors="replace"), f.name,
                                        companions)
                    else:
                        import json as _json
                        data = _json.loads((ex_dir / f"{exk}.json").read_text())
                        _open_project(data, f"the {avail_ex[exk].lower()} example")
        msg = st.session_state.pop("opened_msg", None)
        if msg:
            callout("ok", "Opened.", msg + " Check the inputs on Model setup, then "
                    "run it on Single run.")
        with st.container(border=True):
            section("Case", "Name the analysis, then start from scratch, open a "
                    "saved project, or load an existing DLBreach input file.")
            P["case_name"] = st.text_input(
                "Case name", value=P.get("case_name", "case"),
                help=HLP.h("case_name"))
            P["notes"] = st.text_area(
                "Notes (written into the input file)",
                value=P.get("notes", ""), height=90, help=HLP.h("notes"))
            import json as _json
            pj1, pj2 = st.columns(2)
            pj1.download_button(
                "Save project (.json)",
                _json.dumps({k: v for k, v in P.items() if not k.startswith("_")},
                            indent=1, default=float).encode(),
                file_name=f"{P.get('case_name') or 'case'}_project.json",
                mime="application/json", use_container_width=True,
                help="Every input on these pages, including the stage-storage "
                     "table and the site datum, in one file.")
            pj = pj2.file_uploader("Open project (.json)", type=["json"],
                                   key="proj_loader", label_visibility="collapsed",
                                   help=HLP.h("project_open"))
            if pj is not None and st.session_state.get("proj_sig") != (pj.name, pj.size):
                try:
                    data = _json.loads(pj.getvalue().decode("utf-8"))
                    st.session_state.proj_sig = (pj.name, pj.size)
                    _open_project(data, pj.name)
                except Exception as exc:              # noqa: BLE001
                    callout("warn", "Could not open that project.", str(exc))
            up = st.file_uploader("Load an existing DLBreach input file (.txt)",
                                  type=["txt"], key="txt_loader",
                                  help=HLP.h("txt_open"))
            if up is not None:
                sig = (up.name, up.size)
                if st.session_state.get("loaded_sig") != sig:
                    st.session_state.loaded_sig = sig
                    try:
                        load_input_text(up.getvalue().decode("utf-8", "replace"),
                                        up.name)
                    except Exception as exc:          # noqa: BLE001
                        callout("warn", "Could not read that file.", str(exc))
            load_report()
            data_files_card()
    with c2:
        with st.container(border=True):
            section("DLBreach executable")
            if BROWSER:
                callout("info", "Browser version.",
                        "DLBreach runs on your own computer. Each run page "
                        "prepares the input files to download; run them with "
                        "DLBreach and upload the outputs back.")
            else:
                if st.button("Browse for DLBreach.exe…",
                             help="Opens a file dialog on this computer."):
                    picked = browse_for_executable()
                    if picked:
                        st.session_state.exe_path = picked
                        save_config(exe_path=picked)
                        st.rerun()
                    else:
                        st.info("No file dialog is available. Paste the path "
                                "below instead.")
                exe_status()
                newp = st.text_input("Path to DLBreach.exe",
                                     value=st.session_state.exe_path,
                                     help=HLP.h("exe_path"))
                if newp != st.session_state.exe_path:
                    st.session_state.exe_path = newp
                    if Path(newp).is_file():
                        save_config(exe_path=newp)
                path, ok = exe_status()
                if ok:
                    callout("ok", "Executable found.", Path(path).name)
                else:
                    callout("warn", "Executable not found.",
                            "Give the full path to DLBreach.exe.")
        with st.container(border=True):
            section("Site datum", "DLBreach works in metres above the "
                    "embankment base, and inputs stay in that datum. These "
                    "settings change how elevations are shown and exported.")
            d1, d2 = st.columns(2)
            P["datum_base_rl"] = d1.number_input(
                "Embankment base elevation (site RL)",
                value=float(P.get("datum_base_rl", 0.0)), step=0.5, format="%.3f",
                help=HLP.h("datum_base_rl"))
            P["datum_label"] = d2.text_input(
                "Site datum label", value=P.get("datum_label", "m RL (mine grid)"),
                help=HLP.h("datum_label"))
            d3, d4, d5 = st.columns(3)
            P["datum_bench_site"] = d3.number_input(
                "Benchmark, site RL", value=float(P.get("datum_bench_site", 0.0)),
                step=0.5, format="%.3f", help=HLP.h("datum_bench_site"))
            P["datum_bench_geo"] = d4.number_input(
                "Same point, geodetic", value=float(P.get("datum_bench_geo", 0.0)),
                step=0.5, format="%.3f", help=HLP.h("datum_bench_geo"))
            P["datum_geo_label"] = d5.text_input(
                "Geodetic label", value=P.get("datum_geo_label", "m AHD"),
                help=HLP.h("datum_geo_label"))
            choice("Display elevations in", "datum_display",
                   ["model", "site", "geo"],
                   fmt=lambda k: {"model": "Model datum (above base)",
                                  "site": "Site RL", "geo": "Geodetic"}[k],
                   help_=HLP.h("datum_display"))

    templates_card()


def project_json() -> bytes:
    import json as _json
    return _json.dumps({k: v for k, v in P.items() if not k.startswith("_")},
                       indent=1, default=float).encode()


def templates_card():
    """Templates for every file the dashboard reads, with what each holds."""
    with st.container(border=True):
        section("Templates and file formats",
                "Every file the dashboard reads, prepared from the current "
                "inputs. Fill one in outside the dashboard, then load it on the "
                "page shown.")
        cn = P.get("case_name") or "case"
        rows = [
            ("DLBreach input file (.txt)",
             "The single file DLBreach reads, with every card annotated: file "
             "rules, units and the stage-storage layout. Open on Project.",
             TPL.input_file_template(P).encode(), f"{cn}_input_template.txt",
             "text/plain"),
            ("Stage-storage table (.csv)",
             TPL.STAGE_STORAGE_NOTE + " Upload on Model setup, Impoundment.",
             TPL.stage_storage_template(P), "stage_storage_template.csv", "text/csv"),
            ("Scenario runs (.csv)",
             "Runs as columns, every variable parameter as a row, in the units "
             "shown. Blank cells keep the Model setup value. Upload on "
             "Sensitivity scenarios.",
             TPL.scenario_template(P).to_csv(index=False).encode(),
             "scenario_runs_template.csv", "text/csv"),
            ("Project (.json)",
             "Every dashboard input in one file. Open on Project.",
             project_json(), f"{cn}_project.json", "application/json"),
        ]
        for i, (name, desc, data, fname, mime) in enumerate(rows):
            t1, t2 = st.columns([4, 1])
            t1.markdown(f"<div class='dlb-tpl'><b>{name}</b><br>"
                        f"<span>{desc}</span></div>", unsafe_allow_html=True)
            t2.download_button("Download", data, file_name=fname, mime=mime,
                               key=f"tpl_{i}", use_container_width=True)
        st.download_button("Download all templates (.zip)",
                           TPL.all_templates_zip(P, project_json()),
                           file_name="dlbreach_templates.zip",
                           mime="application/zip", key="tpl_all",
                           help="All of the above, with a README describing "
                                "each file.")


def _open_project(data: dict, label: str, keep_report: bool = False):
    """Replace every input with a saved project or example, and start the
    results afresh."""
    if not keep_report:
        st.session_state.pop("load_report", None)
        st.session_state.pop("loaded_text", None)
    P.clear()
    P.update(DEFAULT_PARAMS)
    P.update(data)
    P["res_curve"] = [tuple(x) for x in P.get("res_curve") or []]
    if not SOLID_WASTE_ENABLED and P.get("dam_type", "water") != "water":
        P["dam_type"] = "water"
        st.session_state["solid_coerced"] = True
    P["_ss_ver"] = int(st.session_state.get("proj_n", 0)) + 100
    resync_inputs()
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("keep_tl_"):
            del st.session_state[k]
    st.session_state.proj_n = st.session_state.get("proj_n", 0) + 1
    st.session_state.result_df = None
    st.session_state.result_sig = None
    st.session_state.opened_msg = f"Loaded {label} ({P.get('case_name', 'case')})."
    st.session_state["_restore_done"] = True
    st.rerun()


def water_checks(p: dict | None = None) -> list[str]:
    """
    Reasons DLBreach would release nothing: the pond does not reach the
    pipe, the pilot channel or settled crest, or sits at or below the
    erosion limit with no storage above it.
    """
    p = p or P
    msgs = [f"This case reads {r}, which is not attached (Project page)."
            for r in data_files_missing(p)]
    kept = {str(c).split(None, 1)[0] for c in p.get("extra_cards") or []}
    if not p.get("write_reservoir", True) or "Upstream_Reservoir_Inflow" in kept:
        # the upstream level is prescribed by the loaded file (time series or
        # data file), or inflow fills the reservoir during the run, so the
        # initial pond level alone does not decide whether water is released
        return msgs
    H, w = float(p["emb_height"]), float(p["wsl_up_initial"])
    if w <= float(p["hard_bottom_elev"]) + 1e-6:
        msgs.append(f"The initial pond level ({w:g} m above base) is at or below "
                    f"the erosion limit, so there is no water to release.")
    if int(p["breach_mode"]) == 2:
        zp = H - float(p["pipe_depth"])
        if w <= zp:
            msgs.append(f"The pond ({w:g} m) is below the pipe ({zp:g} m above "
                        f"base), so no flow can enter the pipe.")
    elif w <= H - float(p["pilot_depth"]):
        msgs.append("The pond is below the pilot channel or settled crest, so no "
                    "overtopping flow can start.")
    v = storage_at(p, w)
    if v is not None and v <= 0:
        msgs.append("The stage-storage gives no storage at the initial pond level.")
    return msgs


# =====================================================================
# MODEL SETUP
# =====================================================================
def page_setup():
    # the core toggle sits on a later tab; read its state first, so the
    # tabs before it see the same case
    if "keep_in_has_core" in st.session_state:
        _core_switch(bool(st.session_state["keep_in_has_core"]))
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        with h1:
            section("Dam cross-section", "Redraws as you edit. DLBreach routes "
                    "the impoundment as clear water"
                    + ("; the tailings and cone of depression shown come from "
                       "the Tailings release page." if is_tailings() else "."))
        with h2:
            seed("keep_ve_setup", "Auto")
            ve_choice = st.selectbox("Vertical exaggeration",
                                     ["Auto", "1×", "2×", "3×", "5×", "8×", "12×", "20×", "40×"],
                                     key="keep_ve_setup", help=HLP.h("ve"))
        ve = None if ve_choice == "Auto" else float(ve_choice.rstrip("×"))
        slot = st.container()

    lt = st.session_state.get("loaded_text")
    if lt:
        d = card_differences(lt[1], build_input_text(P))
        parts = [f"{lab}: {', '.join(v)}" for lab, v in
                 (("changed", d["changed"]), ("added", d["added"]),
                  ("no longer written", d["missing"])) if v]
        if parts:
            callout("info", f"Differences from {lt[0]} as loaded.",
                    "; ".join(parts) + ". These follow from edits on this page "
                    "(or cards the dashboard adds); the Input file tab shows the "
                    "file DLBreach will read.")
    kept = [c.split(None, 1)[0] for c in P.get("extra_cards") or []]
    if kept:
        where = []
        if not P.get("write_reservoir", True):
            where.append("the upstream water level")
        if P.get("downstream_mode", "channel") != "channel":
            where.append("the downstream boundary")
        callout("note", f"This case includes {len(kept)} DLBreach card"
                f"{'s' if len(kept) != 1 else ''} the dashboard does not edit.",
                ", ".join(kept) + ". They are written to the input file exactly "
                "as loaded (see the Input file tab)."
                + (" They set " + " and ".join(where) + ", so the matching "
                   "inputs below are not used." if where else "")
                + (" The cross-section shows the clay cover; input checks do not "
                   "account for these cards." if clay_cover(P) else
                   " The cross-section and input checks do not account for them."))

    t_geo, t_mat, t_core, t_imp, t_basis, t_file = st.tabs(
        ["Geometry & breach", "Material", "Clay core (optional)",
         "Impoundment & boundaries", "Inputs & basis", "Input file"])

    with t_geo:
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            group("Embankment configuration")
            num_u("emb_height", 0.1, 500.0, 0.5)
            num_u("emb_crest_width", 0.1, 500.0, 0.5)
            num_u("emb_us_slope", 0.1, 50.0, 0.1, "%.2f")
            num_u("emb_ds_slope", 0.1, 50.0, 0.1, "%.2f")
            num_u("emb_length", 1.0, 100000.0, 1.0)
        with c2:
            group("Breach initiation")
            choice("Failure mode", "breach_mode", [1, 2],
                   fmt=lambda k: {1: "Overtopping", 2: "Piping"}[k],
                   help_=HELP["breach_mode"])
            if P["breach_mode"] == 1:
                choice("Overtopping submode", "overtopping_mode", [1, 2, 3],
                       fmt=lambda k: {1: "1 — surface erosion",
                                      2: "2 — headcut erosion",
                                      3: "3 — composite with clay core"}[k],
                       radio=False, help_=HELP["overtopping_mode"])
                if int(P["overtopping_mode"]) == 3 and not P.get("has_core"):
                    callout("warn", "Submode 3 needs a clay core.",
                            "Describe the core on the Clay core tab.")
                trig = choice("Overtopping initiated by", "ot_trigger",
                              ["pilot", "settlement"],
                              fmt=lambda k: {"pilot": "Pilot channel",
                                             "settlement": "Crest settlement"}[k],
                              help_=HLP.h("ot_trigger"))
                if trig == "settlement":
                    num_u("pilot_depth", 0.0, 50.0, 0.1,
                          label="Crest settlement height (m)",
                          help_=HLP.h("settle_depth"))
                    num_u("pilot_width", 0.0, 500.0, 1.0,
                          label="Crest settlement width (m)",
                          help_=HLP.h("settle_width"))
                else:
                    num_u("pilot_depth", 0.0, 50.0, 0.05)
                    num_u("pilot_width", 0.0, 200.0, 0.1)
                ot = P["wsl_up_initial"] - (P["emb_height"] - P["pilot_depth"])
                if ot > 0:
                    st.caption(f"Pond overtopping height: **{ot:.2f} m** above "
                               f"the {'settled crest' if trig == 'settlement' else 'pilot channel invert'}.")
                else:
                    callout("warn", "No overtopping.",
                            f"The pond is {abs(ot):.2f} m below the "
                            f"{'settled crest' if trig == 'settlement' else 'pilot channel invert'}, "
                            f"so no flow can start. Increase the "
                            f"{'settlement' if trig == 'settlement' else 'pilot channel depth'} "
                            f"or the pond level.")
            else:
                num_u("pipe_depth", 0.0, 500.0, 0.1)
                num_u("pipe_width", 0.01, 50.0, 0.01)
                P["pipe_head_loss"] = st.number_input(
                    "Pipe entrance head loss coefficient",
                    value=float(P.get("pipe_head_loss", 0.05)), step=0.01,
                    format="%.3f", help=HELP.get("pipe_head_loss"))
            choice("Breach location", "breach_location", [2.0, 1.0],
                   fmt=lambda k: {2.0: "Two-sided (mid-dam)",
                                  1.0: "One-sided (abutment)"}[k],
                   help_=HELP["breach_location"])
        with c3:
            group("Breach development")
            num_u("hard_bottom_elev", -200.0, 500.0, 0.5)
            if P.get("datum_display", "model") != "model":
                st.caption(f"= {zdisp(P['hard_bottom_elev'])}")
            num_u("manning_n", 0.005, 0.2, 0.001, "%.4f")
            if "Breach_Manning_n" in (P.get("omit_cards") or []):
                st.caption("Not used: this case sets Manning's n by segments "
                           "(Breach_Manning_n_Segments, kept as loaded).")
            st.caption(f"DLBreach report recommends "
                       f"{recommended_manning_n(P):.4f} for this material "
                       f"(field case).")
            if P["breach_mode"] == 1 and int(P["overtopping_mode"]) == 2:
                choice("Headcut formula", "headcut_model", [1, 2, 3],
                       fmt=lambda k: {1: "1 — C1[(qH)^1/3 − A0]",
                                      2: "2 — Ct·q^1/3·H^1/2 (suggested)",
                                      3: "3 — C2·(qH)^1/3"}[k],
                       radio=False, help_=HELP["headcut_model"])
                num_u("headcut_coef", 0.0, 1000.0, 0.0001, "%.4f")
            group("Time control")
            P["time_step"] = st.number_input(
                "Time step (s)", 0.1, 5.0, float(P["time_step"]), 0.1,
                help=HELP["time_step"])
            P["sim_end"] = st.number_input(
                "Simulation end time (s)", 1.0, 1e7, float(P["sim_end"]), 1000.0,
                help=HELP["sim_end"])

    with t_mat:
        m1, m2, m3 = st.columns(3, gap="large")
        with m1:
            group("Classification")
            choice("Sediment model", "sediment_type", [1, 2],
                   fmt=lambda k: {1: "Non-cohesive", 2: "Cohesive"}[k],
                   help_=HELP["sediment_type"])
            num_u("sed_d50", 0.0001, 1000.0, 0.1, "%.4f")
            num_u("sed_sg", 1.0, 5.0, 0.01)
        with m2:
            group("Porosity")
            choice("Porosity from", "porosity_from_bulk", [False, True],
                   fmt=lambda k: "Bulk unit weight" if k else "Direct entry",
                   help_=HLP.h("porosity_from_bulk"))
            if P["porosity_from_bulk"]:
                P["bulk_unit_weight"] = st.number_input(
                    "Bulk unit weight (kN/m³)", 10.0, 30.0,
                    float(P.get("bulk_unit_weight", 20.0)), 0.1,
                    help=HLP.h("bulk_unit_weight"))
                num_u("sed_saturation", 0.0, 100.0, 5.0, "%.0f")
                n = U.porosity_from_bulk(P["bulk_unit_weight"], P["sed_sg"],
                                         P["sed_saturation"])
                if n is None:
                    callout("warn", "Inconsistent inputs.",
                            "No porosity satisfies this bulk unit weight, "
                            "specific gravity and saturation.")
                else:
                    P["sed_porosity"] = round(n, 4)
                    st.caption(f"Porosity n = e/(1+e) with e = (γw·Gs − γ) / "
                               f"(γ − γw·S): **{n:.3f}**")
                    st.session_state.pop("keep_in_sed_porosity", None)
            else:
                num_u("sed_porosity", 0.01, 0.8, 0.01)
        with m3:
            group("Strength and erodibility")
            num_u("sed_clay", 0.0, 100.0, 0.5, "%.1f")
            num_u("sed_cohesion", 0.0, 1000.0, 0.5, "%.2f")
            num_u("sed_friction", 1.0, 70.0, 0.5, "%.1f")
            if P["sediment_type"] == 1:
                num_u("adaptation_lambda", 0.1, 50.0, 0.5)
                P["include_adaptation_lambda"] = st.checkbox(
                    "Write the adaptation length card",
                    value=bool(P.get("include_adaptation_lambda", True)),
                    help=HLP.h("include_adaptation_lambda"))
            else:
                num_u("kd", 0.0, 1000.0, 0.1)
                num_u("tauc", 0.0, 1000.0, 0.01)

    with t_core:
        core_tab()

    with t_imp:
        i1, i2 = st.columns([3, 2], gap="large")
        with i1:
            group("Stage-storage")
            # A case that gives the reservoir as a power law (methods 2-4)
            # opens on the power-law inputs, not on an empty table.
            if P.get("ss_source") not in ("table", "file", "power"):
                P["ss_source"] = ("power" if int(P.get("reservoir_method", 2)) in (2, 3, 4)
                                  else "table")
            src = choice("Source", "ss_source", ["table", "file", "power"],
                         fmt=lambda k: {"table": "Edit table",
                                        "file": "Upload CSV / Excel",
                                        "power": "Single level (power law)"}[k],
                         help_=HLP.h("ss_source"))
            off, lab = datum()
            if src == "file":
                st.download_button("Template (.csv)", TPL.stage_storage_template(P),
                                   file_name="stage_storage_template.csv",
                                   mime="text/csv", key="ss_tpl",
                                   help=TPL.STAGE_STORAGE_NOTE)
                f = st.file_uploader("Stage-storage file", type=["csv", "xlsx", "xls"],
                                     key="ss_upload", help=HLP.h("ss_file"))
                if f is not None:
                    df0, sheets = read_table_file(f.getvalue(), f.name)
                    if sheets and len(sheets) > 1:
                        sh = st.selectbox("Sheet", sheets,
                                          help="Worksheet holding the table.")
                        df0, _ = read_table_file(f.getvalue(), f.name, sh)
                    ge, gv = guess_columns(df0)
                    cols = [str(c) for c in df0.columns]
                    s1, s2 = st.columns(2)
                    ec = s1.selectbox("Elevation column", cols,
                                      index=cols.index(ge) if ge in cols else 0,
                                      help=HLP.h("ss_elev_col"))
                    vc = s2.selectbox("Volume column", cols,
                                      index=cols.index(gv) if gv in cols else min(1, len(cols) - 1),
                                      help=HLP.h("ss_vol_col"))
                    s3, s4 = st.columns(2)
                    vu = s3.radio("Volume units", ["m³", "Mm³"], horizontal=True,
                                  help=HLP.h("ss_vol_units"))
                    eu = s4.radio("Elevations are in", ["Site RL", "Model datum"],
                                  horizontal=True, help=HLP.h("ss_elev_datum"))
                    pairs = stage_storage_from_table(
                        df0, ec, vc, 1e6 if vu == "Mm³" else 1.0,
                        float(P.get("datum_base_rl", 0.0)) if eu == "Site RL" else 0.0)
                    for m in check_stage_storage(pairs):
                        callout("warn", "Check the table.", m)
                    st.caption(f"{len(pairs)} levels read, "
                               f"{pairs[0][0]:.2f} to {pairs[-1][0]:.2f} m above "
                               f"base." if pairs else "No numeric rows found.")
                    if pairs and st.button("Use this stage-storage", type="primary"):
                        P["res_curve"], P["reservoir_method"] = pairs, 0
                        P["_ss_ver"] = int(P.get("_ss_ver", 0)) + 1
                        st.rerun()
            elif src == "table":
                # The table is used only if the case already has one, or once
                # the user edits it. Opening it never changes a power-law
                # reservoir (methods 2-4).
                m_now = int(P.get("reservoir_method", 0))
                have = m_now in (0, 1) and bool(P.get("res_curve"))
                curve = (P["res_curve"] if have else
                         [(0.0, 0.0), (10.0, 1.0e6), (18.0, 5.0e6)])
                if not have:
                    callout("note", "Example table, not used yet.",
                            (f"This case uses a power-law reservoir (method {m_now}). "
                             if m_now in (2, 3, 4) else "")
                            + "Edit the table to use a stage-storage table instead.")
                ycol = ("Surface area (m²)" if m_now == 1 and have
                        else "Storage volume (m³)")
                tab = pd.DataFrame({f"Elevation ({lab})": [z + off for z, _ in curve],
                                    ycol: [v for _, v in curve]})
                # The editor is keyed by a version number. Its edits are
                # committed to the parameters and the version moves on, so the
                # next run starts a fresh editor from the committed table rather
                # than re-applying the same edits (which would duplicate added
                # rows).
                ver = int(P.get("_ss_ver", 0))
                st.caption("Level against "
                           + ("surface area (method 1, as loaded)" if ycol.startswith("Surface")
                              else "stored volume")
                           + ", one row per level. Add rows at the bottom; values "
                             "must increase with level.")
                ed = st.data_editor(tab, num_rows="dynamic",
                                    use_container_width=True,
                                    key=f"ss_editor_{ver}_{off}", height=260)
                try:
                    new = sorted({round(float(a) - off, 6): float(b)
                                  for a, b in ed.dropna().itertuples(index=False)}.items())
                    if new and new != sorted((round(z, 6), v) for z, v in curve):
                        P["res_curve"] = new
                        P["reservoir_method"] = m_now if have else 0
                        P["_ss_ver"] = ver + 1
                        st.rerun()
                except (TypeError, ValueError):
                    callout("warn", "Check the table.", "Every cell must be a number.")
                for m in check_stage_storage(P.get("res_curve") or []):
                    callout("warn", "Check the table.", m)
            else:
                ml = {2: "2 — volume and area at a level",
                      3: "3 — volume at a level, exponent m",
                      4: "4 — area at a level, exponent m"}
                # As with the table: opening these inputs on a case that has a
                # stage-storage table (methods 0 and 1) changes nothing until
                # the user changes one of them.
                m_now = int(P.get("reservoir_method", 2))
                using = m_now in ml
                if not using:
                    callout("note", "Example values, not used yet.",
                            f"This case uses a stage-storage table (method {m_now}). "
                            "Change a value below to use a single level instead.")
                before = tuple(P.get(k) for k in ("res_VH", "res_AH", "res_H", "res_m"))
                rm = st.selectbox(
                    "Method", list(ml), index=list(ml).index(m_now if using else 2),
                    format_func=lambda k: ml[k], help=HELP["reservoir_method"])
                if rm in (2, 3):
                    num_u("res_VH", 0.0, 1e12, 1000.0, "%.1f")
                if rm in (2, 4):
                    P["res_AH"] = st.number_input("Surface area at level H (m²)",
                                                  value=float(P.get("res_AH", 0)),
                                                  step=1000.0, format="%.1f",
                                                  help=HELP["res_AH"])
                P["res_H"] = st.number_input("Reference level H (m above base)",
                                             value=float(P.get("res_H", 0)), step=0.5,
                                             help=HELP["res_H"])
                if rm in (3, 4):
                    P["res_m"] = st.number_input("Exponent m", 1.0, 3.0,
                                                 float(P.get("res_m", 2.0)), 0.05,
                                                 help=HELP["res_m"])
                after = tuple(P.get(k) for k in ("res_VH", "res_AH", "res_H", "res_m"))
                if using or rm != 2 or after != before:
                    P["reservoir_method"] = rm
            num_u("wsl_up_initial", 0.0, 500.0, 0.1)
            if P.get("datum_display", "model") != "model":
                st.caption(f"= {zdisp(P['wsl_up_initial'])}")
        with i2:
            group("Stage-storage curve")
            if int(P.get("reservoir_method", 0)) in (0, 1) and P.get("res_curve"):
                cv = pd.DataFrame({"x": [v / 1e6 for _, v in P["res_curve"]],
                                   "y": [z + off for z, _ in P["res_curve"]],
                                   "Series": "Stage-storage"})
                chart(cv, "Storage (Mm³)", f"Elevation ({lab})", "sscurve")
            group("Downstream boundary")
            P["ds_channel_width"] = st.number_input(
                "Channel width (m)", 0.1, 1e5, float(P["ds_channel_width"]), 1.0,
                help=HELP["ds_channel_width"])
            P["ds_channel_slope"] = st.number_input(
                "Channel slope (m/m)", 1e-5, 1.0, float(P["ds_channel_slope"]), 0.001,
                format="%.4f", help=HELP["ds_channel_slope"])
            P["ds_channel_n"] = st.number_input(
                "Channel Manning n", 0.005, 0.2, float(P["ds_channel_n"]), 0.001,
                format="%.3f", help=HELP["ds_channel_n"])
            P["wsl_down_initial"] = st.number_input(
                "Initial downstream water level (m above base)", 0.0, 500.0,
                float(P["wsl_down_initial"]), 0.01, help=HELP["wsl_down_initial"])

    with t_basis:
        st.caption("Inputs as they will appear in the report appendix. Add the "
                   "basis or reference for each value in the last column.")
        tab = inputs_table()
        bkey = "basis_" + str(abs(hash(tuple(tab["Parameter"]))) % 10**8)
        ed = st.data_editor(tab, use_container_width=True, hide_index=True,
                            disabled=["Parameter", "Value", "Unit"],
                            key=bkey, height=520)
        P["basis"] = {r["Parameter"]: r["Basis / reference"]
                      for r in ed.to_dict("records")
                      if isinstance(r.get("Basis / reference"), str)
                      and r["Basis / reference"].strip()}

    with t_file:
        txt = build_input_text(P)
        st.caption("Exactly what is written to casename.txt and passed to DLBreach.")
        st.code(txt, language="text")
        st.download_button("Download input file", txt.encode(),
                           file_name=f"{P['case_name']}.txt", mime="text/plain")

    with st.container(border=True):
        section("Input guidance check", "Compares the inputs with the "
                "recommendations in the DLBreach technical report (Wu 2016).")
        probs = list(water_checks())
        if P["wsl_up_initial"] > P["emb_height"]:
            probs.append("Initial pond level is above the crest.")
        if P["breach_mode"] == 2 and P["pipe_depth"] > P["emb_height"]:
            probs.append("Pipe depth exceeds the embankment height.")
        core_on = int(P["breach_mode"]) == 1 and int(P["overtopping_mode"]) == 3
        if core_on and not P.get("has_core"):
            probs.append("Overtopping submode 3 is for an embankment with a clay "
                         "core, but no core is described (Clay core tab).")
        if P.get("has_core"):
            probs += core_outside(P)
        for m in probs:
            callout("warn", "Inconsistent input.", m)
        cautions = []
        if P.get("has_core") and not core_on:
            cautions.append(("Clay core not used in this mode.",
                             "The DLBreach file format guide describes the core "
                             "cards for overtopping submode 3 (Wu 2016). They are "
                             "written to the file, but with the current failure "
                             "mode the core may not be modelled."))
        if (P.get("write_reservoir", True)
                and int(P.get("reservoir_method", 0)) in (0, 1) and P.get("res_curve")):
            lo = min(z for z, _ in P["res_curve"])
            if P["hard_bottom_elev"] < lo - 1e-6:
                cautions.append(("Erosion limit below the stage-storage table.",
                                 f"The breach can erode below the lowest level in "
                                 f"the table ({lo:g} m above base). If the pond "
                                 f"falls below that level, DLBreach works outside "
                                 f"the table. Extend the table down to the erosion "
                                 f"limit where storage data allow."))
        for lead, body in cautions:
            callout("note", lead, body)
        g = dlbreach_guidance(P, field=True)
        if not g and not probs and not cautions:
            callout("ok", "No departures found.", "")
        for x in g:
            callout("note", f"{x['Parameter']}: {x['Entered']} entered, "
                            f"{x['Recommended']} recommended.",
                    f"{x['Basis']} {x['Effect']}")

    with slot:
        svg = cross_section_svg(PD({"_cone": cone_overlay()}), ve_override=ve)
        components.html(FONT_LINK + svg, height=svg_height(svg) + 12, scrolling=False)


CORE_FIELDS = ["core_height", "core_crest_width", "core_us_slope", "core_ds_slope",
               "core_center", "core_manning_n", "core_sed_type", "core_d50",
               "core_sg", "core_porosity", "core_clay", "core_cohesion",
               "core_friction", "core_kd", "core_tauc"]


def _core_switch(on: bool):
    """Apply the clay core toggle. A core switched on starts inside the
    embankment, just below the crest."""
    if on and not P.get("has_core"):
        if float(P.get("core_height", 0)) >= float(P["emb_height"]):
            P["core_height"] = round(0.9 * float(P["emb_height"]), 2)
        for k in CORE_FIELDS:
            for pre in ("keep_in_", "_model_keep_in_", "_clamped_keep_in_"):
                st.session_state.pop(pre + k, None)
    P["has_core"] = on


def core_tab():
    """Clay core inputs (Wu 2016, Clay Core Parameters), for overtopping
    submode 3. A case without a core writes none of these cards."""
    if "keep_in_has_core" not in st.session_state:
        st.session_state["keep_in_has_core"] = bool(P.get("has_core"))
    _core_switch(st.toggle("The embankment has a clay core",
                           key="keep_in_has_core", help=HELP["has_core"]))
    if not P["has_core"]:
        st.caption("No core: none of the core cards is written. Turn this on to "
                   "describe a composite embankment for overtopping submode 3.")
        return
    from dlbreach_io import CORE_CARDS
    card_of = {k: c for c, k, _ in CORE_CARDS}
    before = {k: P.get(k) for k in CORE_FIELDS}
    mode3 = int(P["breach_mode"]) == 1 and int(P["overtopping_mode"]) == 3
    if not mode3:
        callout("note", "Used with overtopping submode 3.",
                "Choose Overtopping, submode 3 on the Geometry & breach tab for "
                "DLBreach to model the core (Wu 2016).")
    k1, k2, k3 = st.columns(3, gap="large")
    with k1:
        group("Core geometry")
        num_u("core_height", 0.01, 500.0, 0.5)
        num_u("core_crest_width", 0.0, 500.0, 0.5)
        num_u("core_us_slope", 0.01, 50.0, 0.05, "%.3f")
        num_u("core_ds_slope", 0.01, 50.0, 0.05, "%.3f")
        num_u("core_center", -1000.0, 1000.0, 0.5)
        poly = core_polygon(P)
        if poly:
            st.caption(f"Drawn standing on the embankment base: base width "
                       f"{poly[3][0] - poly[0][0]:,.2f} m, crest "
                       f"{float(P['emb_height']) - poly[1][1]:,.2f} m below the "
                       f"embankment crest.")
    with k2:
        group("Core material")
        choice("Core sediment model", "core_sed_type", [1, 2],
               fmt=lambda k: {1: "Non-cohesive", 2: "Cohesive"}[k],
               help_=HELP["core_sed_type"])
        num_u("core_d50", 0.0001, 1000.0, 0.01, "%.4f")
        num_u("core_sg", 1.0, 5.0, 0.01)
        num_u("core_porosity", 0.01, 0.8, 0.01)
        num_u("core_clay", 0.0, 100.0, 0.5, "%.1f")
    with k3:
        group("Strength and erodibility")
        num_u("core_cohesion", 0.0, 1000.0, 0.5, "%.2f")
        num_u("core_friction", 1.0, 70.0, 0.5, "%.1f")
        num_u("core_manning_n", 0.005, 0.2, 0.001, "%.4f")
        if int(P["core_sed_type"]) == 2:
            num_u("core_kd", 0.0, 1000.0, 0.1)
            num_u("core_tauc", 0.0, 1000.0, 0.01)
        elif "Core_Cohesive_Erosion_kd" in (P.get("core_cards") or []):
            st.caption("Core kd and τc are kept as loaded; DLBreach uses them "
                       "for a cohesive core only.")
    # a loaded core writes the cards its file gave; a field edited here is
    # written from then on (and kd and tauc once the core is made cohesive)
    if P.get("core_cards"):
        cards = list(P["core_cards"])
        for k in CORE_FIELDS:
            if P.get(k) != before[k] and card_of[k] not in cards:
                cards.append(card_of[k])
        if int(P["core_sed_type"]) == 2 and before["core_sed_type"] != 2:
            cards += [c for c in ("Core_Cohesive_Erosion_kd",
                                  "Core_Cohesive_Erosion_Tauc") if c not in cards]
        P["core_cards"] = cards
        unused = [c for c, k, _ in CORE_CARDS if c not in cards
                  and not (k in ("core_kd", "core_tauc")
                           and int(P["core_sed_type"]) != 2)]
        if unused:
            st.caption("Not in the loaded file, so not written (DLBreach uses its "
                       "own value): " + ", ".join(unused) + ". Edit a field to "
                       "write it.")
    for m in core_outside(P):
        callout("warn", "Check the core.", m)


def inputs_table() -> pd.DataFrame:
    """Model inputs in practitioner units, with the user's basis notes."""
    off, lab = datum()
    rows = [("Embankment height", P["emb_height"], "m"),
            ("Crest width", P["emb_crest_width"], "m"),
            ("Upstream slope", f"{1 / P['emb_us_slope']:.2f}H:1V", ""),
            ("Downstream slope", f"{1 / P['emb_ds_slope']:.2f}H:1V", ""),
            ("Embankment length", P["emb_length"], "m"),
            ("Crest elevation", round(P["emb_height"] + off, 3), lab),
            ("Failure mode", "Overtopping" if int(P["breach_mode"]) == 1
             else "Piping", "")]
    if int(P["breach_mode"]) == 2:
        rows += [("Pipe elevation",
                  round(P["emb_height"] - P["pipe_depth"] + off, 3), lab),
                 ("Initial pipe width", P["pipe_width"], "m")]
    else:
        rows += [("Pilot channel depth", P["pilot_depth"], "m"),
                 ("Pilot channel width", P["pilot_width"], "m")]
    rows += [("Erosion limit", round(P["hard_bottom_elev"] + off, 3), lab),
             ("Initial pond level", round(P["wsl_up_initial"] + off, 3), lab),
             ("Median grain size D50", round(P["sed_d50"] * 1000, 4), "mm"),
             ("Specific gravity", P["sed_sg"], ""),
             ("Porosity", P["sed_porosity"], "")]
    if P.get("porosity_from_bulk"):
        rows += [("Bulk unit weight", P["bulk_unit_weight"], "kN/m³"),
                 ("Degree of saturation", round(P["sed_saturation"] * 100, 1), "%")]
    rows += [("Clay size fraction", round(P["sed_clay"] * 100, 2), "%"),
             ("Cohesion", round(P["sed_cohesion"] / 1000, 3), "kPa"),
             ("Internal friction angle",
              round(float(np.degrees(np.arctan(P["sed_friction"]))), 1), "°"),
             ("Breach Manning n", P["manning_n"], ""),
             ("Sediment model", "Non-cohesive" if int(P["sediment_type"]) == 1
              else "Cohesive", "")]
    if int(P["sediment_type"]) == 2:
        rows += [("Erodibility kd", P["kd"], "cm³/N·s"),
                 ("Critical shear stress", P["tauc"], "Pa")]
    if P.get("has_core"):
        rows += [("Core height", P["core_height"], "m"),
                 ("Core crest width", P["core_crest_width"], "m"),
                 ("Core upstream slope", f"{1 / P['core_us_slope']:.2f}H:1V", ""),
                 ("Core downstream slope", f"{1 / P['core_ds_slope']:.2f}H:1V", ""),
                 ("Core offset from crest centre", P["core_center"],
                  "m, + downstream"),
                 ("Core D50", round(P["core_d50"] * 1000, 4), "mm"),
                 ("Core specific gravity", P["core_sg"], ""),
                 ("Core porosity", P["core_porosity"], ""),
                 ("Core clay size fraction", round(P["core_clay"] * 100, 2), "%"),
                 ("Core cohesion", round(P["core_cohesion"] / 1000, 3), "kPa"),
                 ("Core internal friction angle",
                  round(float(np.degrees(np.arctan(P["core_friction"]))), 1), "°"),
                 ("Core Manning n", P["core_manning_n"], ""),
                 ("Core sediment model", "Non-cohesive"
                  if int(P["core_sed_type"]) == 1 else "Cohesive", "")]
        if int(P["core_sed_type"]) == 2:
            rows += [("Core erodibility kd", P["core_kd"], "cm³/N·s"),
                     ("Core critical shear stress", P["core_tauc"], "Pa")]
    basis = P.get("basis", {})
    return pd.DataFrame([(a, f"{b:,.6g}" if isinstance(b, float) else str(b), c,
                          basis.get(a, "")) for a, b, c in rows],
                        columns=["Parameter", "Value", "Unit", "Basis / reference"])


# =====================================================================
# TAILINGS RELEASE (tailings and CCR only)
# =====================================================================
def tl_for(df, p: dict | None = None) -> dict | None:
    """Tailings released with a run, for solid waste dams; None otherwise."""
    if df is None or not is_tailings() or not P.get("tl", {}).get("method"):
        return None
    return tailings_for_run(df, p or P, P["tl"])


def page_tailings():
    tl = P.setdefault("tl", {})
    tl.setdefault("method", "fm")
    df = st.session_state.result_df

    def tnum(label, key, default, step, fmt=None, help_=None, lo=None, hi=None):
        wk = f"keep_in_tl_{key}"
        if wk not in st.session_state:
            st.session_state[wk] = float(tl.get(key, default))
        tl[key] = st.number_input(label, min_value=lo, max_value=hi, step=step,
                                  format=fmt, key=wk, help=help_)
        return tl[key]

    callout("info", "What this page does.",
            "DLBreach routes the impoundment as clear water. This page estimates "
            "the tailings (or ash) released with that water, by one of three "
            "methods used in practice, and the resulting bulked hydrograph. "
            "These calculations sit outside DLBreach and use the latest Single "
            "run.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            section("Free water")
            seed("keep_tl_src", tl.get("water_source", "run"))
            src = st.radio("Free water volume", ["run", "manual"], key="keep_tl_src",
                           horizontal=True,
                           format_func=lambda k: {"run": "From the DLBreach run",
                                                  "manual": "Enter pond and flood"}[k])
            tl["water_source"] = src
            if src == "manual":
                tnum("Supernatant pond volume (m³)", "pond_m3", 1.0e6, 1e4, "%.0f", lo=0.0)
                tnum("Flood inflow volume (m³)", "flood_m3", 0.0, 1e4, "%.0f", lo=0.0)
            elif df is not None:
                st.caption(f"The latest run released "
                           f"{float(df['cum_volume'].iloc[-1]):,.0f} m³ of water.")
            else:
                st.caption("No run yet: run the model on Single run.")
        with st.container(border=True):
            section("Stored tailings")
            tnum("Mass of solids stored (t)", "solids_t", 1.0e7, 1e5, "%.0f", lo=1.0)
            tnum("Average dry density (t/m³)", "dry_density", 1.4, 0.05, "%.2f",
                 lo=0.3, hi=3.0)
            tnum("Specific gravity of solids", "sg", 2.7, 0.01, "%.2f", lo=1.5, hi=5.0)
            tnum("Degree of saturation (%)", "sat_pct", 100.0, 5.0, "%.0f",
                 lo=0.0, hi=100.0)
            tnum("Tailings beach level at the dam (m above base)", "beach_level",
                 min(float(P["wsl_up_initial"]), float(P["emb_height"])) - 2.0,
                 0.1, "%.2f")
            st.caption(f"= {zdisp(tl['beach_level'])}")
            free_now = (float(df["cum_volume"].iloc[-1]) if (df is not None and src == "run")
                        else tl.get("pond_m3", 0.0) + tl.get("flood_m3", 0.0))
            cv = insitu_cv(free_now, 0.0, tl["solids_t"], tl["dry_density"],
                           tl["sg"], tl["sat_pct"] / 100)
            if cv:
                tiles([("Stored tailings", f"{cv['tailings_m3'] / 1e6:,.2f} Mm³"),
                       ("In-situ Cw", f"{cv['Cw'] * 100:,.0f} %"),
                       ("In-situ Cv", f"{cv['Cv'] * 100:,.0f} %",
                        "if all contents mixed")])
                st.caption("Cw = 1/(WC+1), Cv = Cw/(SG + (1−SG)·Cw), with WC the "
                           "ratio of all water to solids. An upper bound for a "
                           "breach flow.")

    with c2:
        with st.container(border=True):
            section("Release method")
            method = choice("Method", "tl_method", ["fm", "cone", "ratio"],
                            fmt=lambda k: {"fm": "Fontaine and Martin (2015)",
                                           "cone": "Cone of depression",
                                           "ratio": "Ratio of free water"}[k])
            tl["method"] = method
            if method == "fm":
                seed("keep_tl_fm_basis", "Cw")
                basis = st.radio("Specify the outflow by", ["Cw", "Cv"],
                                 horizontal=True, key="keep_tl_fm_basis",
                                 format_func=lambda k: {"Cw": "Solids content by weight",
                                                        "Cv": "Solids concentration by volume"}[k])
                if basis == "Cw":
                    tnum("Solids content of the outflow by weight, Cw (%)",
                         "fm_cw", 50.0, 1.0, "%.1f", lo=1.0, hi=95.0)
                else:
                    cvv = tnum("Solids concentration of the outflow by volume, Cv (%)",
                               "fm_cv", 25.0, 1.0, "%.1f", lo=1.0, hi=70.0)
                    tl["fm_cw"] = cw_from_cv(cvv / 100, tl["sg"]) * 100
                    st.caption(f"Equivalent Cw = {tl['fm_cw']:.1f} %")
                with st.expander("Equations (Fontaine and Martin 2015)", expanded=False):
                    for lab, eq in (
                        ("Eq. 12 — solids content of the outflow",
                         r"\%s = \frac{M_{S\text{-}MOB}}{M_{S\text{-}MOB}+M_{IW\text{-}MOB}+M_W}"),
                        ("Eq. 13 — mobilised solids (valid for %w < 1/%s − 1)",
                         r"M_{S\text{-}MOB} = \frac{M_W}{(1/\%s) - 1 - \%w}"),
                        ("Eq. 14 — mobilised interstitial water",
                         r"M_{IW\text{-}MOB} = \left(\frac{M_{S\text{-}MOB}}{\rho_D}-"
                         r"\frac{M_{S\text{-}MOB}}{\rho_S}\right) S\,\rho_W"),
                        ("Eq. 15 — volume of mobilised tailings",
                         r"V_{T\text{-}MOB} = \frac{M_{S\text{-}MOB}+M_{IW\text{-}MOB}}{\rho_{BULK}}"),
                        ("Eq. 16 — breach outflow volume",
                         r"V_{OUT} = V_W + V_{T\text{-}MOB}"),
                        ("Eq. 17 — share of the impoundment released",
                         r"\%V_{OUT} = \frac{V_{OUT}}{V_W + V_T}")):
                        st.markdown(f"**{lab}**")
                        st.latex(eq)
                    st.caption("%s is the solids content by weight of the outflow "
                               "and %w the water content of the stored tailings. "
                               "Mobilised solids are capped at the solids stored.")
            elif method == "cone":
                tnum("Post-failure slope β (°)", "cone_slope_deg", 4.0, 0.25, "%.2f",
                     "CDA (2021) reports 2–5° (3.5–9 %) from past failures, and "
                     "asks for site-specific judgement.", lo=0.5, hi=20.0)
                seed("keep_tl_cw", tl.get("cone_width", "bottom"))
                tl["cone_width"] = st.radio("Breach width at the apex", ["bottom", "top"],
                                            key="keep_tl_cw", horizontal=True,
                                            format_func=lambda k: k.title() + " width")
                tnum("Maximum backscarp distance (m, 0 = none)", "cone_lmax", 0.0,
                     10.0, "%.0f", lo=0.0)
                tl["show_cone"] = st.checkbox("Show the cone on the cross-section",
                                              value=bool(tl.get("show_cone", True)))
                st.caption("The cone follows the breach: its height is the tailings "
                           "beach minus the breach invert at each time step, and its "
                           "apex width is the breach width DLBreach reports then. "
                           "The cone sets the volume of tailings mobilised; the "
                           "rate it grows sets the tailings release rate.")
                with st.expander("Equations and interpretation"):
                    st.latex(r"L(t)=\frac{h(t)}{\tan\beta},\qquad h(t)=z_{beach}-z_b(t)")
                    st.latex(r"V(t)=\tfrac12\,B(t)\,L(t)\,h(t)+\frac{\pi\,h(t)^3}{6\tan^2\beta}")
                    callout("note", "Interpretation required.",
                            "CDA (2021) gives the cone of depression as a schematic "
                            "(Figure A.1) and applies it to liquefied and slumped "
                            "volumes. The half-cone form is the practice convention; "
                            "following it through time with the DLBreach breach, and "
                            "taking its growth as the release rate, is this "
                            "dashboard's construction.")
            else:
                tnum("Tailings released as a fraction of free water", "ratio", 0.30,
                     0.05, "%.2f", lo=0.0, hi=5.0)
                st.caption("A fixed proportion of the free water, as used in some "
                           "practice.")

    r = tl_for(df)
    with st.container(border=True):
        section("Release")
        if df is None:
            callout("info", "No run yet.", "Run the model on Single run; the release "
                    "is calculated from that run.")
        elif not r or not r.get("ok"):
            callout("warn", "Nothing released.", (r or {}).get("note", ""))
        else:
            tiles([("Free water", f"{r['free_water_m3'] / 1e6:,.3f} Mm³"),
                   ("Tailings released", f"{r['tailings_m3'] / 1e6:,.3f} Mm³",
                    f"solids {r['solids_m3'] / 1e6:,.3f} · water "
                    f"{r['interstitial_m3'] / 1e6:,.3f}"),
                   ("Total release", f"{r['total_m3'] / 1e6:,.3f} Mm³", None, True),
                   ("Bulking factor", f"{r['bulking']:,.2f}"),
                   ("Peak, bulked", f"{r['peak_total']:,.0f} m³/s",
                    f"water {df['Q_breach'].max():,.0f}")])
            if r.get("note"):
                st.caption(r["note"])
            h = pd.DataFrame({"t": df["time_hr"], "w": df["Q_breach"],
                              "s": r["Q_tailings"], "tot": r["Q_total"]})
            chart(series_long(h, "t", {"w": "Water (DLBreach)", "s": "Tailings",
                                       "tot": "Total (bulked)"}),
                  "Time (h)", "Discharge (m³/s)", "tl_hydro")

    with st.container(border=True):
        section("Sensitivity: tailings in the stage-storage",
                "A bounding sensitivity used in practice: route the cone of "
                "depression through DLBreach as if it were water, on top of the "
                "pond.")
        cone = cone_overlay()
        if not cone:
            st.caption("Choose the cone of depression method and show it on the "
                       "cross-section to enable this.")
        else:
            a1, a2 = st.columns(2)
            if a1.button("Apply cone to stage-storage"):
                if "res_curve_original" not in st.session_state:
                    st.session_state.res_curve_original = (
                        int(P.get("reservoir_method", 0)), list(P.get("res_curve") or []))
                P["res_curve"] = combined_stage_storage(P, cone, 1.0, storage_at)
                P["reservoir_method"] = 0
                P["_ss_ver"] = int(P.get("_ss_ver", 0)) + 1
                st.rerun()
            if "res_curve_original" in st.session_state and a2.button("Restore original"):
                m0, c0 = st.session_state.pop("res_curve_original")
                P["reservoir_method"], P["res_curve"] = m0, c0
                P["_ss_ver"] = int(P.get("_ss_ver", 0)) + 1
                st.rerun()

    with st.container(border=True):
        section("References")
        for k in ("fontaine2015", "cda2021"):
            st.markdown(DATA.CITATIONS[k])


# =====================================================================
# SINGLE RUN
# =====================================================================
def _step_face(delta, n, to=None):
    cur = int(st.session_state.get("keep_face_idx", n - 1))
    st.session_state.keep_face_idx = to if to is not None else max(0, min(n - 1, cur + delta))


def hydrograph_csv(df: pd.DataFrame, tr: dict | None) -> bytes:
    """Time series for inundation modelling: hours, minutes, water discharge,
    and for solid waste dams the tailings and total (bulked) discharge."""
    out = pd.DataFrame({"time_h": df["time_hr"].round(5),
                        "time_min": (df["time_hr"] * 60).round(3),
                        "Q_water_m3s": df["Q_breach"].round(3)})
    if tr:
        out["Q_tailings_m3s"] = np.round(tr["Q_tailings"], 3)
        out["Q_total_m3s"] = np.round(tr["Q_total"], 3)
    return out.to_csv(index=False).encode()


def page_single():
    exe_path, exe_ok = exe_status()
    with st.container(border=True):
        section("Deterministic run", "Runs DLBreach once with the Model setup "
                "configuration, or loads an existing output file.")
        cA, cB = st.columns([1, 3], gap="large")
        with cA:
            if BROWSER:
                go = False
                st.download_button("1 · Download input file",
                                   build_input_text(P).encode(),
                                   file_name=f"{P['case_name'] or 'case'}.txt",
                                   mime="text/plain", use_container_width=True)
                st.caption("2 · Run it with DLBreach"
                           + (" (with " + ", ".join(P.get("data_file_refs")) + " in "
                              "the same folder)" if P.get("data_file_refs") else "")
                           + ".  3 · Upload the .out file.")
            else:
                blocked = water_checks()
                go = st.button("Run DLBreach", type="primary",
                               disabled=not exe_ok or bool(blocked),
                               use_container_width=True)
                if not exe_ok:
                    st.caption("Set the executable on the Project page.")
                elif blocked:
                    st.caption("The warning below says why. Fix it on Model setup.")
        with cB:
            up = st.file_uploader("Or load an existing .out file",
                                  type=["out", "txt", "csv"], key="out_loader",
                                  help="A casename.out file written by DLBreach. "
                                       "Its results are shown as they are; they "
                                       "may not match the inputs on Model setup.")
        if go:
            with st.spinner("Running DLBreach…"):
                res = run_case(exe_path, build_input_text(P),
                               case_name=P["case_name"] or "case",
                               data_files=P.get("data_files"))
            try:
                if not res["ok"]:
                    callout("warn", "The run did not produce an output file.", "")
                    st.code((res["stdout"] or "") + "\n" + (res["stderr"] or ""))
                else:
                    try:
                        st.session_state.result_df = parse_out(res["out_path"])
                        st.session_state.result_sig = input_signature()
                        st.session_state.keep_face_idx = len(thin(st.session_state.result_df)) - 1
                    except ValueError:
                        callout("warn", "DLBreach finished but wrote no results.",
                                "Its output file has no data rows. The messages "
                                "it printed are below.")
                        st.code((res["stdout"] or "") + "\n" + (res["stderr"] or ""))
            finally:
                if res.get("created_temp"):
                    # the run folder holds a copy of the inputs: remove it
                    import shutil as _sh
                    _sh.rmtree(res["work_dir"], ignore_errors=True)
        if up is not None:
            sig = (up.name, up.size)
            if st.session_state.get("out_sig") != sig:
                try:
                    # read through a temporary file that is deleted at once,
                    # so nothing uploaded is left in the dashboard folder
                    import tempfile as _tf
                    with _tf.TemporaryDirectory(prefix="dlb_up_") as _td:
                        tmp = Path(_td) / "uploaded.out"
                        tmp.write_bytes(up.getvalue())
                        st.session_state.result_df = parse_out(tmp)
                    st.session_state.result_sig = None
                    st.session_state.out_sig = sig
                    st.session_state.keep_face_idx = len(thin(st.session_state.result_df)) - 1
                except Exception as exc:              # noqa: BLE001
                    callout("warn", "Could not read that file.", str(exc))

    for m in water_checks():
        callout("warn", "Nothing will be released.", m)
    df = st.session_state.result_df
    if df is None:
        callout("info", "No results yet.", "Run the model above, or load an output file.")
        return
    stale_notice()
    if float(df["Q_breach"].max()) <= 0:
        callout("warn", "This run released no water.",
                "Check the pond level against the breach on Model setup.")
    s = summarise(df, crest_elev=P.get("emb_height"))
    ved = eroded_dam_volume(P, s["final_bottom_width_m"], s["final_bottom_elev_m"],
                            s["final_side_slope"])
    tr = tl_for(df)
    tr = tr if (tr and tr.get("ok")) else None
    wsub = "water" if is_tailings() else None
    items = [("Peak outflow", f"{s['peak_outflow_m3s']:,.0f} m³/s", wsub, True),
             ("Time to peak", f"{s['time_to_peak_hr']:.2f} h"),
             ("Breach height", f"{s['max_breach_depth_m']:,.2f} m", "crest to invert"),
             ("Final top width", f"{s['final_top_width_m']:,.1f} m"),
             ("Eroded embankment", f"{ved:,.0f} m³"),
             ("Release volume", f"{s['total_outflow_volume_m3']:,.0f} m³", wsub)]
    if tr:
        items.insert(1, ("Bulked peak", f"{tr['peak_total']:,.0f} m³/s",
                         f"tailings {tr['tailings_m3'] / 1e6:,.2f} Mm³", True))
    tiles(items, cols=len(items))

    plot_df = thin(df)
    off, lab = datum()
    with st.container(border=True):
        section("Breach outflow hydrograph", "Discharge through the breach as "
                "DLBreach computes it. Download it for inundation modelling.")
        cols = {"Q_breach": "Breach outflow"}
        h = df.copy()
        if tr:
            h["Q_bulked"] = tr["Q_total"]
            cols["Q_bulked"] = "Total, bulked"
        tv = t_view([(df["time_hr"], df["Q_breach"])])
        chart(series_long(thin(h), "time_hr", cols), "Time (h)", "Discharge (m³/s)",
              "hydro", x_auto_max=tv)
        st.download_button("Download hydrograph for inundation modelling (.csv)",
                           hydrograph_csv(df, tr),
                           file_name=f"{P['case_name'] or 'case'}_hydrograph.csv",
                           mime="text/csv")
        g1, g2 = st.columns(2, gap="large")
        with g1:
            st.markdown("**Breach widths**  \nTop width at the crest; bottom "
                        "width at the invert.")
            chart(series_long(plot_df, "time_hr", {"breach_bottom_width": "Bottom width",
                                                   "breach_top_width": "Top width"}),
                  "Time (h)", "Width (m)", "widths", x_auto_max=tv)
        with g2:
            st.markdown("**Pond level and breach invert**  \nThe breach stops "
                        "cutting down at the erosion limit.")
            e = plot_df.copy()
            e["wsl_up"] += off
            e["breach_bottom_elev"] += off
            chart(series_long(e, "time_hr", {"wsl_up": "Pond level",
                                             "breach_bottom_elev": "Breach invert"}),
                  "Time (h)", f"Elevation ({lab})", "levels", x_auto_max=tv)

    with st.container(border=True):
        f1, f2 = st.columns([3, 1])
        with f1:
            section("Breach geometry, looking upstream from downstream",
                    ("For piping, the pipe enlarges with the crest intact until the "
                     "roof collapses; the breach then cuts down to the erosion limit "
                     "(red dashed) and widens. " if int(P["breach_mode"]) == 2 else
                     "The breach cuts down to the erosion limit (red dashed) and "
                     "widens. ")
                    + ("One-sided breach (Breach_Location 1): one side is not "
                       "erodible, so the breach is drawn against the left-hand "
                       "abutment and widens to the right only (Wu 2016)."
                       if float(P.get("breach_location", 2.0)) < 1.5 else
                       "Two-sided breach (Breach_Location 2): centred on the crest, "
                       "widening both ways."))
            st.markdown(
                "<div class='dlb-note'><b>Why the water in the breach is below "
                "the pond.</b> DLBreach takes the flow depth at the breach as the "
                "larger of two values (Wu 2016, Eq. 3.5): the critical depth over "
                "a broad-crested weir, two-thirds of the pond's height above the "
                "invert; or the average of the pond and tailwater heights above "
                "the invert. Water accelerates out of the pond, so its surface "
                "drops through the breach. While the tailwater (dotted) is low, "
                "the critical depth governs; once the tailwater rises past "
                "one-third of the pond's height above the invert, the average "
                "governs and the flow depth steps up. <i>Depth set by</i> in the "
                "readout shows which applies.</div>", unsafe_allow_html=True)
        with f2:
            seed("keep_face_ve", "Auto")
            fv = st.selectbox("Vertical exaggeration",
                              ["Auto", "1×", "2×", "5×", "10×", "20×", "40×"],
                              key="keep_face_ve", help=HLP.h("ve"))
        ve_f = None if fv == "Auto" else float(fv.rstrip("×"))
        if st.toggle("Play as animation", value=False, help=HLP.h("face_play")):
            a = breach_animation_html(PD(), plot_df, ve_override=ve_f)
            components.html(FONT_LINK + a, height=animation_height(a), scrolling=False)
        else:
            n = len(plot_df)
            seed("keep_face_idx", n - 1)
            st.session_state.keep_face_idx = int(min(max(st.session_state.keep_face_idx, 0), n - 1))
            b = st.columns([1, 1, 1, 1, 8])
            b[0].button("⏮", on_click=_step_face, args=(None, n, 0), key="fb0")
            b[1].button("◀", on_click=_step_face, args=(-1, n), key="fb1")
            b[2].button("▶", on_click=_step_face, args=(1, n), key="fb2")
            b[3].button("⏭", on_click=_step_face, args=(None, n, n - 1), key="fb3")
            m = st.select_slider("Hydrograph time", options=list(range(n)),
                                 key="keep_face_idx", help=HLP.h("face_time"),
                                 format_func=lambda i: f"{plot_df.iloc[i]['time_hr']:.2f} h")
            state = plot_df.iloc[m].to_dict()
            svg = breach_face_svg(PD(), state, ve_override=ve_f)
            components.html(FONT_LINK + svg, height=svg_height(svg) + 12, scrolling=False)
            w = check_breach_consistency(P, state)
            if w:
                callout("warn", "Geometry check.", w)

    with st.container(border=True):
        section("Breach geometry development — text export",
                "Tab-delimited: widths, invert, depth, side slope, pond level, "
                "discharge and volume through time, with a stage column marking "
                "the pre-collapse pipe phase. Elevations in the display datum.")
        e1, e2 = st.columns([1, 3])
        seed("keep_geom_interval", 5.0)
        iv = e1.number_input("Interval (min)", min_value=0.1, step=1.0,
                             key="keep_geom_interval", help=HLP.h("geom_interval"))
        txt = BATCH.geometry_text(df, P, iv, off, lab, P.get("case_name", ""))
        e2.download_button("Download breach geometry (.txt)", txt.encode(),
                           file_name=f"{P['case_name'] or 'case'}_breach_geometry.txt",
                           mime="text/plain")


# =====================================================================
# SCENARIOS
# =====================================================================
SCEN_OUT = {"peak_outflow_m3s": "Peak outflow (m³/s)",
            "time_to_peak_hr": "Time to peak (h)",
            "max_breach_depth_m": "Breach height (m)",
            "final_top_width_m": "Breach top width (m)",
            "final_bottom_width_m": "Breach bottom width (m)",
            "eroded_m3": "Eroded embankment volume (m³)",
            "total_outflow_volume_m3": "Release volume (m³)"}


def scenario_keys_available() -> list[str]:
    keys = [k for k in U.CATALOGUE]
    if not is_tailings():
        keys = [k for k in keys if k != "beach_level"]
    # the core is modelled for overtopping submode 3 only (Wu 2016)
    if not (P.get("has_core") and int(P["breach_mode"]) == 1
            and int(P["overtopping_mode"]) == 3):
        keys = [k for k in keys if not k.startswith("core_")]
    # leave out inputs that would not change the file DLBreach reads
    return [k for k in keys if k not in DEFAULT_PARAMS or MCX.affects_input(P, k)]


def scenario_definitions() -> tuple[dict, dict, dict]:
    """(params by run, groups by run, read report) from the current grid."""
    g = st.session_state.get("scen_grid")
    if g is None or g.empty:
        return {}, {}, {}
    vals, rep = BATCH.read_grid(g)
    params = {r: BATCH.grid_params(P, vals.get(r, {})) for r in rep["runs"]}
    return params, rep.get("groups", {}), rep


def page_scenarios():
    exe_path, exe_ok = exe_status()
    with st.container(border=True):
        section("1 · Choose what varies between runs")
        keys = scenario_keys_available()
        seed("keep_scen_keys", ["sed_d50"])
        st.session_state.keep_scen_keys = [k for k in st.session_state.keep_scen_keys
                                           if k in keys]
        chosen = st.multiselect(
            "Parameters", keys, key="keep_scen_keys",
            format_func=lambda k: f"{U.CATALOGUE[k][4]} — {U.label_unit(k)}",
            help=HLP.h("scen_params"))
        c1, c2 = st.columns(2)
        seed("keep_scen_n", 3)
        n_runs = c1.number_input("Number of runs", min_value=1, max_value=60,
                                 step=1, key="keep_scen_n", help=HLP.h("scen_n"))
        seed("keep_scen_prefix", "Sensitivity")
        prefix = c2.text_input("Run name prefix", key="keep_scen_prefix",
                               help=HLP.h("scen_prefix"))
        runs = [f"{prefix} {i + 1}" for i in range(int(n_runs))]

        g = st.session_state.get("scen_grid")
        want_rows = [BATCH.GROUP_ROW] + [U.label(k) for k in chosen]
        have = (g is not None and list(g["Parameter"]) == want_rows
                and [c for c in g.columns if c not in ("Parameter", "Unit")] == runs)
        if not have:
            new = BATCH.grid_template(P, chosen, runs)
            if g is not None:                       # keep values already typed
                for _, row in g.iterrows():
                    for r in runs:
                        if r in g.columns and row["Parameter"] in list(new["Parameter"]):
                            new.loc[new["Parameter"] == row["Parameter"], r] = row[r]
            st.session_state.scen_grid = new
            st.session_state.scen_ver = st.session_state.get("scen_ver", 0) + 1

    with st.container(border=True):
        section("2 · Enter the runs",
                "Runs are columns, parameters are rows, in practitioner units. "
                "The first row is an optional group label (for example Sunny "
                "day or Flood day). Blank or N/A cells keep the base value from "
                "Model setup.")
        grid = st.session_state.scen_grid.astype(object)
        edited = st.data_editor(grid, use_container_width=True, hide_index=True,
                                disabled=["Parameter", "Unit"],
                                key=f"scen_editor_{st.session_state.get('scen_ver', 0)}")
        st.session_state.scen_grid = edited
        d1, d2, d3 = st.columns(3)
        d1.download_button("Download as CSV", edited.to_csv(index=False).encode(),
                           file_name="scenario_runs.csv", mime="text/csv",
                           use_container_width=True)
        buf = io.BytesIO()
        edited.to_excel(buf, index=False)
        d2.download_button("Download as Excel", buf.getvalue(),
                           file_name="scenario_runs.xlsx",
                           mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet", use_container_width=True)
        up = d3.file_uploader("Upload a filled table or run log", type=["csv", "xlsx"],
                              key="scen_upload", label_visibility="collapsed",
                              help=HLP.h("scen_upload"))
        if up is not None and st.session_state.get("scen_sig") != (up.name, up.size):
            try:
                g2 = BATCH.read_grid_file(up.getvalue(), up.name)
                vals, rep = BATCH.read_grid(g2)
                found = [k for k in U.CATALOGUE
                         if any(k in v for v in vals.values())]
                st.session_state.keep_scen_keys = found
                st.session_state.keep_scen_n = len(rep["runs"])
                tmpl = BATCH.grid_template(P, found, rep["runs"], rep.get("groups"))
                for r in rep["runs"]:
                    for k, v in vals[r].items():
                        disp = v if k == "bulk_unit_weight" else U.from_model(k, v)
                        tmpl.loc[tmpl["Parameter"] == U.label(k), r] = round(disp, 6)
                st.session_state.scen_grid = tmpl
                st.session_state.scen_ver = st.session_state.get("scen_ver", 0) + 1
                st.session_state.scen_sig = (up.name, up.size)
                st.session_state.keep_scen_prefix = rep["runs"][0].rsplit(" ", 1)[0] \
                    if rep["runs"] else "Sensitivity"
                st.session_state.scen_upload_report = rep
                st.rerun()
            except Exception as exc:                  # noqa: BLE001
                callout("warn", "Could not read that file.", str(exc))
        rep0 = st.session_state.get("scen_upload_report")
        if rep0 and rep0.get("unrecognised"):
            callout("warn", "Rows not recognised in the uploaded file.",
                    ", ".join(rep0["unrecognised"]))

    params, groups, rep = scenario_definitions()
    for m in rep.get("non_numeric", []):
        callout("warn", "Not a number.", m)
    if params:
        keys_all = sorted({k for p in params.values() for k in p
                           if k in U.CATALOGUE or k == "sed_porosity"})
        filled = pd.DataFrame([{"realisation": i + 1,
                                **{k: params[r].get(k) for k in keys_all
                                   if isinstance(params[r].get(k), (int, float))}}
                               for i, r in enumerate(params)])
        for m in constraint_violations(P, filled):
            callout("warn", "Check the runs.", m.replace("realisations", "runs"))

    with st.container(border=True):
        section("3 · Run")
        names = list(params)
        safe = {r: BATCH.safe_case_name(r, i) for i, r in enumerate(names)}
        if BROWSER:
            z = BATCH.make_batch_zip([(safe[r], build_input_text(params[r])) for r in names],
                                     extra=P.get("data_files") or None)
            st.download_button(f"1 · Download {len(names)} input files (.zip)", z,
                               file_name=f"{P['case_name'] or 'case'}_runs.zip",
                               mime="application/zip")
            st.caption("2 · Unzip, add DLBreach.exe, double-click run_all.bat.  "
                       "3 · Upload the .out files.")
            ups = st.file_uploader("Outputs (.zip or .out files)", type=["zip", "out"],
                                   accept_multiple_files=True, key="scen_out_up",
                                   help="The .out files DLBreach wrote, or a zip of "
                                        "them. Matched to runs by file name.")
            if ups:
                outs = BATCH.read_outputs([(u.name, u.getvalue()) for u in ups])
                st.session_state.scen_store = _scenario_results(
                    names, params, groups, {r: outs.get(safe[r]) for r in names})
        else:
            if data_files_missing():
                st.caption("Attach the data files this case reads (Project page) "
                           "to run it.")
            if st.button(f"Run all {len(names)} runs", type="primary",
                         disabled=not (exe_ok and names) or bool(data_files_missing())):
                bar = st.progress(0.0)
                outs = {}
                for i, r in enumerate(names):
                    bar.progress(i / max(len(names), 1), text=f"{r}")
                    rr = run_case(exe_path, build_input_text(params[r]),
                                  case_name=safe[r],
                                  data_files=params[r].get("data_files"))
                    try:
                        outs[r] = parse_out(rr["out_path"]) if rr["ok"] else None
                    except ValueError:                # output without data rows
                        outs[r] = None
                    finally:
                        if rr.get("created_temp"):
                            import shutil as _sh
                            _sh.rmtree(rr["work_dir"], ignore_errors=True)
                bar.empty()
                st.session_state.scen_store = _scenario_results(names, params,
                                                                groups, outs)

    store = st.session_state.get("scen_store")
    if not store:
        return
    summ, hyd = store["summary"], store["hydros"]
    with st.container(border=True):
        section("Results")
        lab_extra = {"tailings_m3": "Tailings released (m³)",
                     "peak_total": "Bulked peak (m³/s)"}
        show = summ.rename(columns={**SCEN_OUT, **lab_extra})
        fmt = {v: "{:,.2f}" for v in list(SCEN_OUT.values()) + list(lab_extra.values())}
        st.dataframe(show.style.format({k: v for k, v in fmt.items() if k in show},
                                       na_rep="—"),
                     use_container_width=True, hide_index=True)
        st.download_button("Download results (.csv)", show.to_csv(index=False).encode(),
                           file_name=f"{P['case_name'] or 'case'}_run_results.csv",
                           mime="text/csv")
    geo = store.get("geoms") or {}
    if hyd:
        with st.container(border=True):
            section("Runs compared through time",
                    "Each line is one run. Choose what to compare.")
            off, lab = datum()
            tabs = st.tabs(["Outflow", "Top width", "Bottom width",
                            "Breach height", "Pond level"])
            tv_s = t_view(list(hyd.values()))
            with tabs[0]:
                long = pd.concat([pd.DataFrame({"x": t, "y": q, "Series": r})
                                  for r, (t, q) in hyd.items()], ignore_index=True)
                chart(long, "Time (h)", "Discharge (m³/s)", "scen_hydro",
                      x_auto_max=tv_s)
            specs = [("breach_top_width", "Top width (m)", 0.0),
                     ("breach_bottom_width", "Bottom width (m)", 0.0),
                     ("breach_depth", "Breach height, crest to invert (m)", 0.0),
                     ("wsl_up", f"Pond level ({lab})", off)]
            for tab, (col, ytitle, shift) in zip(tabs[1:], specs):
                with tab:
                    parts = []
                    for r, g in geo.items():
                        if g is None or g.empty:
                            continue
                        if col == "breach_depth":
                            y = float(store["params"][r]["emb_height"]) - g["breach_bottom_elev"]
                        else:
                            y = g[col] + shift
                        parts.append(pd.DataFrame({"x": g["time_hr"], "y": y,
                                                   "Series": r}))
                    if parts:
                        chart(pd.concat(parts, ignore_index=True), "Time (h)",
                              ytitle, f"scen_{col}", x_auto_max=tv_s)
    if geo:
        with st.container(border=True):
            section("Breach development by run",
                    "Looking upstream from downstream. Choose a run to play.")
            seed("keep_scen_anim", list(geo)[0])
            if st.session_state.keep_scen_anim not in geo:
                st.session_state.keep_scen_anim = list(geo)[0]
            ra = st.selectbox("Run", list(geo), key="keep_scen_anim",
                              help="Run whose breach development to play.")
            animate_run(store["params"][ra], geo[ra], "scen")


def _scenario_results(names, params, groups, outs) -> dict:
    from dlbreach_mc import _thin_geometry
    rows, hyd, geo, case = [], {}, {}, {}
    for r in names:
        df = outs.get(r)
        row = {"Run": r, "Group": groups.get(r, "")}
        if df is not None:
            s = summarise(df, crest_elev=params[r]["emb_height"])
            case[r] = {**s, **case_values(params[r], df)}
            s["eroded_m3"] = eroded_dam_volume(params[r], s["final_bottom_width_m"],
                                               s["final_bottom_elev_m"],
                                               s["final_side_slope"])
            row.update({k: s.get(k) for k in SCEN_OUT})
            tr = tl_for(df, params[r])
            if tr and tr.get("ok"):
                row["tailings_m3"] = tr["tailings_m3"]
                row["peak_total"] = tr["peak_total"]
            hyd[r] = _thin_hydrograph(df)
            geo[r] = _thin_geometry(df)
        rows.append(row)
    return {"summary": pd.DataFrame(rows), "hydros": hyd, "geoms": geo,
            "params": params, "case": case}


def animate_run(p: dict, geom: pd.DataFrame, key: str):
    """Breach development animation for one stored run."""
    if geom is None or geom.empty:
        st.caption("No geometry stored for this run.")
        return
    seed(f"keep_ve_{key}", "Auto")
    v = st.columns([1, 3])[0].selectbox(
        "Vertical exaggeration", ["Auto", "1×", "2×", "5×", "10×", "20×", "40×"],
        key=f"keep_ve_{key}", help=HLP.h("ve"))
    ve = None if v == "Auto" else float(v.rstrip("×"))
    off, lab = datum()
    a = breach_animation_html(dict(p, _z_off=off, _z_lab=lab), geom, ve_override=ve)
    components.html(FONT_LINK + a, height=animation_height(a), scrolling=False)


# =====================================================================
# MONTE CARLO
# =====================================================================
MC_OUT = {"max_breach_depth_m": "Breach height (m)",
          "final_top_width_m": "Breach top width (m)",
          "eroded_m3": "Eroded embankment volume (m³)",
          "peak_outflow_m3s": "Peak outflow (m³/s)",
          "total_outflow_volume_m3": "Release volume (m³)"}


def page_mc():
    exe_path, exe_ok = exe_status()
    params, _groups, _rep = scenario_definitions()
    options = ["Base case"] + list(params)
    bases = {"Base case": dict(P), **params}

    with st.container(border=True):
        section("1 · Which runs", "Each chosen run is the base for its own "
                "Monte Carlo ensemble. Runs come from Sensitivity scenarios.")
        seed("mc_runs", ["Base case"])
        st.session_state.mc_runs = [r for r in st.session_state.mc_runs if r in options]
        chosen_runs = st.multiselect("Runs", options, key="mc_runs",
                                     help=HLP.h("mc_runs"))

    from dlbreach_mc import relevant_candidates
    cands = relevant_candidates(P)
    with st.container(border=True):
        section("2 · Uncertain parameters",
                "Distributions are entered in practitioner units and converted "
                "for DLBreach. A sampled parameter replaces the run's value.")
        seed("mc_chosen", [k for k in ("sed_d50", "manning_n") if k in cands])
        st.session_state.mc_chosen = [c for c in st.session_state.mc_chosen if c in cands]
        chosen = st.multiselect("Parameters", list(cands), key="mc_chosen",
                                format_func=lambda k: U.label_unit(k),
                                help=HLP.h("mc_params"))
        chosen_scen = [r for r in chosen_runs if r in params]
        varied = {k for r in chosen_scen for k in params[r] if k in U.CATALOGUE
                  and params[r].get(k) != P.get(k)}
        clash = [U.label(k) for k in chosen if k in varied]
        if clash:
            callout("note", "Also varied between runs.",
                    ", ".join(clash) + ": the sampled values replace the run "
                    "values within each ensemble.")
        specs = {}
        for key in chosen:
            base = float(U.from_model(key, P.get(key, 1.0)) or 1.0)
            with st.expander(U.label_unit(key), expanded=True):
                cc = st.columns(5)
                seed(f"mc_d_{key}", "triangular")
                dist = cc[0].selectbox("Distribution", DISTRIBUTIONS[1:],
                                       key=f"mc_d_{key}", help=HLP.h("mc_dist"))
                for nm, v in (("lo", base * 0.8), ("hi", base * 1.2), ("mo", base),
                              ("mu", base), ("sd", abs(base) * 0.15), ("mn", 0.0)):
                    seed(f"mc_{nm}_{key}", float(v))
                spec = {"dist": dist}
                if dist == "uniform":
                    spec["low"] = cc[1].number_input("Low", key=f"mc_lo_{key}", format="%g",
                                                    help=HLP.h("mc_low"))
                    spec["high"] = cc[2].number_input("High", key=f"mc_hi_{key}", format="%g",
                                                    help=HLP.h("mc_high"))
                elif dist == "triangular":
                    spec["low"] = cc[1].number_input("Low", key=f"mc_lo_{key}", format="%g",
                                                    help=HLP.h("mc_low"))
                    spec["mode"] = cc[2].number_input("Most likely", key=f"mc_mo_{key}", format="%g",
                                                    help=HLP.h("mc_mode"))
                    spec["high"] = cc[3].number_input("High", key=f"mc_hi_{key}", format="%g",
                                                    help=HLP.h("mc_high"))
                else:
                    spec["mean"] = cc[1].number_input("Mean", key=f"mc_mu_{key}", format="%g",
                                                    help=HLP.h("mc_mean"))
                    spec["sd"] = cc[2].number_input("Std. dev.", key=f"mc_sd_{key}", format="%g",
                                                    help=HLP.h("mc_sd"))
                spec["min"] = cc[4].number_input("Min (clip)", key=f"mc_mn_{key}", format="%g",
                                                    help=HLP.h("mc_min"))
                specs[key] = spec
        q1, q2 = st.columns(2)
        seed("mc_nreal", 100)
        n_real = q1.number_input("Realisations per run", 10, 100000, key="mc_nreal",
                                 step=10, help=HLP.h("mc_nreal"))
        seed("mc_seed", 42)
        seed_v = q2.number_input("Random seed", 0, 10**6, key="mc_seed", step=1,
                                 help=HLP.h("mc_seed"))

    def samples_for(run_name):
        s = build_sample_table(bases[run_name], specs, int(n_real), seed=int(seed_v))
        for c in s.columns:
            if c != "realisation":
                s[c] = s[c].map(lambda v, c=c: U.to_model(c, v))
        return s

    with st.container(border=True):
        section("3 · Run")
        if chosen_runs and specs:
            for m in constraint_violations(P, samples_for(chosen_runs[0])):
                callout("warn", "Check the distributions.", m)
        if BROWSER:
            cases = []
            for r in chosen_runs:
                s = samples_for(r)
                tag = BATCH.safe_case_name(r, 0)[:20]
                for _, row in s.iterrows():
                    p = dict(bases[r], **{c: float(row[c]) for c in s.columns
                                          if c != "realisation"})
                    cases.append((f"{tag}_mc{int(row.realisation):05d}",
                                  build_input_text(p)))
            st.download_button(f"1 · Download {len(cases)} input files (.zip)",
                               BATCH.make_batch_zip(cases, extra=P.get("data_files") or None),
                               file_name=f"{P['case_name'] or 'case'}_mc.zip",
                               mime="application/zip", disabled=not cases)
            st.caption("2 · Unzip, add DLBreach.exe, run run_all.bat.  3 · Upload "
                       "the outputs. Keep the same settings until loaded.")
            ups = st.file_uploader("Outputs (.zip or .out)", type=["zip", "out"],
                                   accept_multiple_files=True, key="mc_out_up",
                                   help="The .out files DLBreach wrote, or a zip of "
                                        "them. Matched to realisations by file name.")
            if ups:
                outs = BATCH.read_outputs([(u.name, u.getvalue()) for u in ups])
                store = {}
                for r in chosen_runs:
                    tag = BATCH.safe_case_name(r, 0)[:20]
                    s = samples_for(r)
                    res, hyd, geo = BATCH.ensemble_from_outputs(
                        bases[r], s, outs, name_fn=lambda i, t=tag: f"{t}_mc{i:05d}")
                    store[r] = _mc_post(r, res, list(specs), hyd, bases[r], geo)
                st.session_state.mc_store = store
        elif st.button("Run Monte Carlo", type="primary",
                       disabled=not (exe_ok and chosen_runs and specs)
                       or bool(data_files_missing())):
            store = {}
            bar = st.progress(0.0)
            for j, r in enumerate(chosen_runs):
                def cb(done, total, j=j, r=r):
                    bar.progress((j + done / total) / len(chosen_runs),
                                 text=f"{r}: {done} of {total}")
                res, hyd, geo = run_monte_carlo(bases[r], samples_for(r), exe_path,
                                                n_workers=min(8, max(1, os.cpu_count() or 4)),
                                                timeout=900, progress_callback=cb)
                store[r] = _mc_post(r, res, list(specs), hyd, bases[r], geo)
            bar.empty()
            st.session_state.mc_store = store

    store = st.session_state.get("mc_store") or {}
    if not store:
        callout("info", "No ensemble yet.", "Choose runs and parameters, then run.")
        return
    mc_results(store)


MC_PICKS = ["Median peak", "Mean peak", "Minimum peak", "Maximum peak",
            "Choose by number"]
MC_SCATTER_OUT = {"peak_outflow_m3s": "Peak outflow (m³/s)",
                  "final_top_width_m": "Final top width (m)",
                  "final_bottom_width_m": "Final bottom width (m)",
                  "max_breach_depth_m": "Breach height (m)",
                  "time_to_peak_hr": "Time to peak (h)",
                  "eroded_m3": "Eroded embankment volume (m³)"}


def mc_results(store: dict):
    """Results of the Monte Carlo ensembles: summary, a chosen realisation,
    the ensemble through time, and how the sampled inputs drive the
    results."""
    with st.container(border=True):
        section("Summary", "Minimum, average and maximum over the completed "
                "realisations of each run.")
        tab = mc_summary_table(store)
        st.dataframe(tab, use_container_width=True, hide_index=True)
        st.download_button("Download summary (.csv)", tab.to_csv(index=False).encode(),
                           file_name=f"{P['case_name'] or 'case'}_mc_summary.csv",
                           mime="text/csv")

    # ---- which ensemble, which realisation ----
    with st.container(border=True):
        section("Inspect a realisation",
                "Pick one realisation to follow through the charts below. It is "
                "drawn in black on the time charts and as a diamond on the "
                "input charts.")
        c1, c2, c3 = st.columns([2, 2, 1])
        seed("keep_mc_detail", list(store)[0])
        if st.session_state.keep_mc_detail not in store:
            st.session_state.keep_mc_detail = list(store)[0]
        r = c1.selectbox("Ensemble", list(store), key="keep_mc_detail",
                         help="Each run chosen on this page has its own ensemble.")
        res, cols, hyd, base_p = (store[r]["results"], store[r]["cols"],
                                  store[r]["hydros"], store[r]["base"])
        geoms = store[r].get("geoms") or {}
        ok = res[res["ok"] == True]                     # noqa: E712
        seed("keep_mc_pick", "Median peak")
        pick = c2.selectbox("Realisation", MC_PICKS, key="keep_mc_pick",
                            help=HLP.h("mc_pick"))
        if ok.empty:
            callout("warn", "No realisation completed.",
                    "Check the error column in the full results download.")
            st.download_button("Download all realisations (.csv)",
                               res.to_csv(index=False).encode(),
                               file_name=f"{BATCH.safe_case_name(r, 0)}_mc_all.csv",
                               mime="text/csv")
            return
        nums = [int(x) for x in ok["realisation"]]
        if pick == "Choose by number":
            seed("keep_mc_num", nums[0])
            if st.session_state.keep_mc_num not in nums:
                st.session_state.keep_mc_num = nums[0]
            rn = int(c3.selectbox("Number", nums, key="keep_mc_num",
                                  help="Realisation number, as in the full "
                                       "results download."))
            idx = int(res.index[res["realisation"] == rn][0])
        else:
            stat = {"Median peak": "Median", "Mean peak": "Mean",
                    "Minimum peak": "Min", "Maximum peak": "Max"}[pick]
            idx = representative_realisation(res, "peak_outflow_m3s", stat)
            rn = int(res.loc[idx, "realisation"])
            c3.markdown(f"<div style='padding-top:1.9rem'><b>No. {rn}</b></div>",
                        unsafe_allow_html=True)
        st.caption(f"{len(ok)} of {len(res)} realisations completed.")
        p_sel = realisation_params(base_p, res, idx, cols)
        row = res.loc[idx]
        ins = [(U.label(c), f"{U.from_model(c, float(row[c])):,.4g} {U.unit(c)}"
                .replace(" –", "")) for c in cols if c in res.columns]
        tiles([(f"Realisation {rn}", f"{float(row['peak_outflow_m3s']):,.0f} m³/s",
                "peak outflow", True),
               ("Time to peak", f"{float(row['time_to_peak_hr']):.2f} h"),
               ("Breach height", f"{float(row['max_breach_depth_m']):,.2f} m"),
               ("Final top width", f"{float(row['final_top_width_m']):,.1f} m"),
               ("Release volume", f"{float(row['total_outflow_volume_m3']):,.0f} m³")])
        if ins:
            st.markdown("**Sampled inputs of this realisation:** "
                        + "; ".join(f"{a} {b}" for a, b in ins))
        m1, m2, m3 = st.columns(3)
        m1.download_button("Input file (.txt)", build_input_text(p_sel).encode(),
                           file_name=f"{BATCH.safe_case_name(r, 0)}_r{rn}.txt",
                           mime="text/plain", use_container_width=True,
                           help="Re-run it as a single run for the full-"
                                "resolution output.")
        gm = geoms.get(rn)
        if rn in hyd:
            t, q = hyd[rn]
            m2.download_button("Hydrograph (.csv)",
                               pd.DataFrame({"time_h": t, "Q_water_m3s": q})
                               .to_csv(index=False).encode(),
                               file_name=f"{BATCH.safe_case_name(r, 0)}_r{rn}_hydrograph.csv",
                               mime="text/csv", use_container_width=True,
                               help="Thinned to the points that define the "
                                    "hydrograph, peak included.")
        m3.download_button("All realisations (.csv)", res.to_csv(index=False).encode(),
                           file_name=f"{BATCH.safe_case_name(r, 0)}_mc_all.csv",
                           mime="text/csv", use_container_width=True,
                           help="Sampled inputs and results of every realisation.")

    sel_name = f"Realisation {rn}"
    # ---- through time ----
    with st.container(border=True):
        section("Ensemble through time",
                "Each statistic is taken across the realisations at every moment, "
                "so an envelope curve is not itself a model run. Beyond the end "
                "of a realisation its outflow is taken as zero and its breach "
                "geometry as the final breach.")
        seed("keep_mc_env", ["P05", "Median", "P95"])
        picks = st.multiselect("Envelope curves", ENVELOPE_STATS, key="keep_mc_env",
                               help=HLP.h("mc_env"))
        off, lab = datum()
        crest = {k: float(realisation_params(
            base_p, res, int(res.index[res["realisation"] == k][0]), cols)
            .get("emb_height", base_p["emb_height"])) for k in geoms} if geoms else {}
        tabs = st.tabs(["Outflow", "Top width", "Bottom width", "Breach height",
                        "Pond level"])
        tv_m = t_view(list(hyd.values())) if hyd else None
        env_colours = {"Min": "#9DB9D3", "Max": "#9DB9D3", "P05": "#5B9BD5",
                       "P95": "#5B9BD5", "P10": "#5B9BD5", "P90": "#5B9BD5",
                       "P25": "#2F7BBF", "P75": "#2F7BBF", "Median": "#17324D",
                       "Mean": "#2E8B57", sel_name: "#000000"}

        def env_chart(grid, curves, sel_x, sel_y, ytitle, key, shift=0.0):
            env = hydrograph_percentiles(grid, curves, picks)
            parts = []
            if not env.empty:
                e = env.reset_index().rename(columns={"index": "t"})
                for c in env.columns:
                    parts.append(pd.DataFrame({"x": e["t"], "y": e[c] + shift,
                                               "Series": c}))
            if sel_x is not None:
                parts.append(pd.DataFrame({"x": sel_x, "y": np.asarray(sel_y) + shift,
                                           "Series": sel_name}))
            if parts:
                chart(pd.concat(parts, ignore_index=True), "Time (h)", ytitle, key,
                      colours=env_colours, dashed=[sel_name], x_auto_max=tv_m)

        with tabs[0]:
            if hyd:
                grid, curves = hydrograph_ensemble(hyd)
                t, q = hyd.get(rn, (None, None))
                env_chart(grid, curves, t, q, "Discharge (m³/s)", "mc_env")
        geo_tabs = [("breach_top_width", "Top width (m)", 0.0),
                    ("breach_bottom_width", "Bottom width (m)", 0.0),
                    ("breach_depth", "Breach height, crest to invert (m)", 0.0),
                    ("wsl_up", f"Pond level ({lab})", off)]
        for tab, (col, ytitle, shift) in zip(tabs[1:], geo_tabs):
            with tab:
                if not geoms:
                    st.caption("No breach geometry stored for this ensemble.")
                    continue
                grid, curves = MCX.geometry_ensemble(geoms, col, crest=crest)
                if gm is not None:
                    sy = (crest.get(rn, base_p["emb_height"]) - gm["breach_bottom_elev"]
                          if col == "breach_depth" else gm[col])
                    env_chart(grid, curves, gm["time_hr"], sy, ytitle,
                              f"mc_{col}", shift)
                else:
                    env_chart(grid, curves, None, None, ytitle, f"mc_{col}", shift)

    # ---- inputs against results ----
    if cols:
        with st.container(border=True):
            section("How the sampled inputs drive the breach",
                    "Each point is one realisation. A steep trend means the "
                    "result is sensitive to that input.")
            s1, s2 = st.columns(2)
            seed("keep_mc_x", cols[0])
            if st.session_state.keep_mc_x not in cols:
                st.session_state.keep_mc_x = cols[0]
            xk = s1.selectbox("Input", cols, key="keep_mc_x",
                              format_func=U.label_unit, help=HLP.h("mc_x"))
            outs = [k for k in MC_SCATTER_OUT if k in ok.columns]
            seed("keep_mc_y", "final_top_width_m")
            if st.session_state.keep_mc_y not in outs:
                st.session_state.keep_mc_y = outs[0]
            yk = s2.selectbox("Result", outs, key="keep_mc_y",
                              format_func=lambda k: MC_SCATTER_OUT[k],
                              help=HLP.h("mc_y"))
            xs = ok[xk].astype(float).map(lambda v: U.from_model(xk, v))
            sc = pd.DataFrame({"x": xs, "y": ok[yk].astype(float),
                               "Series": "Realisations",
                               "Event": ok["realisation"].map(lambda v: f"No. {int(v)}")})
            sc.loc[ok["realisation"].astype(int) == rn, "Series"] = sel_name
            chart(sc, U.label_unit(xk), MC_SCATTER_OUT[yk], "mc_scatter",
                  kind="scatter", highlight=sel_name, height=320,
                  colours={"Realisations": "#5B9BD5", sel_name: "#000000"})
            try:
                from dlbreach_mc import input_output_correlation
                # in the units shown, so the sign matches the chart (slopes
                # are shown as H per 1V, the inverse of the model's V/H)
                okp = ok.copy()
                for c in cols:
                    okp[c] = okp[c].astype(float).map(lambda v, c=c: U.from_model(c, v))
                corr = input_output_correlation(okp, cols, yk)
                if corr is not None and not corr.empty:
                    corr = corr.copy()
                    corr["parameter"] = corr["parameter"].map(U.label_unit)
                    st.caption("Spearman rank correlation with "
                               f"{MC_SCATTER_OUT[yk].lower()}: "
                               + "; ".join(f"{a} {b:+.2f}" if np.isfinite(b)
                                           else f"{a} (result does not vary)"
                                           for a, b in
                                           corr[["parameter", "rank correlation"]]
                                           .itertuples(index=False)))
            except Exception:                                  # noqa: BLE001
                pass

    # ---- breach development of the chosen realisation ----
    if gm is not None:
        with st.container(border=True):
            section(f"Breach development of realisation {rn}",
                    "Looking upstream from downstream. Change the realisation "
                    "above to compare.")
            animate_run(p_sel, gm, "mc")


def _mc_pick(entry: dict, pick: str, num=None):
    """(index, realisation number, label) of the realisation to show for an
    ensemble, or None if nothing completed."""
    res = entry["results"]
    ok = res[res["ok"] == True]                         # noqa: E712
    if ok.empty:
        return None
    nums = [int(x) for x in ok["realisation"]]
    if pick == "Choose by number" and num in nums:
        return (int(res.index[res["realisation"] == num][0]), int(num),
                f"realisation {num}")
    if pick == "Choose by number":
        pick = "Median peak"
    stat = {"Median peak": "Median", "Mean peak": "Mean",
            "Minimum peak": "Min", "Maximum peak": "Max"}.get(pick, "Median")
    idx = representative_realisation(res, "peak_outflow_m3s", stat)
    rn = int(res.loc[idx, "realisation"])
    return idx, rn, f"realisation {rn} ({pick.lower()})"


def mc_report_data(store: dict) -> tuple[list, list]:
    """Envelope panels and input-against-result data of every ensemble, for
    the report. The ensemble open on the Monte Carlo page shows the
    realisation picked there; the others show their median-peak
    realisation."""
    picks = st.session_state.get("keep_mc_env") or ["P05", "Median", "P95"]
    open_run = st.session_state.get("keep_mc_detail")
    off, lab = datum()
    env_out, drv_out = [], []
    for name, ent in store.items():
        if name == open_run:
            sel = _mc_pick(ent, st.session_state.get("keep_mc_pick", "Median peak"),
                           st.session_state.get("keep_mc_num"))
        else:
            sel = _mc_pick(ent, "Median peak")
        if sel is None:
            continue
        idx, rn, sel_label = sel
        res, cols, hyd, base_p = ent["results"], ent["cols"], ent["hydros"], ent["base"]
        geoms = ent.get("geoms") or {}
        ok = res[res["ok"] == True]                     # noqa: E712
        panels = []
        if hyd:
            grid, curves = hydrograph_ensemble(hyd)
            env = hydrograph_percentiles(grid, curves, picks)
            panels.append({"title": "Breach outflow", "ylabel": "Discharge (m³/s)",
                           "t": grid, "curves": {c: env[c].to_numpy() for c in env},
                           "sel": hyd.get(rn)})
        if geoms:
            crest = {k: float(realisation_params(
                base_p, res, int(res.index[res["realisation"] == k][0]), cols)
                .get("emb_height", base_p["emb_height"])) for k in geoms}
            gm = geoms.get(rn)
            for col, title, ylabel, shift in (
                    ("breach_top_width", "Top width", "Width (m)", 0.0),
                    ("breach_bottom_width", "Bottom width", "Width (m)", 0.0),
                    ("breach_depth", "Breach height, crest to invert", "Height (m)", 0.0),
                    ("wsl_up", "Pond level", f"Elevation ({lab})", off)):
                grid, curves = MCX.geometry_ensemble(geoms, col, crest=crest)
                env = hydrograph_percentiles(grid, curves, picks)
                selxy = None
                if gm is not None:
                    yy = (crest.get(rn, base_p["emb_height"]) - gm["breach_bottom_elev"]
                          if col == "breach_depth" else gm[col])
                    selxy = (gm["time_hr"].to_numpy(), np.asarray(yy) + shift)
                panels.append({"title": title, "ylabel": ylabel, "t": grid,
                               "curves": {c: env[c].to_numpy() + shift for c in env},
                               "sel": selxy})
        env_out.append({"name": name, "sel_label": sel_label, "panels": panels})
        if cols:
            outs = [(MC_SCATTER_OUT[k], ok[k].astype(float).to_numpy())
                    for k in ("peak_outflow_m3s", "final_top_width_m",
                              "max_breach_depth_m") if k in ok]
            ins = [(U.label_unit(c), ok[c].astype(float)
                    .map(lambda v, c=c: U.from_model(c, v)).to_numpy())
                   for c in cols if c in ok]
            drv_out.append({"name": name, "sel_label": sel_label, "inputs": ins,
                            "outputs": outs,
                            "sel": (ok["realisation"].astype(int) == rn).to_numpy()})
    return env_out, drv_out


def _mc_post(run, res, cols, hyd, base_p, geoms=None) -> dict:
    """Add eroded embankment volume and, for solid waste dams, tailings
    released and bulked peak, to each completed realisation."""
    geoms = geoms or {}
    ev, tv, pk = [], [], []
    for i in res.index:
        if not bool(res.loc[i, "ok"]):
            ev.append(np.nan); tv.append(np.nan); pk.append(np.nan)
            continue
        p = realisation_params(base_p, res, i, cols)
        ev.append(eroded_dam_volume(p, float(res.loc[i, "final_bottom_width_m"]),
                                    float(res.loc[i, "final_bottom_elev_m"]),
                                    float(res.loc[i, "final_side_slope"])))
        g = geoms.get(int(res.loc[i, "realisation"]))
        tr = tl_for(g, p) if g is not None else None
        tv.append(tr["tailings_m3"] if (tr and tr.get("ok")) else np.nan)
        pk.append(tr["peak_total"] if (tr and tr.get("ok")) else np.nan)
    res = res.copy()
    res["eroded_m3"] = ev
    if is_tailings():
        res["tailings_m3"], res["peak_total"] = tv, pk
    return {"results": res, "cols": cols, "hydros": hyd, "base": base_p,
            "geoms": geoms}


def mc_summary_table(store: dict) -> pd.DataFrame:
    rows = []
    outs = dict(MC_OUT)
    if any("tailings_m3" in d["results"] for d in store.values()):
        outs.update({"tailings_m3": "Tailings released (m³)",
                     "peak_total": "Bulked peak outflow (m³/s)"})
    for col, lab in outs.items():
        for stat in ("Minimum", "Average", "Maximum"):
            row = {"Output": lab, "Statistic": stat}
            for r, d in store.items():
                ok = d["results"][d["results"]["ok"] == True]   # noqa: E712
                v = pd.to_numeric(ok.get(col), errors="coerce").dropna() \
                    if col in ok else pd.Series(dtype=float)
                row[r] = (np.nan if v.empty else
                          {"Minimum": v.min(), "Average": v.mean(),
                           "Maximum": v.max()}[stat])
            rows.append(row)
    t = pd.DataFrame(rows)
    for r in store:
        t[r] = t[r].map(lambda x: "—" if pd.isna(x) else f"{x:,.1f}")
    return t


# =====================================================================
# CASE HISTORIES
# =====================================================================
def case_point(df) -> tuple[dict | None, dict]:
    """This analysis as a point for the case-history charts."""
    s = summarise(df, crest_elev=P["emb_height"]) if df is not None else None
    pt = {}
    if s:
        d = derive_inputs(P, df)
        pt = {"Hb": s["max_breach_depth_m"], "Qp": s["peak_outflow_m3s"],
              "Vw": d["Vw"], "tf": d["tf_hr"],
              "Bave": (s["final_top_width_m"] + s["final_bottom_width_m"]) / 2,
              "Vout": s["total_outflow_volume_m3"]}
    return s, pt


WATER_CASE_REFS = ["froehlich2016", "xu2009"]
WATER_CASE_NOTE = ("Some dams appear in both water-dam compilations; where "
                   "Froehlich revised a peak discharge the two values differ.")


CASE_SCEN = "Scenario runs"
CASE_MC = "Monte Carlo"
CASE_SCEN_COLOUR = "#2E8B57"
CASE_MC_COLOURS = ["#5E6B77", "#7A5AA6", "#C9A227", "#17A2B8", "#8A5A2B"]


def _case_row(src: dict, series: str, event: str) -> dict:
    """One run as the five case-history quantities."""
    def f(k):
        v = src.get(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        return v if np.isfinite(v) else None
    tw, bw = f("final_top_width_m"), f("final_bottom_width_m")
    return {"Hb": f("max_breach_depth_m"), "Qp": f("peak_outflow_m3s"),
            "Vw": f("water_volume_above_invert_m3"), "tf": f("formation_time_hr"),
            "Bave": (tw + bw) / 2 if (tw is not None and bw is not None) else None,
            "Series": series, "Event": event}


def case_overlays(scen: bool, mc: bool) -> tuple[list, dict, list, list]:
    """Scenario and Monte Carlo runs as points for the case-history charts:
    (rows, colours by series, series drawn small and light, runs left out).
    Results from before version 1.0.3 lack the stored water volume and
    formation time, so they are left out and named in the last list."""
    rows, colours, faint, missing = [], {}, [], []
    sc = st.session_state.get("scen_store") if scen else None
    if sc:
        for r, src in (sc.get("case") or {}).items():
            rows.append(_case_row(src, CASE_SCEN, r))
        if sc.get("case") is None:
            missing.append("the scenario runs")
        colours[CASE_SCEN] = CASE_SCEN_COLOUR
    store = (st.session_state.get("mc_store") or {}) if mc else {}
    for j, (name, ent) in enumerate(store.items()):
        res = ent["results"]
        ser = CASE_MC if len(store) == 1 else f"{CASE_MC}: {name}"
        if "formation_time_hr" not in res.columns:
            missing.append(name)
            continue
        ok = res[res["ok"] == True]                     # noqa: E712
        for _, r in ok.iterrows():
            rows.append(_case_row(r.to_dict(), ser,
                                  f"{name}, realisation {int(r['realisation'])}"))
        colours[ser] = CASE_MC_COLOURS[j % len(CASE_MC_COLOURS)]
        faint.append(ser)
    return rows, colours, faint, missing


CASE_AXES = {"c_qhb": ("Hb", "Qp"), "c_qvw": ("Vw", "Qp"),
             "c_bvw": ("Vw", "Bave"), "c_tvw": ("Vw", "tf")}


def _with_overlays(data: pd.DataFrame, key: str, extra: list | None) -> pd.DataFrame:
    """Case-history table with scenario and Monte Carlo points added before
    this analysis, so the single run stays last in the legend."""
    if not extra:
        return data
    xk, yk = CASE_AXES[key]
    add = pd.DataFrame([{"x": e[xk], "y": e[yk], "Series": e["Series"],
                         "Event": e["Event"]} for e in extra
                        if e.get(xk) is not None and e.get(yk) is not None
                        and e[xk] > 0 and e[yk] > 0])
    if add.empty:
        return data
    model = data["Series"] == CASES.MODEL
    return pd.concat([data[~model], add, data[model]], ignore_index=True)


def water_case_panels(pt: dict, extra: list | None = None) -> list[dict]:
    """The four water-dam case-history charts, for the page and the report.
    extra: scenario and Monte Carlo points from case_overlays."""
    vw = "Water volume above breach invert (m³)"
    pans = [
        dict(title="Peak outflow against breach height",
             sub="Froehlich (2016a), 41 failures; Xu and Zhang (2009), 75.",
             data=CASES.water_peak_vs_breach_height({"x": pt.get("Hb"), "y": pt.get("Qp")}),
             xlabel="Breach height (m)", ylabel="Peak outflow (m³/s)", key="c_qhb",
             logx=True, logy=True),
        dict(title="Peak outflow against water volume",
             sub="Froehlich (2016a); Xu and Zhang (2009).",
             data=CASES.water_peak_vs_volume({"x": pt.get("Vw"), "y": pt.get("Qp")}),
             xlabel=vw, ylabel="Peak outflow (m³/s)", key="c_qvw",
             logx=True, logy=True),
        dict(title="Average breach width against water volume",
             sub="Xu and Zhang (2009).",
             data=CASES.water_width_vs_volume({"x": pt.get("Vw"), "y": pt.get("Bave")}),
             xlabel=vw, ylabel="Average breach width (m)", key="c_bvw",
             logx=True, logy=True),
        dict(title="Failure time against water volume",
             sub="Xu and Zhang (2009). DLBreach formation time: onset of "
                 "downcutting to final geometry.",
             data=CASES.water_time_vs_volume({"x": pt.get("Vw"), "y": pt.get("tf")}),
             xlabel=vw, ylabel="Failure time (h)", key="c_tvw",
             logx=True, logy=True)]
    for pn in pans:
        pn["data"] = _with_overlays(pn["data"], pn["key"], extra)
    return pans


def case_selection() -> tuple[dict, list, dict, list, list]:
    """The runs chosen on Case histories, for the page and the report:
    (single-run point, scenario and Monte Carlo rows, colours, faint
    series, runs left out)."""
    df = st.session_state.result_df
    s, pt = case_point(df)
    if not st.session_state.get("keep_cases_det", True):
        pt = {}
    rows, cols, faint, missing = case_overlays(
        bool(st.session_state.get("keep_cases_scen", False)),
        bool(st.session_state.get("keep_cases_mc", False)))
    return pt, rows, cols, faint, missing


MC_CASE_NOTE = ("The spread of a Monte Carlo ensemble reflects uncertainty "
                "in the inputs for one dam; the scatter of the case histories "
                "reflects differences between many dams.")


def case_report_styles(cols: dict, faint: list) -> dict:
    """Report marker styles: (colour, marker, size, alpha) by series."""
    st_ = {}
    for name, c in cols.items():
        st_[name] = (c, "o", 9, 0.45) if name in faint else (c, "^", 34, 0.95)
    return st_


def page_cases():
    df = st.session_state.result_df
    s, _ = case_point(df)
    has_scen = bool(st.session_state.get("scen_store"))
    has_mc = bool(st.session_state.get("mc_store"))
    if s:
        stale_notice()
    callout("info", "Measured outcomes only.",
            "Your single run is the black diamond among real failures; scenario "
            "runs and Monte Carlo realisations can be added below. No regression "
            "lines are drawn. " + CASES.COMPLETENESS_NOTE)
    if not is_tailings():
        with st.container(border=True):
            section("Runs to show", "Each run is placed by its own inputs and "
                    "results. The spread of a Monte Carlo ensemble reflects "
                    "uncertainty in the inputs for one dam; the scatter of the "
                    "case histories reflects differences between many dams. "
                    "Agreement shows the results are plausible, not that they "
                    "are right for this dam.")
            seed("keep_cases_det", True)
            seed("keep_cases_scen", False)
            seed("keep_cases_mc", False)
            t1, t2, t3 = st.columns(3)
            t1.toggle("Single run", key="keep_cases_det", disabled=not s,
                      help="The run on Single run, as a black diamond.")
            t2.toggle("Scenario runs", key="keep_cases_scen", disabled=not has_scen,
                      help="Every run on Sensitivity scenarios, as green markers. "
                           "Hover for the run name.")
            t3.toggle("Monte Carlo realisations", key="keep_cases_mc",
                      disabled=not has_mc,
                      help="Every completed realisation, as small light points, "
                           "one colour per ensemble.")
            avail = [n for n, ok in (("Single run", s), ("Sensitivity scenarios",
                     has_scen), ("Monte Carlo", has_mc)) if not ok]
            if avail:
                st.caption("Nothing to add yet from: " + ", ".join(avail) + ".")
    pt, extra, cols, faint, missing = case_selection()
    if missing:
        callout("note", "Some runs are not shown.",
                "These results were made before version 1.0.3, which stores "
                "the water volume and formation time each chart needs: "
                + ", ".join(missing) + ". Run them again to add them.")

    def card(title, sub, data, xt, yt, key, lx, ly, one=False):
        with st.container(border=True):
            section(title, sub)
            chart(data, xt, yt, key, kind="scatter", log_x=lx, log_y=ly,
                  one_to_one=one, height=300, colours=cols, faint=faint)

    if not is_tailings():
        pans = water_case_panels(pt, extra)
        c1, c2 = st.columns(2, gap="large")
        for col, idxs in ((c1, (0, 2)), (c2, (1, 3))):
            with col:
                for k in idxs:
                    pn = pans[k]
                    card(pn["title"], pn["sub"], pn["data"], pn["xlabel"],
                         pn["ylabel"], pn["key"], pn["logx"], pn["logy"])
        st.caption(WATER_CASE_NOTE)
        refs = WATER_CASE_REFS
    else:
        tr = tl_for(df)
        tr = tr if (tr and tr.get("ok")) else None
        vout = tr["total_m3"] if tr else pt.get("Vout")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            card("Tailings released against free water released",
                 "Rana et al. (2021) database: tailings = total outflow − "
                 "supernatant pond. Eleven events (one of the twelve in Rana "
                 "et al. 2023, Fig. 5, is not reconstructible).",
                 CASES.tailings_vs_free_water(
                     {"x": tr["free_water_m3"], "y": tr["tailings_m3"]} if tr else None),
                 "Free water released (m³)", "Tailings released (m³)", "c_tf",
                 True, True, one=True)
            card("Breach height against total outflow", "Adria et al. (2023).",
                 CASES.tailings_breach_height_vs_outflow({"x": vout, "y": pt.get("Hb")}),
                 "Total outflow volume (m³)", "Breach height (m)", "c_thb", True, False)
        with c2:
            card("Mean breach width against total outflow",
                 "Rana et al. (2021); Adria et al. (2023).",
                 CASES.tailings_width_vs_outflow({"x": vout, "y": pt.get("Bave")}),
                 "Total outflow volume (m³)", "Mean breach width (m)", "c_tbw",
                 True, True)
            if not tr:
                callout("info", "Add the tailings release.",
                        "Set up the Tailings release page to place your result "
                        "on the tailings against free water chart.")
        refs = ["rana2021", "adria2023"]
    with st.container(border=True):
        section("References")
        for k in refs:
            st.markdown(DATA.CITATIONS[k])


# =====================================================================
# EXPORT
# =====================================================================
def page_export():
    df = st.session_state.result_df
    with st.container(border=True):
        section("Report details", "Shown on the title page and in every page header.")
        for k, v in {"keep_rep_title": f"DLBreach breach analysis — {P.get('case_name', '')}",
                     "keep_rep_sub": "Report appendix", "keep_rep_by": ABOUT.AUTHOR,
                     "keep_rep_org": "", "keep_rep_date": date.today().isoformat(),
                     "keep_rep_hdr": "Appendix", "keep_rep_pre": "",
                     "keep_rep_notes": ""}.items():
            seed(k, v)
        c1, c2 = st.columns(2)
        c1.text_input("Title", key="keep_rep_title", help=HLP.h("rep_title"))
        c2.text_input("Subtitle", key="keep_rep_sub", help=HLP.h("rep_sub"))
        c1.text_input("Prepared by", key="keep_rep_by", help=HLP.h("rep_by"))
        c2.text_input("Organisation", key="keep_rep_org", help=HLP.h("rep_org"))
        c1.text_input("Date", key="keep_rep_date", help=HLP.h("rep_date"))
        c2.text_input("Header, right side", key="keep_rep_hdr", help=HLP.h("rep_hdr"))
        c1.text_input("Page number prefix", key="keep_rep_pre", help=HLP.h("rep_pre"))
        st.text_area("Notes for the title page", key="keep_rep_notes", height=90,
                     help=HLP.h("rep_notes"))
    tlr = tl_for(df)
    tlr = tlr if (tlr and tlr.get("ok")) else None
    avail = {"title": True, "inputs": True, "section": True,
             "hydrograph": df is not None, "development": df is not None,
             "face": df is not None, "geomtable": df is not None,
             "tailings": bool(tlr and is_tailings()),
             "scenarios": bool(st.session_state.get("scen_store")),
             "mc": bool(st.session_state.get("mc_store")),
             "mc_env": bool(st.session_state.get("mc_store")),
             "mc_drivers": any(d.get("cols") for d in
                               (st.session_state.get("mc_store") or {}).values()),
             "cases": df is not None or bool(case_selection()[1]), "cards": True}
    if df is not None:
        stale_notice()
    with st.container(border=True):
        section("Contents", "Sections that need results are available once "
                "the run, scenarios or Monte Carlo have been done.")
        chosen, cols = [], st.columns(2)
        secs = {k: v for k, v in REPORT_SECTIONS.items()
                if SOLID_WASTE_ENABLED or k != "tailings"}
        prev = st.session_state.setdefault("rsec_avail_prev", {})
        for i, (k, lab) in enumerate(secs.items()):
            seed(f"keep_rsec_{k}", avail.get(k, False))
            # a section that has just become available starts ticked
            if avail.get(k, False) and not prev.get(k, True):
                st.session_state[f"keep_rsec_{k}"] = True
            prev[k] = avail.get(k, False)
            if cols[i % 2].checkbox(lab, key=f"keep_rsec_{k}",
                                    help=None if avail.get(k, False) else
                                    "Needs results that are not available yet.",
                                    disabled=not avail.get(k, False)) and avail.get(k):
                chosen.append(k)
        seed("keep_rep_gint", 10.0)
        st.number_input("Breach geometry table interval (min)", min_value=0.5,
                        step=1.0, key="keep_rep_gint", help=HLP.h("rep_gint"))
        st.caption(f"Elevations will be given in {datum()[1]}.")
    seed("keep_rep_fmt", "PDF")
    fmt = st.radio("Format", ["PDF", "Word"], key="keep_rep_fmt", horizontal=True,
                   help=HLP.h("rep_fmt"))
    if st.button(f"Build {fmt}", type="primary", disabled=not chosen):
        off, lab = datum()
        ex = {"z_off": off, "z_lab": lab, "inputs_table": inputs_table(),
              "input_text": build_input_text(P),
              "geom_interval_min": st.session_state.keep_rep_gint,
              "cone": cone_overlay(),
              "q_total": tlr["Q_total"] if tlr else None}
        if tlr and is_tailings():
            ex["tailings"] = pd.DataFrame([
                ("Method", {"fm": "Fontaine and Martin (2015)",
                            "cone": "Cone of depression",
                            "ratio": "Ratio of free water"}[tlr["method"]]),
                ("Free water (m³)", f"{tlr['free_water_m3']:,.0f}"),
                ("Tailings released (m³)", f"{tlr['tailings_m3']:,.0f}"),
                ("  of which solids (m³)", f"{tlr['solids_m3']:,.0f}"),
                ("  of which interstitial water (m³)", f"{tlr['interstitial_m3']:,.0f}"),
                ("Total release (m³)", f"{tlr['total_m3']:,.0f}"),
                ("Bulking factor", f"{tlr['bulking']:.2f}"),
                ("Cv of release", f"{tlr['Cv'] * 100:.1f} %")],
                columns=["Quantity", "Value"])
        sc = st.session_state.get("scen_store")
        if sc:
            ex["scenario_summary"] = sc["summary"].rename(columns={
                **SCEN_OUT, "tailings_m3": "Tailings released (m³)",
                "peak_total": "Bulked peak (m³/s)"}).round(2)
            ex["scenario_hydros"] = sc["hydros"]
        mc = st.session_state.get("mc_store")
        if mc:
            ex["mc_table"] = mc_summary_table(mc)
            ex["mc_env"], ex["mc_drivers"] = mc_report_data(mc)
        pt_c, extra_c, cols_c, faint_c, _ = case_selection()
        if pt_c or extra_c:
            shown = (["the single run is the black-edged diamond"] if pt_c else []) \
                + (["scenario runs are green triangles"]
                   if any(e["Series"] == CASE_SCEN for e in extra_c) else []) \
                + (["Monte Carlo realisations are small light points"]
                   if faint_c else [])
            ex["cases"] = {
                "panels": [dict(pn, styles=case_report_styles(cols_c, faint_c))
                           for pn in water_case_panels(pt_c, extra_c)],
                "refs": [DATA.CITATIONS[k] for k in WATER_CASE_REFS],
                "note": ("Measured outcomes only; " + "; ".join(shown)
                         + ". No regression lines are drawn. "
                         + (MC_CASE_NOTE + " " if faint_c else "")
                         + CASES.COMPLETENESS_NOTE + " " + WATER_CASE_NOTE)}
        meta = {"title": st.session_state.keep_rep_title,
                "subtitle": st.session_state.keep_rep_sub,
                "prepared_by": st.session_state.keep_rep_by,
                "organisation": st.session_state.keep_rep_org,
                "date": st.session_state.keep_rep_date,
                "header_right": st.session_state.keep_rep_hdr,
                "page_prefix": st.session_state.keep_rep_pre,
                "notes": st.session_state.keep_rep_notes}
        with st.spinner("Building the report…"):
            try:
                if fmt == "Word":
                    st.session_state.report_file = (
                        build_docx(chosen, meta, P, df, ex), "docx",
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document")
                else:
                    st.session_state.report_file = (
                        build_report(chosen, meta, P, df, ex), "pdf",
                        "application/pdf")
            except ModuleNotFoundError as exc:
                st.session_state.report_file = None
                callout("warn", f"Word export needs the {exc.name} package.",
                        "Close the dashboard and start it again with Launch "
                        "DLBreach Dashboard.bat, which installs missing "
                        "packages. Or, from a terminal in the dashboard folder: "
                        "<code>.venv\\Scripts\\activate</code> then "
                        "<code>pip install -r requirements.txt</code>.")
    if st.session_state.get("report_file"):
        data, ext, mime = st.session_state.report_file
        st.download_button(f"Download {ext.upper()}", data,
                           file_name=f"{P['case_name'] or 'case'}_appendix.{ext}",
                           mime=mime, type="primary")


# =====================================================================
# DISPATCH AND FOOTER
# =====================================================================
def _chapter_state(name: str) -> str:
    """done, current or todo, for the contents panel."""
    if name == PAGE:
        return "current"
    seen = name in st.session_state.get("visited", set())
    rs = result_state()
    done = {
        "About": seen,
        "Project": seen and (BROWSER or exe_status()[1]),
        "Model setup": seen and not water_checks(),
        "Tailings release": seen,
        "Single run": rs in ("current", "loaded"),
        "Sensitivity scenarios": bool(st.session_state.get("scen_store")),
        "Monte Carlo": bool(st.session_state.get("mc_store")),
        "Case histories": seen and rs != "none",
        "Export": bool(st.session_state.get("report_file")),
    }.get(name, False)
    return "done" if done else "todo"


def _contents_panel():
    """The contents of the dashboard, read like the contents of a book: one
    section per page, a marker for sections done, and the headings of the
    open section."""
    states = {n: _chapter_state(n) for n in _names}
    n_done = sum(1 for v in states.values() if v == "done")
    css = []
    for i, n in enumerate(_names, start=1):
        k, stt = f".st-key-toc .st-key-toc_{i} .stButton", states[n]
        mark = "\\2713" if stt == "done" else str(i)
        style = {"done": "background:#2E7D4F;border-color:#2E7D4F;color:#FFFFFF;",
                 "current": "background:#17324D;border-color:#17324D;color:#FFFFFF;",
                 "todo": ""}[stt]
        css.append(f'{k} button::before {{content:"{mark}";{style}}}')
        if stt == "current":
            css.append(f"{k} button {{background:#FFFFFF !important;"
                       f"border-color:#C9D6E2 !important;}}"
                       f"{k} button p {{font-weight:700 !important;color:#17324D !important;}}")
    css.append(f".st-key-toc .st-key-toc_{len(_names)} .stButton::after {{display:none;}}")
    st.markdown("<style>" + "".join(css) + "</style>", unsafe_allow_html=True)
    pct = 100 * n_done / max(len(_names), 1)
    st.markdown(
        f'<div class="dlb-toc-head"><p class="t">Contents</p>'
        f'<p class="c">Work through the sections in order.</p>'
        f'<div class="dlb-prog"><div style="width:{pct:.0f}%"></div></div>'
        f'<p class="dlb-prog-lab">{n_done} of {len(_names)} sections done</p></div>',
        unsafe_allow_html=True)
    try:
        box = st.container(key="toc")
    except TypeError:
        box = st.container()
    with box:
        for i, n in enumerate(_names, start=1):
            st.button(n, key=f"toc_{i}", on_click=_go_to, args=(PAGES[i - 1],),
                      use_container_width=True,
                      help=ABOUT.PAGE_GUIDE.get(n, ("",))[0] or None)
            if n == PAGE and UI.RENDERED:
                links = "".join(
                    f'<p><a href="#{a}">'
                    f'{t[4:] if t[:1].isdigit() and t[1:4] == " · " else t}</a></p>'
                    for t, a in UI.RENDERED)
                st.markdown(f'<div class="dlb-toc-sub"><p class="lab">On this '
                            f'page</p>{links}</div>', unsafe_allow_html=True)



def _contained(fn, where: str):
    """Run part of the page so that an error is reported on screen instead
    of stopping the session; inputs and results stay in place."""
    try:
        fn()
    except Exception as exc:                            # noqa: BLE001
        # Streamlit's own control flow (st.rerun, st.stop) must pass
        if type(exc).__name__ in ("RerunException", "StopException"):
            raise
        callout("warn", f"Something went wrong on {where}.",
                "Your inputs and results are kept. Try the last action again; "
                "if it repeats, send the details below to "
                f"{ABOUT.CONTACT_EMAIL}.")
        with st.expander("Details"):
            st.exception(exc)


if not st.session_state.get("_session_started"):
    # the first run of a new session: offer the last inputs, but do not
    # overwrite the autosave with the starter dam until the user decides
    st.session_state["_session_started"] = True
    st.session_state["_autosaved"] = None
    st.session_state["_fresh"] = AUTOSAVE.is_file() and not BROWSER
_contained(restore_offer, "the restore offer")
page_intro(PAGE)
_contained({"About": page_about, "Project": page_project, "Model setup": page_setup,
            "Tailings release": page_tailings, "Single run": page_single,
            "Sensitivity scenarios": page_scenarios, "Monte Carlo": page_mc,
            "Case histories": page_cases, "Export": page_export}[PAGE], PAGE)
with _status_slot.container():
    _contained(_status_strip, "the status strip")
with _toc_slot.container():
    _contained(_contents_panel, "the contents panel")
_autosave()

st.divider()
_i = PAGES.index(page)
f1, f2, f3 = st.columns([1, 2, 1])
if _i > 0:
    f1.button(f"← {PAGES[_i - 1].split('. ', 1)[1]}", on_click=_go, args=(-1,),
              use_container_width=True, key="nav_prev")
# In the browser version, name the Streamlit build in use: the contents
# panel styling depends on it, so it is the first thing to check if the
# page looks different from the local version.
_build = f" · browser version, Streamlit {st.__version__}" if BROWSER else ""
f2.markdown(f'<div class="dlb-foot">Page {_i + 1} of {len(PAGES)} · {PAGE}{_build}</div>',
            unsafe_allow_html=True)
if _i < len(PAGES) - 1:
    f3.button(f"{PAGES[_i + 1].split('. ', 1)[1]} →", type="primary", on_click=_go,
              args=(1,), use_container_width=True, key="nav_next")
