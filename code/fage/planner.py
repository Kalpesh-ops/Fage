"""Candidate generation, safety simulation and ranking. Pure functions over a Forecast."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal

from . import narrator
from .forecast import Forecast
from .loader import Option, Profile, Request

CENT = Decimal("0.01")
MAX_CHANGES = 3


@dataclass(frozen=True)
class SpendingChange:
    action: str                 # stop | reduce_to
    event_id: str
    source: str
    description: str
    category: str
    new_amount: Decimal | None

    def render(self) -> str:
        return f"stop:{self.event_id}" if self.action == "stop" else f"reduce_to:{self.event_id}:{fmt_amount(self.new_amount)}"


@dataclass
class Candidate:
    method: str
    plan: list[tuple[date, Decimal]]
    changes: tuple[SpendingChange, ...] = ()
    option_id: str | None = None
    total_paid: Decimal = Decimal(0)
    completes_by_deadline: bool = False
    safe: bool = False
    lowest_balance: Decimal | None = None
    rejection_reason: str | None = None

    def rank_key(self):
        opt = int(self.option_id.rsplit("_", 1)[-1]) if self.option_id else -1
        return (not self.completes_by_deadline, bool(self.changes), self.total_paid, self.plan[0][0] if self.plan else date.max,
                len(self.plan), opt)


@dataclass
class Decision:
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: date | None
    spending_changes_needed: str
    decision_explanation: str
    trace: dict = field(default_factory=dict)

    def row(self) -> dict:
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": fmt_plain(self.amount_safe_to_pay),
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment.isoformat() if self.earliest_date_for_full_payment else "",
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }


def fmt_amount(x: Decimal) -> str:
    q = x.quantize(CENT)
    return str(int(q)) if q == q.to_integral_value() else f"{q:.2f}"


def fmt_plain(x: Decimal) -> str:
    q = x.quantize(CENT)
    if q == q.to_integral_value():
        return str(int(q))
    return f"{q:.2f}".rstrip("0").rstrip(".")


def fmt_plan(plan) -> str:
    return "|".join(f"{d.isoformat()}:{fmt_amount(a)}" for d, a in plan) if plan else "none"


class Simulator:
    def __init__(self, fc: Forecast, minimum: Decimal):
        self.fc, self.minimum = fc, minimum
        self.base = fc.daily()

    def lowest(self, payments=(), changes: tuple[SpendingChange, ...] = ()) -> Decimal:
        drop = {c.source for c in changes if c.action == "stop"}
        override = {}
        for c in changes:
            if c.action == "reduce_to":
                override[c.source] = -c.new_amount
        series = self.fc.daily(extra=[(d, -a) for d, a in payments], drop_sources=drop, override=override)
        return min(b for _, b in series)

    def suffix_min(self, series=None):
        series = series or self.base
        out, run = [], None
        for day, bal in reversed(series):
            run = bal if run is None else min(run, bal)
            out.append((day, run))
        return list(reversed(out))


def installment_months(o: Option) -> int:
    if o.every_days is None:
        return 1
    if 28 <= o.every_days <= 31:
        return o.n
    return math.ceil(o.n * o.every_days / 30.44)


def change_options(fc: Forecast, prof: Profile) -> list[SpendingChange]:
    seen, out = {}, []
    for f in fc.flows:
        if f.kind != "recurring_expense" or f.date > fc.end or f.source in seen:
            continue
        seen[f.source] = True
        if f.category in prof.protect:
            continue
        if f.category in prof.stop_ok and f.flexibility in ("stoppable", "reducible_or_stoppable"):
            out.append(SpendingChange("stop", f.event_id, f.source, f.description, f.category, None))
        if (f.category in prof.reduce_ok and f.flexibility in ("reducible", "reducible_or_stoppable")
                and f.minimum_allowed_amount is not None and f.minimum_allowed_amount < -f.amount):
            out.append(SpendingChange("reduce_to", f.event_id, f.source, f.description, f.category, f.minimum_allowed_amount))
    return out


def change_sets(options: list[SpendingChange]):
    for k in range(1, MAX_CHANGES + 1):
        for combo in itertools.combinations(options, k):
            if len({c.source for c in combo}) == k:
                yield combo


def decide(req: Request, prof: Profile, fc: Forecast, options: list[Option]) -> Decision:
    sim = Simulator(fc, prof.minimum)
    suffix = sim.suffix_min()
    safe = max(Decimal(0), min(req.amount, suffix[0][1] - prof.minimum)).quantize(CENT, ROUND_FLOOR)
    earliest = next((day for day, low in suffix if low - req.amount >= prof.minimum), None)
    methods = set(prof.methods)
    cands: list[Candidate] = []

    def evaluate(c: Candidate) -> Candidate:
        c.total_paid = sum((a for _, a in c.plan), Decimal(0))
        c.completes_by_deadline = bool(c.plan) and c.plan[-1][0] <= req.deadline
        c.lowest_balance = sim.lowest(c.plan, c.changes)
        c.safe = c.lowest_balance >= prof.minimum
        if not c.safe and not c.rejection_reason:
            c.rejection_reason = f"balance falls to {c.lowest_balance} below minimum {prof.minimum}"
        cands.append(c)
        return c

    change_opts = change_options(fc, prof)

    # full payment today
    full = Candidate("full_payment", [(req.date, req.amount)])
    if "full_payment" not in methods:
        full.rejection_reason = "user does not consider full_payment"
        cands.append(full)
    else:
        evaluate(full)
        if not full.safe:
            for combo in change_sets(change_opts):
                c = evaluate(Candidate("full_payment", [(req.date, req.amount)], combo))
                if c.safe:
                    break

    # partial payment
    if not req.allows_partial:
        cands.append(Candidate("partial_payment", [], rejection_reason="request does not allow partial payment"))
    elif "partial_payment" not in methods:
        cands.append(Candidate("partial_payment", [], rejection_reason="user does not consider partial_payment"))
    elif not (0 < safe < req.amount) or earliest is None:
        cands.append(Candidate("partial_payment", [], rejection_reason="no positive safe amount below the request or no safe completion date"))
    else:
        c = Candidate("partial_payment", [(req.date, safe), (earliest, req.amount - safe)])
        if earliest > req.deadline:
            c.rejection_reason = "second payment would be after the desired completion date"
        evaluate(c)
        if c.rejection_reason and c.safe:
            c.safe = False

    # supplied installment options
    for o in sorted(options, key=lambda o: o.option_id):
        if o.method != "installments":
            continue
        plan = [(o.first_date + timedelta(days=(o.every_days or 0) * i), o.payment_amount) for i in range(o.n)]
        c = Candidate("installments", plan, option_id=o.option_id)
        if "installments" not in methods:
            c.rejection_reason = "user does not consider installments"
            cands.append(c)
            continue
        if prof.max_installment_months is None:
            c.rejection_reason = "user will not consider installments (no max_installment_months)"
            cands.append(c)
            continue
        if installment_months(o) > prof.max_installment_months:
            c.rejection_reason = f"{installment_months(o)} months exceeds max {prof.max_installment_months}"
            cands.append(c)
            continue
        if o.first_date < req.date:
            c.rejection_reason = "first payment before request date"
            cands.append(c)
            continue
        evaluate(c)
        if not c.completes_by_deadline:
            c.safe, c.rejection_reason = False, "final installment after desired completion date"

    # wait
    if "full_payment" not in methods:
        cands.append(Candidate("wait", [], rejection_reason="wait requires the user to accept full_payment"))
    elif earliest is None:
        cands.append(Candidate("wait", [], rejection_reason="full amount never becomes safe within the forecast window"))
    elif earliest > req.date:
        evaluate(Candidate("wait", [(earliest, req.amount)]))

    safe_cands = sorted((c for c in cands if c.safe), key=Candidate.rank_key)
    best = safe_cands[0] if safe_cands else None
    for c in cands:
        if c.safe and c is not best and not c.rejection_reason:
            c.rejection_reason = "ranked lower"

    if best is None:
        method, status, plan, changes = "not_recommended", "not_affordable", [], ()
    else:
        method, plan, changes = best.method, best.plan, best.changes
        if method == "full_payment" and not changes:
            status = "affordable_now"
        elif method == "wait":
            status = "affordable_later"
        else:
            status = "affordable_with_plan"
    if status == "affordable_now":
        earliest = req.date
    text = narrator.render(method, status, prof.currency, prof.minimum, req.amount, safe, plan, changes, req.deadline, earliest,
                           prof.methods, req.allows_partial)
    trace = {
        "safe_today": str(safe), "earliest": earliest.isoformat() if earliest else None,
        "lowest_day": min(sim.base, key=lambda x: x[1])[0].isoformat(),
        "candidates": [{"method": c.method, "option_id": c.option_id, "plan": fmt_plan(c.plan),
                        "changes": [x.render() for x in c.changes], "safe": c.safe,
                        "completes_by_deadline": c.completes_by_deadline, "total_paid": str(c.total_paid),
                        "lowest_balance": str(c.lowest_balance) if c.lowest_balance is not None else None,
                        "rejection_reason": c.rejection_reason, "chosen": c is best} for c in cands],
        "notes": fc.notes,
    }
    return Decision(req.request_id, safe, status, method, fmt_plan(plan), earliest,
                    "|".join(c.render() for c in changes) if changes else "none", text, trace)
