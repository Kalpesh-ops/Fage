"""Deterministic explanation templates (no model call)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal


def money(cur: str, amount: Decimal) -> str:
    q = amount.quantize(Decimal("0.01"))
    if q == q.to_integral_value():
        return f"{cur} {int(q):,}"
    return f"{cur} {q:,.2f}"


def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def change_sentence(changes, cur: str) -> str:
    parts = []
    for c in changes:
        noun = c.description[:1].lower() + c.description[1:]
        if c.action == "stop":
            parts.append(f"stop the {noun}")
        else:
            parts.append(f"reduce the {noun} to {money(cur, c.new_amount)}")
    s = _join(parts)
    return s[:1].upper() + s[1:]


def render(method: str, status: str, cur: str, minimum: Decimal, requested: Decimal, safe: Decimal, plan, changes,
           deadline: date, earliest: date | None, user_methods=(), allows_partial: bool = False) -> str:
    m = money(cur, minimum)
    if method == "full_payment" and changes:
        return f"{change_sentence(changes, cur)}, then pay {money(cur, requested)} today. This leaves at least {m} available."
    if method == "full_payment":
        # Five of six full_payment samples say "leaves at least"; the lone "keeps the ... minimum" sample is not explained
        # by floor binding or any tested rule, so no variant rule (see evaluation/calibration.md, "Full-payment wording").
        return f"Pay {money(cur, requested)} today. This leaves at least {m} available over the next 90 days."
    if method == "wait" and plan[0][0] < deadline:
        return (f"Wait until {long_date(plan[0][0])}, then pay {money(cur, requested)} in full. "
                f"Paying sooner would put the {m} minimum at risk.")
    if method == "installments":
        return (f"Use {len(plan)} installments of {money(cur, plan[0][1])}, starting {long_date(plan[0][0])}. "
                f"This leaves at least {m} available.")
    if method == "partial_payment":
        return (f"Pay {money(cur, plan[0][1])} today and the remaining {money(cur, plan[1][1])} on {long_date(plan[1][0])}. "
                f"This completes the full request and keeps the {m} minimum protected.")
    if method == "wait":
        return (f"Pay {money(cur, requested)} in full on {long_date(plan[0][0])}. "
                f"Paying earlier would take the balance below the {m} minimum.")
    partial_only = allows_partial and "partial_payment" in user_methods and not {"full_payment", "installments"} & set(user_methods)
    if safe > 0 and earliest is None and partial_only:
        return (f"Do not proceed with the {money(cur, requested)} request. Although {money(cur, safe)} is available today, "
                f"the full amount cannot be completed safely within 90 days.")
    return f"Do not make this payment by {long_date(deadline)}. None of the available options keeps the {m} minimum protected."
