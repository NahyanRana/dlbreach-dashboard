# Contributing

Thank you for helping improve the DLBreach Dashboard. It is maintained by
one person alongside other work, so replies may take a few days.

## Reporting a problem or suggesting a change

Open an [issue](https://github.com/NahyanRana/dlbreach-dashboard/issues)
and pick the form that fits (bug report or feature request). For a bug,
the most useful things are:

- the version shown in the header, and local or browser version;
- what you did, what you expected and what happened;
- the text under **Details** if the page showed *Something went wrong*;
- the project file (`.json`, from **Project → Save project**) or DLBreach
  input file, if you can share it.

**Do not attach confidential project or client data.** Reproduce the
problem with a worked example or made-up inputs where you can.

Questions about DLBreach itself (the physics, the executable, its input
and output formats) belong with Prof. Wu; see his
[DLBreach page](https://webspace.clarkson.edu/~wwu/DLBreach.html).

## Proposing code

1. Fork the repository and create a branch.
2. Keep to the existing layout: `app.py` is the interface; calculations sit
   in the `dlbreach_*.py` modules, which do not import Streamlit, so they
   can be tested on their own.
3. Anything the dashboard computes outside DLBreach must cite its source
   where it is shown, and a check against that source belongs in
   `test_core.py`.
4. Run the tests before opening a pull request:

   ```bash
   python test_core.py
   python test_app_headless.py
   python dev/apptest_smoke.py      # needs streamlit
   python dev/qa_walkthrough.py     # Linux/macOS
   ```

5. Open a pull request describing what changed and why. GitHub Actions
   runs the same tests on Windows and Linux.

Never commit DLBreach.exe, model outputs or project data; `.gitignore`
blocks the common cases.

By contributing, you agree that your contribution is released under the
[MIT licence](LICENSE).
