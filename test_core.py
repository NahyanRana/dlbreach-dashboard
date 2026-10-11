"""Quick self-test of the parts that do not need DLBreach.exe."""
import numpy as np
import pandas as pd

from dlbreach_io import DEFAULT_PARAMS, build_input_text, parse_out, summarise, OUT_COLUMNS
from dlbreach_mc import build_sample_table, ensemble_statistics, input_output_correlation

# ---- 1. card file, noncohesive overtopping -------------------------
p = dict(DEFAULT_PARAMS)
p["case_name"] = "tsf_test"
txt = build_input_text(p)
print("=== noncohesive overtopping ===")
print(txt)

# ---- 2. cohesive + headcut variant ---------------------------------
p2 = dict(DEFAULT_PARAMS)
p2.update({"sediment_type": 2, "overtopping_mode": 2, "reservoir_method": 3})
txt2 = build_input_text(p2)
assert "Cohesive_Soil_Erosion_kd" in txt2
assert "Headcut_Model" in txt2
assert "END_PARAMETERS" in txt2
assert "Upstream_Reservoir 3," in txt2
print("=== cohesive/headcut variant: cards switched correctly ===")

# ---- 3. piping variant ---------------------------------------------
p3 = dict(DEFAULT_PARAMS)
p3["breach_mode"] = 2
txt3 = build_input_text(p3)
assert "Initial_Piping_Breach" in txt3
assert "Overtopping_Mode" not in txt3
print("=== piping variant: cards switched correctly ===")

# ---- 4. reservoir curve method 0 ------------------------------------
p4 = dict(DEFAULT_PARAMS)
p4["reservoir_method"] = 0
p4["res_curve"] = [(0.0, 0.0), (5.0, 1.0e5), (10.0, 6.0e5), (18.0, 5.0e6)]
txt4 = build_input_text(p4)
assert "0, 4" in txt4
print("=== stage-storage curve written ===")

# ---- 5. synthetic .out file and parser ------------------------------
n = 60
t = np.linspace(0, 6, n)
q = 800 * np.exp(-((t - 2.0) ** 2) / 0.8)
rows = []
for i in range(n):
    rows.append([
        t[i], q[i], 0.0,
        18 - 6 * (t[i] / 6), 0.5,
        20 - 14 * (t[i] / 6),
        max(0.0, 40 * (t[i] / 6)),
        max(0.0, 60 * (t[i] / 6)),
        max(0.0, 500 * (t[i] / 6)),
        1.0,
        float(np.trapezoid(q[:i + 1], t[:i + 1] * 3600)) if i else 0.0,
        q[i] * 0.02, q[i] * 0.02,
    ])
import tempfile as _tmp, os as _os
_SYN = _os.path.join(_tmp.mkdtemp(prefix="dlb_test_"), "synthetic.out")   # not in the folder
with open(_SYN, "w") as f:
    f.write("  DLBreach results\n")
    f.write("  Time(hr)  Qbreach  Qspill  WSLup  WSLdn  zb  Bbot  Btop  A  slope  Vol  Qsu  Qsd\n")
    for r in rows:
        f.write("  " + "  ".join(f"{v:.6g}" for v in r) + "\n")

df = parse_out(_SYN)
assert list(df.columns)[:13] == OUT_COLUMNS, df.columns
assert len(df) == n, len(df)
print("=== parser ===")
print(df.head(3).to_string(index=False))
print("\nsummary:", {k: round(v, 2) for k, v in summarise(df).items()})

# ---- 6. Monte Carlo sampling ----------------------------------------
specs = {
    "sed_d50":        {"dist": "lognormal", "mean": 0.001, "sd": 0.0004, "min": 1e-5},
    "sed_porosity":   {"dist": "triangular", "low": 0.30, "mode": 0.35, "high": 0.45},
    "manning_n":      {"dist": "uniform", "low": 0.018, "high": 0.030},
    "emb_us_slope":   {"dist": "normal", "mean": 0.4, "sd": 0.05, "min": 0.1, "max": 0.8},
}
s = build_sample_table(DEFAULT_PARAMS, specs, 500, seed=42)
print("\n=== sampling ===")
print(s.describe().T[["mean", "std", "min", "max"]].to_string())
assert s["sed_d50"].min() > 0
assert s["emb_us_slope"].between(0.1, 0.8).all()

