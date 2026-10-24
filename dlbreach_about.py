"""
dlbreach_about.py
-----------------
Text for the About page. Kept separate so wording can be revised without
touching the interface.
"""

TITLE = "DLBreach Dashboard"
SUBTITLE = "An interactive Monte Carlo companion to a physically based dam breach algorithm"
AUTHOR = "Dr. Nahyan M. Rana"
PREPARED_BY = ("Prepared by Dr. Nahyan M. Rana, Geosyntec Consultants and "
               "University of Waterloo")
VERSION = "Version 1.0.2"
VERSION_SHORT = "version 1.0.2"
ALGORITHM_BY = "Algorithm by Prof. Weiming Wu, Clarkson University"
CONTACT_EMAIL = "nahyan.rana@geosyntec.com"
CONTACT_HTML = (
    '<div class="dlb-contact"><p class="h">Questions and feedback</p>'
    '<p>This is a development build; comments and questions are welcome.</p>'
    f'<p class="e"><a href="mailto:{CONTACT_EMAIL}?subject=DLBreach%20Dashboard">'
    f'{CONTACT_EMAIL}</a></p></div>')

ABOUT_MODEL = """
### The algorithm

DLBreach is a simplified, physically based model of embankment breaching
developed by **Professor Weiming Wu**, Clarkson University (Wu 2013, 2016).
It advances a breach through time by coupling flow through the breach,
non-equilibrium sediment transport and the stability of the breach sides,
for overtopping or piping initiation in cohesive or non-cohesive fill. Its
outputs, breach hydrographs and the erosion of the embankment through
time, respond directly to the embankment's material properties and
geometry.

The model, its technical report and the input and output file
specifications are at
[webspace.clarkson.edu/~wwu/DLBreach.html](https://webspace.clarkson.edu/~wwu/DLBreach.html).
"""

ABOUT_DASHBOARD = """
### This dashboard

Developed by **Dr. Nahyan M. Rana** (Geosyntec Consultants; University of
Waterloo) to help practitioners and researchers apply DLBreach to research
and industry projects efficiently and probabilistically: structured input
in practitioner units, a live cross-section, sensitivity runs, Monte Carlo
ensembles, comparison with case histories, and report-ready output.

Every simulation is executed by the published DLBreach executable; the
dashboard writes the input, runs it and presents the output, and adds no
physics to the model. Anything it derives from the output, such as the
flow depth drawn in the breach or the eroded embankment volume, is
identified where it is shown. The dashboard was developed with an AI
coding assistant, under the author's direction and engineering review,
and each release is checked by automated tests, independent review and
benchmark cases. Professor Wu was consulted during
development; the dashboard is independent of, and not endorsed by, him or
Clarkson University.

This version covers water-retaining dams. Support for solid waste dams
(tailings, coal ash) is in development.
"""

LIMITATIONS = """
### Model limitations

- **Developed for water-retaining dams.** DLBreach was developed and tested
  against laboratory experiments and historical failures of
  water-retaining embankments and levees (Wu 2016). It was not developed
  or validated for tailings or coal combustion residual (solid waste)
  dams.
- **Clear water only.** DLBreach routes the impoundment as clear water;
  stored solids are not eroded or carried by the model.
- **Simplified breach geometry.** The breach is represented as a
  trapezoid, and results depend strongly on uncertain inputs such as grain
  size, erosion limit and Manning's n. Sensitivity and Monte Carlo analysis
  are recommended.
"""

FOUNDATIONS = """
### Foundational methodology

The dashboard implements the probabilistic approach of **Palmen and Kent
(2024)**: DLBreach (Wu 2013, 2016) is run within a Monte Carlo framework,
with uncertain inputs sampled from statistical distributions and the
resulting breach outputs analysed as distributions. The approach includes
sensitivity checks on individual parameters, input–output correlation,
selection of representative realisations, and comparison with historical
failure databases. Other breach models using a Monte Carlo approach
include Embrea (HR Wallingford 2024) and McBreach (Kleinschmidt 2024). The
dashboard provides an interactive interface to this method and adds no
physics of its own.

- Palmen, L., & Kent, N. (2024). Use of a physically based erosion breach
  model for water and tailings dams within a probabilistic framework.
  *ANCOLD 2024 Conference Proceedings*.
- HR Wallingford (2024). *Embrea*. https://www.dambreach.org/tools/embrea
- Kleinschmidt (2024). *McBreach*. https://www.kleinschmidtgroup.com/mcbreach/
"""

HOW_TO_CITE = """
### How to cite

Please cite the model, the method it implements (Palmen and Kent 2024,
above), and the dashboard where it was used:
"""

