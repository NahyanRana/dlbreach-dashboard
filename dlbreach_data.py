"""
dlbreach_data.py
----------------
Case-history data for the empirical comparison.

Two published compilations are embedded here so that the dashboard has
no spreadsheet dependency at runtime. Both describe TAILINGS dam
failures. They are kept separate from the water-retaining dam data that
underlies the Froehlich and related peak-discharge equations, because
the two populations must not be conflated.

Sources are given in CITATIONS below and are reproduced in the
interface. Values are as published; no gap filling or interpolation has
been applied, and missing entries are None rather than zero.
"""

from __future__ import annotations


CITATIONS = {
    "rana2021": (
        "Rana, N.M., Ghahramani, N., Evans, S.G., McDougall, S., "
        "Small, A. and Take, W.A. (2021). Catastrophic mass flows "
        "resulting from tailings impoundment failures. Engineering "
        "Geology, 292, 106262."),
    "adria2023": (
        "Adria, D.A.M., Ghahramani, N., Rana, N.M., Martin, V., "
        "McDougall, S., Evans, S.G. and Take, W.A. (2023). Insights "
        "from the compilation and critical assessment of breach and "
        "runout characteristics from historical tailings dam failures: "
        "implications for numerical modelling. Mine Water and the "
        "Environment, 42, 650-669."),
    "adria2024": (
        "Adria, D.A.M., Martin, V. and McDougall, S. (2024). Volumes of "
        "dam material mobilized by erosion during tailings dam failure "
        "events. Tailings and Mine Waste 2024, Colorado, USA."),
    "froehlich1995": (
        "Froehlich, D.C. (1995). Peak outflow from breached embankment "
        "dam. Journal of Water Resources Planning and Management, "
        "121(1), 90-97."),
    "froehlich2008": (
        "Froehlich, D.C. (2008). Embankment dam breach parameters and "
        "their uncertainties. Journal of Hydraulic Engineering, 134(12), "
        "1708-1721."),
    "froehlich2016": (
        "Froehlich, D.C. (2016a). Predicting peak discharge from "
        "gradually breached embankment dam. Journal of Hydrologic "
        "Engineering, 21(11), 04016041."),
    "froehlich2016b": (
        "Froehlich, D.C. (2016b). Empirical model of embankment dam "
        "breaching. Conference paper, June 2016. "
        "doi:10.1201/9781315644479-285."),
    "wu2016": (
        "Wu, W. (2016). Introduction to DLBreach — A Simplified "
        "Physically-Based Dam/Levee Breach Model, version 2016.4. "
        "Technical Report, Clarkson University, Potsdam, NY."),
    "xu2009": (
        "Xu, Y. and Zhang, L.M. (2009). Breaching parameters for earth and "
        "rockfill dams. Journal of Geotechnical and Geoenvironmental "
        "Engineering, 135(12), 1957-1970."),
    "fontaine2015": (
        "Fontaine, D.D. and Martin, V. (2015). Tailings mobilization "
        "estimates for dam breach studies. Proceedings of Tailings and Mine "
        "Waste 2015, Vancouver, BC."),
    "cda2021": (
        "Canadian Dam Association (2021). Technical Bulletin: Tailings "
        "Dam Breach Analysis."),
}