# ---- 7. statistics and correlation ----------------------------------
fake = s.copy()
fake["ok"] = True
fake["peak_outflow_m3s"] = (900 * (fake["sed_d50"] / 0.001) ** 0.3
                            * (0.02 / fake["manning_n"]) ** 0.5
                            + np.random.default_rng(0).normal(0, 20, len(fake)))
print("\nensemble stats:", {k: round(v, 1) for k, v in
                            ensemble_statistics(fake, "peak_outflow_m3s").items()})
print("\ncorrelation:")
print(input_output_correlation(fake, list(specs), "peak_outflow_m3s").to_string(index=False))

_SKIPPED = []

# Regression checks pinned to project data (the Run4 benchmark and a
# practitioner run log) live in test_private_benchmarks.py, which is kept
# out of the repository. They run here when that file is present.
from pathlib import Path as _P
if _P("test_private_benchmarks.py").exists():
    import runpy as _rp
    _rp.run_path("test_private_benchmarks.py", run_name="__main__")
else:
    _SKIPPED.append("project benchmarks (test_private_benchmarks.py not present)")

# Confidential names (kept in dev/private_terms.txt, never published) must
# not appear in any file that would be published.
import sys as _sys
_sys.path.insert(0, "dev")
try:
    from scan_confidential_names import scan as _scan
except ImportError:                           # inside the download: no dev folder
    _scan = lambda: None
_res = _scan()
if _res is None:
    _SKIPPED.append("confidential-name scan (dev/private_terms.txt not present)")
else:
    assert not _res[1], "confidential names found: " + "; ".join(_res[1])
    print(f"=== confidential-name scan: {_res[0]} names, none found ===")

# ---- 9. cone of depression -------------------------------------------
from dlbreach_tailings import cone_geometry
_c = cone_geometry(30.0, 20.0, 5.0, 200.0)              # invented geometry
assert abs(_c["L"] - 200.0) < 1e-6
assert abs(_c["volume"] - _c["volume_closed_form_untruncated"]) / _c["volume"] < 1e-3
_ct = cone_geometry(30.0, 20.0, 5.0, 200.0, l_max=150)
assert _ct["truncated"] and _ct["volume"] < _c["volume"]
assert cone_geometry(15.0, 20.0, 5.0, 10.0) == {}          # beach below invert
print("=== cone of depression: ok ===")

# ---- 10. scenario tables and batch packages ---------------------------
import io as _io, zipfile as _zf
from dlbreach_batch import (read_scenario_table, scenario_params,
                            make_batch_zip, read_outputs)
_tab, _rep = read_scenario_table(
    b"Run,Sediment_Diameter,Breach Manning n,Typo\nA,0.005,0.02,x\nB,0.05,,y\n",
    "t.csv")
assert _rep["recognised"] == {"Sediment_Diameter": "sed_d50",
                              "Breach Manning n": "manning_n"}
assert _rep["unrecognised"] == ["Typo"]
_pB = scenario_params(DEFAULT_PARAMS, _tab.iloc[1])
assert _pB["sed_d50"] == 0.05 and _pB["manning_n"] == DEFAULT_PARAMS["manning_n"]
_z = _zf.ZipFile(_io.BytesIO(make_batch_zip([("A", "x"), ("B", "y")])))
assert {"A.txt", "B.txt", "run_all.bat", "README.txt"} <= set(_z.namelist())
# the dashboard's own table download (with a Unit column) reads back (v0.14)
from dlbreach_batch import read_grid_file as _rgf, read_grid as _rg
_v, _r = _rg(_rgf(b"Parameter,Unit,Run 1,Run 2\nScenario group,,,\n"
                  b"Median grain size D50,mm,1.0,2.0\n", "t.csv"))
