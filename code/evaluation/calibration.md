# Calibration on the 25 public samples

The samples are a development set. They were used to choose between readings the specification leaves
open; they are never read by the solver. The same code path runs for every user, and no branch in
`code/fage` references a request, user, event or option id (`grep -rn "request_[0-9]\|user_[0-9]" code/fage`
is empty).

Tools: `evaluation/score.py` (per-field scorecard), `evaluation/investigations/sweep.py` (full-pipeline grid),
`evaluation/investigations/calibrate.py` (amount-only grid), `evaluation/investigations/debug_user.py` (projected flows for one user). All investigation scripts and verdicts: `evaluation/investigations/INDEX.md`.

## Findings that changed the design

| Question | Evidence from samples | Decision |
|---|---|---|
| Is future income projected from history, or only from `scheduled` rows? | request_13: earliest full date 15 May needs April and May salaries although only March is scheduled. request_01: safe amount requires salaries after the scheduled one. request_05's low safe amount is explained by the salary series ending ("Final employer payroll", nothing after), not by an income rule. | Project a salary series only when it is monthly, the same amount appears ≥3 times, and the next payday is not overdue. Scheduled salary rows replace that month and extend the series. |
| Gig payouts, commissions, freelance invoices? | request_10: safe amount 12,700 is only reachable with **no** weekly platform payouts. | Not a category exclusion: such income fails `confirmed_recurring_income()` (irregular cadence or varying amount), so it is unconfirmed and counts only when a message states an amount and a date. See "Income rule". |
| Does a message's confirmed salary replace settled payroll history? | request_11: message says base salary 38.76M, history shows 23.26M; truth's later earliest date (15 Jul) is inconsistent with the higher figure. | Conflict rule 4 (safer reading): cap at settled history. |
| Salary date moved by a message | request_07: truth earliest 23 Oct after "salary now expected on 23 Sep". | A moved payday shifts all later cycles. |
| Horizon for monthly obligations | request_09 (rent day 90), request_12 (day 87), request_05 (day 88), request_10 (day 87), request_08 (day 83 after a mid-April payment): truth excludes these. | **Rule, not constant:** monthly series are projected through the end of the **request month + 2 calendar months** (`monthly_horizon=calendar_months`, N=3). Replaces the earlier fitted `monthly_window_days=82`; see "Monthly horizon: rule vs constant" below. |
| Which income is projected? | See "Income rule" below. | `confirmed_recurring_income()`: regular + fixed + current. No category list. |
| Weekly/biweekly spend falling on `request_date` | request_25 residual matches one dining occurrence dated on the request day. | `skip_request_day_periodic = True` (already in the balance). |
| Variable spend estimator | mean vs median vs max vs last. | `mean` of all history per| Explanation variants | full payment: 5 of 6 samples say "leaves at least"; the lone "keeps the … minimum" (request_09) is not explained by floor binding or any tested rule. wait: "Wait until …" when the date is before the deadline (one example, request_04). not affordable: "Do not proceed … although X is available" when partial payment is the user's only route (request_14, request_24). | Full payment always renders "leaves at least" (request_09 accepted as a miss); wait and not-affordable rules in `narrator.render`. See "Explanation templates" and "Full-payment wording". |X is available" only when partial payment is the user's only route (request_14, request_24). | Encoded in `narrator.render`. |

## Sweep results (`evaluation/investigations/sweep.py`, offline, images unavailable)

Top configurations (sum of exact matches on 6 decision fields + amount within 5%):

| monthly_window_days | skip_request_day_periodic | var_stat | same_day_order | status | method | plan | earliest | changes | explanation | amount ≤5% |
|---|---|---|---|---|---|---|---|---|---|---|
| 84–86 | True | mean | net | 22 | 23 | 22 | 20 | 22 | 18 | 14 |
| 84–86 | False | mean | net | 22 | 23 | 22 | 20 | 22 | 18 | 12 |
| 84–86 | True | median | net | 21 | 22 | 21 | 21 | 22 | 18 | 14 |
| 90 (spec literal) | False | mean | net | 19 | 20 | 19 | 17 | 22 | 15 | 10 |

After the evidence fixes (salary move, safer confirmed salary) earliest-date matches rose to 21/25.

Second sweep, with all 16 image amounts extracted (prompt `img-v2`, since replaced by the closed-schema `img-v3`; see
SECURITY.md) and a `monthly_max_occurrences` knob:

