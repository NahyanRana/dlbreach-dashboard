"""
dlbreach_io.py
--------------
Core input/output handling for DLBreach (Wu, 2016, version 2016.4).

Three jobs:
  1. build_input_text()  -> turn a dictionary of parameters into a valid
                            casename.txt card file
  2. run_case()          -> run DLBreach.exe on that file and return the
                            output file path
  3. parse_out()         -> read casename.out into a pandas DataFrame

Nothing here knows about Streamlit. That keeps this file testable on its
own, which matters: if something breaks, you can check whether it is the
model wrapper or the interface.

Units are SI throughout, as DLBreach requires.
Elevations are referenced to the embankment base.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# Output file columns, in the order DLBreach writes them.
# Source: Wu (2016), "Inputs and Outputs of DLBreach", Model Outputs.
# ---------------------------------------------------------------------
OUT_COLUMNS = [
    "time_hr",              # time (hours)
    "Q_breach",             # breach flow discharge (m3/s)
    "Q_spillway",           # flow through spillways/gates on embankment (m3/s)
    "wsl_up",               # upstream water level above embankment base (m)
    "wsl_down",             # downstream water level (m)
    "breach_bottom_elev",   # breach bottom elevation (m)
    "breach_bottom_width",  # breach bottom width (m)
    "breach_top_width",     # breach top width (m)
    "breach_flow_area",     # flow area at the breach (m2)
    "breach_side_slope",    # breach side slope (V/H)
    "cum_volume",           # cumulative water volume, breach + spillway (m3)
    "Qs_up",                # sediment discharge upstream (m3/s)
    "Qs_down",              # sediment discharge downstream (m3/s)
]


# ---------------------------------------------------------------------
# 1. Building the input card file
# ---------------------------------------------------------------------

def _card(name: str, *values, comment: str = "") -> str:
    """Format a single DLBreach card line."""
    if values:
        body = ", ".join(_fmt(v) for v in values)
        line = f"{name} {body}"
    else:
        line = name
    if comment:
        line = f"{line} ! {comment}"
    return line


def _fmt(v) -> str:
    """Format a number the way DLBreach expects (real values keep a decimal)."""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        # Keep a decimal point and avoid scientific notation. DLBreach reads
        # these as Fortran reals, so "20.0" is safer than "20", and large
        # values such as reservoir volumes must not come out as 5e+06.
        # Values are written in full (shortest exact form), so a loaded
        # file's numbers are written back unchanged.
        if v != 0 and abs(v) < 1e-4:
            s = f"{v:.12f}".rstrip("0")       # very small values
        else:
            s = repr(v)
            if "e" in s or "E" in s:          # very large values
                s = f"{v:.6f}".rstrip("0")
        return s + "0" if s.endswith(".") else s
    return str(v)


def build_input_text(p: dict) -> str:
    """
    Build the full text of a DLBreach casename.txt file.

    `p` is a flat dictionary of parameters. See DEFAULT_PARAMS below for
    the keys and their meaning. Only the cards that are actually needed
    for the selected breach mode are written, which keeps the file clean
    and avoids DLBreach reading cards that do not apply.
    """
    L: list[str] = []

    L.append("! DLBreach input file")
    L.append(f"! Case: {p.get('case_name', 'case')}")
    if p.get("notes"):
        for line in str(p["notes"]).splitlines():
            L.append(f"! {line}")
    L.append("")

    # --- time control -------------------------------------------------
    L.append("! ---- Time control ----")
    L.append(_card("Time_Step", float(p["time_step"]), comment="in sec"))
    L.append(_card("Simulation_Period",
                   float(p["sim_start"]), float(p["sim_end"]),
                   comment="in sec"))
    L.append("")

    # --- water properties ---------------------------------------------
    L.append("! ---- Water properties ----")
    L.append(_card("Water_Density", float(p.get("water_density", 1000.0)),
                   comment="in kg/m^3"))
    L.append(_card("Water_Kinematic_Viscosity",
                   float(p.get("water_viscosity", 1.0e-6)), comment="m^2/s"))
    L.append("")

    # --- embankment geometry -----------------------------------------
    L.append("! ---- Embankment geometry ----")
    L.append(_card("Embankment_Height", float(p["emb_height"]), comment="in m"))
    L.append(_card("Embankment_Crest_Width", float(p["emb_crest_width"]),
                   comment="in m"))
    L.append(_card("Embankment_Upstream_Slope", float(p["emb_us_slope"]),
                   comment="V/H"))
    L.append(_card("Embankment_Downstream_Slope", float(p["emb_ds_slope"]),
                   comment="V/H"))
    L.append(_card("Embankment_Length", float(p["emb_length"]), comment="in m"))
    L.append("")

    # --- breach mode --------------------------------------------------
    L.append("! ---- Breach mode ----")
    mode = int(p["breach_mode"])
    L.append(_card("Breach_Mode", mode,
                   comment="1 = overtopping, 2 = piping"))
    # Cards for the other failure mode are written only if the loaded file
    # had them (DLBreach reads the ones for the chosen mode), so a loaded
    # file is written back card for card.
    had = set(p.get("loaded_cards") or [])
    loss = p.get("pipe_loss_card") or "Pipe_Local_Head_Loss_Coefficient"
    if mode == 1 or "Overtopping_Mode" in had:
        L.append(_card("Overtopping_Mode", int(p["overtopping_mode"]),
                       comment="1 = surface erosion, 2 = headcut, 3 = clay core"))
    if mode == 1 or "Initial_Overtopping_Breach" in had:
        L.append(_card("Initial_Overtopping_Breach",
                       float(p["pilot_depth"]), float(p["pilot_width"]),
                       comment="depth, width in m"))
    if mode == 2 or "Initial_Piping_Breach" in had:
        L.append(_card("Initial_Piping_Breach",
                       float(p["pipe_depth"]), float(p["pipe_width"]),
                       comment="depth below crest, width in m"))
    losses = [c for c in ("Pipe_Local_Head_Loss_Coefficient",
                          "Pipe_Entrance_Head_Loss_Coef") if c in had]
    if mode == 2 and not losses:
        losses = [loss]
    for c in losses:                       # every head loss card loaded
        L.append(_card(c, float(p.get("pipe_head_loss", 0.05))))
    L.append(_card("Breach_Location", float(p["breach_location"]),
                   comment="2.0 = two-sided, 1.0 = one-sided"))
    L.append(_card("Hard_Bottom_Elevation", float(p["hard_bottom_elev"]),
                   comment="in m, negative below embankment base"))
    if "Breach_Manning_n" not in (p.get("omit_cards") or []):
        L.append(_card("Breach_Manning_n", float(p["manning_n"])))
    if p.get("side_slope_constant") not in (None, "", 0):
        L.append(_card("Breach_Side_Slope_Constant",
                       float(p["side_slope_constant"]), comment="V/H"))
    L.append("")

    # --- embankment sediment -----------------------------------------
    L.append("! ---- Embankment sediment ----")
    sed_type = int(p["sediment_type"])  # 1 noncohesive, 2 cohesive
    L.append(_card("Noncohesive_or_Cohesive_Sediment", sed_type,
                   comment="1 = noncohesive, 2 = cohesive"))
    L.append(_card("Sediment_Diameter", float(p["sed_d50"]), comment="in m"))
    L.append(_card("Sediment_Specific_Gravity", float(p["sed_sg"])))
    L.append(_card("Sediment_Porosity", float(p["sed_porosity"])))
    L.append(_card("Sediment_Clay_Content", float(p["sed_clay"]),
                   comment="fraction 0-1"))
    L.append(_card("Sediment_Cohesion", float(p["sed_cohesion"]), comment="in Pa"))
    L.append(_card("Sediment_Internal_Friction", float(p["sed_friction"]),
                   comment="tan(phi)"))

    # Both parameter sets are written by default. DLBreach uses whichever
    # applies to the selected sediment type and ignores the other, and real
    # project input files commonly carry both. The adaptation length card is
    # optional: when a loaded file omitted it, it stays omitted so that the
    # model's own default is used and a benchmark run is reproduced exactly.
    if p.get("include_adaptation_lambda", True):
        L.append(_card("Noncohesive_Sed_Adaptation_Lamda",
                       float(p["adaptation_lambda"]),
                       comment="6.0 field, 3.0 laboratory"))
    if p.get("include_cohesive_params", True) or int(p.get("sediment_type", 1)) == 2:
        L.append(_card("Cohesive_Soil_Erosion_kd", float(p["kd"]),
                       comment="cm^3/N-s"))
        L.append(_card("Cohesive_Soil_Erosion_Tauc", float(p["tauc"]),
                       comment="in Pa"))
    L.append("")

    # --- clay core (Wu 2016, Clay Core Parameters) ---------------------
    # DLBreach uses these cards for overtopping submode 3 (composite
    # embankment with a clay core). They are written whenever the case has
    # a core, so a loaded file keeps them whatever mode is chosen.
    if p.get("has_core"):
        L.append("! ---- Clay core ----")
        # A loaded core writes the cards its file gave (and any the user has
        # since edited); a new core writes them all, kd and tauc for a
        # cohesive core only.
        only = set(p.get("core_cards") or [])
        for card, key, unit in CORE_CARDS:
            if only and card not in only:
                continue
            if not only and key in ("core_kd", "core_tauc") \
                    and int(p.get("core_sed_type", 2)) != 2:
                continue
            v = p.get(key, DEFAULT_PARAMS[key])
            v = int(v) if key == "core_sed_type" else float(v)
            L.append(_card(card, v, comment=unit))
        L.append("")

    # --- headcut model, for overtopping mode 2 (or as loaded) ----------
    if (mode == 1 and int(p["overtopping_mode"]) == 2) or "Headcut_Model" in had:
        L.append("! ---- Headcut erosion ----")
        L.append(_card("Headcut_Model", int(p["headcut_model"]),
                       float(p["headcut_coef"]),
                       comment="model 2 default, Ct ~ 0.0025-0.0049"))
        L.append("")

    # --- initial water levels ----------------------------------------
    L.append("! ---- Water levels ----")
    L.append(_card("Initial_Up&Downstream_WSL",
                   float(p["wsl_up_initial"]), float(p["wsl_down_initial"]),
                   comment="in m above embankment base"))

    # --- upstream reservoir routing -----------------------------------
    res_method = int(p["reservoir_method"])
    if not p.get("write_reservoir", True):
        # the loaded file gave the upstream boundary another way (for
        # example a water level time series), kept among the cards below
        pass
    elif res_method == 2:
        # volume and surface area known at a given level
        L.append(_card("Upstream_Reservoir", 2,
                       float(p["res_VH"]), float(p["res_AH"]), float(p["res_H"])))
    elif res_method == 3:
        # volume known at a given level, exponent m supplied
        L.append(_card("Upstream_Reservoir", 3,
                       float(p["res_VH"]), float(p["res_H"]), float(p["res_m"])))
    elif res_method == 4:
        # surface area known at a given level, exponent m supplied
        L.append(_card("Upstream_Reservoir", 4,
                       float(p["res_AH"]), float(p["res_H"]), float(p["res_m"])))
    elif res_method == 0:
        pairs = p["res_curve"]  # list of (z, V)
        L.append(f"Upstream_Reservoir {' ' * 18}0, {len(pairs)}")
        for z, v in pairs:
            L.append(f"{' ' * 37}{_fmt(float(z))}, {_fmt(float(v))}")
    elif res_method == 1:
        pairs = p["res_curve"]  # list of (z, As)
        L.append(f"Upstream_Reservoir {' ' * 18}1, {len(pairs)}")
        for z, a in pairs:
            L.append(f"{' ' * 37}{_fmt(float(z))}, {_fmt(float(a))}")

    # --- downstream boundary ------------------------------------------
    if p.get("downstream_mode", "channel") == "channel":
        L.append(_card("Downstream_Channel_Flow_Out",
                       float(p["ds_channel_width"]),
                       float(p["ds_channel_slope"]),
                       float(p["ds_channel_n"]),
                       comment="width, slope, Manning n"))
    L.append("")

    extra = [c for c in (p.get("extra_cards") or []) if str(c).strip()]
    if extra:
        L.append("! ---- Cards from the loaded file, written unchanged ----")
        L.append("! (the dashboard does not edit these; see Model setup)")
        for c in extra:
            L.append(str(c).rstrip())
            L.append("")

    L.append("")
    L.append("END_PARAMETERS")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------
# 1b. Reading an existing input card file
# ---------------------------------------------------------------------

# Clay core cards, in the order of the DLBreach file format guide:
# (card, parameter key, comment written with it)
CORE_CARDS = [
    ("Core_Height", "core_height", "in m"),
    ("Core_Crest_Width", "core_crest_width", "in m"),
    ("Core_Upstream_Slope", "core_us_slope", "V/H"),
    ("Core_Downstream_Slope", "core_ds_slope", "V/H"),
    ("Core_Center_Location", "core_center",
     "in m, core crest centre from embankment crest centre, + downstream"),
    ("Core_Manning_n", "core_manning_n", "when the core is exposed to the flow"),
    ("Core_Sediment_Diameter", "core_d50", "in m"),
    ("Core_Sediment_Specific_Gravity", "core_sg", ""),
    ("Core_Sediment_Porosity", "core_porosity", ""),
    ("Core_Sediment_Clay_Content", "core_clay", "fraction 0-1"),
    ("Core_Sediment_Cohesion", "core_cohesion", "in Pa"),
    ("Core_Sediment_Internal_Friction", "core_friction", "tan(phi)"),
    ("Core_Noncohesive_or_Cohesive", "core_sed_type", "1 = noncohesive, 2 = cohesive"),
    ("Core_Cohesive_Erosion_kd", "core_kd", "cm^3/N-s"),
    ("Core_Cohesive_Erosion_Tauc", "core_tauc", "in Pa"),
]

# card name -> (parameter key(s), type)
_CARD_MAP = {
    "Time_Step": (["time_step"], float),
    "Simulation_Period": (["sim_start", "sim_end"], float),
    "Water_Density": (["water_density"], float),
    "Water_Kinematic_Viscosity": (["water_viscosity"], float),
    "Embankment_Height": (["emb_height"], float),
    "Embankment_Crest_Width": (["emb_crest_width"], float),
    "Embankment_Upstream_Slope": (["emb_us_slope"], float),
    "Embankment_Downstream_Slope": (["emb_ds_slope"], float),
    "Embankment_Length": (["emb_length"], float),
    "Breach_Mode": (["breach_mode"], int),
    "Overtopping_Mode": (["overtopping_mode"], int),
    "Initial_Overtopping_Breach": (["pilot_depth", "pilot_width"], float),
    "Initial_Piping_Breach": (["pipe_depth", "pipe_width"], float),
    "Pipe_Local_Head_Loss_Coefficient": (["pipe_head_loss"], float),
    "Pipe_Entrance_Head_Loss_Coef": (["pipe_head_loss"], float),
    "Breach_Location": (["breach_location"], float),
    "Hard_Bottom_Elevation": (["hard_bottom_elev"], float),
    "Breach_Manning_n": (["manning_n"], float),
    "Breach_Side_Slope_Constant": (["side_slope_constant"], float),
    "Noncohesive_or_Cohesive_Sediment": (["sediment_type"], int),
    "Sediment_Diameter": (["sed_d50"], float),
    "Sediment_Specific_Gravity": (["sed_sg"], float),
    "Sediment_Porosity": (["sed_porosity"], float),
    "Sediment_Clay_Content": (["sed_clay"], float),
    "Sediment_Cohesion": (["sed_cohesion"], float),
    "Sediment_Internal_Friction": (["sed_friction"], float),
    "Noncohesive_Sed_Adaptation_Lamda": (["adaptation_lambda"], float),
    "Cohesive_Soil_Erosion_kd": (["kd"], float),
    "Cohesive_Soil_Erosion_Tauc": (["tauc"], float),
    "Initial_Up&Downstream_WSL": (["wsl_up_initial", "wsl_down_initial"], float),
    "Downstream_Channel_Flow_Out": (["ds_channel_width", "ds_channel_slope",
                                     "ds_channel_n"], float),
}
_CARD_MAP.update({c: ([k], int if k == "core_sed_type" else float)
                  for c, k, _ in CORE_CARDS})


# Cards the dashboard reads into its own inputs and writes itself. Any other
# card in a loaded file is kept and written back unchanged.
_EDITED_CARDS = set(_CARD_MAP) | {"Headcut_Model", "Upstream_Reservoir"}
# card names are matched without regard to case, then written in this form
_CANON = {n.upper(): n for n in _EDITED_CARDS}
_CARD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_&]*$")
_FILE_REF = re.compile(r"^[^\s]+\.(txt|dat|csv|out|prn)$", re.I)


def _num(tok: str):
    try:
        return float(tok)
    except ValueError:
        return None


def split_cards(text: str) -> list[dict]:
    """
    Split a DLBreach input file into cards. A card starts with a name
    (Embankment_Height, Upstream_WSL_Time_Series, ...); numeric lines that
    follow (tables, time series) belong to it. Comment-only and blank lines
    belong to no card. Each card keeps its original lines verbatim, its
    numbers, and any words (such as data file names).
    """
    cards: list[dict] = []
    for raw in text.splitlines():
        s = raw.split("!")[0].strip()
        if not s:
            continue
        toks = s.replace(",", " ").split()
        if toks[0].upper().startswith("END_PARAMETERS"):
            break
        if _CARD_NAME.match(toks[0]) and _num(toks[0]) is None:
            cards.append({"name": toks[0], "lines": [raw.rstrip()],
                          "values": [], "words": []})
            toks = toks[1:]
        elif not cards:
            continue                                  # stray data before any card
        else:
            cards[-1]["lines"].append(raw.rstrip())
        for t in toks:
            v = _num(t)
            if v is None:
                cards[-1]["words"].append(t)
            else:
                cards[-1]["values"].append(v)
    return cards


def card_differences(original: str, written: str) -> dict:
    """
    Compare the cards of an input file with those the dashboard writes for
    it. Returns lists of card names: missing (in the file, not written),
    changed (written with different values) and added (written, not in the
    file), plus the number of cards compared.
    """
    ca, cb = split_cards(original), split_cards(written)
    a = {c["name"].upper(): c for c in ca}
    b = {c["name"].upper(): c for c in cb}
    seen, dup = set(), []
    for c in ca:
        u = c["name"].upper()
        if u in seen and c["name"] not in dup:
            dup.append(c["name"])
        seen.add(u)

    def same(x, y):
        if x["words"] != y["words"] or len(x["values"]) != len(y["values"]):
            return False
        return all(abs(u - v) <= 1e-9 * max(1.0, abs(u), abs(v))
                   for u, v in zip(x["values"], y["values"]))

    return {"n": len(ca),
            "missing": [a[n]["name"] for n in a if n not in b],
            "changed": [a[n]["name"] for n in a if n in b and not same(a[n], b[n])],
            "added": [b[n]["name"] for n in b if n not in a],
            "duplicates": dup}


def read_input_file(text: str) -> dict:
    """
    Read an existing DLBreach casename.txt and return a parameter dict
    that the dashboard understands.

    This is the quickest way to reproduce a case you have already run:
    load the file, confirm the regenerated cards match, then vary from
    there. Cards that the dashboard does not yet expose are ignored, so
    always check the generated file before relying on a loaded case.
    """
    p: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        line = raw.split("!")[0].strip()          # drop comments
        if line.upper().startswith("END_PARAMETERS"):
            break                                 # nothing after it is read
        if not line:
            continue

        parts = line.split(None, 1)
        name = _CANON.get(parts[0].upper(), parts[0])
        rest = parts[1] if len(parts) > 1 else ""

        # --- headcut model, two entries ---
        if name == "Headcut_Model":
            vals = [v for v in rest.replace(",", " ").split() if v]
            if vals:
                p["headcut_model"] = int(float(vals[0]))
            if len(vals) > 1:
                p["headcut_coef"] = float(vals[1])
            continue

        # --- reservoir card, may be followed by a table ---
        if name == "Upstream_Reservoir":
            vals = [float(v) for v in rest.replace(",", " ").split() if v]
            if not vals:
                continue
            method = int(vals[0])
            p["reservoir_method"] = method
            if method in (0, 1):
                n_pairs = int(vals[1]) if len(vals) > 1 else 0
                curve = []
                while i < len(lines) and len(curve) < n_pairs:
                    s = lines[i].split("!")[0].strip()
                    i += 1
                    if not s:
                        continue
                    try:
                        a, b = [float(x) for x in s.replace(",", " ").split()[:2]]
                    except (ValueError, IndexError):
                        i -= 1
                        break
                    curve.append((a, b))
                p["res_curve"] = curve
            elif method == 2 and len(vals) >= 4:
                p["res_VH"], p["res_AH"], p["res_H"] = vals[1], vals[2], vals[3]
            elif method == 3 and len(vals) >= 4:
                p["res_VH"], p["res_H"], p["res_m"] = vals[1], vals[2], vals[3]
            elif method == 4 and len(vals) >= 4:
                p["res_AH"], p["res_H"], p["res_m"] = vals[1], vals[2], vals[3]
            continue

        # --- simple scalar cards ---
        if name in _CARD_MAP:
            keys, caster = _CARD_MAP[name]
            vals = [v for v in rest.replace(",", " ").split() if v]
            for k, v in zip(keys, vals):
                try:
                    p[k] = caster(float(v))
                except ValueError:
                    pass

    # Everything the dashboard does not edit is kept, verbatim, and written
    # back unchanged; boundary cards it would otherwise add are left out.
    cards = split_cards(text)
    names = {_CANON.get(c["name"].upper(), c["name"]) for c in cards}
    p["extra_cards"] = ["\n".join(c["lines"]) for c in cards
                        if c["name"].upper() not in _CANON]
    # a segmented Manning's n replaces the single value: do not add one
    uppers = {c["name"].upper() for c in cards}
    p["omit_cards"] = (["Breach_Manning_n"] if "BREACH_MANNING_N_SEGMENTS" in uppers
                       and "BREACH_MANNING_N" not in uppers else [])
    # card names written in their standard form (DLBreach may match exactly)
    p["renamed_cards"] = sorted({f"{c['name']} → {_CANON[c['name'].upper()]}"
                                 for c in cards if c["name"].upper() in _CANON
                                 and c["name"] != _CANON[c["name"].upper()]})
    p["write_reservoir"] = "Upstream_Reservoir" in names
    p["downstream_mode"] = ("channel" if "Downstream_Channel_Flow_Out" in names
                            else "from_file")
    # the edited cards the file gave, so cards for the other failure mode
    # are written back as loaded
    p["loaded_cards"] = sorted(n for n in names if n in _EDITED_CARDS)
    p["include_cohesive_params"] = bool(
        names & {"Cohesive_Soil_Erosion_kd", "Cohesive_Soil_Erosion_Tauc"})
    # card names are matched without regard to case, so the adaptation
    # length card is found however it is written
    p["include_adaptation_lambda"] = "Noncohesive_Sed_Adaptation_Lamda" in names
    core_names = [c for c, _, _ in CORE_CARDS]
    p["has_core"] = bool(names & set(core_names))
    # the core cards the file gives are the ones written back
    p["core_cards"] = [c for c in core_names if c in names]
    p["pipe_loss_card"] = ("Pipe_Entrance_Head_Loss_Coef"
                           if "Pipe_Entrance_Head_Loss_Coef" in names else "")
    refs = sorted({w.strip("'\"") for c in cards if c["name"].upper() not in _CANON
                   for w in c["words"] if _FILE_REF.match(w.strip("'\""))})
    # references the dashboard cannot place in the run folder (absolute
    # paths, "..") are left to DLBreach and reported, not asked for
    p["data_file_refs"] = [r for r in refs if data_file_relpath(r) is not None]
    p["data_file_refused"] = [r for r in refs if data_file_relpath(r) is None]
    # leading comment lines become the notes (not the dashboard's own header)
    notes = []
    for raw in text.splitlines():
        t = raw.strip()
        if not t:
            continue
        if not t.startswith("!"):
            break
        t = t.lstrip("!").strip()
        if t and t != "DLBreach input file" and not t.startswith("Case:") \
                and not t.startswith("----"):
            notes.append(t)
    p["notes"] = "\n".join(notes)
    return p




def run_case(exe_path: str | Path,
             input_text: str,
             case_name: str = "case",
             work_dir: str | Path | None = None,
             timeout: int = 600,
             data_files: dict | None = None) -> dict:
    """
    Run DLBreach on a single case.

    DLBreach requires the input file to sit in the same directory as the
    executable, and it asks for the case name on screen, so the name is
    piped to standard input.

    Returns a dict with keys: ok, out_path, stdout, stderr, work_dir.
    """
    exe_path = Path(exe_path).resolve()
    # A folder is accepted: look for the executable inside it. This is a
    # common slip and the resulting error is otherwise cryptic.
    if exe_path.is_dir():
        found = list(exe_path.glob("*.exe"))
        if not found:
            raise FileNotFoundError(
                f"{exe_path} is a folder and contains no .exe file. "
                "Give the full path to DLBreach.exe itself.")
        exe_path = found[0]
    if not exe_path.is_file():
        raise FileNotFoundError(f"DLBreach executable not found: {exe_path}")

    created_temp = work_dir is None
    work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="dlb_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    # copy the executable next to the input file
    local_exe = work_dir / exe_path.name
    if not local_exe.exists():
        shutil.copy2(exe_path, local_exe)

    # data files the input refers to by name (water level series, waves);
    # one named like this run's own input or output would be overwritten
    own = {f"{case_name}.txt".lower(), f"{case_name}.out".lower()}
    clash = [f for f in (data_files or {})
             if (data_file_relpath(f) or Path("")).as_posix().lower() in own]
    if clash:
        return {"ok": False, "out_path": None, "stdout": "",
                "stderr": (f"The data file {clash[0]} has the same name as this "
                           f"run's own files ({case_name}). Rename the case."),
                "work_dir": work_dir, "created_temp": created_temp}
    for fname, content in (data_files or {}).items():
        write_data_file(work_dir, fname, content)

    txt_path = work_dir / f"{case_name}.txt"
    txt_path.write_text(input_text, encoding="ascii", errors="replace")

    out_path = work_dir / f"{case_name}.out"
    if out_path.exists():
        out_path.unlink()

    try:
        proc = subprocess.run(
            [str(local_exe)],
            input=f"{case_name}\n",
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            timeout=timeout,
        )
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return {"ok": False, "out_path": None, "stdout": "",
                "stderr": f"Timed out after {timeout} s", "work_dir": work_dir,
                "created_temp": created_temp}

    ok = out_path.exists() and out_path.stat().st_size > 0
    return {"ok": ok,
            "out_path": out_path if ok else None,
            "stdout": stdout,
            "stderr": stderr if stderr else ("" if ok else f"return code {rc}"),
            "work_dir": work_dir,
            "created_temp": created_temp}


# ---------------------------------------------------------------------
# 3. Reading the output file
# ---------------------------------------------------------------------

def data_file_relpath(name: str) -> Path | None:
    """The path, relative to the run folder, at which DLBreach will look for
    a data file the input names. Sub-folders are kept ("data\\tide.txt");
    absolute paths, drive letters and ".." are refused (None)."""
    raw = str(name).strip().strip("'\"")
    if raw.startswith(("/", "\\")):
        return None                                 # absolute path
    parts = [x for x in re.split(r"[\\/]+", raw) if x not in ("", ".")]
    if not parts or any(x == ".." for x in parts) or ":" in parts[0]:
        return None
    return Path(*parts)


def write_data_file(folder: Path, name: str, content) -> None:
    """Write a data file where the input expects it, inside the run folder."""
    rel = data_file_relpath(name)
    if rel is None:
        return
    target = Path(folder) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    target.write_bytes(data)


def parse_out(path: str | Path) -> pd.DataFrame:
    """
    Read a DLBreach casename.out file into a DataFrame.

    The file is ASCII with 13 numeric columns. Header or banner lines are
    skipped by testing whether a line parses as numbers, which is more
    robust than assuming a fixed number of header rows.
    """
    rows = []
    with open(path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.replace(",", " ").split()
            try:
                vals = [float(x) for x in parts]
            except ValueError:
                continue          # header or text line
            if len(vals) < 3:
                continue          # not a data row
            rows.append(vals)

    if not rows:
        raise ValueError(f"No numeric data found in {path}")

    ncol = max(len(r) for r in rows)
    rows = [r for r in rows if len(r) == ncol]

    if ncol >= len(OUT_COLUMNS):
        names = OUT_COLUMNS + [f"extra_{i}" for i in range(ncol - len(OUT_COLUMNS))]
    else:
        names = OUT_COLUMNS[:ncol]

    df = pd.DataFrame(rows, columns=names)
    return df


def summarise(df: pd.DataFrame, crest_elev: float | None = None) -> dict:
    """
    Pull the headline numbers a breach analysis actually reports.

    `crest_elev` is the embankment height. Supply it wherever possible:
    breach depth is properly measured from the crest down to the final
    invert. Without it the depth can only be measured from the initial
    pilot notch or pipe invert, which understates the true breach depth
    by the depth of that starting condition.
    """
    s: dict = {}
    if "Q_breach" in df:
        s["peak_outflow_m3s"] = float(df["Q_breach"].max())
        i = int(df["Q_breach"].idxmax())
        s["time_to_peak_hr"] = float(df.loc[i, "time_hr"])
    if "breach_top_width" in df:
        s["final_top_width_m"] = float(df["breach_top_width"].iloc[-1])
        s["max_top_width_m"] = float(df["breach_top_width"].max())
    if "breach_bottom_width" in df:
        s["final_bottom_width_m"] = float(df["breach_bottom_width"].iloc[-1])
    if "breach_side_slope" in df:
        s["final_side_slope"] = float(df["breach_side_slope"].iloc[-1])
    if "breach_bottom_elev" in df:
        zmin = float(df["breach_bottom_elev"].min())
        s["final_bottom_elev_m"] = float(df["breach_bottom_elev"].iloc[-1])
        if crest_elev is not None:
            s["max_breach_depth_m"] = float(crest_elev) - zmin
        else:
            s["max_breach_depth_m"] = float(
                df["breach_bottom_elev"].iloc[0] - zmin)
    if "cum_volume" in df:
        s["total_outflow_volume_m3"] = float(df["cum_volume"].iloc[-1])
    if "time_hr" in df:
        s["simulated_duration_hr"] = float(df["time_hr"].iloc[-1])
    return s


# ---------------------------------------------------------------------
# Defaults: a starting parameter set. Edit freely in the interface.
# ---------------------------------------------------------------------

DEFAULT_PARAMS = {
    "case_name": "case",
    "notes": "",

    "time_step": 0.5,
    "sim_start": 0.0,
    "sim_end": 100000.0,
    "water_density": 1000.0,
    "water_viscosity": 1.0e-6,

    "emb_height": 20.0,
    "emb_crest_width": 10.0,
    "emb_us_slope": 0.4,
    "emb_ds_slope": 0.4,
    "emb_length": 300.0,

    "breach_mode": 1,          # 1 overtopping, 2 piping
    "overtopping_mode": 1,     # 1 surface erosion, 2 headcut, 3 clay core
    "pilot_depth": 0.2,
    "pilot_width": 1.0,
    "pipe_depth": 5.0,
    "pipe_width": 0.1,
    "pipe_head_loss": 0.05,
    "breach_location": 2.0,
    "hard_bottom_elev": 0.0,
    "manning_n": 0.02,
    "side_slope_constant": None,

    "sediment_type": 1,        # 1 noncohesive, 2 cohesive
    "sed_d50": 0.001,
    "sed_sg": 2.65,
    "sed_porosity": 0.35,
    "sed_clay": 0.05,
    "sed_cohesion": 0.0,
    "sed_friction": 0.75,
    "adaptation_lambda": 6.0,
    "include_adaptation_lambda": True,
    "include_cohesive_params": True,
    "pipe_loss_card": "",
    "write_reservoir": True,
    "extra_cards": [],
    "omit_cards": [],
    "loaded_cards": [],
    "data_file_refs": [],
    "data_file_refused": [],
    "renamed_cards": [],
    "data_files": {},
    "kd": 10.0,
    "tauc": 0.15,

    "headcut_model": 2,
    "headcut_coef": 0.0049,

    # clay core (overtopping submode 3). Starting values for a new core
    # follow Prof. Wu's Banqiao validation input (a cohesive clay core).
    "has_core": False,
    "core_cards": [],          # cards of a loaded core; empty: all
    "core_height": 18.0,
    "core_crest_width": 3.0,
    "core_us_slope": 4.0,
    "core_ds_slope": 4.0,
    "core_center": 0.0,
    "core_manning_n": 0.016,
    "core_sed_type": 2,
    "core_d50": 0.00003,
    "core_sg": 2.65,
    "core_porosity": 0.3,
    "core_clay": 0.4,
    "core_cohesion": 30000.0,
    "core_friction": 0.5,
    "core_kd": 18.0,
    "core_tauc": 0.15,

    "wsl_up_initial": 18.0,
    "wsl_down_initial": 0.01,

    "reservoir_method": 2,     # 2 = volume and area known at level H
    "res_VH": 5.0e6,
    "res_AH": 5.0e5,
    "res_H": 18.0,
    "res_m": 2.0,
    "res_curve": [],

    "downstream_mode": "channel",
    "ds_channel_width": 100.0,
    "ds_channel_slope": 0.01,
    "ds_channel_n": 0.03,
}


# ---------------------------------------------------------------------
# Remembering the executable location
# ---------------------------------------------------------------------

import json

CONFIG_PATH = Path(__file__).resolve().parent / ".dlbreach_config.json"

# Places worth checking before asking the user. The application folder is
# searched first, then a few conventional locations.
_COMMON_DIRS = [
    Path.home() / "DLBreach",
    Path.home() / "Documents" / "DLBreach",
    Path.home() / "Desktop" / "DLBreach",
    Path("C:/DLBreach"),
    Path("C:/Program Files/DLBreach"),
]


def load_config() -> dict:
    """Read remembered settings. Returns an empty dict if none exist."""
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(**kwargs) -> bool:
    """
    Merge values into the stored settings.

    Used to remember the executable path between sessions, so that it
    does not have to be entered on every launch. Failure is not an error
    worth interrupting the user for; the path simply is not remembered.
    """
    cfg = load_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def find_executable() -> str | None:
    """
    Look for a DLBreach executable without asking.

    The remembered path is checked first, then the application folder,
    then a few conventional install locations. Names containing
    "dlbreach" are preferred over any other executable found.
    """
    remembered = load_config().get("exe_path")
    if remembered and Path(remembered).is_file():
        return remembered

    here = Path(__file__).resolve().parent
    for d in [here, *_COMMON_DIRS]:
        try:
            if not d.is_dir():
                continue
            exes = sorted(d.glob("*.exe"))
        except OSError:
            continue
        named = [e for e in exes if "dlbreach" in e.name.lower()]
        if named:
            return str(named[0])
        if exes and d != here:
            return str(exes[0])
    return None


def browse_for_executable() -> str | None:
    """
    Open a native file dialog on the machine running the application.

    This is only meaningful for a local installation, where the server
    and the user are the same computer. It is guarded because a browser
    cannot reveal a file path, so on a hosted deployment there is no
    dialog to open and the caller should fall back to typing the path.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:                                  # noqa: BLE001
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askopenfilename(
            title="Select DLBreach executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        root.destroy()
        return path or None
    except Exception:                                  # noqa: BLE001
        return None


# ---------------------------------------------------------------------
# Stage-storage tables from CSV or Excel
# ---------------------------------------------------------------------

def read_table_file(data: bytes, filename: str, sheet=None) -> tuple:
    """
    Read a CSV or Excel file into a DataFrame. For Excel, returns the list
    of sheet names as well so the user can choose one.
    """
    import io as _io
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        xl = pd.ExcelFile(_io.BytesIO(data))
        sheets = xl.sheet_names
        df = xl.parse(sheet if sheet in sheets else sheets[0])
        return df, sheets
    return pd.read_csv(_io.BytesIO(data)), []


def guess_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Best guess at the elevation and volume columns from the headings."""
    cols = [str(c) for c in df.columns]
    low = [c.lower() for c in cols]
    elev = next((cols[i] for i, c in enumerate(low)
                 if any(k in c for k in ("elev", "stage", "level", "rl"))), None)
    vol = next((cols[i] for i, c in enumerate(low)
                if any(k in c for k in ("storage", "volume", "vol"))
                and cols[i] != elev), None)
    return elev, vol


def stage_storage_from_table(df: pd.DataFrame, elev_col: str, vol_col: str,
                             vol_factor: float = 1.0,
                             elev_shift: float = 0.0) -> list[tuple]:
    """
    Convert two columns into (level, volume) pairs in the model datum.

    vol_factor   multiplies volumes into m3 (1 for m3, 1e6 for Mm3)
    elev_shift   subtracted from levels: the embankment base elevation when
                 the table is in site RL, zero when already in model datum

    Rows with non-numeric entries are dropped; the result is sorted by
    level and duplicate levels are removed.
    """
    z = pd.to_numeric(df[elev_col], errors="coerce")
    v = pd.to_numeric(df[vol_col], errors="coerce")
    ok = z.notna() & v.notna()
    pairs = sorted({round(float(a) - elev_shift, 4): float(b) * vol_factor
                    for a, b in zip(z[ok], v[ok])}.items())
    return [(a, b) for a, b in pairs]


def check_stage_storage(pairs: list[tuple]) -> list[str]:
    """Problems that would make a stage-storage table unusable."""
    msgs = []
    if len(pairs) < 2:
        msgs.append("At least two levels are needed.")
        return msgs
    vols = [v for _, v in pairs]
    if any(b < a - 1e-6 for a, b in zip(vols, vols[1:])):
        msgs.append("Volume decreases with elevation somewhere in the table.")
    flat = [(pairs[i][0], pairs[i + 1][0]) for i in range(len(pairs) - 1)
            if abs(vols[i + 1] - vols[i]) <= 1e-6]
    if flat:
        z0, z1 = flat[0][0], flat[-1][1]
        msgs.append(f"The volume does not change between {z0:g} and {z1:g} m above "
                    f"base ({len(flat)} rows). A pond level cannot be found from a "
                    f"volume in that range, which may show as jumps in the pond "
                    f"level and spikes in the hydrograph. Keep only the highest "
                    f"row of the flat range.")
    if pairs[0][0] < -1e-6:
        msgs.append("The lowest level is below the embankment base. Check the "
                    "base elevation if the table is in site RL.")
    return msgs
