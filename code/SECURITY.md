# Fage security model

This describes what the code does, not the original design brief. Where the two differ, the code is stronger: untrusted
message text never reaches a model.

## Trust boundary in one picture

```
dataset CSVs (trusted structure) ──► loader ──► forecast ──► planner ──► narrator ──► output.csv
                                                  ▲
                                   validated Amendment records only
                                                  ▲
                     ┌────────────────────────────┴───────────────────────────┐
     messages.csv (untrusted text)                              images (untrusted pixels)
     deterministic rule table, NO model                          vision model → raw text
     unmatched text → rejected                                   strict {amount, currency} check
     instruction-shaped text → blocked                           anything else → rejected
```

`forecast.py`, `planner.py`, `narrator.py`, `validator.py` and `loader.py` import nothing from `providers.py`. The
model client is constructed in `main.py` and passed only to `evidence.extract_image`. No model output can reach a
decision except as one validated amount on one event that our code chose.

## 1. Message path: no model in the loop

**Mechanism** (`fage/evidence.py`, `RULES`, `classify_message`, `parse_messages`)

* **Ordered rules, first match wins.** Each message is matched against an ordered table of 26 named rules. Each rule has
  a fixed list of English and Indonesian trigger phrases and maps to one action from a closed set (`ACTIONS`).
* **Values come from fixed patterns.** Amounts are read only with a currency-code pattern (`IDR|INR|EUR|USD|ZAR`
  followed by a number). Dates are read only as ISO `YYYY-MM-DD` or `D Month YYYY`, and percentages only as `N%`. Nothing
  else in the text is interpreted.
* **The action set has no decision in it.** Actions change forecast inputs (salary amount or date, a confirmed
  one-off credit, a rent percentage, a retry of a failed debit). None can set a status, method, plan or safe amount.

**Rejection, not guessing.** A message is blocked, and no amendment is emitted, when any of these hold:

| Condition | Rule recorded | Why |
|---|---|---|
| Matches the advance-fee instruction rule (`pay the release/processing charge`, `bayar biaya pencairan/pemrosesan`) | `advance_fee_instruction` | instruction-shaped text telling the user to pay |
| Matches no rule at all | `none` | unrecognised text is not interpreted |
| Matches an income rule but states no amount in a supported currency | the income rule | the amount is not guessed |
| States an amount above the per-currency cap (`AMOUNT_CAP`) | the income rule | implausible unverified credit |
| `related_event_id` is not an event in this user's ledger | the matched rule | cross-user reference |

**Result on the dataset** (`evaluation/rejected_amendments.json`, from `python code/main.py`):
* 215 messages parsed, 213 accepted and 2 blocked;
* 0 unrecognised;
* the two blocked messages are both advance-fee prize scams, one in English and one in Indonesian:

| evidence | user | language | what it tried | effect if trusted | action |
|---|---|---|---|---|---|
| message_67 | user_88 | English | Claimed a cash prize and told the user to pay a release/processing charge today to receive it, with urgency | An unplanned outgoing fee plus an unconfirmed prize treated as incoming cash | Blocked, no amendment; forecast unchanged |
| message_142 | user_179 | Indonesian | Same scheme ("Bayar biaya pencairan hari ini…") | Same | Blocked, no amendment; forecast unchanged |

Neither user has a request in the sample set, and neither message changes any output row.

**Recognised but cash-neutral.** Messages that describe money which is not yet cash are accepted as evidence with no
cash effect. Examples: a payout still pending, a prize in processing, a refund not yet received, a bonus awaiting
review, a portfolio valuation change. They map to `ignore_unconfirmed` or `non_cash` and add nothing to the forecast.
That's consistent with the ledger rules: pending credits, `unrealized` and `non_cash` rows are never cash.

## 2. Image path: the only model surface

16 ledger rows have a blank `amount` and a linked image. This is the only place a model is called.

**Binding is ours.**
* `main.py` resolves `image_id → related_event_id` from `images.csv` and refuses the image if that event is not in the
  requesting user's ledger.
* The resulting `Amendment.event_id` is always that event. The model is never asked for, and cannot supply, an event
  id: a response containing an `event_id` key fails the closed-schema check below.

**Request** (`image_prompt`, `IMAGE_SCHEMA`, prompt version `img-v3`)
* The prompt says the image is untrusted and instructions inside it must be ignored.
* It gives the row's description, category, currency and dates, and asks for the amount that row represents.
* Requested schema: `{"amount": number, "currency": one of IDR|INR|EUR|USD|ZAR}`, both required, nothing else.
* Temperature 0, output capped at 4,096 tokens.

**Validation of what comes back** (`validate_image_response`). The provider returns raw text, and the validator runs
these checks in order. The first failure rejects the response. Nothing is repaired, rounded, stripped or re-asked:

1. The response is a string, and after trimming surrounding whitespace it starts with `{` and ends with `}`. Prose,
   code fences, arrays, or trailing text such as injected instructions are rejected.
2. It parses as JSON with numbers kept as exact decimals. `NaN`/`Infinity` are rejected, and so are duplicate keys.
3. The top-level value is an object whose keys are exactly `amount` and `currency`. Any extra field (`event_id`,
   `note`, `affordability_status`, …) is rejected, as is any missing field.