# ---------------------------------------------------------------------
# Rana et al. (2021) — tailings dam failures with runout characterised.
# H    dam height at the breach location (m)
# VT   total impounded volume (m3)
# VF   total outflow volume (m3)
# Bw   mean dam breach width (m), largely GIS-estimated
# ---------------------------------------------------------------------
RANA_2021 = [
    {"event": 'Barahona', "year": 1928, "cda": '1A', "H": 63, "VT": 1.8e+07, "VF": 2.7e+06, "Bw": 200},
    {"event": 'Los Cedros', "year": 1937, "cda": '1B', "H": 35, "VT": None, "VF": 1.5e+06, "Bw": None},
    {"event": 'Huogodu', "year": 1962, "cda": '1B', "H": 19, "VT": 5.42e+06, "VF": 3.68e+06, "Bw": 113},
    {"event": 'Bellavista', "year": 1965, "cda": '1A', "H": 20, "VT": 400000, "VF": 55000, "Bw": 100},
    {"event": 'Cerro Negro', "year": 1965, "cda": '1A', "H": 20, "VT": 400000, "VF": 70000, "Bw": None},
    {"event": 'El Cobre', "year": 1965, "cda": '1A', "H": None, "VT": 5.735e+06, "VF": 2.4e+06, "Bw": 400},
    {"event": 'La Patagua', "year": 1965, "cda": '1A', "H": 15, "VT": 100000, "VF": 27000, "Bw": None},
    {"event": 'Los Maquis', "year": 1965, "cda": '1A', "H": 15, "VT": 43000, "VF": 21000, "Bw": 60},
    {"event": 'Sgorigrad', "year": 1966, "cda": '1A', "H": 45, "VT": 1.52e+06, "VF": 220000, "Bw": None},
    {"event": 'Hokkaido', "year": 1968, "cda": '2A', "H": 12, "VT": 300000, "VF": 90000, "Bw": 170},
    {"event": 'Certej', "year": 1971, "cda": '1A', "H": None, "VT": None, "VF": 300000, "Bw": 80},
    {"event": 'Cities Service', "year": 1971, "cda": '1B', "H": 15, "VT": 1.234e+07, "VF": 9e+06, "Bw": None},
    {"event": 'Bafokeng', "year": 1974, "cda": '1A', "H": 20, "VT": 1.3e+07, "VF": 3e+06, "Bw": 110},
    {"event": 'Deneen Mica', "year": 1974, "cda": '1B', "H": 26, "VT": 300000, "VF": 38000, "Bw": 60},
    {"event": 'Arcturus', "year": 1978, "cda": '1A', "H": 25, "VT": 960000, "VF": 200000, "Bw": 160},
    {"event": 'Mochikoshi', "year": 1978, "cda": '1A', "H": None, "VT": 480000, "VF": 80000, "Bw": 90},
    {"event": 'Church Rock', "year": 1979, "cda": '1B', "H": 11, "VT": 370000, "VF": 370000, "Bw": None},
    {"event": 'Tyrone Mine', "year": 1980, "cda": 'Unknown', "H": 66, "VT": 2.5e+06, "VF": 2e+06, "Bw": None},
    {"event": 'Cerro Negro', "year": 1985, "cda": '1A', "H": 40, "VT": 2e+06, "VF": 500000, "Bw": None},
    {"event": 'Niujiaolong', "year": 1985, "cda": '1B', "H": 39, "VT": 1.1e+06, "VF": 730000, "Bw": None},
    {"event": 'Stava', "year": 1985, "cda": '1A', "H": None, "VT": 300000, "VF": 185220, "Bw": 120},
    {"event": 'Veta del Agua', "year": 1985, "cda": '1A', "H": 24, "VT": 700000, "VF": 280000, "Bw": None},
    {"event": 'Ollinghouse', "year": 1985, "cda": 'Unknown', "H": 5, "VT": 120000, "VF": 25000, "Bw": None},
    {"event": 'Stancil', "year": 1989, "cda": '1B', "H": 9, "VT": 74000, "VF": 38000, "Bw": None},
    {"event": 'Merriespruit', "year": 1994, "cda": '1A', "H": 31, "VT": 7e+06, "VF": 630000, "Bw": 150},
    {"event": 'Tapo Canyon', "year": 1994, "cda": '1A', "H": 24, "VT": None, "VF": 55000, "Bw": 60},
    {"event": 'Omai', "year": 1995, "cda": '1B', "H": 45, "VT": 5.2e+06, "VF": 4.2e+06, "Bw": None},
    {"event": 'Marcopper', "year": 1996, "cda": '1B', "H": None, "VT": 1.5e+07, "VF": 1.6e+06, "Bw": None},
    {"event": 'Pinto Valley', "year": 1997, "cda": '2A', "H": None, "VT": None, "VF": 240000, "Bw": 180},
    {"event": 'Aznalcollar', "year": 1998, "cda": '1A', "H": 27, "VT": 1.5e+07, "VF": 6.8e+06, "Bw": 200},
    {"event": 'Aitik', "year": 2000, "cda": '1B', "H": 15, "VT": 1.5e+07, "VF": 2.5e+06, "Bw": None},
    {"event": 'Baia Mare', "year": 2000, "cda": '1B', "H": None, "VT": 800000, "VF": 100000, "Bw": 25},
    {"event": 'Inez', "year": 2000, "cda": '1B', "H": None, "VT": 8.7e+06, "VF": 1.07e+06, "Bw": None},
    {"event": 'Sasa', "year": 2003, "cda": 'Unknown', "H": None, "VT": 1e+06, "VF": 100000, "Bw": None},
    {"event": 'Comurhex', "year": 2004, "cda": '1A/1B', "H": None, "VT": None, "VF": 30000, "Bw": 70},
    {"event": 'Cavendish Mill', "year": 2007, "cda": '1A', "H": 15, "VT": None, "VF": 20000, "Bw": None},
    {"event": 'Mineracao', "year": 2007, "cda": '1A', "H": None, "VT": None, "VF": 2e+06, "Bw": None},
    {"event": 'Kingston', "year": 2008, "cda": '1A', "H": 18, "VT": None, "VF": 4.1e+06, "Bw": 1300},
    {"event": 'Xiangfen', "year": 2008, "cda": '1A', "H": 50.7, "VT": 290000, "VF": 190000, "Bw": None},
    {"event": 'Karamken', "year": 2009, "cda": '1A', "H": 27, "VT": 5.1e+06, "VF": 1.38e+06, "Bw": 50},
    {"event": 'Ajka', "year": 2010, "cda": '1A', "H": 22, "VT": 6e+06, "VF": 1.644e+06, "Bw": 90},
    {"event": 'Caudalosa', "year": 2010, "cda": '1A', "H": None, "VT": None, "VF": 21420, "Bw": None},
    {"event": 'Las Palmas', "year": 2010, "cda": '2A', "H": 15, "VT": 125000, "VF": 100000, "Bw": None},
    {"event": 'Kayakari', "year": 2011, "cda": '2A', "H": 36, "VT": 400000, "VF": 41000, "Bw": 110},
    {"event": 'Gullbridge', "year": 2012, "cda": '1B', "H": 8, "VT": 800000, "VF": 100500, "Bw": 30},
    {"event": 'Philex', "year": 2012, "cda": '1A/1B', "H": None, "VT": None, "VF": 3.5e+06, "Bw": None},
    {"event": 'Talvivaara (Sotkamo)', "year": 2012, "cda": '1B', "H": None, "VT": 5e+06, "VF": 1.2e+06, "Bw": None},
    {"event": 'Obed Mountain', "year": 2013, "cda": '1B', "H": None, "VT": None, "VF": 670000, "Bw": None},
    {"event": 'Dan River', "year": 2014, "cda": '1B', "H": 13, "VT": 588370, "VF": 138000, "Bw": None},
    {"event": 'Mount Polley', "year": 2014, "cda": '1B', "H": 40, "VT": 7.35e+07, "VF": 2.5e+07, "Bw": 160},
    {"event": 'Fundao', "year": 2015, "cda": '2A', "H": 110, "VT": 5.25e+07, "VF": 3.2e+07, "Bw": 700},
    {"event": 'Luoyang', "year": 2016, "cda": '2A', "H": 20, "VT": None, "VF": 2e+06, "Bw": 200},
    {"event": 'Jharsuguda', "year": 2017, "cda": '2A/2B', "H": None, "VT": None, "VF": 2.5e+06, "Bw": 800},
    {"event": 'Mishor Rotem', "year": 2017, "cda": '1B', "H": 60, "VT": None, "VF": 100000, "Bw": 50},
    {"event": 'Tonglvshan', "year": 2017, "cda": '2A/2B', "H": None, "VT": None, "VF": 200000, "Bw": 300},
    {"event": 'Cadia', "year": 2018, "cda": '2A', "H": 94, "VT": None, "VF": 1.33e+06, "Bw": 300},
    {"event": 'Cieneguita', "year": 2018, "cda": '2A/2B', "H": None, "VT": None, "VF": 440000, "Bw": 80},
    {"event": 'Cobriza', "year": 2019, "cda": '1A/1B', "H": None, "VT": None, "VF": 67500, "Bw": 38},
    {"event": 'Feijao', "year": 2019, "cda": '2A', "H": 87, "VT": 1.27e+07, "VF": 9.7e+06, "Bw": 600},
    {"event": 'Hindalco', "year": 2019, "cda": '1A/1B', "H": 5, "VT": None, "VF": None, "Bw": 600},
    {"event": 'Luming', "year": 2020, "cda": '1B', "H": None, "VT": None, "VF": 2.53e+06, "Bw": None},
]


