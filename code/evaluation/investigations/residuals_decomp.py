"""Exact-decomposition search (analysis only). Writes code/evaluation/investigations/residuals_decomp_data.md.

For each uncapped sample, find integer-unit estimates and occurrence counts that reproduce the truth deduction exactly:
  D_truth = fixed(+/- pending) - income + sum_i n_i * est_i
est_i from one shared statistic of the series history, rounded to the currency unit (IDR: 100). n_i = our occurrence
count up to the binding day shifted by -1/0/+1 per series.
"""
import itertools
import statistics
import sys
from collections import Counter
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import io, contextlib  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    import residuals as R  # noqa: E402
from fage.forecast import to_home  # noqa: E402
from fage.loader import load_sample_labels  # noqa: E402

labels = load_sample_labels(ROOT / "dataset")
STATS = {
    "mean": lambda a: sum(a) / len(a), "median": lambda a: Decimal(statistics.median(a)), "last": lambda a: a[-1],
    "max": max, "min": min, "mean_last3": lambda a: sum(a[-3:]) / len(a[-3:]), "mean_last4": lambda a: sum(a[-4:]) / len(a[-4:]),
}
ROUNDS = {"round": ROUND_HALF_UP, "ceil": ROUND_CEILING, "floor": ROUND_FLOOR}
L = []
w = L.append
w("# Exact decomposition search\n")
pattern_counter = Counter()
solved = 0
tested = 0
for req in R.ds.sample_requests:
    truth = Decimal(labels[req.request_id]["amount_safe_to_pay"])
    if truth == req.amount:
        continue
    tested += 1
    prof, fc, _ = R.build(req)
    cur = prof.currency
    unit = Decimal(100) if cur == "IDR" else Decimal(1)
    h = R.headroom(fc, prof)
    bind, raw = min(h, key=lambda x: x[1])
    d_truth = prof.balance - prof.minimum - truth
    vary = {}
    for s in fc.series:
        if s.direction == "debit":
            a = [to_home(e.amount, e.currency, cur, e.date, R.ds.fx) for e in s.events if e.amount is not None]
            if len(set(a)) > 1:
                vary["|".join(s.key)] = a
    upto = [f for f in fc.flows if f.date <= bind]
    income = sum((f.amount for f in upto if f.amount > 0), Decimal(0))
    pending = -sum((f.amount for f in upto if f.kind == "pending"), Decimal(0))
    fixed = -sum((f.amount for f in upto if f.amount < 0 and f.source not in vary), Decimal(0))
    counts = {k: sum(1 for f in upto if f.source == k) for k in vary}
    # include varying series that have no occurrence before the binding day (n may shift to +1)
    keys = sorted(vary)
    sols = []
    for pend_mode, fixed_v in (("pending kept", fixed), ("pending dropped", fixed - pending)):
        target = d_truth - fixed_v + income
        for stat, fn in STATS.items():
            for rname, rmode in ROUNDS.items():
                ests = {k: (fn(vary[k]) / unit).quantize(Decimal(1), rmode) * unit for k in keys}
                for shifts in itertools.product((-1, 0, 1), repeat=len(keys)):
                    ns = {k: counts[k] + s for k, s in zip(keys, shifts)}
                    if any(n < 0 for n in ns.values()):
                        continue
                    if sum(ns[k] * ests[k] for k in keys) == target:
                        tag = ",".join(f"{k.split('|')[1]}{'+' if s > 0 else ''}{s if s else ''}" for k, s in zip(keys, shifts) if s)
                        sols.append((sum(abs(s) for s in shifts), pend_mode, stat, rname, tag or "no shift"))
    sols.sort()
    if pending == 0:
        sols = [s for s in sols if s[1] == "pending kept"]
    if sols:
        solved += 1
        best = sols[0][0]
        for s in sols:
            if s[0] == best:
                pattern_counter[(s[1], s[2], s[3])] += 1
    w(f"## {req.request_id} ({cur}) binding {bind}; our counts " + ", ".join(f"{k.split('|')[1]}={counts[k]}" for k in keys))
    w(f"target estimated total (pending kept) = {d_truth - fixed + income:,.2f}; solutions (fewest shifts first): {len(sols)}")
    for s in sols[:6]:
        w(f"- shifts={s[0]} | {s[1]} | stat={s[2]} round={s[3]} | {s[4]}")
    w("")
w(f"\n## Summary\n\nSamples with an exact integer decomposition: {solved}/{tested}.\n")
w("Minimal-shift solutions by (pending mode, stat, rounding) — count of samples where that combo is among the minimal solutions:\n")
for k, v in pattern_counter.most_common(20):
    w(f"- {k}: {v}")
(HERE / "residuals_decomp_data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[-25:]))
