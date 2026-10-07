r"""labs/w6d4_quote_check.py -- Week 6 Din 4, Step 0c: does every quote in the frozen file appear on the line it cites?
Finds every  path:LINE 'quoted text'  in the file and compares the quote with that line of the file AT A GIVEN COMMIT
(default HEAD), whitespace-collapsed. It checks that the line was copied, not that the answer is right -- it never reads
the KEY. Run it BEFORE the seal commit, fix what it flags, run it again. Values and labels only (P-52).
Usage: .\.venv\Scripts\python.exe -u labs\w6d4_quote_check.py docs\daily\week_06\DIN_04_PREDICTIONS_FROZEN.md [--rev HEAD]"""
import argparse
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CITE = re.compile(r"([\w./\\-]+\.(?:py|ini|md|ps1|toml|txt)):(\d+)\s*'([^']+)'")


def norm(s: str) -> str:
    return " ".join(s.split())


ap = argparse.ArgumentParser()
ap.add_argument("frozen")
ap.add_argument("--rev", default="HEAD")
a = ap.parse_args()
text = Path(a.frozen).read_text(encoding="utf-8")
cache: dict = {}
counts = {"exact": 0, "other_line": 0, "not_in_file": 0, "no_file": 0}
for m in CITE.finditer(text):
    path, n, quote = m.group(1).replace("\\", "/"), int(m.group(2)), norm(m.group(3))
    if path not in cache:
        r = subprocess.run(["git", "show", f"{a.rev}:{path}"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
        cache[path] = r.stdout.splitlines() if r.returncode == 0 else None
    lines = cache[path]
    if lines is None:
        verdict = "no_file"
    elif 1 <= n <= len(lines) and quote in norm(lines[n - 1]):
        verdict = "exact"
    else:
        hits = [i + 1 for i, ln in enumerate(lines) if quote in norm(ln)]
        verdict = "other_line" if hits else "not_in_file"
        if hits:
            verdict += "(found_at=" + ",".join(f":{h}" for h in hits[:5]) + ")"
    counts[verdict.split("(")[0]] += 1
    print(f"{path}:{n} {verdict} quote={quote[:60]!r}")
print("quotes=" + str(sum(counts.values())) + " " + " ".join(f"{k}={v}" for k, v in counts.items()) + f" rev={a.rev}")
