"""Create code.zip at the repository root from code/ (plus .env.example).

Ships the response cache so `python code/main.py --offline` reproduces output.csv without any API key.
Excludes __pycache__, .env and sweep scratch ledgers.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", ".venv"}
SKIP_FILES = {"sweep_ledger.jsonl", "residuals_ledger.jsonl", ".env"}

with zipfile.ZipFile(ROOT / "code.zip", "w", zipfile.ZIP_DEFLATED) as z:
    n = 0
    for p in sorted((ROOT / "code").rglob("*")):
        if p.is_dir() or SKIP_DIRS & set(p.parts) or p.name in SKIP_FILES:
            continue
        z.write(p, p.relative_to(ROOT).as_posix())
        n += 1
    z.write(ROOT / ".env.example", ".env.example")
print(f"code.zip: {n + 1} files")
