"""Independent contract checks over a finished output CSV. Returns a list of violations."""
from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .loader import Dataset

COLUMNS = ["request_id", "amount_safe_to_pay", "affordability_status", "recommended_payment_method", "payment_plan",
           "earliest_date_for_full_payment", "spending_changes_needed", "decision_explanation"]
STATUSES = {"affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"}
METHODS = {"full_payment", "partial_payment", "installments", "wait", "not_recommended"}


def validate(path: Path, ds: Dataset, requests=None) -> list[str]:
    requests = requests if requests is not None else ds.requests
    errs: list[str] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            errs.append(f"columns {reader.fieldnames} != {COLUMNS}")
        rows = list(reader)
    by_id = {r.request_id: r for r in requests}
    ids = [r["request_id"] for r in rows]
    if sorted(ids) != sorted(by_id) or len(ids) != len(set(ids)):
        errs.append(f"row ids mismatch: {len(ids)} rows for {len(by_id)} requests")
    events = {e.event_id: e for evs in ds.events_by_user.values() for e in evs}
    for row in rows:
        rid = row["request_id"]
        req = by_id.get(rid)
        if not req:
            continue
        prof = ds.profiles[req.user_id]
        e = lambda msg: errs.append(f"{rid}: {msg}")  # noqa: E731
        try:
            safe = Decimal(row["amount_safe_to_pay"])
        except InvalidOperation:
            e("amount_safe_to_pay not a number")
            continue
        if not (0 <= safe <= req.amount):
            e("amount_safe_to_pay out of range")
        st, me = row["affordability_status"], row["recommended_payment_method"]
        if st not in STATUSES:
            e(f"bad status {st}")
        if me not in METHODS:
            e(f"bad method {me}")
        earliest = row["earliest_date_for_full_payment"]
        if st == "affordable_now" and earliest != req.date.isoformat():
            e("affordable_now requires earliest == request_date")
        if earliest and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", earliest):
            e("bad earliest date format")
        plan = []
        if row["payment_plan"] != "none":
            for part in row["payment_plan"].split("|"):
                m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}):(\d+(?:\.\d{1,2})?)", part)
                if not m:
                    e(f"bad plan entry {part}")
                    break
                plan.append((date.fromisoformat(m.group(1)), Decimal(m.group(2))))
            if [p[0] for p in plan] != sorted(p[0] for p in plan):
                e("plan not chronological")
        if (me == "not_recommended") != (row["payment_plan"] == "none"):
            e("payment_plan none iff not_recommended")
        if me in ("full_payment", "wait", "partial_payment", "installments") and me != "wait" and me not in prof.methods:
            e(f"method {me} not accepted by user")
        if me == "wait" and "full_payment" not in prof.methods:
            e("wait requires full_payment acceptance")
        if me == "partial_payment":
            if st != "affordable_with_plan" or not req.allows_partial or len(plan) != 2:
                e("partial_payment shape/status invalid")
            elif plan[0] != (req.date, safe) or plan[0][1] + plan[1][1] != req.amount or not (0 < safe < req.amount):
                e("partial_payment amounts invalid")
            elif earliest != plan[1][0].isoformat() or plan[1][0] > req.deadline:
                e("partial second payment must be on earliest date and by deadline")
        if me == "installments":
            opts = ds.options_by_request.get(rid, [])
            ok = False
            for o in opts:
                if o.method != "installments" or o.n != len(plan):
                    continue
                exp = [(o.first_date.toordinal() + (o.every_days or 0) * i, o.payment_amount) for i in range(o.n)]
                if [(d.toordinal(), a) for d, a in plan] == exp:
                    ok = True
            if not ok:
                e("installment plan does not match a supplied option")
            if prof.max_installment_months is None:
                e("installments for a user with no max_installment_months")
        changes = row["spending_changes_needed"]
        if changes != "none":
            parts = changes.split("|")
            if len(parts) > 3:
                e("more than three spending changes")
            touched = []
            for p in parts:
                bits = p.split(":")
                ev = events.get(bits[1]) if len(bits) > 1 else None
                if not ev or ev.user_id != req.user_id:
                    e(f"spending change references unknown event {p}")
                    continue
                touched.append(ev.event_id)
                if ev.category in prof.protect:
                    e(f"{p} touches protected category")
                if bits[0] == "stop":
                    if ev.category not in prof.stop_ok or ev.flexibility not in ("stoppable", "reducible_or_stoppable"):
                        e(f"{p} not stoppable for this user")
                elif bits[0] == "reduce_to" and len(bits) == 3:
                    if ev.category not in prof.reduce_ok or ev.flexibility not in ("reducible", "reducible_or_stoppable"):
                        e(f"{p} not reducible for this user")
                    if ev.minimum_allowed_amount is not None and Decimal(bits[2]) < ev.minimum_allowed_amount:
                        e(f"{p} below minimum_allowed_amount")
                else:
                    e(f"bad change {p}")
            if len(touched) != len(set(touched)):
                e("same event both stopped and reduced")
        if not row["decision_explanation"].strip():
            e("empty explanation")
    return errs
