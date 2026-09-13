# Fage data contracts

All money is `decimal.Decimal` in the user's home currency after conversion. Dates are `datetime.date`.

## Input records (`fage/loader.py`)

| Record | Key fields | Notes |
|---|---|---|
| `Profile` | `currency, balance, minimum, protect, reduce_ok, stop_ok, methods, max_installment_months` | `max_installment_months=None` means installments are refused |
| `Request` | `request_id, user_id, date, amount, deadline, allows_partial` | label columns of `sample_requests.csv` are never read into this type |
| `Event` | `event_id, type, category, direction, amount?, currency, event_date, settlement_date, status, linked_event_id, flexibility, minimum_allowed_amount` | `Event.date = settlement_date or event_date`; `amount=None` when blank |
| `Option` | `option_id, method, payment_amount, n, first_date, every_days, fee, total` | installment plan = `first_date + i*every_days`, `i < n` |

## Cash-flow rules (`fage/forecast.py`)

| Source | Counted as | When |
|---|---|---|
| settled history before `request_date` | already inside `current_available_balance`; used only to detect series | — |
| `pending` debit | outflow | settlement date (or request date if earlier) |
| `pending` credit, `failed`, `cancelled`, `unrealized`, `non_cash` | ignored | — |
| `scheduled` debit / credit | flow | its date |
| recurring expense series, monthly | projected outflow | same day of month, through the end of request month + 2 calendar months |
| recurring expense series, weekly / 10 / 14 / 21-day | projected outflow | cadence from last occurrence, 90-day window, excluding request day |
| credit series that is regular (monthly), fixed (identical amount ≥3 times) and current (not overdue) | projected inflow | same day of month, 90-day window |
| any other credit history (fails one of the three tests) | not projected: unconfirmed income | counted only if a message confirms amount and date |

## `Amendment` (`fage/evidence.py`) — the only thing evidence can emit

```python
@dataclass(frozen=True)
class Amendment:
    action: str            # closed set, see evidence.ACTIONS
    evidence_id: str       # message_id or image_id
    user_id: str
    event_id: str | None   # must belong to user_id
    value: Decimal | None
    currency: str | None
    effective_from: date | None
    confidence: float
    note: str
```

Actions: `set_amount, salary_set, salary_next_only, salary_first, salary_move, income_ended, salary_remaining,
base_salary_only, one_off_income, rent_increase_pct, debit_retry, keep_debit, ignore_unconfirmed,
internal_transfer, non_cash, untrusted_instruction, informational`.

## `Candidate` / `Decision` (`fage/planner.py`)

```python
@dataclass
class Candidate:
    method: str                          # full_payment | partial_payment | installments | wait
    plan: list[tuple[date, Decimal]]
    changes: tuple[SpendingChange, ...]  # stop / reduce_to on a projected flexible series
    option_id: str | None
    total_paid: Decimal
    completes_by_deadline: bool
    safe: bool                           # lowest simulated balance >= minimum over the window
    lowest_balance: Decimal | None
    rejection_reason: str | None

@dataclass
class Decision:
    request_id: str
    amount_safe_to_pay: Decimal          # computed on the unmodified forecast
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: date | None   # capacity only, ignores preferences and changes
    spending_changes_needed: str
    decision_explanation: str
    trace: dict                          # every candidate with its rejection reason, notes, amendments
```

Ranking of safe candidates: completes by deadline → no spending changes → lowest total paid → earliest
start → fewest payments → lowest `payment_option_id`.

## Output (`output.csv`)

`request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation`
