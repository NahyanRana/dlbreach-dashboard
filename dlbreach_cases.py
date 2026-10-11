"""
dlbreach_cases.py
-----------------
Case History Comparison: places a result among measured outcomes of real
dam failures. Measured data only; no regression lines.

Water-retaining dams
    Froehlich (2016a) Table 1 — 41 failures with measured peak discharge
    Xu and Zhang (2009) Table 1 — 75 earth and rockfill dam failures
    The two sets share some dams. Both are shown as published, so a dam can
    appear twice, and where Froehlich revised a peak discharge the two
    values differ (Banqiao, Hell Hole, Oros).

Tailings dams
    Rana et al. (2021) — free water and tailings outflow volumes, and mean
    breach widths, from their supplementary database
    Adria et al. (2023) — breach heights and widths

Every builder returns a long-form table with columns x, y, Series, Event,
ready for the comparison chart.
"""

from __future__ import annotations

import pandas as pd

from dlbreach_data import (ADRIA_2023, FROEHLICH_2016A, RANA_2021,
                           RANA_2021_FW_TF, XU_ZHANG_2009)

MODEL = "This analysis"


def _model(rows, pt):
    if pt and pt.get("x") and pt.get("y"):
        rows.append({"x": float(pt["x"]), "y": float(pt["y"]),
                     "Series": MODEL, "Event": pt.get("label", "this analysis")})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Water-retaining dams
# ---------------------------------------------------------------------

def water_peak_vs_breach_height(pt=None, normalise_by_dam: bool = False):
    """
    Peak outflow against breach height. With normalise_by_dam, breach
    height is divided by dam height, which only Xu and Zhang report.
    """
    rows = []
    if not normalise_by_dam:
        for r in FROEHLICH_2016A:
            rows.append({"x": r["Hb"], "y": r["Qp"],
                         "Series": "Froehlich (2016a)", "Event": r["event"]})
    for r in XU_ZHANG_2009:
        if r["Qp"] and r["Hb"]:
            if normalise_by_dam:
                if not r["Hd"]:
                    continue
                x = r["Hb"] / r["Hd"]
            else:
                x = r["Hb"]
            rows.append({"x": x, "y": r["Qp"], "Series": "Xu and Zhang (2009)",
                         "Event": r["event"]})
    return _model(rows, pt)


def water_peak_vs_volume(pt=None):
    """Peak outflow against volume of water above the breach invert."""
    rows = [{"x": r["Vw"], "y": r["Qp"], "Series": "Froehlich (2016a)",
             "Event": r["event"]} for r in FROEHLICH_2016A]
    rows += [{"x": r["Vw"], "y": r["Qp"], "Series": "Xu and Zhang (2009)",
              "Event": r["event"]} for r in XU_ZHANG_2009 if r["Qp"] and r["Vw"]]
    return _model(rows, pt)


def water_width_vs_volume(pt=None):
    """Average breach width against Vw (Xu and Zhang report Bave)."""
    rows = [{"x": r["Vw"], "y": r["Bave"], "Series": "Xu and Zhang (2009)",
             "Event": r["event"]} for r in XU_ZHANG_2009 if r["Bave"] and r["Vw"]]
    return _model(rows, pt)


def water_time_vs_volume(pt=None):
    """Failure time against Vw (Xu and Zhang report Tf)."""
    rows = [{"x": r["Vw"], "y": r["Tf"], "Series": "Xu and Zhang (2009)",
             "Event": r["event"]} for r in XU_ZHANG_2009 if r["Tf"] and r["Vw"]]
    return _model(rows, pt)


def water_breach_vs_dam_height(pt=None):
    """Breach height against dam height (Xu and Zhang)."""
    rows = [{"x": r["Hd"], "y": r["Hb"], "Series": "Xu and Zhang (2009)",
             "Event": r["event"]} for r in XU_ZHANG_2009 if r["Hd"] and r["Hb"]]
    return _model(rows, pt)


# ---------------------------------------------------------------------
# Tailings dams
# ---------------------------------------------------------------------

def tailings_vs_free_water(pt=None):
    """
    Tailings outflow against free water outflow (the form of Rana et al.
    2023, Fig. 5), reconstructed from the Rana et al. (2021) database.
    A 1:1 line is drawn by the chart, not included here.
    """
    rows = []
    for r in RANA_2021_FW_TF:
        cda = r["cda"].upper()
        series = ("Rana et al. (2021) — CDA Case 1A" if "1A" in cda
                  else "Rana et al. (2021) — CDA Case 1B")
        rows.append({"x": r["Fw"], "y": r["TF"], "Series": series,
                     "Event": r["event"]})
    return _model(rows, pt)


def tailings_width_vs_outflow(pt=None):
    """Mean breach width against total outflow volume."""
    rows = [{"x": r["VF"], "y": r["Bw"], "Series": "Rana et al. (2021)",
             "Event": r["event"]} for r in RANA_2021 if r.get("VF") and r.get("Bw")]
    for a in ADRIA_2023:
        if a["VOut"] and a["BT"] and a["BB"]:
            rows.append({"x": a["VOut"], "y": (a["BT"] + a["BB"]) / 2,
                         "Series": "Adria et al. (2023)", "Event": a["event"]})
    return _model(rows, pt)


def tailings_breach_height_vs_outflow(pt=None, normalise_by_dam: bool = False):
    """Breach height (or breach height / dam height) against total outflow."""
    rows = []
    for a in ADRIA_2023:
        hdb = a.get("HDB") or a.get("HD")
        if a["HB"] and a["VOut"]:
            if normalise_by_dam:
                if not hdb:
                    continue
                y = a["HB"] / hdb
            else:
                y = a["HB"]
            rows.append({"x": a["VOut"], "y": y, "Series": "Adria et al. (2023)",
                         "Event": a["event"]})
    return _model(rows, pt)


COMPLETENESS_NOTE = (
    "Each chart shows only the events that report both variables plotted, "
    "so the number of points differs between charts. Points are measured or "
    "reported values, not predictions.")