assert _r["unrecognised"] == [] and abs(_v["Run 2"]["sed_d50"] - 0.002) < 1e-12, (_v, _r)
print("=== scenario tables and batch packages: ok ===")

# ---- 11. practitioner units and porosity ------------------------------
import math as _m
import dlbreach_units as _U
assert abs(_U.to_model("sed_d50", 5) - 0.005) < 1e-12
assert abs(_U.to_model("emb_us_slope", 2) - 0.5) < 1e-12
assert abs(_U.to_model("sed_friction", 34) - _m.tan(_m.radians(34))) < 1e-12
assert abs(_U.from_model("sed_friction", _U.to_model("sed_friction", 34)) - 34) < 1e-9
assert abs(_U.to_model("sed_clay", 3) - 0.03) < 1e-12
assert abs(_U.porosity_from_bulk(20.6, 2.7, 1.0) - 0.3530) < 5e-4
assert _U.porosity_from_bulk(30.0, 2.65, 1.0) is None          # inconsistent
print("=== units and porosity: ok ===")

# ---- 12. tailings release, against the published worked examples ------
from dlbreach_tailings import (fontaine_martin, insitu_cv, cone_volume_practice,
                               cw_from_cv, cv_from_cw, bulking_factor)
_fm = fontaine_martin(200e6, 1.4, 2.7, 1.0, 10e6, 0.55)     # F&M (2015) example
assert round(_fm["VT"] / 1e6) == 143 and round(_fm["VS"] / 1e6) == 74
assert round(_fm["MS_MOB"] / 1e6) == 21 and round(_fm["MIW_MOB"] / 1e6) == 7
assert round(_fm["VT_MOB"] / 1e6) == 15 and round(_fm["VOUT"] / 1e6) == 25
assert round(_fm["pct_VOUT"] * 100) == 16
# in-situ Cv against the direct definition, solids volume / total volume
_ci = insitu_cv(1e6, 2e5, 2e6, 1.5, 2.7)
_vs = 2e6 / 2.7
_vw = 1e6 + 2e5 + (2e6 / 1.5 - _vs)
assert abs(_ci["Cv"] - _vs / (_vs + _vw)) < 1e-12
assert abs(insitu_cv(1e6, 0, 2e6, 1.5, 2.7)["Cv"] - 0.3175) < 5e-4
assert abs(cv_from_cw(cw_from_cv(0.25, 2.7), 2.7) - 0.25) < 1e-12
_cp = cone_volume_practice(10.0, _m.degrees(_m.atan(0.05)), 200)   # invented
# by hand: L = 10/0.05 = 200; 0.5*200*200*10 = 200,000; pi*10^3/(6*0.05^2) = 209,440
assert abs(_cp["V"] - (200000 + _m.pi * 1000 / 0.015)) < 1e-6 and abs(_cp["V"] - 409440) < 1
assert abs(bulking_factor(5e6, 2e6) - 1.4) < 1e-12
print("=== tailings release methods: ok ===")

# ---- 13b. loaded input files are written back card for card (v0.15) -----
# Cards the dashboard does not edit (clay core, inflow, water level series,
# downstream basin, data file names) are kept verbatim; boundary cards the
# file did not use are not added; numbers are written in full.
from dlbreach_io import (read_input_file as _rif, card_differences as _cd,
                         build_input_text as _bit, split_cards as _sc)
