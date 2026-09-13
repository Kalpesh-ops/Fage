"""Reconstruct cash flows and project a daily balance for the forecast window.

Everything here is deterministic. Parameters that the samples had to disambiguate live in PARAMS
(see evaluation/calibration.md for how each was chosen).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from .loader import Event, Profile

CENT = Decimal("0.01")

PARAMS = {
    "window_days": 90,          # forecast covers request_date .. request_date + window_days
    "var_stat": "mean",         # mean | median | max | last | meanN
    "var_last_n": 0,            # 0 = all history, else last N occurrences
    "var_round": "none",        # none | ceil | round  (to whole currency units)
    "monthly_var_stat": "mean",
    "income_stale_factor": 1.5,  # a series is alive when request_date <= last + factor*gap
    "same_day_order": "net",    # net | debits_first
    "include_request_day_items": True,
    "min_occurrences": 3,
    "skip_request_day_periodic": True,  # weekly/biweekly spend already posted on request_date is in the balance
    # How far monthly series are projected (see calibration.md):
    #   day_window      -> occurrences up to request_date + monthly_window_days
    #   steps_from_last -> at most monthly_horizon_n calendar-month steps after the last observed occurrence
    #   calendar_months -> occurrences inside the request month and the following monthly_horizon_n - 1 months
    "monthly_horizon": "calendar_months",
    "monthly_window_days": 90,
    "monthly_horizon_n": 3,
    "horizon_applies_to_income": False,
}

OUTFLOW_TYPES = {"expense", "subscription", "debt_payment"}


@dataclass
class Flow:
    date: date
    amount: Decimal          # signed, home currency
    source: str              # event_id or series key
    kind: str                # pending | scheduled | recurring_expense | recurring_income | amendment
    category: str = ""
    description: str = ""
    event_id: str | None = None   # latest historical event of the series (for spending changes)
    flexibility: str = "fixed"
    minimum_allowed_amount: Decimal | None = None


@dataclass
class Series:
    key: tuple
    events: list[Event]
    cadence: str             # monthly | periodic
    gap: float
    direction: str

    @property
    def last(self) -> Event:
        return self.events[-1]


@dataclass
class Forecast:
    start: date
    end: date
    opening: Decimal
    flows: list[Flow]
    series: list[Series] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def daily(self, extra: list[tuple[date, Decimal]] = (), drop_sources: set = frozenset(),
              override: dict | None = None) -> list[tuple[date, Decimal]]:
        """Return (day, lowest balance on that day) for every day in the window."""
        by_day: dict[date, list[Decimal]] = {}
        for f in self.flows:
            if f.source in drop_sources:
                continue
            amt = override.get(f.source, f.amount) if override else f.amount
            if f.date > self.end:
                continue
            by_day.setdefault(max(f.date, self.start), []).append(amt)
        for day, amt in extra:
            by_day.setdefault(max(day, self.start), []).append(amt)
        out, bal, day = [], self.opening, self.start
        debits_first = PARAMS["same_day_order"] == "debits_first"
        while day <= self.end:
            items = by_day.get(day, [])
            if debits_first:
                low = bal + sum((a for a in items if a < 0), Decimal(0))
                bal = bal + sum(items, Decimal(0))
                out.append((day, min(low, bal)))
            else:
                bal = bal + sum(items, Decimal(0))
                out.append((day, bal))
            day += timedelta(days=1)
        return out


def to_home(amount: Decimal, currency: str, home: str, on: date, fx: dict) -> Decimal:
    if currency == home:
        return amount
    if (on, currency, home) in fx:
        return (amount * fx[(on, currency, home)]).quantize(CENT, ROUND_HALF_UP)
    if (on, home, currency) in fx:
        return (amount / fx[(on, home, currency)]).quantize(CENT, ROUND_HALF_UP)
    # nearest earlier dated rate in the stated direction
    cands = sorted((k for k in fx if k[1] == currency and k[2] == home and k[0] <= on), reverse=True)
    if cands:
        return (amount * fx[cands[0]]).quantize(CENT, ROUND_HALF_UP)
    raise KeyError(f"no fx {currency}->{home} on {on}")


def _stat(values: list[Decimal], stat: str, last_n: int, rounding: str) -> Decimal:
    vals = values[-last_n:] if last_n else values
    if stat == "mean":
        v = sum(vals) / len(vals)
    elif stat == "median":
        v = Decimal(statistics.median(vals))
    elif stat == "max":
        v = max(vals)
    elif stat == "last":
        v = vals[-1]
    else:
        raise ValueError(stat)
    if rounding == "ceil":
        return v.quantize(Decimal(1), ROUND_CEILING)
    if rounding == "round":
        return v.quantize(Decimal(1), ROUND_HALF_UP)
    return v.quantize(CENT, ROUND_HALF_UP)


def _add_months(day: date, months: int, dom: int) -> date:
    y, m = divmod(day.month - 1 + months, 12)
    y, m = day.year + y, m + 1
    last_dom = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(dom, last_dom))


def monthly_limit(start: date, end: date) -> tuple[date, int]:
    """(last projectable date, max calendar-month steps) for monthly series under the configured horizon mode."""
    mode = PARAMS["monthly_horizon"]
    if mode == "day_window":
        return min(end, start + timedelta(days=PARAMS["monthly_window_days"])), 10**6
    if mode == "steps_from_last":
        return end, PARAMS["monthly_horizon_n"]
    if mode == "calendar_months":
        first_after = _add_months(date(start.year, start.month, 1), PARAMS["monthly_horizon_n"], 1)
        return min(end, first_after - timedelta(days=1)), 10**6
    raise ValueError(mode)


def _cadence(dates: list[date]) -> tuple[str, float]:
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    if not gaps:
        return "single", 0.0
    g = statistics.median(gaps)
    if 26 <= g <= 33:
        return "monthly", 30.4
    return "periodic", float(g)


def detect_series(history: list[Event], home: str, fx: dict) -> list[Series]:
    """Group settled, unlinked history into recurring series."""
    groups: dict[tuple, list[Event]] = {}
    for e in history:
        if e.direction == "credit":
            # every settled, unlinked credit is a candidate; confirmed_recurring_income() decides what is projected
            groups.setdefault(("in", e.category, e.description), []).append(e)
        elif e.type in OUTFLOW_TYPES and e.direction == "debit":
            groups.setdefault(("out", e.category), []).append(e)
    out = []
    for key, evs in groups.items():
        evs.sort(key=lambda e: e.date)
        if key[0] == "out":
            cad, gap = _cadence([e.date for e in evs])
            if cad != "monthly":
                # a category may hold several monthly items with different descriptions
                subs: dict[str, list[Event]] = {}
                for e in evs:
                    subs.setdefault(e.description, []).append(e)
                if len(subs) > 1 and all(len(s) >= 3 and _cadence([e.date for e in s])[0] == "monthly" for s in subs.values()):
                    for desc, s in subs.items():
                        out.append(Series(key + (desc,), s, "monthly", 30.4, "debit"))
                    continue
        if len(evs) < PARAMS["min_occurrences"]:
            continue
        cad, gap = _cadence([e.date for e in evs])
        out.append(Series(key, evs, cad, gap, "debit" if key[0] == "out" else "credit"))
    return out


def project_series(s: Series, start: date, end: date, home: str, fx: dict) -> list[Flow]:
    amounts = [to_home(e.amount, e.currency, home, e.date, fx) for e in s.events if e.amount is not None]
    if not amounts:
        return []
    last = s.last.date
    varying = len(set(amounts)) > 1
    if s.cadence == "monthly":
        stat = PARAMS["monthly_var_stat"] if varying else "last"
    else:
        stat = PARAMS["var_stat"]
    amt = _stat(amounts, stat, PARAMS["var_last_n"] if s.cadence != "monthly" else 0,
                PARAMS["var_round"] if varying else "none")
    dates = []
    if s.cadence == "monthly":
        dom = statistics.mode([e.date.day for e in s.events[-3:]])
        mend, max_k = monthly_limit(start, end)
        k = 1
        while k <= max_k:
            nd = _add_months(last, k, dom)
            if nd > mend:
                break
            if nd >= start:
                dates.append(nd)
            k += 1
    else:
        gap = max(1, round(s.gap))
        nd = last + timedelta(days=gap)
        first_ok = start + timedelta(days=1) if PARAMS["skip_request_day_periodic"] else start
        while nd <= end:
            if nd >= first_ok:
                dates.append(nd)
            nd += timedelta(days=gap)
    sign = Decimal(-1) if s.direction == "debit" else Decimal(1)
    kind = "recurring_expense" if s.direction == "debit" else "recurring_income"
    return [Flow(x, sign * amt, "|".join(s.key), kind, s.last.category, s.last.description, s.last.event_id,
                 s.last.flexibility, s.last.minimum_allowed_amount) for x in dates]


def confirmed_recurring_income(s: Series, start: date) -> tuple[bool, str]:
    """Future income is counted only when history makes it effectively confirmed.

    A credit series qualifies when it is (1) regular: monthly cadence, (2) fixed: the identical amount (in its own
    currency) settled at least three times, and (3) current: the next expected credit is not overdue. Gig payouts,
    commissions, freelance invoices, bonuses, prizes and refunds fail (1) or (2) because their timing or amount varies
    or they occur once; they are therefore unconfirmed and count only if a message confirms an amount and a date.
    """
    if s.direction != "credit":
        return False, "not a credit"
    if s.cadence != "monthly":
        return False, f"irregular cadence (median gap {s.gap:.0f} days)"
    amounts = [e.amount for e in s.events]
    top = statistics.mode(amounts)
    if amounts.count(top) < PARAMS["min_occurrences"]:
        return False, "amount varies (no fixed amount settled 3 times)"
    if (start - s.last.date).days > PARAMS["income_stale_factor"] * 30.4:
        return False, f"overdue since {s.last.date} (series ended)"
    return True, "regular, fixed, current"


def _monthly_dates(anchor: date, start: date, end: date, include_anchor: bool = False) -> list[date]:
    if PARAMS["horizon_applies_to_income"]:
        end = monthly_limit(start, end)[0]
    out, k = [], 0 if include_anchor else 1
    while True:
        nd = _add_months(anchor, k, anchor.day)
        if nd > end:
            return out
        if nd >= start:
            out.append(nd)
        k += 1


def build(profile: Profile, events: list[Event], start: date, fx: dict, amendments: list = ()) -> Forecast:
    home = profile.currency
    end = start + timedelta(days=PARAMS["window_days"])
    fc = Forecast(start, end, profile.balance, [])
    am_by = {}
    for a in amendments:
        am_by.setdefault(a.action, []).append(a)

    # 1. image amounts fill blank rows
    filled = {a.event_id: a.value for a in am_by.get("set_amount", [])}
    events = [Event(**{**e.__dict__, "amount": filled[e.event_id]}) if e.amount is None and e.event_id in filled else e for e in events]
    for e in events:
        if e.amount is None:
            fc.notes.append(f"{e.event_id} has no amount and no usable image; excluded")

    def conv(amount, cur, on):
        return to_home(amount, cur or home, home, on, fx)

    history = [e for e in events if e.status == "settled" and not e.linked_event_id and e.date < start and e.amount is not None]
    series = detect_series(history, home, fx)
    fc.series = series

    # 2. one-off known future cash: pending debits, scheduled rows, settled rows dated in the window
    scheduled_salary: list[Flow] = []
    for e in events:
        if e.amount is None:
            continue
        amt = to_home(e.amount, e.currency, home, e.date, fx)
        sign = Decimal(-1) if e.direction == "debit" else Decimal(1)
        if e.status == "pending" and e.direction == "debit":
            fc.flows.append(Flow(max(e.date, start), -amt, e.event_id, "pending", e.category, e.description, e.event_id))
        elif e.status == "scheduled" and e.date >= start and e.direction in ("debit", "credit"):
            f = Flow(e.date, sign * amt, e.event_id, "scheduled", e.category, e.description, e.event_id)
            fc.flows.append(f)
            if e.direction == "credit":
                scheduled_salary.append(f)  # a scheduled credit is confirmed income by definition
        elif e.status == "settled" and e.date >= start and e.direction in ("debit", "credit"):
            fc.flows.append(Flow(e.date, sign * amt, e.event_id, "future_settled", e.category, e.description, e.event_id))

    # 3. recurring expenses
    for s in series:
        if s.direction != "debit":
            continue
        if (start - s.last.date).days > PARAMS["income_stale_factor"] * max(s.gap, 1):
            fc.notes.append(f"expense series {s.key} ended at {s.last.date}")
            continue
        flows = project_series(s, start, end, home, fx)
        if s.last.category == "rent" and am_by.get("rent_increase_pct"):
            pct = am_by["rent_increase_pct"][-1].value or Decimal(0)
            for f in flows:
                f.amount = (f.amount * (1 + pct / 100)).quantize(CENT, ROUND_HALF_UP)
            fc.notes.append(f"rent +{pct}% from next payment")
        fc.flows.extend(flows)

    # 4. salary: stable monthly series, anchored by scheduled rows and amended by messages
    salary_series = []
    for s in series:
        if s.direction != "credit":
            continue
        ok, why = confirmed_recurring_income(s, start)
        if ok:
            salary_series.append(s)
        else:
            fc.notes.append(f"income series {s.key} not projected: {why}")
    if am_by.get("salary_remaining") or am_by.get("base_salary_only"):
        a = (am_by.get("salary_remaining") or am_by.get("base_salary_only"))[-1]
        target = conv(a.value, a.currency, start)
        if salary_series:
            keep = min(salary_series, key=lambda s: abs(conv(statistics.mode([e.amount for e in s.events]), s.last.currency, start) - target))
            salary_series = [keep]
    salary_flows: list[Flow] = []
    for s in salary_series:
        base = statistics.mode([e.amount for e in s.events])
        dom = statistics.mode([e.date.day for e in s.events[-3:]])
        anchor = _add_months(s.last.date, 0, dom)
        for x in _monthly_dates(anchor, start, end):
            salary_flows.append(Flow(x, conv(base, s.last.currency, x), "|".join(s.key), "recurring_income", "salary",
                                     s.last.description, s.last.event_id))
    # scheduled salary rows replace the projected occurrence of that month and extend the series
    for sf in scheduled_salary:
        salary_flows = [f for f in salary_flows if abs((f.date - sf.date).days) > 10]
        if not salary_series:
            src = next(e for e in events if e.event_id == sf.source)
            for x in _monthly_dates(sf.date, start, end):
                salary_flows.append(Flow(x, to_home(src.amount, src.currency, home, x, fx), sf.source + "|next", "recurring_income",
                                         "salary", sf.description, sf.source))
    for a in am_by.get("salary_first", []):
        if not a.effective_from or a.effective_from < start:
            continue
        existing = [f for f in scheduled_salary if abs((f.date - a.effective_from).days) <= 10]
        amount = conv(a.value, a.currency, a.effective_from)
        if existing:
            for f in existing:
                f.amount, f.date = amount, a.effective_from
        salary_flows = [f for f in salary_flows if f.date < a.effective_from - timedelta(days=10) or f.kind != "recurring_income"
                        or f.date > a.effective_from + timedelta(days=10)]
        if not existing:
            fc.flows.append(Flow(a.effective_from, amount, a.evidence_id, "message_income", "salary", "confirmed salary"))
        if not salary_flows or all(f.date < a.effective_from for f in salary_flows):
            for x in _monthly_dates(a.effective_from, start, end):
                salary_flows.append(Flow(x, conv(a.value, a.currency, x), a.evidence_id + "|next", "recurring_income", "salary",
                                         "confirmed salary"))
        fc.notes.append(f"{a.evidence_id}: salary {a.value} {a.currency} on {a.effective_from}")
    all_salary = sorted(salary_flows + scheduled_salary, key=lambda f: f.date)
    for a in am_by.get("salary_remaining", []) + am_by.get("base_salary_only", []):
        # conflict rule 4: when the message and settled payroll history disagree, keep the lower (safer) amount
        for f in all_salary:
            f.amount = min(f.amount, conv(a.value, a.currency, f.date))
        fc.notes.append(f"{a.evidence_id}: confirmed salary {a.value} {a.currency} (capped at settled history); variable income excluded")
    for a in am_by.get("salary_set", []):
        for f in all_salary:
            if a.effective_from is None or f.date >= a.effective_from:
                f.amount = conv(a.value, a.currency, f.date)
        fc.notes.append(f"{a.evidence_id}: salary set to {a.value} {a.currency} from {a.effective_from or 'next payroll'}")
    for a in am_by.get("salary_next_only", []):
        if all_salary:
            all_salary[0].amount = conv(a.value, a.currency, all_salary[0].date)
            fc.notes.append(f"{a.evidence_id}: next salary {a.value} {a.currency}")
    for a in am_by.get("salary_move", []):
        if all_salary and a.effective_from:
            # the revised payday replaces the old one for this and every later cycle
            fc.notes.append(f"{a.evidence_id}: salary moved {all_salary[0].date} -> {a.effective_from} (and later cycles)")
            first = all_salary[0].date
            for f in all_salary:
                months = (f.date.year - first.year) * 12 + f.date.month - first.month
                f.date = _add_months(a.effective_from, months, a.effective_from.day)
    if am_by.get("income_ended"):
        fc.notes.append("employment/contract ended: no projected salary")
        salary_flows = []
    fc.flows.extend(salary_flows)
    for a in am_by.get("one_off_income", []):
        when = a.effective_from or (all_salary[0].date if all_salary else None)
        if when and start <= when <= end:
            fc.flows.append(Flow(when, conv(a.value, a.currency, when), a.evidence_id, "message_income", "income", a.note or "confirmed one-off credit"))
    for a in am_by.get("debit_retry", []):
        failed = next((e for e in events if e.event_id == a.event_id), None)
        retry_scheduled = any(e.status == "scheduled" and e.linked_event_id == a.event_id for e in events)
        if failed and failed.amount is not None and not retry_scheduled:
            fc.flows.append(Flow(start, -to_home(failed.amount, failed.currency, home, failed.date, fx), a.evidence_id,
                                 "retry_debit", failed.category, failed.description, failed.event_id))
    return fc
