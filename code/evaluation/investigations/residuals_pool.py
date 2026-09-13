"""Diagnostic for the series-vs-pool hypothesis (analysis only; the forecaster is not changed).

Re-estimates the variable component of each uncapped sample's deduction up to our binding day, with pool categories
modelled as a per-day spend rate instead of projected occurrences, and reports how the truth/ours ratio spread
changes. Writes code/evaluation/investigations/residuals_pool_data.md.
"""
import collections
import io
import contextlib
import statistics
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
with contextlib.redirect_stdout(io.StringIO()):
    import residuals as R  # noqa: E402
from fage.forecast import OUTFLOW_TYPES, to_home  # noqa: E402
from fage.loader import load_sample_labels  # noqa: E402

labels = load_sample_labels(ROOT / "dataset")
ONE = Decimal(1)


def classify(history, thr):
    """category -> ('series'|'pool', stats). Pool when no single description dominates the category's occurrences."""
    by = collections.defaultdict(list)
    for e in history:
        by[e.category].append(e)
    out = {}
    for cat, es in by.items():
        descs = collections.Counter(e.description for e in es)
        share = descs.most_common(1)[0][1] / len(es)
        out[cat] = ("series" if share >= thr else "pool", {"n": len(es), "distinct": len(descs), "top_share": share})
    return out


def pool_rate(es, cur, start, basis):
    pts = sorted((e.date, to_home(e.amount, e.currency, cur, e.date, R.ds.fx)) for e in es)
    first, last = pts[0][0], pts[-1][0]
    total = sum(a for _, a in pts)
    if basis == "span":
        return total / max(1, (last - first).days)
    if basis == "span_plus_gap":
        gaps = [(b[0] - a[0]).days for a, b in zip(pts, pts[1:])]
        return total / max(ONE, Decimal((last - first).days) + (Decimal(str(statistics.median(gaps))) if gaps else 0))
    if basis == "trailing90":
        lo = start - timedelta(days=90)
        return sum(a for d, a in pts if lo <= d < start) / 90
    if basis == "complete_months":
        months = collections.defaultdict(Decimal)
        for d, a in pts:
            months[(d.year, d.month)] += a
        full = []
        for (y, m), amt in months.items():
            m_first = date(y, m, 1)
            m_last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
            if m_first >= first and m_last <= last:
                full.append((amt, (m_last - m_first).days + 1))
        if not full:
            return None
        return sum(a for a, _ in full) / sum(n for _, n in full)
    raise ValueError(basis)


samples = []
for req in R.ds.sample_requests:
    truth = Decimal(labels[req.request_id]["amount_safe_to_pay"])
    if truth == req.amount:
        continue
    prof, fc, _ = R.build(req)
    cur = prof.currency
    h = R.headroom(fc, prof)
    bind, raw = min(h, key=lambda x: x[1])
    vary = {}
    for s in fc.series:
        if s.direction == "debit":
            a = [to_home(e.amount, e.currency, cur, e.date, R.ds.fx) for e in s.events if e.amount is not None]
            if len(set(a)) > 1:
                vary["|".join(s.key)] = s
    upto = [f for f in fc.flows if f.date <= bind]
    income = sum((f.amount for f in upto if f.amount > 0), Decimal(0))
    fixed = -sum((f.amount for f in upto if f.amount < 0 and f.source not in vary), Decimal(0))
    est_old = -sum((f.amount for f in upto if f.amount < 0 and f.source in vary), Decimal(0))
    truth_est = prof.balance - prof.minimum - truth - fixed + income
    history = [e for e in R.ds.events_by_user[req.user_id] if e.status == "settled" and not e.linked_event_id and e.date < req.date
               and e.amount is not None and e.direction == "debit" and e.type in OUTFLOW_TYPES]
    samples.append(dict(req=req, cur=cur, bind=bind, fc=fc, vary=vary, upto=upto, truth_est=truth_est, est_old=est_old,
                        history=history))

VARIANTS = []
for thr in (0.5, 0.8):
    for basis in ("span", "span_plus_gap", "trailing90", "complete_months"):
        for days_mode in ("incl_request_day", "excl_request_day"):
            for rnd in ("none", "unit"):
                VARIANTS.append((thr, basis, days_mode, rnd))