_SRC = """! A made-up levee case with cards the dashboard does not edit
Time_Step 0.5
Simulation_Period 0.0, 7200.0
Water_Density 1000.0
Water_Kinematic_Viscosity 0.000001
Embankment_Height 4.0
Embankment_Crest_Width 3.0
Embankment_Upstream_Slope 0.3333
Embankment_Downstream_Slope 0.4
Embankment_Length 50.0
Breach_Mode 2
Initial_Piping_Breach 3.5, 0.15
Pipe_Entrance_Head_Loss_Coef 0.05
Overtop_Entrance_Head_Loss_Coef 1.0
Breach_Location 2.0
Hard_Bottom_Elevation -1.5
Breach_Manning_n 0.016
Noncohesive_or_Cohesive_Sediment 2
Sediment_Diameter 0.0001
Sediment_Specific_Gravity 2.65
Sediment_Porosity 0.4
Sediment_Clay_Content 0.05
Sediment_Cohesion 10000.0
Sediment_Internal_Friction 0.32
Cohesive_Soil_Erosion_kd 14.5
Cohesive_Soil_Erosion_Tauc 0.15
Breach_Phase_Time 2
Initial_Up&Downstream_WSL 3.2,-1.0
Upstream_WSL_Time_Series 3
0, 3.2
1.5, 3.4
4.0, 3.0
Downstream_Storage_Basin 0, 3
-2.0	100.0
0.0	250000.0
3.0	4000000.0
Longshore_SedTran_Scaling_Factor 1.2
END_PARAMETERS
"""
_pl = dict(DEFAULT_PARAMS); _pl.update(_rif(_SRC))
_w = _bit(_pl)
_d = _cd(_SRC, _w)
assert not (_d["missing"] or _d["changed"] or _d["added"]), _d
assert "Upstream_Reservoir" not in _w and "Downstream_Channel_Flow_Out" not in _w
assert "Pipe_Entrance_Head_Loss_Coef" in _w and "Pipe_Local_Head_Loss" not in _w
_pl2 = dict(DEFAULT_PARAMS); _pl2.update(_rif(_w))
assert _bit(_pl2) == _w                               # stable on a second load
assert _pl["notes"].startswith("A made-up levee case")
assert [c["name"] for c in _sc(_SRC)][-1] == "Longshore_SedTran_Scaling_Factor"
# card names in any case; duplicates reported; segmented n; cohesive kd
_lc = _SRC.replace("Embankment_Height 4.0", "embankment_height 4.0")
_pc = dict(DEFAULT_PARAMS); _pc.update(_rif(_lc))
assert _pc["emb_height"] == 4.0
_dc = _cd(_lc, _bit(_pc))
assert not (_dc["missing"] or _dc["changed"] or _dc["added"]), _dc
assert _bit(_pc).count("Embankment_Height") == 1
_du = _SRC.replace("Embankment_Length 50.0", "Embankment_Length 50.0\nembankment_length 60.0")
assert _cd(_du, _bit(dict(DEFAULT_PARAMS, **_rif(_du))))["duplicates"] == ["embankment_length"]
_sg = _SRC.replace("Breach_Manning_n 0.016", "Breach_Manning_n_Segments 2, 0.016, 0.02")
_ws = _bit(dict(DEFAULT_PARAMS, **_rif(_sg)))
assert "Breach_Manning_n_Segments" in _ws and "\nBreach_Manning_n " not in _ws
_nk = _SRC.replace("Cohesive_Soil_Erosion_kd 14.5\n", "").replace(
    "Cohesive_Soil_Erosion_Tauc 0.15\n", "").replace(
    "Noncohesive_or_Cohesive_Sediment 2", "Noncohesive_or_Cohesive_Sediment 1")
_pk = dict(DEFAULT_PARAMS, **_rif(_nk))
assert "Cohesive_Soil_Erosion_kd" not in _bit(_pk)          # as loaded
_pk.update(sediment_type=2, kd=55.0)                      # user switches to cohesive
assert "Cohesive_Soil_Erosion_kd 55.0" in _bit(_pk)
# nothing after END_PARAMETERS is read; both n cards kept; renames and
# references the dashboard cannot supply are reported
_ea = _SRC.replace("END_PARAMETERS", "END_PARAMETERS\nSediment_Porosity 0.45")
assert _rif(_ea)["sed_porosity"] == 0.4
_both = _SRC.replace("Breach_Manning_n 0.016",
                     "Breach_Manning_n 0.016\nBreach_Manning_n_Segments 2, 0.016, 0.02")