| monthly_window_days | monthly_max_occurrences | skip_request_day_periodic | var_stat | same_day_order | status | method | plan | earliest | changes | explanation | amount ≤5% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 78 / 80 / 82 | 0 or 3 | True | mean | net | 23 | 24 | 23 | 22 | 22 | 19 | 14 |
| 78 / 80 / 82 | 0 or 3 | False | mean | net | 23 | 24 | 23 | 22 | 22 | 19 | 13 |
| any | 2 | any | any | any | below top 12 | | | | | | |

Chosen at the time: `monthly_window_days=82` (superseded). The day-count window and the `monthly_max_occurrences` knob
were replaced by the calendar-month rule below, which reproduces the same output on every sample and evaluation
request. Other settings kept: `skip_request_day_periodic=True, var_stat=mean, same_day_order=net`.

## Monthly horizon: rule vs constant

**Why the constant was suspect.** `monthly_window_days` tied at 78, 80 and 82. A tie across a range means the samples
can't see the parameter directly, only something that correlates with it.

**Hypotheses tested** (`evaluation/investigations/sweep.py`). All use the cap-free 90-day window for everything else; sums count exact
matches on 6 decision fields plus amount within 5%, on 25 samples.

| Monthly projection | Total | status | method | plan | earliest | changes | explanation | Misses |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| day window 90 (no cap) | 125 | 19 | 20 | 19 | 18 | 22 | 15 | 06,08,09,11,12,13,14,17,19,21,24 |
| day window 78 / 80 / 82 | 147 | 23 | 24 | 23 | 22 | 22 | 19 | 06,11,14,17,19,21,24 |
| day window 84 / 86 | 142 | 22 | 23 | 22 | 21 | 22 | 18 | + 08 |
| day window 88 | 131 | 20 | 21 | 20 | 19 | 22 | 16 | + 08,12,13 |
| N calendar-month steps from the last occurrence, N=2 | 141 | 23 | 24 | 21 | 20 | 22 | 17 | + 03,18 |
| N calendar-month steps from the last occurrence, N=3 or 4 | 125 | identical to no cap | | | | | | |
| **calendar months: request month + N−1, N=3** | **147** | **23** | **24** | **23** | **22** | **22** | **19** | **06,11,14,17,19,21,24** |
| calendar months, N=2 | 131 | | | | | | | |
| calendar months, N=4 | 125 | identical to no cap | | | | | | |
| any of the above, also applied to salary projection | same as without | | | | | | | |

**Result.** (Scores above predate the full-payment wording change. Re-run after it, the calendar rule and the 82-day window both score 146, still identical cell for cell.)
* **Steps from the last occurrence does not work.** Three steps land on day 83–92 depending on day of month, which
  keeps the day-87/88/90 rents the truth drops. It scores the same as no cap.
* **The calendar-month rule does work.** "Everything due in the request month and the next two calendar months"
  matches the fitted constant field-for-field on the samples, with the same misses. On all 250 evaluation requests it
  produces byte-identical `output.csv` to `monthly_window_days=82`.

**Mechanism.** Sample request dates all fall on days 1–12 of their month, so the end of the 3-month bucket falls
80–91 days after the request (offsets 80:1, 82:2, 84:2, 85:4, 86:5, 87:3, 88:5, 89:2, 91:1).
* The excluded rents are exactly the ones dated in the fourth calendar month: request_05 on 2 Feb for a 6 Nov
  request, request_10 on 3 Mar for 6 Dec, request_09 on 2 Oct for 4 Jul, request_12 on 1 Jul for 5 Apr, request_08 on
  1 May for 7 Feb.
* A flat day count can only imitate that by sitting just below the earliest fourth-month bill in the samples. That's
  why 78–82 tie and 84 already loses request_08. The tie was the sweep approximating a calendar boundary with a
  constant.

**What the samples cannot tell us.** Among evaluation requests, the bucket end falls 62–90 days after the request.
Three late-month requests (offsets 62, 67, 70) are where the rule and the constant diverge most. Even so, neither
decisions nor amounts change on any of the 250, because monthly items beyond day 62 never set the binding day for
those users. The rule is preferred because it names a mechanism, not because the data prefers it over 82.

## Income rule

