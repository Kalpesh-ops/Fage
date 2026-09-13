"""Residual investigation for amount_safe_to_pay on the 25 public samples (analysis only; no solver change).

Writes code/evaluation/investigations/residuals.md. Uses the same evidence + forecast path as main.py (offline, cached images).
"""
import sys
from collections import Counter
from datetime import timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fage import evidence, forecast  # noqa: E402
from fage.forecast import to_home  # noqa: E402
from fage.loader import load, load_sample_labels  # noqa: E402
from fage.providers import ModelClient  # noqa: E402

ds = load(ROOT / "dataset")
labels = load_sample_labels(ROOT / "dataset")
client = ModelClient(HERE.parents[1] / "cache", HERE / "residuals_ledger.jsonl", offline=True)
ONE, CENT = Decimal(1), Decimal("0.01")


def build(req):
    prof = ds.profiles[req.user_id]
    events = ds.events_by_user[req.user_id]
    by_id = {e.event_id: e for e in events}
    ev = evidence.parse_messages(ds.messages_by_user.get(req.user_id, []), by_id, req.user_id)
    for img in ds.images_by_user.get(req.user_id, []):
        am, _ = evidence.extract_image(client, img, by_id[img.related_event_id])
        if am:
            ev.amendments.append(am)
    return prof, forecast.build(prof, events, req.date, ds.fx, ev.amendments), ev


def headroom(fc, prof, override=None):
    return [(d, b - prof.minimum) for d, b in fc.daily(override=override)]


def near(a, b, tol_rel=Decimal("0.005"), tol_abs=ONE):
    return abs(a - b) <= max(tol_abs, abs(b) * tol_rel)


rows, matches, backouts, notes = [], {}, {}, {}
round_modes = {
    "as computed (2dp half-up)": lambda x, c: x,
    "floor 2dp": lambda x, c: x.quantize(CENT, ROUND_FLOOR),
    "floor integer": lambda x, c: x.quantize(ONE, ROUND_FLOOR),
    "round half-up integer": lambda x, c: x.quantize(ONE, ROUND_HALF_UP),
    "currency (IDR 100, INR/ZAR 1, EUR/USD 0.01) floor": lambda x, c: (
        (x / 100).quantize(ONE, ROUND_FLOOR) * 100 if c == "IDR" else
        x.quantize(ONE, ROUND_FLOOR) if c in ("INR", "ZAR") else x.quantize(CENT, ROUND_FLOOR)),
}
round_hits = Counter()
per_flow_hits = Counter()

for req in ds.sample_requests:
    prof, fc, ev = build(req)
    cur = prof.currency
    h = headroom(fc, prof)
    bind_day, raw = min(h, key=lambda x: x[1])
    pred = max(Decimal(0), min(req.amount, raw))
    truth = Decimal(labels[req.request_id]["amount_safe_to_pay"])
    capped = truth == req.amount
    resid = None if capped else truth - raw  # positive: truth has more headroom than we do
    rows.append(dict(rid=req.request_id, cur=cur, date=req.date, pred=pred, raw=raw, truth=truth, resid=resid,
                     bind=bind_day, bind_off=(bind_day - req.date).days, capped=capped, req=req.amount))

    # rounding of the final value
    for name, fn in round_modes.items():
        v = max(Decimal(0), min(req.amount, fn(raw, cur)))
        round_hits[name] += v == truth
    # rounding of every estimated recurring amount before summing (analysis override only)
    for name, q in (("per-flow ceil integer", "ceil"), ("per-flow round integer", "round"), ("per-flow floor integer", "floor")):
        mode = {"ceil": "ROUND_CEILING", "round": "ROUND_HALF_UP", "floor": "ROUND_FLOOR"}[q]
        ov = {f.source: f.amount.quantize(ONE, mode) for f in fc.flows if f.kind.startswith("recurring")}
        hh = headroom(fc, prof, ov)
        v = max(Decimal(0), min(req.amount, min(b for _, b in hh)))
        per_flow_hits[name] += v.quantize(CENT) == truth

    if capped:
        notes[req.request_id] = f"truth capped at requested amount; our raw headroom {raw:,.2f} (>= request: {raw >= req.amount})"
        continue

    # ledger search for |resid|
    target = abs(resid)
    cands = []
    for e in ds.events_by_user[req.user_id]:
        if e.amount is None:
            continue
        amt = to_home(e.amount, e.currency, cur, e.date, ds.fx)
        for k, lab in ((Decimal("0.5"), "half"), (ONE, "1x"), (Decimal(2), "2x"), (Decimal(3), "3x")):
            if near(amt * k, target):
                cands.append(f"event {e.event_id} {e.description} ({e.category}, {e.status}, {e.date}) {amt} x{lab}")
    seen = set()
    for f in fc.flows:
        if f.source in seen:
            continue
        seen.add(f.source)
        for k, lab in ((Decimal("0.5"), "half"), (ONE, "1x"), (Decimal(2), "2x"), (Decimal(3), "3x")):
            if near(abs(f.amount) * k, target):
                n_before = sum(1 for g in fc.flows if g.source == f.source and g.date <= bind_day)
                cands.append(f"projected {f.kind} {f.source} amount {abs(f.amount)} x{lab} (occurrences up to binding day: {n_before})")
    # history series statistics (not only the stat we use)
    for s in fc.series:
        amts = [to_home(e.amount, e.currency, cur, e.date, ds.fx) for e in s.events if e.amount is not None]
        if not amts:
            continue
        for stat, v in (("min", min(amts)), ("max", max(amts)), ("last", amts[-1])):
            if near(v, target):
                cands.append(f"series {'|'.join(s.key)} {stat} {v}")
    matches[req.request_id] = sorted(set(cands))[:6]

    # back out the binding day: days whose headroom equals truth; and window ends that would produce truth
    exact_days = [d for d, b in h if near(b, truth)]
    closest_day, closest_val = min(h, key=lambda x: abs(x[1] - truth))
    end_match = None
    run = None
    for d, b in h:
        run = b if run is None else min(run, b)
        if near(run, truth) and end_match is None:
            end_match = d
    start_match = None
    for s_i in range(len(h)):
        if near(min(b for _, b in h[s_i:]), truth):
            start_match = h[s_i][0]
            break
    backouts[req.request_id] = dict(exact_days=exact_days, closest_day=closest_day, closest_gap=closest_val - truth,
                                    end_match=end_match, start_match=start_match)

