"""Second-pass residual analysis (analysis only). Writes code/evaluation/investigations/residuals_deep_data.md.

(a) decomposition of deductions up to the binding day into fixed vs estimated terms and the truth-implied estimate
(b) fractional-part test on truth-implied deductions
(c) subset search (<=3 terms) over nearby projected occurrences, skipped request-day occurrences and salary-day debits
(d) exact-match counts per estimator statistic / rounding for varying series
"""
import itertools
import statistics
import sys
from collections import Counter
from datetime import timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from fage import forecast  # noqa: E402
from fage.forecast import to_home  # noqa: E402
from fage.loader import load_sample_labels  # noqa: E402
import residuals as R  # noqa: E402  (reuses its build(); importing runs its report once)

labels = load_sample_labels(ROOT / "dataset")
ONE, CENT = Decimal(1), Decimal("0.01")
L = []
w = L.append


def varying_sources(fc):
    out = {}
    for s in fc.series:
        if s.direction != "debit":
            continue
        amts = [to_home(e.amount, e.currency, fc_cur, e.date, R.ds.fx) for e in s.events if e.amount is not None]
        if len(set(amts)) > 1:
            out["|".join(s.key)] = amts
    return out


w("# Deep residual analysis\n")
w("## (a) Decomposition up to our binding day\n")
w("D = total net deduction from balance to binding day. `fixed` = pending, scheduled, image-filled, constant-amount "
  "series; `estimated` = series whose history amounts vary (our mean). `truth est` = truth D − fixed − income "
  "(what the truth must have used for the estimated terms if everything else matches).\n")
w("| request | cur | D ours | D truth | fixed | income | est ours | truth est | ratio | D truth frac | fixed frac |")
w("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
stat_hits = Counter()
stat_near = Counter()
subset_rows = []
ratios = []
for req in R.ds.sample_requests:
    prof, fc, _ = R.build(req)
    fc_cur = prof.currency
    truth = Decimal(labels[req.request_id]["amount_safe_to_pay"])
    h = R.headroom(fc, prof)
    bind, raw = min(h, key=lambda x: x[1])
    vary = varying_sources(fc)
    upto = [f for f in fc.flows if f.date <= bind]
    income = sum((f.amount for f in upto if f.amount > 0), Decimal(0))
    est = -sum((f.amount for f in upto if f.amount < 0 and f.source in vary), Decimal(0))
    fixed = -sum((f.amount for f in upto if f.amount < 0 and f.source not in vary), Decimal(0))
    d_ours = prof.balance - prof.minimum - raw
    capped = truth == req.amount
    if not capped:
        d_truth = prof.balance - prof.minimum - truth
        truth_est = d_truth - fixed + income
        ratio = (truth_est / est) if est else None
        if ratio is not None:
            ratios.append((req.request_id, ratio))
        w(f"| {req.request_id} | {fc_cur} | {d_ours:,.2f} | {d_truth:,.2f} | {fixed:,.2f} | {income:,.2f} | {est:,.2f} | "
          f"{truth_est:,.2f} | {ratio:.3f} | {d_truth % 1:.2f} | {fixed % 1:.2f} |" if ratio is not None else
          f"| {req.request_id} | {fc_cur} | {d_ours:,.2f} | {d_truth:,.2f} | {fixed:,.2f} | {income:,.2f} | {est:,.2f} | {truth_est:,.2f} | n/a | {d_truth % 1:.2f} | {fixed % 1:.2f} |")

        # (c) subset search
        resid = truth - raw  # >0: remove deductions; <0: add deductions
        pool = []
        for f in fc.flows:
            if f.amount < 0 and bind - timedelta(days=10) <= f.date <= bind + timedelta(days=10):
                tag = "in" if f.date <= bind else "after"
                pool.append((abs(f.amount), f"{f.source}@{f.date}({tag})"))
        # periodic occurrences we skip on request_date
        for s in fc.series:
            if s.direction == "debit" and s.cadence != "monthly":
                gap = max(1, round(s.gap))
                nd = s.last.date + timedelta(days=gap)
                while nd < req.date:
                    nd += timedelta(days=gap)
                if nd == req.date:
                    amt = abs(next((f.amount for f in fc.flows if f.source == "|".join(s.key)), Decimal(0)))
                    if amt:
                        pool.append((amt, f"{'|'.join(s.key)}@{nd}(skipped request day)"))
        found = []
        for k in (1, 2, 3):
            for combo in itertools.combinations(pool, k):
                tot = sum(c[0] for c in combo)
                if abs(tot - abs(resid)) <= max(ONE, abs(resid) * Decimal("0.003")):
                    found.append(" + ".join(c[1] for c in combo) + f" = {tot:,.2f}")
            if found:
                break
        subset_rows.append((req.request_id, resid, found[:3]))

    # (d) estimator statistics
    for stat in ("mean", "median", "max", "min", "last", "mean_last3", "mean_last4", "mean_last8"):
        for rnd in ("none", "round", "ceil", "floor"):
            ov = {}
            for f in fc.flows:
                if f.source in vary and f.source not in ov:
                    a = vary[f.source]
                    v = {"mean": lambda: sum(a) / len(a), "median": lambda: Decimal(statistics.median(a)),
                         "max": lambda: max(a), "min": lambda: min(a), "last": lambda: a[-1],
                         "mean_last3": lambda: sum(a[-3:]) / len(a[-3:]), "mean_last4": lambda: sum(a[-4:]) / len(a[-4:]),
                         "mean_last8": lambda: sum(a[-8:]) / len(a[-8:])}[stat]()
                    v = {"none": v.quantize(CENT, ROUND_HALF_UP), "round": v.quantize(ONE, ROUND_HALF_UP),
                         "ceil": v.quantize(ONE, ROUND_CEILING), "floor": v.quantize(ONE, ROUND_FLOOR)}[rnd]
                    ov[f.source] = -v
            hh = R.headroom(fc, prof, ov)
            val = max(Decimal(0), min(req.amount, min(b for _, b in hh))).quantize(CENT)
            stat_hits[(stat, rnd)] += val == truth
            stat_near[(stat, rnd)] += abs(val - truth) <= max(ONE, truth * Decimal("0.01"))

w("\nRatio summary (truth est / our est): " + ", ".join(f"{r[-2:]}:{x:.2f}" for r, x in ratios))
w("\n## (c) Subset search (≤3 terms within ±10 days of binding day, plus request-day occurrences we skip)\n")
for rid, resid, found in subset_rows:
    w(f"- **{rid}** residual {resid:,.2f}: " + ("; ".join(found) if found else "no combination"))
w("\n## (d) Estimator statistic × rounding for varying series\n")
w("| stat | rounding | exact (25) | within max(1 unit, 1%) |")
w("|---|---|---:|---:|")
for (stat, rnd), v in sorted(stat_hits.items(), key=lambda kv: (-kv[1], -stat_near[kv[0]])):
    w(f"| {stat} | {rnd} | {v} | {stat_near[(stat, rnd)]} |")
(HERE / "residuals_deep_data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