_wb = _bit(dict(DEFAULT_PARAMS, **_rif(_both)))
assert "\nBreach_Manning_n 0.016" in _wb and "Breach_Manning_n_Segments" in _wb
assert _rif(_lc)["renamed_cards"] == ["embankment_height → Embankment_Height"]
_rf = _rif(_SRC.replace("Longshore_SedTran_Scaling_Factor 1.2", "Longshore_SedTran_Scaling_Factor 1.2\nWave_Data_File ..\\waves.txt\n"
                        "Wind_Data_File wind.txt"))
assert _rf["data_file_refused"] == ["..\\waves.txt"] and _rf["data_file_refs"] == ["wind.txt"]
# data files: where DLBreach will look; nothing outside the run folder
from dlbreach_io import data_file_relpath as _dfr
assert str(_dfr("data\\tide.txt")).replace("\\", "/") == "data/tide.txt"
assert _dfr("'tide.txt'").name == "tide.txt"
assert _dfr("../x.txt") is None and _dfr("C:\\x.txt") is None and _dfr("/x.txt") is None
# a data file named like the run's own files refuses the run
import tempfile as _tf
from dlbreach_io import run_case as _run
with _tf.TemporaryDirectory() as _td:
    (_P(_td) / "x.exe").write_text("")
    _rr = _run(_P(_td) / "x.exe", "x", case_name="up", work_dir=_td,
               data_files={"UP.txt": "1 2"})
    assert not _rr["ok"] and "same name" in _rr["stderr"]
# inputs that cannot change the file are not offered for sampling
from dlbreach_mc import relevant_candidates as _rc
assert "res_VH" not in _rc(_pl) and "sed_d50" in _rc(_pl)
# clay core (Wu 2016, Clay Core Parameters): read into inputs, written
# back card for card, removed when switched off, checked for fit
from dlbreach_viz import core_polygon as _cpoly, core_outside as _cout, clay_cover as _ccov
_CORE = _SRC.replace("Breach_Mode 2\nInitial_Piping_Breach 3.5, 0.15",
                     "Breach_Mode 1\nOvertopping_Mode 3\nInitial_Overtopping_Breach 0.2, 1.0"
                     ).replace("Longshore_SedTran_Scaling_Factor 1.2", """Core_Height 3.5
Core_Crest_Width 0.5
Core_Upstream_Slope 4.0
Core_Downstream_Slope 4.0
Core_Center_Location -0.4
Core_Manning_n 0.016
Core_Sediment_Diameter 0.00003
Core_Sediment_Specific_Gravity 2.65
Core_Sediment_Porosity 0.3
Core_Sediment_Clay_Content 0.4
Core_Sediment_Cohesion 30000.0
Core_Sediment_Internal_Friction 0.5
Core_Noncohesive_or_Cohesive 2
Core_Cohesive_Erosion_kd 18.0
Core_Cohesive_Erosion_Tauc 0.15
Clay_Cover_at_Downstream_Slope 1, 0.016, 0.3""")
_pcore = dict(DEFAULT_PARAMS, **_rif(_CORE))
assert _pcore["has_core"] and _pcore["core_center"] == -0.4 and _pcore["core_sed_type"] == 2
_wcore = _bit(_pcore)
_dcore = _cd(_CORE, _wcore)
assert not (_dcore["missing"] or _dcore["changed"] or _dcore["added"]), _dcore
assert _bit(dict(DEFAULT_PARAMS, **_rif(_wcore))) == _wcore          # stable
assert "Core_Height 4.25" in _bit(dict(_pcore, core_height=4.25))   # an edit is written
assert "Core_" not in _bit(dict(_pcore, has_core=False))             # switched off
assert "Core_" not in _bit(dict(DEFAULT_PARAMS))                      # no core by default
# a non-cohesive core loaded without kd and tauc keeps them out
_nc = _CORE.replace("Core_Noncohesive_or_Cohesive 2", "Core_Noncohesive_or_Cohesive 1"
                    ).replace("Core_Cohesive_Erosion_kd 18.0\n", "").replace(
                    "Core_Cohesive_Erosion_Tauc 0.15\n", "")