**Mechanism.** Future income counts only when history makes it effectively confirmed. `confirmed_recurring_income()`
projects a credit series only if all three hold:

1. **Regular:** monthly cadence (median gap 26–33 days).
2. **Fixed:** the identical amount, in its own currency, settled at least 3 times.
3. **Current:** the next expected credit is not overdue (last credit within 1.5 cycles of the request date).

**What fails, and why.**
* Gig payouts and freelance invoices fail (1) or (2): weekly or irregular timing, amounts that vary.
* Commissions and second household incomes fail (2).
* A "Final employer payroll" leaves the regular series overdue, so it fails (3).
* Prizes, reimbursements and refunds occur once, or are linked to an earlier event, and never form a series.

Unconfirmed income counts only when a message states an amount and a date (`salary_first`, `one_off_income`). A
scheduled credit row is confirmed by definition.

**Tally on the 250 evaluation requests** (from the trace notes):
* irregular cadence: 33 series
* amount varies: 31 series
* overdue (series ended): 17 series

**The rule used to read as an exclusion list.** The earlier code also required `category == "salary"` and dropped
`windfall`/`work_expense` rows from history. Both were removed. Output on all 250 requests and all 25 samples is
byte-identical, so the three conditions alone carry the behaviour. Samples that pin the rule down: request_10 (safe
amount 12,700 only without weekly platform payouts), request_05 (ended payroll), request_13 (irregular second household
income not projected, primary salary projected past the scheduled row).

## Explanation templates: what the misses are, and how well each variant rule is pinned down

**The 6 failing explanations (samples, 19/25) contain no renderer bugs.** A character diff of each miss against
ground truth:

| request | only difference | cause |
|---|---|---|
| request_14 | "EUR 616.29" vs "EUR 597.74" inside the same sentence | `amount_safe_to_pay` |
| request_24 | "INR 13,539.29" vs "INR 13,420" | `amount_safe_to_pay` |
| request_19 | partial split "30,022.77 / 9,637.23" vs "28,820 / 10,840" | `amount_safe_to_pay` feeds the plan |
| request_11 | extra leading "Stop the cloud storage plan and" | planner chose 2 spending changes, truth 1 |
| request_06 | wait sentence vs "Stop the family streaming plan, then pay … today" | planner chose wait; truth used a spending change |
| request_21 | full-payment sentence vs "Stop … and reduce … to USD 23.50, then pay … today" | planner found it safe without changes |

Thousands separators, `.00` suppression ("EUR 620.40", "IDR 665,950", "USD 23.50") and `D Month YYYY` dates match in
all 25. Explanation accuracy is bounded by the amount and decision fields, not by the templates.

**Variant selection: which rules the samples actually support.** For each family, every simple rule tried that
reproduces all samples:

| family (samples) | minority variant seen in | rules that fit every sample | eval rows in family | rows given the minority variant, by rule | status |
|---|---|---|---|---|---|
| full payment, no changes (01, 09, 16) | request_09 only ("This keeps the … minimum available") | partial_payment in methods; ≥3 methods; currency EUR; partial and installments both accepted; allows_partial and accepts partial | 62 | 29 / 10 / 11 / 10 / 14 | **Not identifiable.** One positive example; five rules disagree on up to 19 eval rows. The code uses "partial_payment in methods". This is a guess. |
| wait (03, 04, 08, 13, 18, 23) | request_04 only ("Wait until D, then pay …") | earliest date < desired completion date | 62 | 14 | **Single candidate, single positive example.** Tested alternatives (allows_partial; full-payment-only users) each contradict at least one sample. The mechanism reads naturally ("wait until" when the date is earlier than the deadline, "pay in full on" when it is the deadline), but it rests on one case. |
| not affordable (05, 10, 14, 15, 20, 24, 25) | request_14, request_24 ("Do not proceed … Although X is available today") | partial payment is the user's only route (allows_partial and methods = {partial_payment}); or allows_partial, accepts partial, installments not accepted | 71 | 10 / 11 | **Pinned down.** Two positive examples. The two fitting rules differ on one eval row. Mechanism: the sentence cites today's available amount only when a partial payment was the one route open to the user. Implemented as the first rule. |

### Full-payment wording: floor-binding test and decision

**Hypothesis.** The lone "This keeps the … minimum" full-payment sample (request_09) is the one where the recommended
plan takes the balance exactly to the floor.

