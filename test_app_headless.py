"""
test_app_headless.py
--------------------
Executes every page of the dashboard without a browser, by substituting a
minimal stand-in for Streamlit. It catches the errors a user would meet at
run time — misnamed variables, wrong arguments, missing keys — which a
syntax check cannot.

It does not test appearance. That still needs a person looking at it.

Usage:  python test_app_headless.py

Uses Run4_v3.out from this folder when present (project data, not in the
repository); otherwise dev/fixtures/standin_T1.out, which is stand-in
output for testing only and NOT DLBreach output.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd


class _State(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as exc:
            raise AttributeError(k) from exc

    def __setattr__(self, k, v):
        self[k] = v


class _Ctx:
    """Anything that can be used as a context manager or a column."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, name):
        return getattr(ST, name)


class _Stub(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.__version__ = "stand-in"
        self.session_state = _State()
        self.calls = []
        self.html_out = []          # drawings passed to components.html
        self.md_out = []            # markdown text (callouts, tiles)
        self.contained = []
        self.keys_seen = set()
        self.sidebar = self

    def _claim(self, key):
        """Streamlit refuses two widgets with one key; so does this."""
        if key is None:
            return
        if key in self.keys_seen:
            raise AssertionError(f"duplicate widget key: {key!r}")
        self.keys_seen.add(key)

    def data_editor(self, data, key=None, **k):
        self._claim(key)
        return data

    def popover(self, *a, **k):
        return _Ctx()

    # ---- layout ----
    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Ctx() for _ in range(n)]

    def tabs(self, labels):
        return [_Ctx() for _ in labels]

    def container(self, **k):
        return _Ctx()

    def expander(self, *a, **k):
        return _Ctx()

    def empty(self, *a, **k):
        return _Ctx()

    def exception(self, exc, *a, **k):
        self.contained.append(exc)

    def popover(self, *a, **k):
        return _Ctx()

    # ---- widgets ----
    def _keyed(self, key, fallback):
        self._claim(key)
        if key is not None:
            if key not in self.session_state:
                self.session_state[key] = fallback
            return self.session_state[key]
        return fallback

    def number_input(self, label, min_value=None, max_value=None, value=None,
                     step=None, key=None, **k):
        v = value if value is not None else (min_value or 0.0)
        return self._keyed(key, v)

    def text_input(self, label, value="", key=None, **k):
        return self._keyed(key, value)

    def text_area(self, label, value="", key=None, **k):
        return self._keyed(key, value)

    def radio(self, label, options, index=0, key=None, **k):
        return self._keyed(key, list(options)[index])

    def selectbox(self, label, options, index=0, key=None, **k):
        opts = list(options)
        return self._keyed(key, opts[index] if opts else None)

    def multiselect(self, label, options, default=None, key=None, **k):
        return self._keyed(key, default or [])

    def select_slider(self, label, options, value=None, key=None, **k):
        opts = list(options)
        return self._keyed(key, value if value is not None else opts[-1])

    def toggle(self, label, value=False, key=None, **k):
        return self._keyed(key, value)

    def checkbox(self, label, value=False, key=None, **k):
        return self._keyed(key, value)

    def button(self, *a, key=None, **k):
        self._claim(key)
        return False

    def download_button(self, *a, **k):
        return False

    def file_uploader(self, *a, key=None, **k):
        self._claim(key)
        return None

    def progress(self, *a, **k):
        return types.SimpleNamespace(progress=lambda *a, **k: None,
                                     empty=lambda: None)

    def spinner(self, *a, **k):
        return _Ctx()

    def cache_data(self, fn=None, **k):
        return fn if fn else (lambda f: f)

    def rerun(self):
        pass

    def set_page_config(self, **k):
        pass

    # ---- output: record the call, validate the obvious things ----
    def __getattr__(self, name):
        def _record(*a, **k):
            self.calls.append(name)
            if name in ("markdown", "caption"):
                self.md_out.append(str(a[0]) if a else str(k.get("body", "")))
            if name in ("line_chart", "dataframe", "vega_lite_chart",
                        "scatter_chart", "bar_chart"):
                data = a[0] if a else k.get("data")
                if isinstance(data, pd.DataFrame) and name != "dataframe":
                    assert len(data) > 0, f"{name} received an empty frame"
            if name == "vega_lite_chart" and len(a) > 1:
                spec = a[1]
                assert "layer" in spec or "mark" in spec, "bad vega spec"
            return None
        return _record


