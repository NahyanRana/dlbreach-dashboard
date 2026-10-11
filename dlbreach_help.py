"""
dlbreach_help.py
----------------
Help text for every field on the dashboard, shown behind the "?" beside it.

Parameter descriptions follow the DLBreach file format guide and technical
report (Wu 2016). Units are those the dashboard shows (practitioner units),
not the units of the DLBreach input card; the conversion is stated where it
matters. Where a statement is the dashboard's own construction rather than
DLBreach's, it says so.
"""

from __future__ import annotations

HELP = {
    # ---- project ----
    "case_name":
        "Short name for this analysis. Used for the DLBreach input and output "
        "file names (casename.txt, casename.out) and for downloads. Letters, "
        "numbers, hyphens and underscores are safest.",
    "notes":
        "Free text written as comment lines at the top of the DLBreach input "
        "file. Useful for recording the source of the inputs.",
    "exe_path":
        "Full path to DLBreach.exe on this computer, including the file name. "
        "The dashboard writes casename.txt beside it and runs it. Remembered "
        "between sessions. DLBreach is not distributed with the dashboard; "
        "obtain it from Prof. Wu's page at Clarkson University.",
    "datum_base_rl":
        "Elevation of the embankment base (toe) in your site datum. DLBreach "
        "measures every elevation from the embankment base, so this only "
        "changes how elevations are displayed and exported.",
    "datum_label":
        "Name of the site datum, shown on axes and in exports, for example "
        "m RL (mine grid).",
    "datum_bench_site":
        "Elevation of a benchmark in the site datum. With the next field, this "
        "gives the shift between the site and geodetic datums.",
    "datum_bench_geo":
        "Elevation of the same benchmark in the geodetic datum.",
    "datum_geo_label":
        "Name of the geodetic datum, for example m AHD or m CGVD2013.",
    "datum_display":
        "Datum used for every elevation shown on screen and in exports. Inputs "
        "are always stored in metres above the embankment base, as DLBreach "
        "requires.",
    "project_open":
        "Restore a project saved with Save project: every input, the "
        "stage-storage table and the site datum.",
    "txt_open":
        "Read an existing DLBreach input file (casename.txt) into Model setup. "
        "Cards the dashboard does not expose are ignored, so check the Input "
        "file tab on Model setup before relying on a loaded case.",

    # ---- time control ----
    "time_step":
        "Computational time step, in seconds. DLBreach accepts 0.1 to 5 s and "
        "the appropriate value varies case by case (Wu 2016). If a run behaves "
        "oddly, a smaller step is the first thing to try.",
    "sim_end":
        "End of the simulation, in seconds (86,400 s is one day). It must be "
        "long enough for the breach to develop and the impoundment to drain, "
        "or the hydrograph is cut short.",

    # ---- embankment ----
    "emb_height":
        "Embankment height above its base, in m. DLBreach represents the dam "
        "as a trapezoid with both toes at the same elevation, and measures "
        "every elevation from this base (Wu 2016).",
    "emb_crest_width":
        "Width of the flat crest, in m, measured upstream to downstream.",
    "emb_us_slope":
        "Upstream face slope as horizontal per 1 vertical: enter 3 for 3H:1V. "
        "Converted to the V/H ratio DLBreach reads (1/3 = 0.333).",
    "emb_ds_slope":
        "Downstream face slope as horizontal per 1 vertical: enter 2.5 for "
        "2.5H:1V. Converted to the V/H ratio DLBreach reads.",
    "emb_length":
        "Embankment base length along the crest alignment, in m. DLBreach "
        "takes this as the maximum breach bottom width (Wu 2016).",

    # ---- breach initiation ----
    "breach_mode":
        "How the breach begins. Overtopping: flow over the crest erodes the "
        "embankment downwards. Piping: an internal pipe enlarges until its "
        "roof collapses, after which the breach develops as an open channel.",
    "overtopping_mode":
        "Erosion process for overtopping (Wu 2016). 1: general surface erosion, "
        "for non-cohesive or uncompacted cohesive fill. 2: headcut erosion, for "
        "compacted cohesive fill. 3: composite embankment with a clay core, "
        "described on the Clay core tab.",
    "ot_trigger":
        "How the initial overtopping opening is represented. Pilot channel: a "
        "small notch in the crest. Crest settlement: a settled length of crest "
        "(for example after an earthquake), which the dashboard writes to "
        "DLBreach as a pilot channel of the settled depth and width. The second "
        "is a practice convention, not a separate DLBreach option.",
    "pilot_depth":
        "Depth of the initial notch below the crest, in m. DLBreach needs a "
        "starting breach to grow from. The pond must stand above the notch "
        "invert for flow to start.",
    "pilot_width":
        "Width of the initial notch along the crest, in m.",
    "settle_depth":
        "Height by which the crest has settled, in m. Written to DLBreach as the "
        "pilot channel depth. The pond must stand above the settled crest for "
        "flow to start.",
    "settle_width":
        "Length of crest that has settled, in m. Written to DLBreach as the "
        "pilot channel width.",
    "pipe_depth":
        "Depth from the crest down to the bottom of the initial pipe, in m "
        "(Wu 2016). It sets the head on the pipe, and results are sensitive to "
        "it. The pond must stand above the pipe for flow to start.",
    "pipe_width":
        "Width of the initial pipe, in m. DLBreach assumes a square pipe, so its "
        "height equals this width (Wu 2016).",
    "pipe_head_loss":
        "Local head loss coefficient at the pipe entrance, dimensionless. The "
        "DLBreach default is 0.05 (Wu 2016).",
    "breach_location":
        "Two-sided: the breach forms away from the abutments and widens both "
        "ways. One-sided: one side of the breach is not erodible (an abutment "
        "or a structure), so the breach widens one way only (Wu 2016, "
        "Section 4.3). The breach views draw a one-sided breach against the "
        "left-hand end of the crest.",

    # ---- clay core (Wu 2016, Clay Core Parameters) ----
    "has_core":
        "Composite embankment with a clay core, for overtopping submode 3. "
        "DLBreach erodes the top flat channel and the downstream slope until "
        "the core is exposed, then the core top, the core's downstream slope "
        "and the lower shoulder; it checks the core's stability at each time "
        "step, and once the core fails takes it and the upstream shoulder as "
        "washed away (Wu 2016, Section 4.6). The core is idealised as a "
        "trapezoid.",
    "core_height":
        "Core height, in m (Wu 2016). The dashboard draws the core standing on "
        "the embankment base; the DLBreach guide does not state the reference.",
    "core_crest_width":
        "Width of the flat top of the core, in m.",
    "core_us_slope":
        "Upstream face of the core, as horizontal per 1 vertical: enter 0.25 "
        "for a core face of 1H:4V. Converted to the V/H ratio DLBreach reads.",
    "core_ds_slope":
        "Downstream face of the core, as horizontal per 1 vertical. Converted "
        "to the V/H ratio DLBreach reads.",
    "core_center":
        "Horizontal distance from the embankment crest centre to the core "
        "crest centre, in m; positive downstream, negative upstream (Wu 2016).",
    "core_manning_n":
        "Manning roughness once the core is exposed to the flow, in s/m^(1/3).",
    "core_sed_type":
        "Sediment transport model for the core: non-cohesive or cohesive "
        "(Wu 2016).",
    "core_d50":
        "Median grain size of the core soil, in mm.",
    "core_sg":
        "Specific gravity of the core soil solids.",
    "core_porosity":
        "Porosity of the core soil, as a fraction.",
    "core_clay":
        "Clay size fraction of the core soil, in %.",
    "core_cohesion":
        "Cohesion of the core soil, in kPa (written to DLBreach in Pa).",
    "core_friction":
        "Internal friction angle of the core soil, in degrees (written to "
        "DLBreach as tan phi).",
    "core_kd":
        "Erodibility coefficient of the core soil, in cm³/N·s (cohesive core).",
    "core_tauc":
        "Critical shear stress for erosion of the core soil, in Pa (cohesive "
        "core).",

    # ---- breach development ----
    "hard_bottom_elev":
        "Erosion limit (hard bottom), in m above the embankment base. DLBreach "
        "does not cut below it. Negative values allow scour into the "
        "foundation. Only the average elevation of the hard bottom is used, not "
        "the lowest (Wu 2016). The stage-storage table should extend down to "
        "this level.",
    "manning_n":
        "Manning roughness of the breach channel, in s/m^(1/3). It governs flow "
        "resistance and so the shear stress that drives erosion. The value the "
        "DLBreach technical report recommends for the entered material is shown "
        "beneath the field.",
    "headcut_model":
        "Headcut migration formula, for overtopping submode 2 only. 1: "
        "dx/dt = C1[(qH)^(1/3) - A0], from the erodibility index. 2: "
        "dx/dt = Ct q^(1/3) H^(1/2), better tested in DLBreach and the suggested "
        "default. 3: dx/dt = C2 (qH)^(1/3) (Wu 2016).",
    "headcut_coef":
        "Coefficient of the selected headcut formula. Formula 2: Ct, around "
        "0.0025 to 0.0049 (default 0.0049). Formula 1: the erodibility index. "
        "Formula 3: C2, linearly related to kd (Wu 2016).",

    # ---- material ----
    "sediment_type":
        "Non-cohesive fill uses DLBreach's non-equilibrium sediment transport "
        "model with the adaptation length. Cohesive fill uses the erodibility "
        "coefficient kd and critical shear stress instead (Wu 2016).",
    "sed_d50":
        "Median grain size D50 of the embankment fill, in mm (converted to "
        "metres for DLBreach). For cohesive fill the DLBreach report suggests a "
        "floc size of 0.03 mm. Often the most influential input.",
    "sed_sg":
        "Specific gravity of the embankment solids, dimensionless. About 2.65 "
        "for quartz sand.",
    "porosity_from_bulk":
        "Enter porosity directly, or derive it from bulk unit weight, specific "
        "gravity and degree of saturation using the phase relation shown below "
        "the field.",
    "bulk_unit_weight":
        "In-place bulk unit weight of the fill, in kN/m³. Used only to derive "
        "porosity.",
    "sed_saturation":
        "Degree of saturation of the fill, in %. Used only to derive porosity.",
    "sed_porosity":
        "Porosity of the fill as a fraction of total volume, dimensionless.",
    "sed_clay":
        "Clay content of the fill, in % (converted to a fraction for "
        "DLBreach).",
    "sed_cohesion":
        "Cohesion of the fill, in kPa (converted to Pa for DLBreach). Used in "
        "the slope stability model that sets the breach side slope.",
    "sed_friction":
        "Internal friction angle of the fill, in degrees (converted to tan φ "
        "for DLBreach). Used in the breach side slope stability model.",
    "adaptation_lambda":
        "Non-equilibrium adaptation length for non-cohesive transport, as a "
        "multiple of the breach width at the water surface. Wu (2016) suggests "
        "6.0 for field cases and 3.0 for laboratory cases.",
    "include_adaptation_lambda":
        "Write the adaptation length card to the input file. Untick only to "
        "reproduce an input file that omitted it, so DLBreach uses its own "
        "default.",
    "kd":
        "Erodibility coefficient of cohesive fill, in cm³/N·s, as measured by a "
        "submerged jet test. Higher values erode faster.",
    "tauc":
        "Critical shear stress for erosion of cohesive fill, in Pa. Erosion "
        "starts once the applied shear stress exceeds it.",

    # ---- impoundment ----
    "ss_source":
        "How the impoundment volume is given. A table of level against volume "
        "is the most faithful (DLBreach method 0). The power-law options fit a "
        "curve to one known volume or area (methods 2 to 4).",
    "reservoir_method":
        "Power-law stage-storage (Wu 2016). 2: volume and area known at one "
        "level. 3: volume known at one level, with exponent m. 4: area known at "
        "one level, with exponent m.",
    "res_VH":
        "Stored volume at the reference level H, in m³.",
    "res_AH":
        "Water surface area at the reference level H, in m².",
    "res_H":
        "Level at which the volume or area is known, in m above the embankment "
        "base. Often the normal pool level or the crest.",
    "res_m":
        "Exponent of the power-law stage-area curve. About 2, generally 1 to 3 "
        "(Wu 2016).",
    "res_curve":
        "Level against stored volume, one row per level, levels in the display "
        "datum. DLBreach interpolates linearly between rows (Wu 2016). Volume "
        "should increase with every row, and the table should reach down to "
        "the erosion limit.",
    "ss_file":
        "A CSV or Excel file with a column of levels and a column of volumes. "
        "Other columns are ignored.",
    "ss_elev_col":
        "Column holding the levels.",
    "ss_vol_col":
        "Column holding the stored volumes.",
    "ss_vol_units":
        "Units of the volume column.",
    "ss_elev_datum":
        "Datum of the level column. Site RL levels are converted using the "
        "embankment base elevation set on the Project page.",
    "wsl_up_initial":
        "Pond level at the start of the run, in m above the embankment base. It "
        "must stand above the pilot channel invert, settled crest or pipe for "
        "flow to start.",
    "ds_channel_width":
        "Width of the downstream receiving channel, in m. DLBreach treats it as "
        "wide and rectangular and finds the tailwater depth from uniform flow "
        "(Wu 2016).",
    "ds_channel_slope":
        "Longitudinal slope of the downstream channel, as a fraction "
        "(0.001 = 1 m per km).",
    "ds_channel_n":
        "Manning roughness of the downstream channel. It sets the tailwater "
        "depth, which matters where the breach becomes submerged.",
    "wsl_down_initial":
        "Downstream water level at the start of the run, in m above the "
        "embankment base. Usually small.",

    # ---- display ----
    "ve":
        "Vertical exaggeration of the drawing. Auto picks a value that makes "
        "the section readable. Slopes quoted on the drawing are always true "
        "slopes.",
    "face_time":
        "Moment of the run to draw. The breach is shown as DLBreach reports it "
        "at that time.",
    "flow_depth":
        "Flow depth at the breach, solved from the breach flow area DLBreach "
        "reports. DLBreach sets it as the larger of the critical depth over a "
        "broad-crested weir (two-thirds of the pond's height above the invert) "
        "and the average of the pond and tailwater heights above the invert "
        "(Wu 2016, Eq. 3.5).",
    "face_play":
        "Play the breach development as an animation instead of stepping "
        "through it.",
    "geom_interval":
        "Spacing of the rows in the exported breach geometry table, in minutes.",

    # ---- scenarios ----
    "scen_params":
        "Inputs that change between runs. Every other input keeps its Model "
        "setup value.",
    "scen_n":
        "Number of runs, shown as columns of the table below.",
    "scen_prefix":
        "Run names are this prefix followed by a number.",
    "scen_upload":
        "Upload a filled scenario table, or a run log with runs as columns and "
        "parameters as rows. Parameter names are matched to the dashboard's.",

    # ---- Monte Carlo ----
    "mc_runs":
        "Each chosen run is the base of its own ensemble: the uncertain inputs "
        "below are sampled around it and every other input keeps the run's "
        "value. Runs come from the Sensitivity scenarios page.",
    "mc_params":
        "Inputs to sample. Only inputs that apply to the current setup are "
        "offered.",
    "mc_dist":
        "Sampling distribution. Uniform: equally likely between low and high. "
        "Triangular: most likely value with low and high limits. Normal and "
        "lognormal: mean and standard deviation of the value itself.",
    "mc_low": "Lowest value sampled.",
    "mc_high": "Highest value sampled.",
    "mc_mode": "Most likely value of the triangular distribution.",
    "mc_mean": "Mean of the sampled value.",
    "mc_sd": "Standard deviation of the sampled value.",
    "mc_min":
        "Samples below this value are raised to it, for example to keep a "
        "normal distribution from giving a negative grain size.",
    "mc_nreal":
        "Number of DLBreach runs in each ensemble. Several hundred are usually "
        "needed for stable percentiles; start small to check the setup.",
    "mc_seed":
        "Starting number for the random sampling. The computer draws the "
        "sampled inputs from a reproducible sequence that this number "
        "starts: the same seed with the same settings gives exactly the same "
        "sampled inputs and results, so an ensemble can be repeated or "
        "checked. A different seed gives a different but statistically "
        "equivalent set of samples. If the summary statistics change "
        "noticeably between seeds, use more realisations. Any whole number "
        "will do; record the one used.",
    "mc_env":
        "Statistics drawn through time across the ensemble. Each curve is a "
        "statistic at every moment, not a model run.",
    "mc_pick":
        "Realisation to inspect. Median, mean, minimum and maximum pick the "
        "realisation whose peak outflow is closest to that statistic of the "
        "ensemble. Or choose any realisation by number.",
    "mc_x":
        "Sampled input on the horizontal axis.",
    "mc_y":
        "Result on the vertical axis.",

    # ---- export ----
    "rep_title": "Title on the title page and in the page header.",
    "rep_sub": "Subtitle on the title page.",
    "rep_by": "Name shown as the author.",
    "rep_org": "Organisation shown on the title page.",
    "rep_date": "Date shown on the title page.",
    "rep_hdr": "Text at the right of every page header, for example Appendix D.",
    "rep_pre": "Prefix for page numbers: D- gives D-1, D-2 and so on.",
    "rep_notes": "Free text printed on the title page.",
    "rep_gint": "Spacing of the rows in the breach geometry table, in minutes.",
    "rep_fmt":
        "PDF for a fixed layout, Word for a document you can edit. Both carry "
        "the same content.",
}


def h(key: str) -> str | None:
    """Help text for a key, or None."""
    return HELP.get(key)