_pnc = dict(DEFAULT_PARAMS, **_rif(_nc))
assert "Core_Cohesive_Erosion_kd" not in _bit(_pnc)
# (switching it to cohesive on the Clay core tab adds them: dev/qa_features.py)
assert "Core_Cohesive_Erosion_kd 18.0" in _bit(dict(_pnc, core_sed_type=2, core_cards=_pnc[
    "core_cards"] + ["Core_Cohesive_Erosion_kd", "Core_Cohesive_Erosion_Tauc"]))
# a partial set of core cards is written as loaded, nothing added
_ps = _SRC.replace("Longshore_SedTran_Scaling_Factor 1.2", "core_height 3.0")
_pp = dict(DEFAULT_PARAMS, **_rif(_ps))
_part = _cd(_ps, _bit(_pp))
assert _pp["has_core"] and not (_part["added"] or _part["changed"] or _part["missing"]), _part
assert "Core_Crest_Width" not in _bit(_pp)
assert "Core_Crest_Width" in _bit(dict(_pp, core_cards=_pp["core_cards"] + ["Core_Crest_Width"]))
# a new core (no loaded cards) writes all of them, kd and tauc if cohesive
_new = _bit(dict(DEFAULT_PARAMS, has_core=True, core_sed_type=1))
assert _new.count("\nCore_") == 13 and "Core_Cohesive_Erosion_kd" not in _new
assert _bit(dict(DEFAULT_PARAMS, has_core=True)).count("\nCore_") == 15
# lower-case adaptation length card kept; a comment naming it is not a card
_lam = _SRC.replace("Longshore_SedTran_Scaling_Factor 1.2",
                    "noncohesive_sed_adaptation_lamda 3.0")
assert not _cd(_lam, _bit(dict(DEFAULT_PARAMS, **_rif(_lam))))["missing"]
_lc2 = _SRC.replace("Longshore_SedTran_Scaling_Factor 1.2",
                    "! Noncohesive_Sed_Adaptation_Lamda left at default")
assert not _cd(_lc2, _bit(dict(DEFAULT_PARAMS, **_rif(_lc2))))["added"]
# both pipe head loss cards are written back
_hl = _SRC.replace("Pipe_Entrance_Head_Loss_Coef 0.05",
                   "Pipe_Entrance_Head_Loss_Coef 0.05\nPipe_Local_Head_Loss_Coefficient 0.05")
assert not _cd(_hl, _bit(dict(DEFAULT_PARAMS, **_rif(_hl))))["missing"]
# geometry: crest centre 0.4 m upstream of the embankment crest centre
_poly = _cpoly(_pcore)
_xm = 4.0 / 0.3333 + 3.0 / 2
assert abs((_poly[1][0] + _poly[2][0]) / 2 - (_xm - 0.4)) < 1e-9 and _poly[1][1] == 3.5
assert _cout(_pcore) == []
assert any("above the crest" in m for m in _cout(dict(_pcore, core_height=5.0)))
assert any("upstream face" in m for m in _cout(dict(_pcore, core_center=-9.0)))
assert _ccov(_pcore) == {"downstream slope": 0.3}
# the cover band is 0.3 m thick normal to the downstream face
from dlbreach_viz import cover_polygons as _cvp
import math as _m
_band = _cvp(_pcore)[0]                 # (xd, H), (toe, 0), (toe - dz/S, 0), (xd, H - dz)
_Sd = 0.4
_normal = (_band[0][1] - _band[3][1]) / _m.sqrt(1 + _Sd ** 2)
assert abs(_normal - 0.3) < 1e-9, _normal
# core inputs are offered for sampling only when the core is modelled
assert {"core_kd", "core_center"} <= set(_rc(_pcore))
assert not any(k.startswith("core_") for k in _rc(dict(_pcore, overtopping_mode=1)))
assert "core_kd" not in _rc(dict(_pcore, core_sed_type=1))
# one-sided breach: one side slope in the width check (Wu 2016, Section 4.3)
from dlbreach_viz import check_breach_consistency as _cbc
_st = {"breach_bottom_width": 10.0, "breach_top_width": 30.0,
       "breach_bottom_elev": 0.0, "breach_side_slope": 1.0}