# ---------------------------------------------------------------------
# Adria et al. (2023) — breach observations from tailings dam failures.
# HD    regulatory dam height (m)          HB   breach height (m)
# HDB   dam height at breach location (m)  BT   top breach width (m)
# VOut  total outflow volume (m3)          BB   bottom breach width (m)
# VS    tailings solids (m3)               Tf   formation time (h)
# VI    interstitial water (m3)            VP   supernatant pond (m3)
# ---------------------------------------------------------------------
ADRIA_2023 = [
    {"event": '1i. Prestavèl - Upper Basin', "HD": 33, "HDB": 33, "VOut": 116800, "VS": 56150, "VI": 48850, "VP": 11800, "HB": 22, "BT": 148, "BB": 50, "Tf": None, "process": 'Non-Erosional', "cda": '1A', "raise_": 'US'},
    {"event": '1ii. Prestavèl - Lower Basin', "HD": 22, "HDB": 22, "VOut": 68400, "VS": 32200, "VI": 28000, "VP": 8200, "HB": 13, "BT": 220, "BB": 20, "Tf": None, "process": 'Process II', "cda": '1A', "raise_": 'US'},
    {"event": '2. Gillibrand Pond No. 6', "HD": 24, "HDB": 24, "VOut": 55000, "VS": 27500, "VI": 27500, "VP": None, "HB": 12, "BT": 145, "BB": 42, "Tf": None, "process": 'Non-Erosional', "cda": '1A or 2A', "raise_": 'US'},
    {"event": '3. Harmony 4A', "HD": 31, "HDB": 31, "VOut": 615000, "VS": 288000, "VI": 242000, "VP": 85000, "HB": 27, "BT": 150, "BB": 55, "Tf": None, "process": 'Non-Erosional', "cda": '1A', "raise_": 'US'},
    {"event": '4i. Aznalcóllar - North Pyroclastic Pond', "HD": 28, "HDB": 28, "VOut": 1.2e+07, "VS": 3.6e+06, "VI": 2.9e+06, "VP": 5.5e+06, "HB": 26, "BT": 56, "BB": 84, "Tf": 2, "process": 'Erosional', "cda": '1B', "raise_": 'DS'},
    {"event": '4ii. Aznalcóllar - South Pyritic Pond', "HD": None, "HDB": None, "VOut": 3.1e+06, "VS": 1.1e+06, "VI": 700000, "VP": 1.3e+06, "HB": None, "BT": None, "BB": None, "Tf": None, "process": '', "cda": '1A', "raise_": 'DS'},
    {"event": '5. Tashan', "HD": 51, "HDB": 51, "VOut": 190000, "VS": None, "VI": None, "VP": None, "HB": 17, "BT": 193, "BB": 100, "Tf": None, "process": 'Non-Erosional', "cda": '1A', "raise_": 'US'},
    {"event": '6. MAL Reservoir X', "HD": 27, "HDB": 22, "VOut": 1.2e+06, "VS": 180000, "VI": 180000, "VP": 840000, "HB": 22, "BT": 60, "BB": 60, "Tf": 0.25, "process": 'Erosional / Non-Erosional Hybrid', "cda": '1A', "raise_": 'DS'},
    {"event": '7. Kayakari', "HD": 36, "HDB": 36, "VOut": 41000, "VS": 20500, "VI": 20500, "VP": None, "HB": None, "BT": 50, "BB": 50, "Tf": None, "process": 'Non-Erosional', "cda": '2A', "raise_": 'US'},
    {"event": '8. Mount Polley', "HD": 57, "HDB": 40, "VOut": 2.5e+07, "VS": 7.9e+06, "VI": 6.5e+06, "VP": 1.06e+07, "HB": 36, "BT": 260, "BB": 42, "Tf": 3.5, "process": 'Erosional', "cda": '1B', "raise_": 'CL/US Hybrid'},
    {"event": '9. Fundão Dam I', "HD": 106, "HDB": 106, "VOut": 3.22e+07, "VS": 1.928e+07, "VI": 1.292e+07, "VP": None, "HB": 94, "BT": 650, "BB": 180, "Tf": None, "process": 'Non-Erosional', "cda": '2A', "raise_": 'US'},
    {"event": '10. Tonglüshan North Compartment', "HD": 25, "HDB": 25, "VOut": 500000, "VS": 265000, "VI": 235000, "VP": None, "HB": 12, "BT": 260, "BB": 235, "Tf": None, "process": 'Non-Erosional', "cda": '1A or 2A or 2B or 2A', "raise_": 'US'},
    {"event": '11a. Cadia NTSF Event I', "HD": 94, "HDB": 68, "VOut": 1.17e+06, "VS": 737100, "VI": 432900, "VP": None, "HB": None, "BT": 300, "BB": 240, "Tf": None, "process": 'Non-Erosional (Slump)', "cda": '2A or 2B', "raise_": 'US'},
    {"event": '11b. Cadia NTSF Event II', "HD": None, "HDB": None, "VOut": 160000, "VS": 100800, "VI": 59200, "VP": None, "HB": None, "BT": 30, "BB": 30, "Tf": None, "process": 'Non-Erosional', "cda": '2A', "raise_": ''},
    {"event": '12. Feijão Dam I', "HD": 87, "HDB": 87, "VOut": 9.651e+06, "VS": 5.598e+06, "VI": 4.053e+06, "VP": None, "HB": 80, "BT": 560, "BB": 100, "Tf": None, "process": 'Non-Erosional', "cda": '2A', "raise_": 'US'},
]



