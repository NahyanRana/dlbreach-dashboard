"""
dlbreach_templates.py
---------------------
Downloadable templates for every file the dashboard reads, so that a user
who has not used DLBreach before can prepare inputs outside the dashboard.

File rules for DLBreach input files follow the DLBreach file format guide
(Wu 2016).
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd

import dlbreach_batch as BATCH
import dlbreach_units as U
from dlbreach_io import build_input_text

INPUT_FILE_HEADER = """\
! =====================================================================
! DLBreach input file (casename.txt): annotated template
! ---------------------------------------------------------------------
! How DLBreach reads this file (DLBreach file format guide, Wu 2016):
!  - DLBreach needs only this one file. Name it casename.txt and place it
!    in the same folder as DLBreach.exe. Run DLBreach.exe and type the
!    case name when asked; results are written to casename.out.
!  - Each line is a card: a keyword followed by its values, as below.
!    Text after "!" is a comment.
!  - SI units throughout. Elevations are in metres above the embankment
!    base. Slopes are V/H (a 3H:1V slope is 0.333).
!  - Upstream_Reservoir with method 0 is followed by N rows of
!    "level, volume" (m, m3). Nothing, not even a comment, may appear
!    between the "0, N" line and the rows.
!  - Some cards have defaults and may be omitted; others, such as
!    Time_Step and Simulation_Period, must always be given.
! The values below are this dashboard's current inputs. Edit them, or
! open the file on the Project page to continue in the dashboard.
! =====================================================================

"""

STAGE_STORAGE_NOTE = (
    "Level against stored volume, one row per level, volume increasing with "
    "level. Levels in metres (above the embankment base, or in site RL: the "
    "upload asks which). Volumes in m3 or Mm3 (the upload asks which). Extend "
    "the table down to the erosion limit. Other columns are ignored.")

README = """\
DLBreach Dashboard: file templates
==================================

dlbreach_input_template.txt
    A complete DLBreach input file (casename.txt) with every card the
    dashboard writes, annotated. Use it to run DLBreach directly, or open
    it on the Project page ("Load an existing DLBreach input file").

stage_storage_template.csv
    Reservoir level against stored volume, for Model setup > Impoundment >
    Upload CSV / Excel. {ss}

scenario_runs_template.csv
    Runs as columns, parameters as rows, in the units shown. The first row
    is an optional group label (for example Sunny day). Leave a cell blank
    to keep the Model setup value. Upload it on Sensitivity scenarios.
    Parameter names are matched loosely, so a run log with the same rows
    also reads.

project_template.json
    Every dashboard input in one file, as written by Save project. Open it
    on the Project page.

Questions and feedback: nahyan.rana@geosyntec.com
"""


def input_file_template(p: dict) -> str:
    """The current inputs as a DLBreach input file, with a header that
    explains the file rules."""
    return INPUT_FILE_HEADER + build_input_text(p)


def stage_storage_template(p: dict) -> bytes:
    """Level against volume, from the current table if there is one."""
    rows = [tuple(r) for r in (p.get("res_curve") or [])]
    if len(rows) < 2:
        rows = [(0.0, 0.0), (5.0, 250_000.0), (10.0, 1_000_000.0),
                (15.0, 2_250_000.0), (20.0, 4_000_000.0)]
    df = pd.DataFrame(rows, columns=["Elevation (m above embankment base)",
                                     "Volume (m3)"])
    return df.to_csv(index=False).encode()


def scenario_template(p: dict) -> pd.DataFrame:
    """Every parameter that can vary between runs, three runs pre-filled
    with the current values."""
    keys = [k for k in BATCH.SCENARIO_KEYS if k in U.CATALOGUE and k != "beach_level"]
    return BATCH.grid_template(p, keys, ["Run 1", "Run 2", "Run 3"])


def all_templates_zip(p: dict, project_json: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", README.format(ss=STAGE_STORAGE_NOTE))
        z.writestr("dlbreach_input_template.txt", input_file_template(p))
        z.writestr("stage_storage_template.csv", stage_storage_template(p))
        z.writestr("scenario_runs_template.csv",
                   scenario_template(p).to_csv(index=False))
        z.writestr("project_template.json", project_json)
    return buf.getvalue()
