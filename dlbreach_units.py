"""
dlbreach_units.py
-----------------
Parameter catalogue with practitioner display units.

DLBreach takes grain size in metres, slopes as vertical over horizontal,
internal friction as tan(phi), clay content and porosity as fractions and
cohesion in pascals. Practitioners usually think, and report, in other
units: D50 in mm, slopes as 3H:1V, friction angle in degrees, clay as a
percentage, cohesion in kPa. Every input, scenario table and Monte Carlo
distribution in the dashboard is shown in the practitioner unit, and
converted here, in one place, to what DLBreach needs.

Porosity can also be derived from bulk unit weight, specific gravity and
degree of saturation, from the phase relation

    gamma = gamma_w (Gs + S e) / (1 + e)
    =>  e = (gamma_w Gs - gamma) / (gamma - gamma_w S),   n = e / (1 + e)
"""

from __future__ import annotations

import math

GAMMA_W = 9.81   # kN/m3

# key: (label, display unit, to_model, from_model, group)
_I = (lambda v: v, lambda v: v)
CATALOGUE = {
    # embankment configuration
    "emb_height": ("Embankment height", "m", *_I, "Embankment configuration"),
    "emb_crest_width": ("Crest width", "m", *_I, "Embankment configuration"),
    "emb_us_slope": ("Upstream slope", "H per 1V",
                     lambda v: 1.0 / v, lambda v: 1.0 / v, "Embankment configuration"),
    "emb_ds_slope": ("Downstream slope", "H per 1V",
                     lambda v: 1.0 / v, lambda v: 1.0 / v, "Embankment configuration"),
    "emb_length": ("Embankment length", "m", *_I, "Embankment configuration"),
    # embankment properties
    "sed_d50": ("Median grain size D50", "mm",
                lambda v: v / 1000.0, lambda v: v * 1000.0, "Embankment properties"),
    "sed_sg": ("Specific gravity", "–", *_I, "Embankment properties"),
    "bulk_unit_weight": ("Bulk unit weight", "kN/m³", *_I, "Embankment properties"),
    "sed_saturation": ("Degree of saturation", "%",
                       lambda v: v / 100.0, lambda v: v * 100.0, "Embankment properties"),
    "sed_porosity": ("Porosity", "–", *_I, "Embankment properties"),
    "sed_clay": ("Clay size fraction", "%",
                 lambda v: v / 100.0, lambda v: v * 100.0, "Embankment properties"),
    "sed_cohesion": ("Cohesion", "kPa",
                     lambda v: v * 1000.0, lambda v: v / 1000.0, "Embankment properties"),
    "sed_friction": ("Internal friction angle", "°",
                     lambda v: math.tan(math.radians(v)),
                     lambda v: math.degrees(math.atan(v)), "Embankment properties"),
    "adaptation_lambda": ("Adaptation length lambda", "–", *_I, "Embankment properties"),
    "kd": ("Erodibility kd", "cm³/N·s", *_I, "Embankment properties"),
    "tauc": ("Critical shear stress", "Pa", *_I, "Embankment properties"),
    "manning_n": ("Breach Manning n", "–", *_I, "Embankment properties"),
    # breach initiation and limits
    "pilot_depth": ("Pilot channel depth", "m", *_I, "Breach initiation"),
    "pilot_width": ("Pilot channel width", "m", *_I, "Breach initiation"),
    "pipe_depth": ("Pipe depth below crest", "m", *_I, "Breach initiation"),
    "pipe_width": ("Initial pipe width", "m", *_I, "Breach initiation"),
    "hard_bottom_elev": ("Erosion limit (hard bottom)", "m above base", *_I,
                         "Breach initiation"),
    "headcut_coef": ("Headcut coefficient", "–", *_I, "Breach initiation"),
    # clay core (overtopping submode 3)
    "core_height": ("Core height", "m", *_I, "Clay core"),
    "core_crest_width": ("Core crest width", "m", *_I, "Clay core"),
    "core_us_slope": ("Core upstream slope", "H per 1V",
                      lambda v: 1.0 / v, lambda v: 1.0 / v, "Clay core"),
    "core_ds_slope": ("Core downstream slope", "H per 1V",
                      lambda v: 1.0 / v, lambda v: 1.0 / v, "Clay core"),
    "core_center": ("Core offset from crest centre", "m, + downstream", *_I,
                    "Clay core"),
    "core_manning_n": ("Core Manning n", "–", *_I, "Clay core"),
    "core_d50": ("Core D50", "mm",
                 lambda v: v / 1000.0, lambda v: v * 1000.0, "Clay core"),
    "core_sg": ("Core specific gravity", "–", *_I, "Clay core"),
    "core_porosity": ("Core porosity", "–", *_I, "Clay core"),
    "core_clay": ("Core clay size fraction", "%",
                  lambda v: v / 100.0, lambda v: v * 100.0, "Clay core"),
    "core_cohesion": ("Core cohesion", "kPa",
                      lambda v: v * 1000.0, lambda v: v / 1000.0, "Clay core"),
    "core_friction": ("Core internal friction angle", "°",
                      lambda v: math.tan(math.radians(v)),
                      lambda v: math.degrees(math.atan(v)), "Clay core"),
    "core_kd": ("Core erodibility kd", "cm³/N·s", *_I, "Clay core"),
    "core_tauc": ("Core critical shear stress", "Pa", *_I, "Clay core"),
    # facility
    "wsl_up_initial": ("Initial pond level", "m above base", *_I,
                       "Facility assumptions"),
    "res_VH": ("Reservoir volume at reference level", "m³", *_I,
               "Facility assumptions"),
    "beach_level": ("Tailings beach level", "m above base", *_I,
                    "Facility assumptions"),
}

GROUPS = ["Embankment configuration", "Embankment properties",
          "Breach initiation", "Clay core", "Facility assumptions"]


def label(key: str) -> str:
    return CATALOGUE[key][0] if key in CATALOGUE else key


def unit(key: str) -> str:
    return CATALOGUE[key][1] if key in CATALOGUE else ""


def label_unit(key: str) -> str:
    u = unit(key)
    return f"{label(key)} ({u})" if u and u != "–" else label(key)


def to_model(key: str, v):
    if v is None or key not in CATALOGUE:
        return v
    return CATALOGUE[key][2](float(v))


def from_model(key: str, v):
    if v is None or key not in CATALOGUE:
        return v
    return CATALOGUE[key][3](float(v))


def porosity_from_bulk(gamma: float, gs: float, saturation: float = 1.0,
                       gamma_w: float = GAMMA_W) -> float | None:
    """
    Porosity from bulk unit weight (kN/m3), specific gravity and degree of
    saturation (fraction). Returns None where the inputs are physically
    inconsistent (for example a bulk unit weight above the solids unit
    weight).
    """
    den = gamma - gamma_w * saturation
    if den <= 0:
        return None
    e = (gamma_w * gs - gamma) / den
    if e <= 0:
        return None
    return e / (1.0 + e)


def apply_derived(p: dict) -> dict:
    """
    Fill porosity from bulk unit weight where the configuration asks for it.
    Returns the same dict, updated in place.
    """
    if p.get("porosity_from_bulk") and p.get("bulk_unit_weight"):
        n = porosity_from_bulk(float(p["bulk_unit_weight"]),
                               float(p.get("sed_sg", 2.65)),
                               float(p.get("sed_saturation", 1.0)))
        if n is not None:
            p["sed_porosity"] = round(n, 4)
    return p
