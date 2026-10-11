# Publishing: from this folder to a public release

The repository is **NahyanRana/dlbreach-dashboard**. These steps take it
from private to a public v1.0.0 release with a DOI. About two hours in
all, spread over a few sessions.

| Step | Where | Time |
|---|---|---|
| 1. Create the private repository and push | GitHub Desktop | 20 min |
| 2. Check the tests pass on GitHub | Actions tab | 15 min |
| 3. Clean install on a second machine | Another Windows PC | 20 min |
| 4. Test the browser version | `docs/BROWSER_CHECKLIST.md` | 15 min |
| 5. Make it public, publish the browser version | Settings | 10 min |
| 6. Connect Zenodo, tag v1.0.0, add the DOI | zenodo.org, Releases | 20 min |

**Never commit** DLBreach.exe, `Run4_v3.*`, any `.out` file or any client
data. `.gitignore` blocks these, but check the list of changed files in
GitHub Desktop before every commit.

---

## 1. Create the private repository and push

1. Install **GitHub Desktop** from <https://desktop.github.com> and sign in
   as **NahyanRana**.
2. Make sure this folder is named exactly `dlbreach-dashboard`, and does
   not contain a `.venv` you want to keep elsewhere (it is ignored, so it
   can stay). **File → Add local repository**, choose this folder. When it says the
   folder is not a repository, click **create a repository** here.
   - Name: `dlbreach-dashboard`
   - Leave *Initialize with README*, *Git ignore* and *License* as **None**
     (the folder already has them).
   - **Create repository**.
3. **Private files first.** Copy into this folder the private files you
   keep separately (from `DLBreach_private_files.zip`):
   `test_private_benchmarks.py` to the folder itself, `private_terms.txt`
   to `dev\`. Add any other confidential names to `private_terms.txt`.
   Then run the name scan: click the folder's address bar in File
   Explorer, type `cmd`, press Enter, and run

   ```
   python dev\scan_confidential_names.py
   ```

   It must end with **OK**. Do this before every commit.
4. In the left panel, check the changed files. There must be **no**
   `.exe`, `.out` (except `dev/fixtures/standin_T1.out`), `Run4_v3`,
   `private`, `.venv`, `.xlsx`, `.csv`, `.zip`, `.pdf` or `.docx` files, and
   no `.json` or `.txt` outside `test_cases`. GitHub Desktop should list
   82 files (15 of them Prof. Wu's, in `test_cases/wu_2016`).
5. Summary: `v0.16: repository release preparation`. **Commit to main**.
6. **Publish repository**. Keep **Keep this code private** ticked.
   **Publish**.

## 2. Check the tests pass on GitHub

1. Open the repository on github.com → **Actions** tab. The *Tests*
   workflow starts by itself: 8 jobs (Windows and Linux, Python 3.11 to 3.14).
2. Wait for green ticks (about 10 minutes).
3. If a job is red, open it, copy the red text of the failing step, and
   send it to me. The likeliest first failure is a package version in
   `requirements.txt` that has no installer for one Python version.

## 3. Clean install on a second machine

On a Windows computer that has never run the dashboard:

1. Install Python 3.13 (tick **Add python.exe to PATH**).
2. On github.com, **Code → Download ZIP**. Extract it to
   `C:\Users\<you>\dlbreach-dashboard`.
3. Double-click **Launch DLBreach Dashboard.bat**. Note how long the first
   setup takes.
4. Point to DLBreach.exe, load T1, run it, run 20 Monte Carlo
   realisations, export a PDF.

This checks the README instructions as a new user meets them.

## 4. Test the browser version

Follow `docs/BROWSER_CHECKLIST.md`. Its result decides whether step 5
includes the browser version.

## 5. Make it public, publish the browser version

1. **Settings → General →** scroll to *Danger Zone* → **Change visibility →
   Make public**.
2. If the browser checklist passed:
   - **Settings → Pages →** *Build and deployment*, Source: **GitHub Actions**.
   - **Actions → Publish browser version → Run workflow**.
   - After about three minutes it is live at
     <https://nahyanrana.github.io/dlbreach-dashboard/>.
   - Run the workflow again whenever you want the site to pick up changes.
3. **About** panel on the repository home page (gear icon): add the
   description *An interactive Monte Carlo companion to a physically based
   dam breach algorithm*, the Pages link, and topics `dam-breach`,
   `dlbreach`, `dam-safety`, `monte-carlo`, `streamlit`.

## 6. Connect Zenodo, tag v1.0.0, add the DOI

Zenodo archives each GitHub release and gives it a DOI. Connect it
**before** creating the release.

1. Sign in at <https://zenodo.org> with **Log in with GitHub**.
2. Your name (top right) → **GitHub** → find `dlbreach-dashboard` → switch
   it **On**.
3. Before tagging, update the version to 1.0 in `dlbreach_about.py`,
   `CITATION.cff` (change `version`, and add a line
   `date-released: "YYYY-MM-DD"` with the release date) and `CHANGELOG.md`.
   Commit and push.
4. On GitHub: **Releases → Draft a new release** → tag `v1.0.0` (create
   new tag) → title `v1.0.0` → notes from `CHANGELOG.md` → **Publish
   release**.
5. Within minutes Zenodo shows the release with a DOI. Add it to
   `CITATION.cff` (`doi:`), the README citation and badge, and the
   *How to cite* text in `dlbreach_about.py`. Commit and push.

Zenodo gives two DOIs: one for this version, and a *concept* DOI that
always resolves to the latest version. Cite the concept DOI in the README
and talks.

---

## Updating later

Change the files, commit and push in GitHub Desktop. The tests run on
every push. To update the browser version, run **Publish browser version**
again. For a new release, repeat step 6 from point 3 with the next version
number; Zenodo mints a new version DOI.