CITATIONS_HTML = (
    "<p>Wu, W. (2013). Simplified physically based model of earthen "
    "embankment breaching. <i>Journal of Hydraulic Engineering</i>, 139(8), "
    "837–851.</p>"
    "<p>Wu, W. (2016). Introduction to DLBreach — A Simplified "
    "Physically-Based Dam/Levee Breach Model, version 2016.4. Technical "
    "Report, Clarkson University.</p>"
    "<p>Palmen, L., & Kent, N. (2024). Use of a physically based erosion "
    "breach model for water and tailings dams within a probabilistic "
    "framework. <i>ANCOLD 2024 Conference Proceedings</i>.</p>"
    "<p>Rana, N.M. (2026). DLBreach Dashboard (version 1.0.2) [software]. "
    "Zenodo. https://doi.org/10.5281/zenodo.23307440</p>"
    "<p style='color:#5E6B77'>Related talk (abstract submitted): Rana, N.M. "
    "(2027). DLBreach Dashboard: An Open-Source, Interactive, Monte Carlo Interface to a Physical-Based Dam Breach Algorithm. Lightning talk, International Commission on Large "
    "Dams (ICOLD) Conference, Daejeon, South Korea, 21–27 May 2027.</p>")

GETTING_STARTED = """
### Getting started

Work through the sections in order using the contents panel on the left
(or the buttons at the foot of each page). A tick marks a section that is
done, and the open section lists its headings, which you can click to jump
to. The strip under the header shows what is done and what is still to do.
Every chart has a *Chart options* button for axis limits and for the colour
and line style of each series.
Hover the **?** beside any field for what it means, its unit, and its
source.

1. **Project.** Point to DLBreach.exe. Then either load a worked example,
   start from scratch, open a saved project (.json), or load an existing
   DLBreach input file (.txt). Templates for every input file are on this
   page. Set a site datum if you want elevations in site RL
   or a geodetic datum.
2. **Model setup.** Enter the embankment, breach initiation, fill material
   and impoundment, in practitioner units. The cross-section redraws as you
   type, and the check at the foot of the page flags inputs that would
   release nothing or depart from the DLBreach report's guidance. The
   *Input file* tab shows exactly what DLBreach will read.
3. **Single run.** Run DLBreach once, or load an output file. You get the
   outflow hydrograph, breach widths and levels through time, the breach
   seen from downstream (step through it or play it), and downloads for
   inundation modelling. If you change an input afterwards, the results are
   flagged until you run again.
4. **Sensitivity scenarios.** Choose which inputs change, fill in one
   column per run (or upload a run log), and run them all. Compare the runs'
   outflow, breach widths, depth and pond level, and play any run.
5. **Monte Carlo.** Choose the runs to build ensembles around, the
   uncertain inputs and their distributions, and the number of
   realisations. Results give the minimum, average and maximum, envelopes
   through time for outflow and breach geometry, how each input drives the
   result, and any single realisation to inspect, play and download.
6. **Case histories.** Your result among measured failures of
   water-retaining dams (Froehlich 2016a; Xu and Zhang 2009).
7. **Export.** A report appendix in PDF or Word with the sections you
   choose, including the Monte Carlo envelopes, the input-against-result
   charts and the case-history comparison.
"""

DISCLAIMER = """
### Disclaimer

Provided for technical and research use, without warranty of any kind as
to the accuracy, completeness or fitness for purpose of its results. Dam
breach results are sensitive to uncertain inputs and to the assumptions of
the underlying model, and must be interpreted by a qualified engineer or
geoscientist familiar with the structure assessed and the governing
regulatory framework. Neither the developer, Geosyntec Consultants, the
University of Waterloo nor Clarkson University accepts liability for any
loss or damage arising from its use.
"""


# One line per page: what it is for, and what it needs first. Shown at the
# top of each page.
PAGE_GUIDE = {
    "About": ("What DLBreach is, what this dashboard adds, its limits, and how "
              "to work through it.", ""),
    "Project": ("Name the case, point to DLBreach.exe, and open or load an "
                "existing case if you have one.", ""),
    "Model setup": ("Enter the dam, breach, material and impoundment. The "
                    "cross-section redraws as you type.",
                    "Hover the ? beside a field for its meaning, unit and source."),
    "Single run": ("Run DLBreach once with the Model setup inputs, and look at "
                   "the hydrograph and breach development.",
                   "Needs DLBreach.exe on the Project page, or an existing output "
                   "file to load."),
    "Sensitivity scenarios": ("Run a set of named cases that differ in chosen "
                              "inputs, and compare them.",
                              "Inputs not listed keep their Model setup value."),
    "Monte Carlo": ("Sample uncertain inputs many times and see the spread of "
                    "outflow and breach geometry.",
                    "Each ensemble is built around the base case or a run from "
                    "Sensitivity scenarios."),
    "Case histories": ("Set your result among measured failures of "
                       "water-retaining dams.",
                       "Your result appears once you have a run on Single run."),
    "Export": ("Build a report appendix from the inputs and results.",
               "Sections that need results unlock as you complete the run, "
               "scenarios and Monte Carlo."),
}
