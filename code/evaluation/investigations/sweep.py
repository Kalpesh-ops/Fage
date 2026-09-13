"""Full-pipeline parameter sweep on the public samples (dev-set calibration, no label leakage into the solver)."""
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code"))

import main as app  # noqa: E402
from fage import forecast  # noqa: E402
from fage.loader import load, load_sample_labels  # noqa: E402
from fage.providers import ModelClient  # noqa: E402

FIELDS = ["affordability_status", "recommended_payment_method", "payment_plan", "earliest_date_for_full_payment",
          "spending_changes_needed", "decision_explanation"]


def score(ds, labels, client):
    decisions, _, _ = app.run(ds, ds.sample_requests, client)
    s = {f: 0 for f in FIELDS}
    s["amt_exact"] = s["amt_5pct"] = 0
    misses = []
    for d in decisions:
        row, t = d.row(), labels[d.request_id]
        ok_all = True
        for f in FIELDS:
            s[f] += row[f] == t[f]
            ok_all &= row[f] == t[f]
        tv, pv = Decimal(t["amount_safe_to_pay"]), Decimal(row["amount_safe_to_pay"])
        s["amt_exact"] += abs(tv - pv) <= Decimal("0.01")
        s["amt_5pct"] += abs(tv - pv) <= Decimal("0.05") * max(tv, Decimal(1))
        if not ok_all:
            misses.append(d.request_id[-2:])
    return s, misses


if __name__ == "__main__":
    ds = load(ROOT / "dataset")
    labels = load_sample_labels(ROOT / "dataset")
    client = ModelClient(ROOT / "code" / "cache", ROOT / "code" / "evaluation" / "sweep_ledger.jsonl", offline=True)
    base = {"skip_request_day_periodic": True, "var_stat": "mean", "same_day_order": "net", "monthly_window_days": 90}
    configs = [("day_window 90 (no cap)", {"monthly_horizon": "day_window", "monthly_window_days": 90})]
    configs += [(f"day_window {d}", {"monthly_horizon": "day_window", "monthly_window_days": d}) for d in (78, 80, 82, 84, 86, 88)]
    for n in (2, 3, 4):
        for inc in (False, True):
            tag = " +income" if inc else ""
            configs.append((f"steps_from_last N={n}{tag}", {"monthly_horizon": "steps_from_last", "monthly_horizon_n": n,
                                                            "horizon_applies_to_income": inc}))
            configs.append((f"calendar_months N={n}{tag}", {"monthly_horizon": "calendar_months", "monthly_horizon_n": n,
                                                            "horizon_applies_to_income": inc}))
    print(f"{'config':34} total | " + " ".join(f[:6] for f in FIELDS) + " amtEx amt5% | misses")
    for name, cfg in configs:
        forecast.PARAMS.update(base)
        forecast.PARAMS.update({"horizon_applies_to_income": False, **cfg})
        s, misses = score(ds, labels, client)
        total = sum(s[f] for f in FIELDS) + s["amt_5pct"]
        print(f"{name:34} {total:5} | " + " ".join(f"{s[f]:6}" for f in FIELDS) + f" {s['amt_exact']:5} {s['amt_5pct']:4} | {','.join(misses)}")