# ---------------------------------------------------------------------
# Froehlich (2016a), Table 1 — 41 WATER-RETAINING embankment dam failures
# with measured peak discharge. Transcribed from the published table.
#
# mode: IE internal erosion; OF overtopping by floodwaters; OG outlet
# works failure; OS embankment sliding; OW wave action; OX intentional
# breaching by excavation (analysed by Froehlich as internal erosion).
#
# Check performed on transcription: the minimum and maximum of every
# variable reproduce Froehlich's Table 2 exactly. Recomputing his Eq. 2
# over these rows gives an RMSE of ln Qp of about 0.41, not the 0.277 he
# reports; the cause is not identifiable from the paper, so these rows
# are used only as measured case histories, not to re-derive the fit.
# ---------------------------------------------------------------------
FROEHLICH_2016A = [
    {"event": e, "mode": m, "Wavg": w, "Vw": v * 1e6, "Hw": hw, "Hb": hb,
     "La": la, "Qp": q}
    for (e, m, w, v, hw, hb, la, q) in [
        ("Apishapa, Colorado", "IE", 82.4, 22.8, 28.0, 31.1, 200, 6850),
        ("Baldwin Hills, California", "IE", 59.6, 0.950, 12.2, 21.3, 200, 420),
        ("Banqiao, China", "OF", 97.0, 701, 31.9, 29.5, 2100, 56300),
        ("Bass Haven Lake, Texas", "OX", 22.9, 0.641, 4.90, 9.20, None, 240),
        ("Belci, Romania", "OF", 37.8, 12.7, 15.5, 15.0, 400, 4700),
        ("Bila Desna, Czech Republic", "IE", 29.6, 0.290, 10.7, 14.6, 170, 320),
        ("Bilberry, England", "OS", 62.5, 0.327, 23.6, 23.0, 800, 725),
        ("Big Bay Lake, Mississippi", "IE", 20.4, 17.5, 13.6, 14.0, 200, 4160),
        ("Bradfield (Dale Dyke), England", "IE", 76.0, 3.20, 28.0, 29.0, 300, 2370),
        ("Butler Valley, Arizona", "OF", 9.63, 2.38, 7.16, 7.16, 850, 810),
        ("Castlewood, Colorado", "OF", 47.4, 6.17, 21.6, 21.3, 180, 3570),
        ("Centralia No. 3, Washington", "OS", 10.1, 0.01333, 5.50, 6.10, 40, 71),
        ("Delhi, Iowa", "OF", 31.5, 12.2, 11.2, 11.0, 170, 1950),
        ("FP&L Martin Plant, Florida", "IE", 27.7, 125, 5.09, 9.14, 4100, 2750),
        ("Fred Burr, Montana", "IE", 30.8, 0.750, 10.2, 10.2, 100, 654),
        ("French Landing, Michigan", "IE", 34.3, 3.87, 8.53, 14.2, 350, 929),
        ("Frenchman Creek, Montana", "IE", 37.3, 16.0, 10.8, 12.5, 600, 1420),
        ("Hastberga, Sweden", "OG", 12.7, 30.0, 7.35, 7.00, 200, 600),
        ("Hatchtown, Utah", "OS", 44.8, 16.0, 16.8, 18.3, 200, 4440),
        ("Hell Hole, California", "IE", 103, 30.6, 35.1, 56.4, 470, 17000),
        ("Ireland Reservoir No. 5, Colorado", "IE", 18.0, 0.160, 3.81, 5.18, 370, 110),
        ("Kelly Barnes, Georgia", "IE", 19.4, 0.777, 11.3, 12.8, 80, 680),
        ("Lake Avalon, New Mexico", "IE", 42.7, 31.5, 13.7, 14.6, 370, 2320),
        ("Laurel Run, Pennsylvania", "OF", 40.5, 0.555, 14.1, 13.7, 160, 1050),
        ("Lily Lake, Colorado", "OW", 13.2, 0.0925, 3.35, 3.66, 60, 71),
        ("Little Deer Creek, Utah", "IE", 63.1, 1.36, 22.9, 27.1, 400, 1330),
        ("Lower Latham, Colorado", "IE", 25.7, 7.08, 5.79, 7.01, 120, 340),
        ("Lower Otay, California", "OF", 53.3, 56.9, 39.6, 39.6, 200, 15800),
        ("Lower Two Medicine, Montana", "IE", 33.3, 29.6, 11.3, 11.3, 350, 1800),
        ("Oros, Brazil", "OF", 110, 660, 35.8, 35.5, 2000, 58000),
        ("Porter Hill, Oregon", "OS", 12.0, 0.015, 5.00, 5.80, 80, 30),
        ("Prospect, Colorado", "IE", 13.1, 3.54, 1.68, 4.42, 900, 116),
        ("Puddingstone, California", "OF", 43.0, 0.432, 13.7, 13.7, 420, 960),
        ("Quail Creek, Utah", "IE", 56.6, 30.8, 16.7, 21.3, 550, 3110),
        ("Rito Manzanares, New Mexico", "IE", 13.4, 0.120, 4.57, 7.32, 75, 83),
        ("Schaeffer, Colorado", "OF", 80.8, 4.44, 31.9, 30.5, 350, 4930),
        ("Shimantan, China", "OF", 58.0, 167, 27.4, 25.8, 900, 25300),
        ("South Fork, Pennsylvania", "OF", 64.0, 18.9, 24.6, 24.4, 300, 8500),
        ("Taum Sauk Reservoir, Missouri", "OF", 46.8, 5.39, 36.5, 36.3, 250, 8180),
        ("Teton, Idaho", "IE", 250, 310, 77.4, 86.9, 500, 65120),
        ("Zhuguo, China", "OF", 99.0, 18.5, 23.8, 23.5, 300, 11200),
    ]
]


