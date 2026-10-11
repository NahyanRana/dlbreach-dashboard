"""
dev/scan_confidential_names.py — make sure no confidential name is in the files
that would be published.

The names are confidential themselves, so they are kept in
dev/private_terms.txt (one per line, # for comments), which .gitignore keeps
out of the repository. Run this before every commit; test_core.py also runs
it when the terms file is present. Works on Windows, macOS and Linux.

    python dev/scan_confidential_names.py

Exit code 0: nothing found (or no terms file). 1: names found, listed.
"""

from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS = ROOT / "dev" / "private_terms.txt"
TEXT = {".py", ".md", ".json", ".txt", ".html", ".yml", ".yaml", ".cff",
        ".toml", ".bat", ".csv", ".out", ".gitignore", ".gitattributes", ""}

# The publish allowlist in .gitignore, mirrored for computers without git.
_TOP = [".gitignore", ".gitattributes", "app.py", "dlbreach_*.py", "test_core.py",
        "test_app_headless.py", "index.html", "requirements.txt", "*.md", "LICENSE",
        "CITATION.cff", "Launch DLBreach Dashboard.bat", "Preview browser version.bat"]
_SUB = ["test_cases/README.md", "test_cases/T[0-9]_water_*.json",
        "test_cases/T[0-9]_water_*.txt",
        "test_cases/solid_waste_paused/S[0-9]_solid_*.json",
        "test_cases/solid_waste_paused/S[0-9]_solid_*.txt",
        "test_cases/wu_2016/*_cards*.txt", "test_cases/wu_2016/Mecox_*.txt",
        "dev/README.md", "dev/*.py", "dev/fixtures/standin_T1.out",
        "docs/*.md", "docs/images/*.png", ".streamlit/config.toml", ".github/*"]
_NEVER = ["*private*", "Run4*", "*.exe"]


def published_files() -> list[Path]:
    """Files git would publish: from git when available, else the mirror."""
    git = shutil.which("git")
    if git and (ROOT / ".git").exists():
        r = subprocess.run([git, "-C", str(ROOT), "ls-files", "--cached", "--others",
                            "--exclude-standard"], capture_output=True, text=True)
        if r.returncode == 0:
            return [ROOT / x for x in r.stdout.splitlines() if (ROOT / x).is_file()]
    out = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or ".git" in f.parts or ".venv" in f.parts:
            continue
        rel = f.relative_to(ROOT).as_posix()
        if any(fnmatch.fnmatch(f.name, n) for n in _NEVER):
            continue
        top = "/" not in rel and any(fnmatch.fnmatch(rel, p) for p in _TOP)
        sub = any(fnmatch.fnmatch(rel, p) or (p.endswith("/*") and rel.startswith(p[:-1]))
                  for p in _SUB)
        if top or sub:
            out.append(f)
    return out


def scan() -> tuple[int, list[str]] | None:
    """(number of terms, hits as 'file:line: term'), or None without a terms file."""
    if not TERMS.is_file():
        return None
    terms = [t.strip() for t in TERMS.read_text(encoding="utf-8").splitlines()
             if t.strip() and not t.lstrip().startswith("#")]
    if not terms:
        return 0, []
    pat = re.compile("|".join(re.escape(t) for t in terms), re.I)
    hits = []
    for f in published_files():
        if f.resolve() == TERMS.resolve() or (f.suffix.lower() not in TEXT):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore")
                                 .splitlines(), 1):
            m = pat.search(line)
            if m:
                hits.append(f"{f.relative_to(ROOT).as_posix()}:{i}: {m.group(0)}")
    return len(terms), hits


def main() -> int:
    res = scan()
    if res is None:
        print("No dev/private_terms.txt: nothing to check against. "
              "Put your list of confidential names there (it is never published).")
        return 0
    n, hits = res
    if hits:
        print(f"CONFIDENTIAL NAMES FOUND in files that would be published ({len(hits)}):")
        for h in hits:
            print("  " + h)
        print("Remove them before committing.")
        return 1
    print(f"OK: none of the {n} confidential names is in the "
          f"{len(published_files())} files that would be published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