def estimate(s, thr, basis, days_mode, rnd):
    cls = classify(s["history"], thr)
    cur = s["cur"]
    unit = Decimal(100) if cur == "IDR" else ONE
    total = Decimal(0)
    pools_used = {}
    for key, series in s["vary"].items():
        cat = key.split("|")[1]
        if cls.get(cat, ("series",))[0] == "pool":
            continue
        total += -sum((f.amount for f in s["upto"] if f.source == key), Decimal(0))
    days = (s["bind"] - s["req"].date).days + (1 if days_mode == "incl_request_day" else 0)
    for cat, (kind, _) in cls.items():
        if kind != "pool":
            continue
        es = [e for e in s["history"] if e.category == cat]
        rate = pool_rate(es, cur, s["req"].date, basis)
        if rate is None:
            return None, None
        proj = rate * days
        if rnd == "unit":
            proj = (proj / unit).quantize(ONE, ROUND_HALF_UP) * unit
        pools_used[cat] = proj
        total += proj
    return total, pools_used


L = []
w = L.append
w("# Series vs pool diagnostic\n")
w("Ratio = truth-implied estimated component / our estimated component, up to our binding day (21 uncapped samples). "
  "Current model: occurrences at mean amount for every varying series.\n")
old = [s["truth_est"] / s["est_old"] for s in samples]


def summarize(ratios):
    rs = [float(r) for r in ratios]
    dev = [abs(r - 1) for r in rs]
    return (min(rs), max(rs), statistics.median(rs), statistics.pstdev(rs), sum(d <= 0.02 for d in dev),
            sum(d <= 0.05 for d in dev))


mn, mx, med, sd, w2, w5 = summarize(old)
w("| model | min | max | median | stdev | within 2% | within 5% | exact |")
w("|---|---:|---:|---:|---:|---:|---:|---:|")
w(f"| current (occurrences) | {mn:.3f} | {mx:.3f} | {med:.3f} | {sd:.3f} | {w2} | {w5} | 0 |")
results = []
for v in VARIANTS:
    ratios, exact, ok = [], 0, True
    for s in samples:
        est, _ = estimate(s, *v)
        if est is None or est == 0:
            ok = False
            break
        ratios.append(s["truth_est"] / est)
        exact += abs(s["truth_est"] - est) <= Decimal("0.01")
    if not ok:
        continue
    results.append((summarize(ratios)[3], v, summarize(ratios), exact, ratios))
results.sort(key=lambda r: r[0])
for sd, v, (mn, mx, med, _, w2, w5), exact, _ in results:
    w(f"| pool thr={v[0]} basis={v[1]} days={v[2]} round={v[3]} | {mn:.3f} | {mx:.3f} | {med:.3f} | {sd:.3f} | {w2} | {w5} | {exact} |")

best = results[0]
w(f"\n## Per-sample ratios: current vs best-spread pool variant {best[1]}\n")
w("| request | cur | binding offset | pool categories (distinct descs / top share) | truth est | ours now | ratio now | pool est | ratio pool |")
w("|---|---|---:|---|---:|---:|---:|---:|---:|")
for s, r_old, r_new in zip(samples, old, best[4]):
    cls = classify(s["history"], best[1][0])
    pools = ", ".join(f"{c} ({st['distinct']}/{st['top_share']:.2f})" for c, (k, st) in sorted(cls.items()) if k == "pool")
    est, _ = estimate(s, *best[1])
    w(f"| {s['req'].request_id} | {s['cur']} | +{(s['bind'] - s['req'].date).days} | {pools} | {s['truth_est']:,.2f} | "
      f"{s['est_old']:,.2f} | {r_old:.3f} | {est:,.2f} | {r_new:.3f} |")

w("\n## Classifier on all sample users (threshold 0.5 and 0.8)\n")
kinds = collections.Counter()
for req in R.ds.sample_requests:
    hist = [e for e in R.ds.events_by_user[req.user_id] if e.status == "settled" and not e.linked_event_id and e.date < req.date
            and e.amount is not None and e.direction == "debit" and e.type in OUTFLOW_TYPES]
    for thr in (0.5, 0.8):
        for cat, (k, st) in classify(hist, thr).items():
            kinds[(thr, cat, k)] += 1
for thr in (0.5, 0.8):
    w(f"- thr={thr}: " + "; ".join(f"{cat} {k}={n}" for (t, cat, k), n in sorted(kinds.items()) if t == thr))
(HERE / "residuals_pool_data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