# ---------------------------------------------------------------------
# Xu and Zhang (2009), Table 1 — 75 earth and rockfill WATER-RETAINING dam
# failures. Transcribed from the published table. Verification: the number
# of cases with each variable reproduces the case counts Xu and Zhang report
# for their own regressions (Hb/Hd 71, Bt 61, Bave 53, Qp 39, Tf 30), and
# dams shared with Froehlich (2016a) agree except where Froehlich documents
# revised peak discharges (Banqiao, Hell Hole, Oros).
# Units: Hd, Hw, Hb, Bt, Bb, Bave in m; Vd, Vw in m3; Qp in m3/s; Tf in h;
# Z side slope (H:V). type: HD homogeneous, DC corewall, FD concrete-faced,
# ZD zoned. erod: HE/ME/LE high/medium/low. mode: O overtopping, P piping.
# ---------------------------------------------------------------------
XU_ZHANG_2009 = [
    {"event": 'Apishapa', "location": 'United States', "type": 'HD', "Hd": 34.1, "Vd": 22500000.0, "erod": 'HE', "mode": 'P', "Vw": 22200000.0, "Hw": 28.0, "Hb": 31.1, "Bt": 91.5, "Bb": 81.5, "Bave": 86.5, "Z": 0.44, "Qp": 6850.0, "Tf": 2.5},
    {"event": 'Baimiku', "location": 'China', "type": 'HD', "Hd": 8.0, "Vd": 200000.0, "erod": 'ME', "mode": 'O', "Vw": 200000.0, "Hw": 8.0, "Hb": 8.0, "Bt": 40.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Banqiao', "location": 'China', "type": 'DC', "Hd": 24.5, "Vd": 492000000.0, "erod": 'HE', "mode": 'O', "Vw": 607500000.0, "Hw": 31.0, "Hb": 29.5, "Bt": 372.0, "Bb": 210.0, "Bave": 291.0, "Z": 0.3, "Qp": 78100.0, "Tf": 5.5},
    {"event": 'Bayi', "location": 'China', "type": 'HD', "Hd": 30.0, "Vd": 30000000.0, "erod": 'ME', "mode": 'P', "Vw": 23000000.0, "Hw": 28.0, "Hb": 30.0, "Bt": 45.0, "Bb": 35.0, "Bave": 40.0, "Z": 0.17, "Qp": 5000.0, "Tf": None},
    {"event": 'Castlewood', "location": 'United States', "type": 'DC', "Hd": 21.3, "Vd": 4230000.0, "erod": 'ME', "mode": 'O', "Vw": 6170000.0, "Hw": 21.6, "Hb": 21.3, "Bt": 54.9, "Bb": 33.5, "Bave": 44.2, "Z": 0.5, "Qp": 3570.0, "Tf": None},
    {"event": 'Chenying', "location": 'China', "type": 'HD', "Hd": 12.0, "Vd": 4250000.0, "erod": 'ME', "mode": 'O', "Vw": 5000000.0, "Hw": 12.0, "Hb": 12.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 1200.0, "Tf": 1.83},
    {"event": 'Coedty', "location": 'U.K.', "type": 'DC', "Hd": 11.0, "Vd": 310000.0, "erod": 'HE', "mode": 'O', "Vw": 311000.0, "Hw": 11.0, "Hb": 11.0, "Bt": 67.0, "Bb": 18.2, "Bave": 42.7, "Z": 2.22, "Qp": None, "Tf": None},
    {"event": 'Dalizhuang', "location": 'China', "type": 'HD', "Hd": 12.0, "Vd": 600000.0, "erod": 'ME', "mode": 'O', "Vw": 600000.0, "Hw": 12.0, "Hb": 12.0, "Bt": 40.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Danghe', "location": 'China', "type": 'DC', "Hd": 46.0, "Vd": 15600000.0, "erod": 'LE', "mode": 'O', "Vw": 10700000.0, "Hw": 24.5, "Hb": 25.0, "Bt": 96.0, "Bb": 20.0, "Bave": 58.0, "Z": 0.66, "Qp": 2500.0, "Tf": 3.0},
    {"event": 'Davis Reservior', "location": 'United States', "type": 'FD', "Hd": 11.9, "Vd": 58000000.0, "erod": 'ME', "mode": 'P', "Vw": 58000000.0, "Hw": 11.58, "Hb": 11.9, "Bt": 21.3, "Bb": 15.4, "Bave": 18.3, "Z": 0.25, "Qp": 510.0, "Tf": None},
    {"event": 'Dells', "location": 'United States', "type": None, "Hd": 18.3, "Vd": 13000000.0, "erod": 'HE', "mode": 'O', "Vw": 13000000.0, "Hw": 18.3, "Hb": 18.3, "Bt": 112.8, "Bb": None, "Bave": None, "Z": None, "Qp": 5440.0, "Tf": 0.67},
    {"event": 'Dongchuankou', "location": 'China', "type": 'HD', "Hd": 31.0, "Vd": 27000000.0, "erod": 'HE', "mode": 'O', "Vw": 27000000.0, "Hw": 31.0, "Hb": 31.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 21000.0, "Tf": None},
    {"event": 'Dushan', "location": 'China', "type": 'HD', "Hd": 17.7, "Vd": 670000.0, "erod": 'ME', "mode": 'O', "Vw": 670000.0, "Hw": 17.7, "Hb": 17.7, "Bt": 70.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Elk City', "location": 'United States', "type": 'DC', "Hd": 9.1, "Vd": 740000.0, "erod": 'ME', "mode": 'O', "Vw": 1180000.0, "Hw": 9.44, "Hb": 9.14, "Bt": 45.5, "Bb": 27.7, "Bave": 36.6, "Z": 1.0, "Qp": None, "Tf": 0.83},
    {"event": 'Erlangmiao', "location": 'China', "type": 'HD', "Hd": 12.1, "Vd": 196000.0, "erod": 'ME', "mode": 'O', "Vw": 196000.0, "Hw": 9.0, "Hb": 9.0, "Bt": 36.0, "Bb": 1.6, "Bave": 18.8, "Z": 1.9, "Qp": None, "Tf": None},
    {"event": 'Fengzhuang', "location": 'China', "type": 'HD', "Hd": 10.0, "Vd": 625000.0, "erod": 'ME', "mode": 'O', "Vw": 625000.0, "Hw": 8.0, "Hb": 8.0, "Bt": 40.0, "Bb": 30.0, "Bave": 35.0, "Z": 0.63, "Qp": None, "Tf": None},
    {"event": 'Frankfurt', "location": 'Germany', "type": 'HD', "Hd": 9.8, "Vd": 350000.0, "erod": 'LE', "mode": 'P', "Vw": 352000.0, "Hw": 8.23, "Hb": 9.75, "Bt": 9.2, "Bb": 4.6, "Bave": 6.9, "Z": 0.4, "Qp": 79.0, "Tf": 2.5},
    {"event": 'French Landing', "location": 'United States', "type": 'HD', "Hd": 12.2, "Vd": None, "erod": 'HE', "mode": 'P', "Vw": 3870000.0, "Hw": 8.53, "Hb": 14.2, "Bt": 41.0, "Bb": 13.8, "Bave": 27.4, "Z": 0.97, "Qp": 929.0, "Tf": 0.58},
    {"event": 'Frenchman Dam', "location": 'United States', "type": 'HD', "Hd": 12.5, "Vd": 21000000.0, "erod": 'ME', "mode": 'P', "Vw": 16000000.0, "Hw": 10.8, "Hb": 12.5, "Bt": 67.0, "Bb": 54.4, "Bave": 54.6, "Z": 0.5, "Qp": 1420.0, "Tf": 3.0},
    {"event": 'Frias', "location": 'Argentina', "type": 'FD', "Hd": 15.0, "Vd": 250000.0, "erod": 'ME', "mode": 'O', "Vw": 250000.0, "Hw": 15.0, "Hb": 15.0, "Bt": 62.0, "Bb": None, "Bave": None, "Z": None, "Qp": 400.0, "Tf": 0.25},
    {"event": 'Gouhou', "location": 'China', "type": 'FD', "Hd": 71.0, "Vd": 3300000.0, "erod": 'LE', "mode": 'P', "Vw": 3180000.0, "Hw": 44.0, "Hb": 48.0, "Bt": 138.0, "Bb": 61.0, "Bave": 99.5, "Z": 1.27, "Qp": 2050.0, "Tf": 2.33},
    {"event": 'Grand Rapids', "location": 'United States', "type": 'DC', "Hd": 7.6, "Vd": 220000.0, "erod": 'ME', "mode": 'O', "Vw": 255000.0, "Hw": 7.5, "Hb": 7.5, "Bt": 12.2, "Bb": 9.1, "Bave": 10.7, "Z": None, "Qp": None, "Tf": 0.5},
    {"event": 'Hart', "location": 'United States', "type": 'HD', "Hd": None, "Vd": None, "erod": 'HE', "mode": 'P', "Vw": 6350000.0, "Hw": 10.7, "Hb": 10.8, "Bt": 106.6, "Bb": 41.2, "Bave": 73.9, "Z": 3.03, "Qp": None, "Tf": None},
    {"event": 'Hatfield', "location": 'United States', "type": None, "Hd": 6.8, "Vd": 12300000.0, "erod": 'HE', "mode": 'O', "Vw": 12300000.0, "Hw": 6.8, "Hb": 6.8, "Bt": None, "Bb": 6.1, "Bave": 91.5, "Z": None, "Qp": 3400.0, "Tf": 2.0},
    {"event": 'Hell Hole', "location": 'United States', "type": None, "Hd": 67.1, "Vd": 30600000.0, "erod": 'ME', "mode": 'P', "Vw": 30600000.0, "Hw": 35.1, "Hb": 56.4, "Bt": 175.1, "Bb": 66.9, "Bave": 121.0, "Z": 0.96, "Qp": 7360.0, "Tf": None},
    {"event": 'Horse Creek', "location": 'United States', "type": 'FD', "Hd": 12.2, "Vd": 21000000.0, "erod": 'ME', "mode": 'P', "Vw": 12800000.0, "Hw": 7.01, "Hb": 12.8, "Bt": 76.2, "Bb": 70.0, "Bave": 73.1, "Z": 0.83, "Qp": 3890.0, "Tf": 3.0},
    {"event": 'Hougou', "location": 'China', "type": 'HD', "Hd": 8.0, "Vd": 240000.0, "erod": 'ME', "mode": 'O', "Vw": 240000.0, "Hw": 8.0, "Hb": 8.0, "Bt": None, "Bb": None, "Bave": 20.0, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Huoshishan', "location": 'China', "type": 'HD', "Hd": 13.0, "Vd": 220000.0, "erod": 'HE', "mode": 'O', "Vw": 220000.0, "Hw": 16.0, "Hb": 16.0, "Bt": 45.0, "Bb": 15.0, "Bave": 30.0, "Z": 0.94, "Qp": None, "Tf": None},
    {"event": 'Huqitang', "location": 'China', "type": 'HD', "Hd": 9.9, "Vd": 734000.0, "erod": 'LE', "mode": 'P', "Vw": 424000.0, "Hw": 5.1, "Hb": 9.0, "Bt": 12.0, "Bb": 3.0, "Bave": 7.5, "Z": 0.5, "Qp": 50.0, "Tf": 4.0},
    {"event": 'Jiahezi', "location": 'China', "type": 'HD', "Hd": 18.0, "Vd": 80000000.0, "erod": 'HE', "mode": 'P', "Vw": 42000000.0, "Hw": 12.0, "Hb": 18.0, "Bt": 181.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Johnstown', "location": 'United States', "type": 'ZD', "Hd": 38.1, "Vd": 18900000.0, "erod": 'ME', "mode": 'O', "Vw": 18900000.0, "Hw": 24.6, "Hb": 24.4, "Bt": 128.0, "Bb": 61.0, "Bave": 94.5, "Z": 1.38, "Qp": 8500.0, "Tf": None},
    {"event": 'Kelly Barnes', "location": 'United States', "type": 'HD', "Hd": 11.6, "Vd": 505000.0, "erod": 'HE', "mode": 'O', "Vw": 777000.0, "Hw": 11.3, "Hb": 12.8, "Bt": 35.0, "Bb": 18.0, "Bave": 27.3, "Z": 0.85, "Qp": 680.0, "Tf": 0.5},
    {"event": 'Kodaganar', "location": 'India', "type": 'HD', "Hd": 11.5, "Vd": 12300000.0, "erod": 'ME', "mode": 'O', "Vw": 12300000.0, "Hw": 11.5, "Hb": 11.5, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 1280.0, "Tf": None},
    {"event": 'Lake Frances', "location": 'United States', "type": 'HD', "Hd": 15.2, "Vd": 865000.0, "erod": 'ME', "mode": 'P', "Vw": 789000.0, "Hw": 14.0, "Hb": 17.1, "Bt": 30.0, "Bb": 10.4, "Bave": 18.9, "Z": 0.65, "Qp": None, "Tf": 1.0},
    {"event": 'Lake Latonka', "location": 'United States', "type": 'HD', "Hd": 13.0, "Vd": 4590000.0, "erod": 'ME', "mode": 'P', "Vw": 4090000.0, "Hw": 6.25, "Hb": 8.69, "Bt": 49.5, "Bb": 28.9, "Bave": 39.2, "Z": 1.18, "Qp": 290.0, "Tf": 3.0},
    {"event": 'Lijiaju', "location": 'China', "type": 'HD', "Hd": 25.0, "Vd": 1140000.0, "erod": 'ME', "mode": 'O', "Vw": 1140000.0, "Hw": 25.0, "Hb": 25.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 2950.0, "Tf": None},
    {"event": 'Little Deer Creek', "location": 'United States', "type": 'HD', "Hd": 26.2, "Vd": 1730000.0, "erod": 'HE', "mode": 'P', "Vw": 1360000.0, "Hw": 22.9, "Hb": 27.1, "Bt": 49.9, "Bb": 9.3, "Bave": 29.6, "Z": 0.75, "Qp": 1330.0, "Tf": 0.33},
    {"event": 'Liujiatai', "location": 'China', "type": 'DC', "Hd": 35.9, "Vd": 40540000.0, "erod": 'ME', "mode": 'O', "Vw": 40540000.0, "Hw": 35.9, "Hb": 35.9, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 28000.0, "Tf": None},
    {"event": 'Longtun', "location": 'China', "type": 'DC', "Hd": 9.5, "Vd": 30000000.0, "erod": 'HE', "mode": 'O', "Vw": 30000000.0, "Hw": 9.5, "Hb": 9.5, "Bt": 181.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Lower Otay', "location": 'United States', "type": 'DC', "Hd": 41.2, "Vd": 49300000.0, "erod": 'ME', "mode": 'O', "Vw": 49300000.0, "Hw": 39.6, "Hb": 39.6, "Bt": 172.0, "Bb": 93.8, "Bave": 133.0, "Z": 1.0, "Qp": None, "Tf": None},
    {"event": 'Lower Two Medicine', "location": 'United States', "type": 'HD', "Hd": 11.3, "Vd": 19600000.0, "erod": 'HE', "mode": 'O', "Vw": 19600000.0, "Hw": 11.3, "Hb": 11.3, "Bt": 84.0, "Bb": 50.0, "Bave": 67.0, "Z": 1.5, "Qp": 1800.0, "Tf": None},
    {"event": 'Lyman', "location": 'United States', "type": 'ZD', "Hd": 19.8, "Vd": 49500000.0, "erod": 'HE', "mode": 'P', "Vw": 35800000.0, "Hw": 16.2, "Hb": 19.8, "Bt": 107.0, "Bb": 87.0, "Bave": 97.0, "Z": 1.0, "Qp": None, "Tf": None},
    {"event": 'Lynde Brook', "location": 'United States', "type": 'DC', "Hd": 12.5, "Vd": 2520000.0, "erod": 'ME', "mode": 'P', "Vw": 2880000.0, "Hw": 11.6, "Hb": 12.5, "Bt": 45.7, "Bb": 15.3, "Bave": 30.5, "Z": 1.22, "Qp": None, "Tf": None},
    {"event": 'Mahe', "location": 'China', "type": 'HD', "Hd": 19.5, "Vd": 23400000.0, "erod": 'HE', "mode": 'O', "Vw": 23400000.0, "Hw": 19.5, "Hb": 19.5, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 4950.0, "Tf": None},
    {"event": 'Mammoth', "location": 'United States', "type": 'DC', "Hd": 21.3, "Vd": 13600000.0, "erod": 'ME', "mode": 'O', "Vw": 13600000.0, "Hw": 21.3, "Hb": 21.3, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 2520.0, "Tf": 3.0},
    {"event": 'Martin Cooling Pond Dike', "location": 'United States', "type": None, "Hd": 10.4, "Vd": 136000000.0, "erod": 'HE', "mode": 'P', "Vw": 136000000.0, "Hw": 8.53, "Hb": 12.8, "Bt": None, "Bb": None, "Bave": 186.0, "Z": None, "Qp": 3115.0, "Tf": None},
    {"event": 'Niujiaoyu', "location": 'China', "type": 'DC', "Hd": 10.0, "Vd": 160000.0, "erod": 'LE', "mode": 'P', "Vw": 144000.0, "Hw": 7.2, "Hb": 7.2, "Bt": 20.0, "Bb": 6.0, "Bave": 13.0, "Z": 0.93, "Qp": None, "Tf": 3.0},
    {"event": 'Oros', "location": 'Brazil', "type": 'ZD', "Hd": 35.4, "Vd": 650000000.0, "erod": 'LE', "mode": 'O', "Vw": 660000000.0, "Hw": 35.8, "Hb": 35.5, "Bt": 200.0, "Bb": 130.0, "Bave": 165.0, "Z": 1.0, "Qp": 9630.0, "Tf": None},
    {"event": 'Otter Lake', "location": 'United States', "type": 'HD', "Hd": 6.1, "Vd": 150000.0, "erod": 'ME', "mode": 'P', "Vw": 109000.0, "Hw": 5.0, "Hb": 6.1, "Bt": 17.1, "Bb": 1.5, "Bave": 9.3, "Z": 1.28, "Qp": None, "Tf": None},
    {"event": 'Potato Hill Lake', "location": 'United States', "type": 'HD', "Hd": None, "Vd": None, "erod": 'ME', "mode": 'O', "Vw": 105000.0, "Hw": 7.77, "Hb": 7.77, "Bt": 26.2, "Bb": 6.8, "Bave": 16.5, "Z": 1.25, "Qp": None, "Tf": None},
    {"event": 'Prospect', "location": 'United States', "type": 'HD', "Hd": None, "Vd": None, "erod": 'HE', "mode": 'P', "Vw": 3540000.0, "Hw": 1.68, "Hb": 4.42, "Bt": 91.4, "Bb": 85.4, "Bave": 88.4, "Z": 0.69, "Qp": 116.0, "Tf": None},
    {"event": 'Qielinggou', "location": 'China', "type": 'HD', "Hd": 18.0, "Vd": 700000.0, "erod": 'HE', "mode": 'O', "Vw": 700000.0, "Hw": 18.0, "Hb": 18.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 2000.0, "Tf": 0.17},
    {"event": 'Quail Creek', "location": 'United States', "type": 'HD', "Hd": 24.0, "Vd": 50000000.0, "erod": 'ME', "mode": 'P', "Vw": 30800000.0, "Hw": 16.7, "Hb": 21.3, "Bt": 72.1, "Bb": 67.9, "Bave": 70.0, "Z": 0.1, "Qp": 3110.0, "Tf": None},
    {"event": 'Rito Manzanares', "location": 'United States', "type": 'HD', "Hd": 7.3, "Vd": 24700.0, "erod": 'HE', "mode": 'P', "Vw": 24700.0, "Hw": 4.57, "Hb": 7.32, "Bt": 19.0, "Bb": 7.6, "Bave": 13.3, "Z": 0.77, "Qp": None, "Tf": None},
    {"event": 'Schaeffer Reservoir', "location": 'United States', "type": 'DC', "Hd": 30.5, "Vd": 3920000.0, "erod": 'HE', "mode": 'O', "Vw": 4440000.0, "Hw": 30.5, "Hb": 30.5, "Bt": 210.0, "Bb": 64.0, "Bave": 137.0, "Z": 2.25, "Qp": 4500.0, "Tf": 0.5},
    {"event": 'Shangliuzhuang', "location": 'China', "type": 'HD', "Hd": 14.0, "Vd": 110000.0, "erod": 'ME', "mode": 'O', "Vw": 110000.0, "Hw": 14.0, "Hb": 14.0, "Bt": 30.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Shanhu', "location": 'China', "type": 'HD', "Hd": 11.5, "Vd": 2150000.0, "erod": 'HE', "mode": 'P', "Vw": 1780000.0, "Hw": 12.5, "Hb": 13.0, "Bt": 58.0, "Bb": 24.0, "Bave": 41.0, "Z": 1.31, "Qp": None, "Tf": None},
    {"event": 'Sheep Creek', "location": 'United States', "type": 'HD', "Hd": 17.1, "Vd": 1430000.0, "erod": 'ME', "mode": 'P', "Vw": 910000.0, "Hw": 14.02, "Hb": 17.1, "Bt": 30.5, "Bb": 13.5, "Bave": 22.0, "Z": 0.5, "Qp": None, "Tf": None},
    {"event": 'Shilongshan', "location": 'China', "type": 'HD', "Hd": 14.0, "Vd": 2060000.0, "erod": 'ME', "mode": 'O', "Vw": 2060000.0, "Hw": 14.0, "Hb": 14.0, "Bt": 50.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Shimantan', "location": 'China', "type": 'HD', "Hd": 25.0, "Vd": 94400000.0, "erod": 'HE', "mode": 'O', "Vw": 117000000.0, "Hw": 27.4, "Hb": 25.8, "Bt": 446.0, "Bb": 288.0, "Bave": 367.0, "Z": 0.32, "Qp": 30000.0, "Tf": 5.5},
    {"event": 'Spring Lake', "location": 'United States', "type": 'HD', "Hd": 5.5, "Vd": 135000.0, "erod": 'HE', "mode": 'P', "Vw": 136000.0, "Hw": 5.49, "Hb": 5.49, "Bt": 20.0, "Bb": 9.0, "Bave": 14.5, "Z": 1.0, "Qp": None, "Tf": None},
    {"event": 'Statham Lake', "location": 'United States', "type": 'HD', "Hd": 5.5, "Vd": None, "erod": 'ME', "mode": 'O', "Vw": 564000.0, "Hw": 5.55, "Hb": 5.12, "Bt": 23.8, "Bb": 18.2, "Bave": 21.0, "Z": 0.54, "Qp": None, "Tf": None},
    {"event": 'Swift', "location": 'United States', "type": 'FD', "Hd": 57.6, "Vd": 37000000.0, "erod": 'ME', "mode": 'O', "Vw": 37000000.0, "Hw": 47.85, "Hb": 57.6, "Bt": 225.0, "Bb": 225.0, "Bave": 225.0, "Z": 0.0, "Qp": 24947.0, "Tf": None},
    {"event": 'Teton', "location": 'United States', "type": 'ZD', "Hd": 93.0, "Vd": 356000000.0, "erod": 'ME', "mode": 'P', "Vw": 310000000.0, "Hw": 77.4, "Hb": 86.9, "Bt": 237.9, "Bb": 64.1, "Bave": 151.0, "Z": 1.0, "Qp": 65120.0, "Tf": 4.0},
    {"event": 'Tiemusi', "location": 'China', "type": 'HD', "Hd": 12.0, "Vd": 110000.0, "erod": 'HE', "mode": 'O', "Vw": 110000.0, "Hw": 12.0, "Hb": 12.0, "Bt": 60.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Tongshuyuan', "location": 'China', "type": 'HD', "Hd": 13.0, "Vd": 400000.0, "erod": 'ME', "mode": 'O', "Vw": 400000.0, "Hw": 10.0, "Hb": 10.0, "Bt": 30.0, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": None},
    {"event": 'Trial Lake', "location": 'United States', "type": None, "Hd": None, "Vd": None, "erod": 'ME', "mode": 'P', "Vw": 1480000.0, "Hw": 5.18, "Hb": 5.18, "Bt": 25.2, "Bb": 16.8, "Bave": 21.0, "Z": 0.82, "Qp": None, "Tf": None},
    {"event": 'Upper Pond', "location": 'United States', "type": None, "Hd": 5.2, "Vd": 220000.0, "erod": 'ME', "mode": 'O', "Vw": 222000.0, "Hw": 5.18, "Hb": 5.18, "Bt": 25.4, "Bb": 7.6, "Bave": 16.5, "Z": 1.71, "Qp": None, "Tf": None},
    {"event": 'Wanshangang', "location": 'China', "type": 'HD', "Hd": 13.0, "Vd": 1500000.0, "erod": 'ME', "mode": 'O', "Vw": 1500000.0, "Hw": 12.0, "Hb": 12.0, "Bt": 50.0, "Bb": 30.0, "Bave": 40.0, "Z": 0.83, "Qp": None, "Tf": None},
    {"event": 'Wilkinson Lake', "location": 'United States', "type": 'DC', "Hd": 3.2, "Vd": None, "erod": 'HE', "mode": 'P', "Vw": 533000.0, "Hw": 3.57, "Hb": 3.72, "Bt": 35.5, "Bb": 22.5, "Bave": 29.0, "Z": 1.74, "Qp": None, "Tf": None},
    {"event": 'Winston', "location": 'United States', "type": 'DC', "Hd": 7.3, "Vd": 664000.0, "erod": 'LE', "mode": 'O', "Vw": 662000.0, "Hw": 6.4, "Hb": 6.1, "Bt": 21.3, "Bb": 18.3, "Bave": 19.8, "Z": 0.2, "Qp": None, "Tf": 5.0},
    {"event": 'Yuanmen', "location": 'China', "type": 'HD', "Hd": 19.2, "Vd": 6400000.0, "erod": 'HE', "mode": 'O', "Vw": 6400000.0, "Hw": 19.2, "Hb": 19.2, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": 0.5},
    {"event": 'Zhonghuaju', "location": 'China', "type": 'HD', "Hd": 16.0, "Vd": 140000.0, "erod": 'HE', "mode": 'O', "Vw": 140000.0, "Hw": 16.0, "Hb": 16.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": None, "Tf": 0.4},
    {"event": 'Zhugou', "location": 'China', "type": 'DC', "Hd": 23.5, "Vd": 15400000.0, "erod": 'HE', "mode": 'O', "Vw": 18430000.0, "Hw": 23.5, "Hb": 23.5, "Bt": 159.0, "Bb": 110.0, "Bave": 135.0, "Z": 0.98, "Qp": 11200.0, "Tf": 0.43},
    {"event": 'Zuocun', "location": 'China', "type": 'DC', "Hd": 35.0, "Vd": 40000000.0, "erod": 'HE', "mode": 'O', "Vw": 40000000.0, "Hw": 35.0, "Hb": 35.0, "Bt": None, "Bb": None, "Bave": None, "Z": None, "Qp": 23600.0, "Tf": 1.0},
]


# ---------------------------------------------------------------------
# Free water and tailings outflow volumes, reconstructed from Rana et al.
# (2021) supplementary database as: free water = impounded supernatant pond
# (Fw); tailings outflow = total outflow (VF) minus Fw. Eleven events have
# both values. Rana et al. (2023), Fig. 5, plots twelve; the twelfth is not
# reconstructible from this version of the database.
# ---------------------------------------------------------------------
RANA_2021_FW_TF = [
    {"event": 'Huogodu', "cda": '1B', "Fw": 380000, "VF": 3.68e+06, "TF": 3.3e+06},
    {"event": 'Stava', "cda": '1A', "Fw": 20000, "VF": 185220, "TF": 165220},
    {"event": 'Merriespruit', "cda": '1A', "Fw": 85000, "VF": 630000, "TF": 545000},
    {"event": 'Aznalcollar', "cda": '1A', "Fw": 5.44e+06, "VF": 6.8e+06, "TF": 1.36e+06},
    {"event": 'Inez', "cda": '1B', "Fw": 950000, "VF": 1.07e+06, "TF": 120000},
    {"event": 'Karamken', "cda": '1A', "Fw": 1.1e+06, "VF": 1.38e+06, "TF": 280000},
    {"event": 'Ajka', "cda": '1A', "Fw": 835000, "VF": 1.644e+06, "TF": 809000},
    {"event": 'Gullbridge', "cda": '1B', "Fw": 5000, "VF": 100500, "TF": 95500},
    {"event": 'Obed Mountain', "cda": '1B', "Fw": 469000, "VF": 670000, "TF": 201000},
    {"event": 'Dan River', "cda": '1B', "Fw": 100000, "VF": 138000, "TF": 38000},
    {"event": 'Mount Polley', "cda": '1B', "Fw": 1.06e+07, "VF": 2.5e+07, "TF": 1.44e+07},
]