ST = _Stub()
_components = types.ModuleType("streamlit.components")
_v1 = types.ModuleType("streamlit.components.v1")
def _html(*a, **k):
    ST.calls.append("html")
    ST.html_out.append(str(a[0]) if a else str(k.get("html", "")))


_v1.html = _html
_components.v1 = _v1
ST.components = _components
sys.modules["streamlit"] = ST
sys.modules["streamlit.components"] = _components
sys.modules["streamlit.components.v1"] = _v1


def _run_app():
    ST.calls.clear()
    ST.html_out.clear()
    ST.md_out.clear()
    ST.keys_seen.clear()
    src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    exec(compile(src, "app.py", "exec"), {"__name__": "__main__"})
    _raise_contained()
    return list(ST.calls)


def _raise_contained():
    """The app shows errors on screen instead of stopping; a test must
    still fail on them."""
    if ST.contained:
        exc = ST.contained[0]
        ST.contained.clear()
        raise exc


def main():
    import json
    here = Path(__file__).parent
    from dlbreach_io import DEFAULT_PARAMS, parse_out, read_input_file
    import dlbreach_mc as MC
    import dlbreach_batch as B

    # Solid waste is paused (SOLID_WASTE_ENABLED = False): every dam type
    # gets the water pages, and a solid waste project opens as water.
    names = ["About", "Project", "Model setup", "Single run",
             "Sensitivity scenarios", "Monte Carlo", "Case histories", "Export"]

    def pages_for(dam):
        return [f"{i + 1}. {x}" for i, x in enumerate(names)]

    for dam in ("water", "solid"):
        for pg in pages_for(dam):
            ST.session_state.clear()
            ST.session_state.update(params=dict(DEFAULT_PARAMS, dam_type=dam), page=pg)
            _run_app()
            assert ST.session_state["params"]["dam_type"] == "water"
        print(f"  ok  empty state, {dam} requested: {len(pages_for(dam))} water pages")

    # The Run4 benchmark output is used when it is present (it is project
    # data and is not in the repository). Otherwise a public fixture written
    # by the developer stand-in is used; it is NOT DLBreach output and only
    # gives the pages something with the right shape to draw.
    run4 = here / "Run4_v3.out"
    out_file = run4 if run4.is_file() else here / "dev" / "fixtures" / "standin_T1.out"
    print(f"  using output file: {out_file.relative_to(here)}")
    df = parse_out(out_file)
    rng = np.random.default_rng(3)
    n = 25

    def stores(params):
        res = pd.DataFrame({
            "realisation": np.arange(1, n + 1), "sed_d50": rng.uniform(.002, .012, n),
            # invented values with the right shape, for drawing only
            "ok": True, "error": "", "peak_outflow_m3s": rng.uniform(1e3, 2e3, n),
            "time_to_peak_hr": rng.uniform(1.0, 2.5, n), "max_breach_depth_m": 12.0,
            "final_top_width_m": rng.uniform(50, 80, n),
            "final_bottom_width_m": rng.uniform(30, 55, n),
            "final_bottom_elev_m": 0.0, "final_side_slope": 1.0,
            "total_outflow_volume_m3": 4.0e6, "simulated_duration_hr": 12.0})
        hyd = {i: MC._thin_hydrograph(df) for i in range(1, n + 1)}
        geo = {i: MC._thin_geometry(df) for i in range(1, n + 1)}
        return res, hyd, geo

    cases = sorted((here / "test_cases").glob("T*.json"))
    assert cases, "no test cases found"
    count = 0
    for browser in (False, True):
        sys.platform = "emscripten" if browser else "linux"
        for case in cases:
            params = dict(DEFAULT_PARAMS); params.update(json.loads(case.read_text()))
            params["res_curve"] = [tuple(x) for x in params["res_curve"]]
            dam = params["dam_type"]
            res, hyd, geo = stores(params)
            grid = B.grid_template(params, ["sed_d50", "sed_friction"],
                                   ["Sensitivity 1", "Sensitivity 2"])
            for pg in pages_for(dam):
                ST.session_state.clear()
                p = dict(params)
                ST.session_state.update(page=pg, params=p, result_df=df, scen_grid=grid)
                # results stores are built through the app's own functions
                calls = _run_app()
                count += 1
        print(f"  ok  {'browser' if browser else 'local  '}: {len(cases)} test cases x all pages")
    sys.platform = "linux"

    # scenario and Monte Carlo results through the app's own post-processing,
    # then press Build for PDF and Word
    for case in cases:
        params = dict(DEFAULT_PARAMS); params.update(json.loads(case.read_text()))
        params["res_curve"] = [tuple(x) for x in params["res_curve"]]
        res, hyd, geo = stores(params)
        ns = {}
        for fmt in ("PDF", "Word"):
            ST.session_state.clear()
            ST.session_state.update(page=pages_for(params["dam_type"])[-1],
                                    params=dict(params), result_df=df,
                                    keep_rep_fmt=fmt)
            press = {f"Build {fmt}"}
            orig = _Stub.button
            _Stub.button = lambda self, label, *a, key=None, **k: label in press
            # build the stores the way the pages do
            app_src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
            g = {"__name__": "__main__"}
            ST.calls.clear(); ST.keys_seen.clear()
            exec(compile(app_src, "app.py", "exec"), g)
            _raise_contained()
            ST.session_state["mc_store"] = {"Base case": g["_mc_post"](
                "Base case", res, ["sed_d50"], hyd, params, geo)}
            ST.session_state["scen_store"] = g["_scenario_results"](
                ["Sensitivity 1"], {"Sensitivity 1": params}, {}, {"Sensitivity 1": df})
            for k in ("mc", "mc_env", "mc_drivers", "cases", "scenarios"):
                ST.session_state[f"keep_rsec_{k}"] = True
            ST.calls.clear(); ST.keys_seen.clear()
            exec(compile(app_src, "app.py", "exec"), {"__name__": "__main__"})
            _raise_contained()
            _Stub.button = orig
            data, ext, _ = ST.session_state["report_file"]
            assert (data[:5] == b"%PDF-") if ext == "pdf" else (data[:2] == b"PK")
        tl_rows = "tailings_m3" in ST.session_state["mc_store"]["Base case"]["results"]
        print(f"  ok  {case.stem:22} PDF and Word built; solid waste rows: {tl_rows}")
    # Monte Carlo and Scenarios pages with results present, for every way of
    # picking a realisation
    params = dict(DEFAULT_PARAMS); params.update(json.loads(cases[0].read_text()))
    params["res_curve"] = [tuple(x) for x in params["res_curve"]]
    res, hyd, geo = stores(params)
    app_src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    g = {"__name__": "__main__"}
    ST.session_state.clear()
    ST.session_state.update(page="1. About", params=dict(params), result_df=df)
    ST.calls.clear(); ST.keys_seen.clear()
    exec(compile(app_src, "app.py", "exec"), g)
    _raise_contained()
    mc_store = {"Base case": g["_mc_post"]("Base case", res, ["sed_d50"], hyd,
                                           params, geo)}
    scen_store = g["_scenario_results"](
        ["Sensitivity 1", "Sensitivity 2"],
        {"Sensitivity 1": params, "Sensitivity 2": dict(params, sed_d50=0.004)},
        {}, {"Sensitivity 1": df, "Sensitivity 2": df})
    for pick in g["MC_PICKS"]:
        for xk in ("sed_d50",):
            ST.session_state.clear()
            ST.session_state.update(page="6. Monte Carlo", params=dict(params),
                                    result_df=df, mc_store=mc_store,
                                    keep_mc_pick=pick, keep_mc_num=7,
                                    keep_mc_y="max_breach_depth_m")
            calls = _run_app()
            assert calls.count("vega_lite_chart") >= 6, calls.count("vega_lite_chart")
            assert "html" in calls          # animation of the chosen realisation
    print(f"  ok  Monte Carlo results: {len(g['MC_PICKS'])} ways of picking a "
          f"realisation, envelopes, scatter, animation")
    ST.session_state.clear()
    ST.session_state.update(page="5. Sensitivity scenarios", params=dict(params),
                            result_df=df, scen_store=scen_store)
    calls = _run_app()
    assert calls.count("vega_lite_chart") >= 5
    print("  ok  Scenarios results: comparison tabs and animation")
    print(f"\n{count} page renders.\nALL PAGES EXECUTED WITHOUT ERROR")


if __name__ == "__main__":
    main()