# ------------------------------------------------------------------ report
L = []
w = L.append
w("# amount_safe_to_pay residual investigation (25 public samples)\n")
w("Analysis only: `python code/evaluation/investigations/residuals.py`. Same evidence + forecast path as `main.py` (offline, cached "
  "image amounts, current PARAMS). Residual = truth − our raw headroom (balance − minimum at the binding day, before the "
  "cap at `requested_amount`). Positive residual = truth leaves **more** money than we do (we over-deduct). "
  "Binding day = argmin of daily headroom; offset = days after `request_date`.\n")
w("## 1. Table\n")
w("| request | cur | request_date | predicted | truth | residual | resid % of truth | binding day (offset) |")
w("|---|---|---|---:|---:|---:|---:|---|")
for r in rows:
    res = "capped" if r["capped"] else f"{r['resid']:,.2f}"
    pct = "" if r["capped"] else f"{(r['resid'] / r['truth'] * 100):.1f}%"
    w(f"| {r['rid']} | {r['cur']} | {r['date']} | {r['pred']:,.2f} | {r['truth']:,.2f} | {res} | {pct} | {r['bind']} (+{r['bind_off']}) |")

un = [r for r in rows if not r["capped"]]
pos = [r for r in un if r["resid"] > 0]
neg = [r for r in un if r["resid"] < 0]
zero = [r for r in un if r["resid"] == 0]
w("\n## 2. Sign\n")
w(f"Uncapped samples: {len(un)}. Truth higher (we over-deduct): {len(pos)} "
  f"({', '.join(r['rid'][-2:] for r in pos)}). Truth lower (we under-deduct): {len(neg)} "
  f"({', '.join(r['rid'][-2:] for r in neg)}). Exact: {len(zero)}.\n")
w("Binding-day offsets for uncapped samples: " + ", ".join(f"{r['rid'][-2:]}:+{r['bind_off']}" for r in un) + "\n")

w("## 3. Ledger search for |residual|\n")
w("Match = single event amount, projected series amount, or history min/max/last, times ½, 1, 2 or 3, within "
  "max(1 unit, 0.5%).\n")
for rid, c in matches.items():
    r = next(x for x in rows if x["rid"] == rid)
    w(f"- **{rid}** residual {r['resid']:,.2f} {r['cur']}: " + ("; ".join(c) if c else "no single-term match"))
for rid, n in notes.items():
    w(f"- **{rid}**: {n}")

w("\n## 4. Backed-out binding day\n")
w("`exact days` = days whose headroom equals truth; `window end` = first window end at which the running minimum equals "
  "truth; `window start` = first start day whose suffix minimum equals truth.\n")
w("| request | our binding day | exact-match days | closest day (gap) | window end giving truth | window start giving truth |")
w("|---|---|---|---|---|---|")
for rid, b in backouts.items():
    r = next(x for x in rows if x["rid"] == rid)
    ed = ", ".join(str(d) for d in b["exact_days"][:3]) or "none"
    w(f"| {rid} | {r['bind']} | {ed} | {b['closest_day']} ({b['closest_gap']:,.2f}) | {b['end_match'] or 'none'} | {b['start_match'] or 'none'} |")

w("\n## 5. Rounding re-score (exact matches out of 25)\n")
w("| rounding | exact |")
w("|---|---:|")
for k, v in round_hits.items():
    w(f"| final value: {k} | {v} |")
for k, v in per_flow_hits.items():
    w(f"| {k} (applied to every projected recurring amount) | {v} |")

(HERE / "residuals_data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
