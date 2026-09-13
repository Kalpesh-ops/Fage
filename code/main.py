"""Fage — Buy or Wait? financial decision agent.

Usage:
  python code/main.py                     # full run over dataset/requests.csv -> output.csv
  python code/main.py --offline           # no model calls (cached extractions only)
  python code/main.py --samples           # run the 25 public samples -> code/evaluation/sample_output.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fage import evidence, forecast, planner  # noqa: E402
from fage.loader import load  # noqa: E402
from fage.providers import ModelClient  # noqa: E402
from fage.validator import COLUMNS, validate  # noqa: E402


def run(ds, requests, client) -> tuple[list[planner.Decision], list[dict], list[dict]]:
    decisions, rejected, amendments_log = [], [], []
    for req in requests:
        prof = ds.profiles[req.user_id]
        events = ds.events_by_user.get(req.user_id, [])
        by_id = {e.event_id: e for e in events}
        ev = evidence.parse_messages(ds.messages_by_user.get(req.user_id, []), by_id, req.user_id)
        for img in ds.images_by_user.get(req.user_id, []):
            if img.related_event_id not in by_id:
                ev.rejected.append({"evidence_id": img.image_id, "user_id": req.user_id, "reason": "image event not owned by user"})
                continue
            am, rej = evidence.extract_image(client, img, by_id[img.related_event_id])
            if am:
                ev.amendments.append(am)
            if rej:
                ev.rejected.append(rej)
        fc = forecast.build(prof, events, req.date, ds.fx, ev.amendments)
        dec = planner.decide(req, prof, fc, ds.options_by_request.get(req.request_id, []))
        dec.trace["amendments"] = [{k: str(v) if v is not None else None for k, v in a.__dict__.items()} for a in ev.amendments]
        decisions.append(dec)
        rejected.extend(ev.rejected)
        amendments_log.extend(dec.trace["amendments"])
    return decisions, rejected, amendments_log


def write_csv(path: Path, decisions) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for d in decisions:
            w.writerow(d.row())


def main() -> int:
    ap = argparse.ArgumentParser(description="Fage: Buy or Wait? decision agent")
    ap.add_argument("--data", default=str(ROOT / "dataset"))
    ap.add_argument("--out", default=None, help="output CSV path (default: output.csv at repo root)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="make zero model calls; use cached extractions only")
    mode.add_argument("--refresh", action="store_true",
                      help="ignore the image-extraction cache, re-extract every image with the model and overwrite the cache")
    ap.add_argument("--samples", action="store_true", help="run the public sample requests instead of requests.csv")
    args = ap.parse_args()

    ds = load(args.data)
    eval_dir = Path(__file__).resolve().parent / "evaluation"
    client = ModelClient(Path(__file__).resolve().parent / "cache", eval_dir / "call_ledger.jsonl", offline=args.offline,
                         refresh=args.refresh)
    requests = ds.sample_requests if args.samples else ds.requests
    out = Path(args.out) if args.out else (eval_dir / "sample_output.csv" if args.samples else ROOT / "output.csv")

    decisions, rejected, amendments = run(ds, requests, client)
    write_csv(out, decisions)
    tag = "samples" if args.samples else "requests"
    (eval_dir / f"traces_{tag}.json").write_text(json.dumps({d.request_id: d.trace for d in decisions}, indent=1), encoding="utf-8")
    (eval_dir / "rejected_amendments.json" if not args.samples else eval_dir / "rejected_amendments_samples.json").write_text(
        json.dumps(rejected, indent=1), encoding="utf-8")
    errs = validate(out, ds, requests)
    print(f"wrote {len(decisions)} rows -> {out}")
    print(f"amendments accepted: {len(amendments)}, rejected: {len(rejected)}")
    print("validator:", "PASS" if not errs else f"{len(errs)} issue(s)")
    for e in errs[:30]:
        print("  ", e)
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
