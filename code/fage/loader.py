"""Read the dataset CSVs into plain typed records. No decisions are made here."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

LABEL_COLUMNS = (
    "amount_safe_to_pay", "affordability_status", "recommended_payment_method", "payment_plan",
    "earliest_date_for_full_payment", "spending_changes_needed", "decision_explanation",
)


def D(x: str | None) -> Decimal | None:
    return Decimal(x) if x not in (None, "") else None


def d(x: str | None) -> date | None:
    return date.fromisoformat(x[:10]) if x else None


def split(x: str) -> tuple[str, ...]:
    return tuple(p for p in (x or "").split("|") if p)


@dataclass
class Profile:
    user_id: str
    currency: str
    balance: Decimal
    minimum: Decimal
    priorities: tuple[str, ...]
    protect: tuple[str, ...]
    reduce_ok: tuple[str, ...]
    stop_ok: tuple[str, ...]
    methods: tuple[str, ...]
    max_installment_months: int | None


@dataclass
class Request:
    request_id: str
    user_id: str
    date: date
    type: str
    amount: Decimal
    deadline: date
    allows_partial: bool
    text: str


@dataclass
class Event:
    event_id: str
    user_id: str
    type: str
    description: str
    category: str
    direction: str
    amount: Decimal | None  # original currency; None when the CSV amount is blank
    currency: str
    event_date: date
    settlement_date: date | None
    status: str
    linked_event_id: str
    flexibility: str
    minimum_allowed_amount: Decimal | None

    @property
    def date(self) -> date:
        return self.settlement_date or self.event_date


@dataclass
class Option:
    option_id: str
    request_id: str
    method: str
    payment_amount: Decimal
    n: int
    first_date: date
    every_days: int | None
    fee: Decimal
    total: Decimal


@dataclass
class Message:
    message_id: str
    user_id: str
    request_id: str
    related_event_id: str
    sent_at: date
    source_type: str
    text: str


@dataclass
class ImageRef:
    image_id: str
    user_id: str
    request_id: str
    related_event_id: str
    path: Path


@dataclass
class Dataset:
    root: Path
    profiles: dict[str, Profile]
    requests: list[Request]
    sample_requests: list[Request]
    events_by_user: dict[str, list[Event]]
    fx: dict[tuple[date, str, str], Decimal]
    options_by_request: dict[str, list[Option]]
    messages_by_user: dict[str, list[Message]]
    images_by_user: dict[str, list[ImageRef]]
    extra: dict = field(default_factory=dict)


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _request(r: dict) -> Request:
    return Request(r["request_id"], r["user_id"], d(r["request_date"]), r["request_type"], D(r["requested_amount"]),
                   d(r["desired_completion_date"]), r["allows_partial_payment"].strip().lower() == "true", r["request_text"])


def load(root: str | Path) -> Dataset:
    root = Path(root)
    profiles = {}
    for p in _rows(root / "financial_profiles.csv"):
        m = p["max_installment_months"].strip()
        profiles[p["user_id"]] = Profile(
            p["user_id"], p["home_currency"], D(p["current_available_balance"]), D(p["minimum_balance_to_keep"]),
            split(p["financial_priorities"]), split(p["expense_categories_to_protect"]),
            split(p["expense_categories_user_is_willing_to_reduce"]), split(p["expense_categories_user_is_willing_to_stop"]),
            split(p["payment_methods_user_will_consider"]), int(m) if m else None)

    events: dict[str, list[Event]] = {}
    for e in _rows(root / "financial_events.csv"):
        events.setdefault(e["user_id"], []).append(Event(
            e["event_id"], e["user_id"], e["event_type"], e["description"], e["category"], e["direction"], D(e["amount"]),
            e["currency"], d(e["event_date"]), d(e["settlement_date"]), e["status"], e["linked_event_id"], e["flexibility"],
            D(e["minimum_allowed_amount"])))

    fx = {(d(r["rate_date"]), r["from_currency"], r["to_currency"]): D(r["rate"]) for r in _rows(root / "exchange_rates.csv")}

    options: dict[str, list[Option]] = {}
    for o in _rows(root / "request_payment_options.csv"):
        options.setdefault(o["request_id"], []).append(Option(
            o["payment_option_id"], o["request_id"], o["payment_method"], D(o["payment_amount"]), int(o["number_of_payments"]),
            d(o["first_payment_date"]), int(o["payment_frequency_days"]) if o["payment_frequency_days"] else None,
            D(o["financing_fee"]) or Decimal(0), D(o["total_payable_amount"])))

    messages: dict[str, list[Message]] = {}
    for m in _rows(root / "messages.csv"):
        messages.setdefault(m["user_id"], []).append(Message(
            m["message_id"], m["user_id"], m["request_id"], m["related_event_id"], d(m["sent_at"]), m["source_type"], m["message_text"]))

    images: dict[str, list[ImageRef]] = {}
    for i in _rows(root / "images.csv"):
        images.setdefault(i["user_id"], []).append(ImageRef(
            i["image_id"], i["user_id"], i["request_id"], i["related_event_id"], root / "media" / "images" / f"{i['image_id']}.png"))

    # Label columns in the sample file are never read into Request objects.
    reqs = [_request(r) for r in _rows(root / "requests.csv")]
    samples = [_request(r) for r in _rows(root / "sample_requests.csv")] if (root / "sample_requests.csv").exists() else []
    return Dataset(root, profiles, reqs, samples, events, fx, options, messages, images)


def load_sample_labels(root: str | Path) -> dict[str, dict]:
    """Evaluation-only: ground-truth columns of sample_requests.csv. Never imported by the solver."""
    return {r["request_id"]: {k: r[k] for k in LABEL_COLUMNS} for r in _rows(Path(root) / "sample_requests.csv")}
