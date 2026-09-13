"""Dev-set calibration: sweep ambiguous forecast parameters against the 25 public samples.

Only amount_safe_to_pay / earliest_date_for_full_payment are compared here. Output feeds calibration.md.
"""
import itertools
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))

from fage import forecast  # noqa: E402
from fage.loader import load, load_sample_labels  # noqa: E402


def safe_amount(ds, req):
    prof = ds.profiles[req.user_id]
    fc = forecast.build(prof, ds.events_by_user.get(req.user_id, []), req.date, ds.fx)
    series = fc.daily()
    low = min(b for _, b in series)
    return max(Decimal(0), min(req.amount, low - prof.minimum)), fc


def run(ds, labels, verbose=False):
    hits = 0
    rows = []
    for req in ds.sample_requests:
        s, fc = safe_amount(ds, req)
        truth = Decimal(labels[req.request_id]["amount_safe_to_pay"])
        ok = abs(s - truth) <= Decimal("0.01")
        hits += ok
        rows.append((req.request_id, s, truth, s - truth, ok))
    if verbose:
        for r in rows:
            print(*r)
    return hits, rows


if __name__ == "__main__":
    ds = load(ROOT / "dataset")
    labels = load_sample_labels(ROOT / "dataset")
    if "--sweep" in sys.argv:
        grid = {
            "var_stat": ["mean", "median", "max", "last"],
            "var_last_n": [0, 3, 4, 6, 8],
            "var_round": ["none", "ceil", "round"],
            "monthly_var_stat": ["mean", "max", "last", "median"],
            "same_day_order": ["net", "debits_first"],
            "window_days": [89, 90],
        }
        best = []
        for combo in itertools.product(*grid.values()):
            forecast.PARAMS.update(dict(zip(grid.keys(), combo)))
            h, _ = run(ds, labels)
            best.append((h, combo))
        best.sort(reverse=True)
        for b in best[:15]:
            print(b)
    else:
        run(ds, labels, verbose=True)
