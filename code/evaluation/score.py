"""Scorecard: compare code/evaluation/sample_output.csv with the public sample labels."""
import collections
import csv
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from fage.loader import load_sample_labels  # noqa: E402

pred_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "code" / "evaluation" / "sample_output.csv"
truth = load_sample_labels(ROOT / "dataset")
pred = {r["request_id"]: r for r in csv.DictReader(open(pred_path, encoding="utf-8"))}
fields = ["amount_safe_to_pay", "affordability_status", "recommended_payment_method", "payment_plan",
          "earliest_date_for_full_payment", "spending_changes_needed", "decision_explanation"]
exact = collections.Counter()
band = collections.Counter()
conf = {"affordability_status": collections.Counter(), "recommended_payment_method": collections.Counter()}
rows = []
for rid, t in truth.items():
    p = pred.get(rid, {})
    diffs = []
    for f in fields:
        ok = p.get(f, "") == t[f]
        if f == "amount_safe_to_pay" and not ok and p.get(f):
            ok = Decimal(p[f]) == Decimal(t[f])
        exact[f] += ok
        if not ok:
            diffs.append(f)
    if p.get("amount_safe_to_pay"):
        tv, pv = Decimal(t["amount_safe_to_pay"]), Decimal(p["amount_safe_to_pay"])
        rel = abs(pv - tv) / max(tv, Decimal(1))
        band["<=1%"] += rel <= Decimal("0.01")
        band["<=5%"] += rel <= Decimal("0.05")
        band["<=10%"] += rel <= Decimal("0.10")
    for f in conf:
        conf[f][(t[f], p.get(f))] += 1
    rows.append((rid, diffs, p, t))

n = len(truth)
print(f"Scorecard ({n} samples)")
for f in fields:
    print(f"  {f:32} exact {exact[f]:2}/{n}")
print("  amount_safe_to_pay banded:", {k: f"{v}/{n}" for k, v in band.items()})
for f, c in conf.items():
    print(f"\nConfusion {f} (truth -> pred):")
    for (tv, pv), k in sorted(c.items()):
        print(f"  {tv:22} -> {pv or '-':22} {k}")
print("\nPer-request diffs:")
for rid, diffs, p, t in rows:
    if not diffs:
        print(f"  {rid}: all match")
        continue
    print(f"  {rid}: {', '.join(diffs)}")
    for f in diffs:
        print(f"      {f}: pred={p.get(f)!r}\n      {' ' * len(f)}  true={t[f]!r}")