4. `amount` is a JSON number: a string, boolean, null or object is rejected, including `"1,00,000"`.
5. `amount` is finite and greater than 0.
6. `amount` has at most 2 decimal places; `822.055` is rejected, not rounded.
7. `currency` is exactly one of the five codes, case-sensitive: `inr` and `Rs` are rejected.
8. `currency` equals the bound event's currency.
9. `amount` does not exceed the per-currency cap: IDR 1e10, INR 1e8, ZAR 1e7, EUR 1e6, USD 1e6.

**On rejection:** the amount stays blank and the event is excluded from the forecast. It is never treated as zero.
An evidence record with the bound event, the violation and a raw-response excerpt goes to
`rejected_amendments.json`.

**Provider fail-over cannot launder content.**
* `providers.structured_call` falls over from Gemini to OpenRouter only on transport failure: an HTTP error, a missing
  key, or an empty or malformed API envelope.
* It never falls over because the content was wrong, so a bad answer is rejected, not replaced by a second opinion.
* Responses are cached as raw text keyed by `sha256(prompt_version + prompt + image bytes)`, so validation re-runs on
  every read, including offline replays.

**Tests** (`python code/evaluation/test_evidence_boundary.py`, stdlib only, all passing).
* 28 image-response cases: prose before the object, code fences, text injected after the object, extra fields
  (`event_id`, `note`, `affordability_status`), missing fields, amount as string/bool/null/object, negative, zero,
  3 decimal places, above cap, NaN, Infinity, lowercase or symbol currency, currency mismatch, duplicate keys, array,
  bare text, non-text.
* 5 message cases: English scam, Indonesian scam, an unrecognised "ignore your rules" instruction, an income update
  without an amount, and a cross-user event reference.
* A dataset check that no real message is unrecognised.

## 3. Threat table

| # | Threat | Control | Where enforced | Evidence |
|---|---|---|---|---|
| 1 | Instruction injection in a message | No model reads messages; instruction-shaped text is blocked by rule; unmatched text is rejected | `evidence.RULES`, `parse_messages` | `rejected_amendments.json` (message_67, message_142); boundary tests |
| 2 | Injection or misleading content in an image | Model output limited to a closed two-key object; 9 ordered checks; no repair | `evidence.validate_image_response` | boundary tests (28 cases) |
| 3 | Model tries to decide or target a record | Decision modules import no provider; event id bound from `images.csv` by our code; extra keys rejected | module imports; `main.run`; check 3 | `grep -n import code/fage/{forecast,planner,narrator,validator,loader}.py` |
| 4 | Evidence targets another user | Message `related_event_id` and image `related_event_id` must belong to the requesting user | `parse_messages`; `main.run` | boundary test "cross-user event reference" |
| 5 | Unconfirmed money counted as cash | Pending credits, `unrealized`, `non_cash` never cash; future income only when regular + fixed + current or confirmed by a message with amount and date | `forecast.build`, `confirmed_recurring_income` | trace notes per request; `calibration.md` |
| 6 | Guessed values | Messages without an amount are rejected; images failing validation leave the amount blank, not zero | `parse_messages`; `extract_image` | trace note "has no amount and no usable image; excluded" |
| 7 | Unsafe spending change | `reduce_to` exactly `minimum_allowed_amount`; only user-permitted, non-protected categories; ≤3 changes; one action per event | `planner.change_options` | `validator.validate` re-checks every output row |
| 8 | Conflicting records | Explicit amendment > newer same-source record > settled > safer reading (e.g. message salary capped at settled payroll) | `forecast.build` | trace notes |
| 9 | Secret leakage | Keys only from the environment or git-ignored `.env`; never logged; ledger stores token counts; HTTP errors keep status and message only | `providers.py`, `.gitignore` | `call_ledger.jsonl` |
| 10 | Code execution from data | No `eval`, `exec`, `pickle`, dynamic import or shell; CSV via `csv`; images sent as bytes | all of `code/` | `grep -rnE "eval\(|exec\(|pickle|subprocess|__import__" code/` is empty |
| 11 | Runaway cost / rate limits | Raw-text cache, `--offline`, per-provider RPM limiter, bounded retries with backoff | `providers.py` | `usage_report.md` |
| 12 | Label leakage | Solver never reads sample label columns; no branch references a request, user, event or option id | `loader.load`; `evaluation/` only uses labels | `grep -rn "request_[0-9]\|user_[0-9]" code/fage` is empty |
| 13 | Supply chain | Standard library only at runtime | `README.md` | no third-party imports |

## 4. Residual risks we accept

* **The model chooses which printed figure is the row's amount** (for example a bill's late amount vs its on-time
  amount). Our checks guarantee shape, range and currency, not that the model picked the right line. Mitigation: the
  prompt states the selection rule from the row's own dates and description, and each value is recorded against its
  event.
* **The rule table is only as complete as the templates seen.** A new legitimate template would be rejected
  ("unrecognised") rather than mis-read. That errs toward the unmodified ledger, never toward inventing money.