assert _cbc({"emb_height": 20.0, "breach_location": 1.0}, _st) is None
assert _cbc({"emb_height": 20.0, "breach_location": 2.0}, _st) is not None
# the report draws the same things: core, cover and pilot channel in
# section; abutments and a labelled non-erodible side in the face view
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as _plt
from dlbreach_report import _draw_section, _draw_face
_fig, (_a1, _a2) = _plt.subplots(1, 2)
_draw_section(_a1, _pcore, 0.0, "m")
_labs = [x.get_text() for x in _a1.get_legend().get_texts()]
assert {"Clay core", "Clay cover", "Pilot channel", "Erosion limit"} <= set(_labs), _labs
_draw_face(_a2, dict(_pcore, breach_location=1.0),
           {"breach_bottom_width": 5.0, "breach_top_width": 80.0,
            "breach_bottom_elev": 0.5, "breach_side_slope": 1.0, "wsl_up": 2.0,
            "wsl_down": 0.1, "breach_flow_area": 3.0}, 0.0, "m")
assert "Abutment" in [x.get_text() for x in _a2.get_legend().get_texts()]
assert any("not erodible" in x.get_text() for x in _a2.texts)
_plt.close(_fig)
print("=== clay core inputs and cover: ok ===")

# Prof. Wu's validation inputs (test_cases/wu_2016)
_wu = sorted(_P("test_cases/wu_2016").glob("*_cards*.txt")) if _P("test_cases/wu_2016").is_dir() else []
for _f in _wu:
    _t = _f.read_text(errors="replace")
    _pw = dict(DEFAULT_PARAMS); _pw.update(_rif(_t))
    _ww = _bit(_pw)
    _dw = _cd(_t, _ww)
    assert not (_dw["missing"] or _dw["changed"] or _dw["added"]), (_f.name, _dw)
if _wu:
    print(f"=== loaded files written back card for card: ok (synthetic + {len(_wu)} Wu cases) ===")
else:
    _SKIPPED.append("Wu validation inputs (test_cases/wu_2016 not present)")
    print("=== loaded files written back card for card: ok ===")

# ---- 13c. the Windows download (dev/build_windows_bundle.py) ------------
# What can be checked without Windows; the build itself is tested on
# GitHub's Windows machines by .github/workflows/windows-download.yml.
import importlib.util as _ilu
_bwb_path = _P(__file__).resolve().parent / "dev" / "build_windows_bundle.py"
if not _bwb_path.is_file():                   # inside the download: no dev folder
    _SKIPPED.append("Windows download builder (dev folder not present)")