**Test.** trough − `minimum_balance_to_keep`, simulated on our forecast with truth's plan and spending changes, for
all six full_payment samples:

| request | truth wording | spending changes | trough − minimum |
|---|---|---|---:|
| request_01 | leaves at least | none | 4,985.27 |
| request_06 | leaves at least | stop:event_476 | −50.60 |
| request_09 | keeps the minimum | none | 75.35 |
| request_11 | leaves at least | reduce_to:event_989:665950 | −106,060.83 |
| request_16 | leaves at least | none | 16,610.89 |
| request_21 | leaves at least | stop:event_1815, reduce_to:event_1816:23.50 | 133.23 |

**Result.** request_09 is not at zero, and no sample is. The floor-binding hypothesis is rejected. (06 and 11 go
negative only because of the variable-spend level error in section "Known residual error" of residuals.md.)

**Decision.** No rule is fitted to one sample. Every full_payment explanation uses "This leaves at least {minimum}
available over the next 90 days"; request_09 is accepted as a miss. The earlier guessed rule ("keeps" when the user
accepts partial payment) is removed.

## Rejected hypotheses

Scripts and verdicts are indexed in `investigations/INDEX.md`.

| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| Monthly series are projected N calendar-month steps from their last occurrence | `investigations/sweep.py`, N = 2, 3, 4, with and without the income horizon, cap removed | N=3 and N=4 score **125**, identical to no cap: three steps land on day 83–92 and keep the rents the truth drops. N=2 scores 141 and loses request_03 and request_18. | **Rejected.** The adopted rule is the request month + 2 calendar months (147). |
| Rotating-description categories are pools whose spend should be projected as a per-day rate over the observed span | `investigations/residuals_pool.py`: data-driven series/pool classifier, 32 variants (full span, span + gap, trailing 90 days, complete months; request day in or out; unit rounding; threshold 0.5/0.8) | truth/ours ratio stdev 0.133 → 0.120 at best, range stays 0.82–1.31, within-5% 11 → at most 10, zero exact, 4 samples worse | **Rejected before tuning**, as the test required. The classifier's split is real; the rate model is not the truth's estimator. |
| The safe-amount error is a mechanical offset (rounding, window boundary, single term) | `investigations/residuals.py` | mixed sign, correct binding day, no term match, no rounding gain | **Rejected** |
| The truth's estimate is a shared rounded statistic with ±1 occurrence | `investigations/residuals_decomp.py` | 0 of 7 IDR/INR samples decompose | **Rejected** |
| The lone "keeps the … minimum" full-payment wording (request_09) marks a binding floor | trough − minimum under truth's plan for 6 full_payment samples | request_09 at +75.35, and no sample at 0 | **Rejected**; see "Full-payment wording" above |

## Where the binding day falls, and why the horizon rarely moves the safe amount

Binding day = the argmin of projected headroom under the current configuration. Offsets from `request_date`:

| set | 6–11 days | ≤ 15 days | ≥ 60 days |
|---|---:|---:|---:|
| 25 samples | 17 | 19 | 5 (request_05, 09, 10, 12, 13) |
| 250 evaluation requests | 174 | 188 | 56 |

Most users bind in the week or so before their next salary, well inside any horizon being debated. The monthly-horizon
choice can only move `amount_safe_to_pay` for users who bind late, typically with no projected income:
* samples: the safe amount differs on 4/25 between the calendar rule and no cap (request_05, 09, 10, 12);
* evaluation requests: 16/250.

Decision fields are more exposed than amounts, because the earliest full-payment date looks past the binding day:
4/25 samples (request_08, 09, 12, 13) and 21/250 evaluation rows change between the calendar rule and no cap.

**request_08 check.** The 147 tie between `calendar_months=3` and the 82-day window does not hide a loss plus a
compensating gain. The two configurations differ in 0 cells on all 25 samples and all 250 evaluation requests.
request_08 is wait / 2025-04-15 / affordable_later under both, matching truth. Only with the cap removed entirely does
it flip, to not_recommended.

## Known residual error

`amount_safe_to_pay` is exact on 4/25 and within 5% on 14/25. The ground truth appears to use per-category
spend estimates that differ slightly from any history statistic (implied deductions are whole units), so
exact cents are not recoverable from the data. Decision fields are far less sensitive to this noise.
