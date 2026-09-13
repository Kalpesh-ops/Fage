"""Build evaluation/usage_report.md from the call ledger.

Token counts are measured: they come from the provider's usage fields, recorded in call_ledger.jsonl at call time (a
cache replay carries the counts of the call that produced the cached response). Cost is an estimate: measured tokens x
the published per-token rate stated in the report. Run `python code/main.py`, then
`python code/evaluation/usage_report.py --since <ISO timestamp of that run>`.
"""
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fage.providers import REGISTRY, configure_registry  # noqa: E402

configure_registry()
ledger = HERE / "call_ledger.jsonl"
since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
n_requests = 250
all_rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()] if ledger.exists() else []
rows = [r for r in all_rows if r.get("ts", "") >= since]

per_model = collections.defaultdict(lambda: {"live": 0, "hits": 0, "errors": 0, "in": 0, "out": 0})
for r in rows:
    m = per_model[(r.get("provider") or "none", r.get("model") or "none")]
    if r.get("cache") == "miss":
        m["live"] += 1
        m["in"] += r.get("input_tokens", 0)
        m["out"] += r.get("output_tokens", 0)
    elif r.get("cache") == "hit":
        m["hits"] += 1
        m["in"] += r.get("orig_input_tokens", 0)
        m["out"] += r.get("orig_output_tokens", 0)
    else:
        m["errors"] += 1


def cost(provider, tin, tout):
    reg = REGISTRY.get(provider, {})
    if reg.get("price_in_per_m") is None or reg.get("price_out_per_m") is None:
        return None
    return tin / 1e6 * reg["price_in_per_m"] + tout / 1e6 * reg["price_out_per_m"]


def incident_key(e):
    prov = e.split(":")[0]
    code = re.search(r"HTTP (\d+)", e)
    msg = re.search(r'"message": "([^"]{0,110})', e)
    text = msg.group(1) if msg else e[len(prov) + 1:].strip()[:110]
    return prov, code.group(1) if code else "-", text


L = ["# Token usage and cost: final full-dataset run", ""]
w = L.append
w(f"Run window: ledger rows at or after `{since or 'start'}` ({len(rows)} rows); requests in run: {n_requests}.")
w("")
w("**What is measured and what is estimated.**")
w("* **Model use:** only the 16 document images whose ledger amount is blank. Messages (215) are parsed by deterministic "
  "rules and make no model calls. Of the 16 images, 11 belong to evaluation requests.")
w("* **Tokens are measured.** Input and output token counts are the provider-reported usage for the call that produced "
  "each response, recorded in `call_ledger.jsonl`. A cached replay reports the tokens of that original call. On OpenRouter, "
  "output tokens include the model's internal reasoning tokens.")
w("* **Cost is an estimate:** measured tokens × the published per-token rate stated in the table. It is not an invoice.")
w("* **Tier caveat:** for direct Gemini calls the rate is Google's paid Standard tier, and Google also offers a free tier "
  "for this model. The ledger does not record which tier the key used (its HTTP 429 quota errors are consistent with a "
  "quota-limited plan), so the Gemini share of the estimate is an upper bound and may be USD 0. OpenRouter calls are "
  "billed at OpenRouter's published rate.")
w("")
w("| Provider | Model | Live calls | Cache replays | Errors | Input tokens (measured) | Output tokens (measured) | Rate used (USD / 1M in, out) | Estimated cost (USD) |")
w("|---|---|---:|---:|---:|---:|---:|---|---:|")
tot = collections.Counter()
for (prov, model), m in sorted(per_model.items()):
    reg = REGISTRY.get(prov, {})
    c = cost(prov, m["in"], m["out"])
    rate = (f"{reg['price_in_per_m']}, {reg['price_out_per_m']} ({reg['price_source']})"
            if c is not None else "no published rate asserted")
    w(f"| {prov} | {model} | {m['live']} | {m['hits']} | {m['errors']} | {m['in']:,} | {m['out']:,} | {rate} | "
      f"{'n/a' if c is None else f'{c:.4f}'} |")
    for k in ("live", "hits", "errors", "in", "out"):
        tot[k] += m[k]
    tot["cost"] += c or 0
w(f"| **all** | | {tot['live']} | {tot['hits']} | {tot['errors']} | {tot['in']:,} | {tot['out']:,} | | {tot['cost']:.4f} |")
w("")
w("## Totals")
w("")
w(f"* Model requests behind this output: {tot['live'] + tot['hits']}")
w(f"* Tokens (measured): {tot['in']:,} input + {tot['out']:,} output = {tot['in'] + tot['out']:,}")
w(f"* Average tokens per request (over {n_requests} requests): {(tot['in'] + tot['out']) / n_requests:,.1f}")
w(f"* Estimated total cost: USD {tot['cost']:.4f}")
w(f"* Estimated cost per request: USD {tot['cost'] / n_requests:.6f}")
w("")
w("## Provider incidents across the whole session (full ledger)")
w("")
w(f"Ledger span: {all_rows[0]['ts'] if all_rows else '-'} to {all_rows[-1]['ts'] if all_rows else '-'}. "
  "Each row is one failed attempt as recorded, either a call that failed on every provider (`errors`) or a primary "
  "failure before a successful fail-over (`fallback_from`; only recorded from 11:37 onward, so fail-overs between 11:31 "
  "and 11:34 appear as OpenRouter successes without a stated Gemini reason).")
w("")
w("| Provider | HTTP | Message (truncated) | Attempts | First | Last |")
w("|---|---|---|---:|---|---|")
incidents = collections.defaultdict(list)
for r in all_rows:
    for e in (r.get("errors") or []) + (r.get("fallback_from") or []):
        incidents[incident_key(e)].append(r["ts"])
for (prov, code, text), ts in sorted(incidents.items(), key=lambda kv: kv[1][0]):
    w(f"| {prov} | {code} | {text.replace('|', '/')} | {len(ts)} | {ts[0]} | {ts[-1]} |")
w("")
w("**Why Gemini failed mid-run.** Three causes, in order:")
w("1. `API key not valid` (HTTP 400) before a key was configured.")
w("2. `models/gemini-2.5-flash is no longer available to new users` (HTTP 404). The default model was changed to "
  "`gemini-3.6-flash`, which the key's models endpoint lists.")
w("3. `You exceeded your current quota` (HTTP 429) on every attempt from 12:23 to 12:30, during the closed-schema "
  "(`img-v3`) re-extraction. After bounded retries each call failed over to OpenRouter.")
served = collections.Counter(r.get("provider") for r in rows if r.get("cache") in ("hit", "miss"))
w("")
w("Provenance of the responses behind this output (from the ledger, not assumed): "
  + ", ".join(f"{k}: {v}" for k, v in sorted(served.items())) + ". Gemini answered the images it reached before its "
  "quota ran out; the rest failed over to OpenRouter.")
w("")
w("The two OpenRouter failures were self-inflicted and fixed: HTTP 402 because `max_tokens` defaulted above the "
  "account's credit (now capped at 4,096), and one response truncated at the earlier 1,024-token cap.")
(HERE / "usage_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