else:
  _spec = _ilu.spec_from_file_location("_bwb", _bwb_path)
  _bwb = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_bwb)
  _af = _bwb.app_files(["app.py", "dlbreach_io.py", "dev/standin_dlbreach.py", ".github/workflows/tests.yml",
                        "test_core.py", "test_app_headless.py", "Launch DLBreach Dashboard.bat",
                        "PUBLISHING.md", "README.md", ".streamlit/config.toml",
                        "test_cases/wu_2016/Teton_cards.txt", ".gitignore"])
  assert _af == [".streamlit/config.toml", "README.md", "app.py", "dlbreach_io.py",
                 "test_cases/wu_2016/Teton_cards.txt", "test_core.py"], _af
  _pth = _bwb.pth_text("313").splitlines()
  assert _pth[0] == "python313.zip" and "import site" in _pth and r"..\app" in _pth
  assert _bwb.version_name('VERSION_SHORT = "version 0.16, development build"', None) == "v0.16"
  assert _bwb.version_name("", "v1.0.0") == "v1.0.0"
  assert _bwb.version_name('VERSION_SHORT = "version 0.16, x"', "main") == "v0.16"
  assert r'"%~dp0python\python.exe" -m streamlit run app.py' in _bwb.LAUNCHER
  assert "DLBreach.exe" in _bwb.readme_first("v1.0.0", "3.13.7")
  assert "not included" in _bwb.readme_first("v1.0.0", "3.13.7")
  print("=== Windows download builder (file choice, paths, launcher): ok ===")

# ---- 14. case-history data ---------------------------------------------
import dlbreach_data as _D
assert len(_D.XU_ZHANG_2009) == 75 and len(_D.FROEHLICH_2016A) == 41
assert sum(1 for r in _D.XU_ZHANG_2009 if r["Qp"]) == 39      # per Xu & Zhang
assert sum(1 for r in _D.XU_ZHANG_2009 if r["Tf"]) == 30
assert len(_D.RANA_2021_FW_TF) == 11
print("=== case-history data: ok ===")

# ---- 18. stage-storage checks and help text (v0.8) ----------------------
from dlbreach_io import check_stage_storage as _css
assert any("does not change" in m for m in _css([(0, 0), (1, 0), (2, 0), (3, 10)]))
assert not _css([(0, 0), (1, 5), (2, 10)])
import dlbreach_units as _U
from dlbreach_help import HELP as _H
for _k in _U.CATALOGUE:
    if _k != "beach_level":
        assert _k in _H, f"no help for {_k}"
assert "degrees" in _H["sed_friction"] and "kPa" in _H["sed_cohesion"]
assert "mm" in _H["sed_d50"] and "%" in _H["sed_clay"]
print("=== stage-storage checks and help coverage: ok ===")

# ---- 19. eroded embankment volume stops at the base (v0.9) ---------------
from dlbreach_empirical import eroded_dam_volume as _edv
_pe = {"emb_height": 10.0, "emb_crest_width": 4.0, "emb_us_slope": 0.5,
       "emb_ds_slope": 0.5}
# rectangular opening 10 m wide through the full height: width x section area
_area = 4.0 * 10.0 + 0.5 * 10.0 ** 2 * (2.0 + 2.0)
assert abs(_edv(_pe, 10.0, 0.0, 1e9) - 10.0 * _area) < 1e-6 * _area
# scour below the base adds no embankment volume beyond the opening's
# extra width at the base level
_v_neg = _edv(_pe, 10.0, -5.0, 1e9)
assert abs(_v_neg - 10.0 * _area) < 1e-6 * _area, _v_neg
print("=== eroded volume limited to the embankment: ok ===")


# ---- 20. which term sets the breach flow depth (v0.11) -------------------
from dlbreach_viz import flow_regime as _fr
# Wu (2016) Eq. 3.5: tailwater governs once it exceeds 1/3 of the pond head
assert _fr({"breach_bottom_elev": 0, "wsl_up": 9, "wsl_down": 2.9}) == "Critical depth"
assert _fr({"breach_bottom_elev": 0, "wsl_up": 9, "wsl_down": 3.1}) == "Tailwater"
assert _fr({"breach_bottom_elev": 0, "wsl_up": 9}) is None
print("=== flow depth regime (Wu 2016, Eq. 3.5): ok ===")


print()
if _SKIPPED:
    print("Skipped: " + "; ".join(_SKIPPED))
print("ALL CHECKS PASSED")
