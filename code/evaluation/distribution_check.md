# Distribution check: 250 evaluation predictions vs the 25 samples

Purpose: before submitting, see whether the prediction mix on the hidden set departs from what the samples show.
"Sample truth CI" is the Wilson 95% interval for the sample proportion (n = 25), so only large departures can be
flagged. `output.csv` is compared with sample truth and with our own predictions on the samples.

## Output fields

| Field value | Sample truth | 95% CI | Our sample preds | Eval preds (250) | Flag |
|---|---:|---|---:|---:|---|
| affordable_now | 3 (12%) | 4–30% | 4 (16%) | 62 (25%) | inside; highest-drift status |
| affordable_with_plan | 9 (36%) | 20–55% | 7 (28%) | 55 (22%) | inside |
| affordable_later | 6 (24%) | 11–43% | 7 (28%) | 62 (25%) | inside |
| not_affordable | 7 (28%) | 14–48% | 7 (28%) | 71 (28%) | inside |
| full_payment | 6 (24%) | 11–43% | 5 (20%) | 69 (28%) | inside |
| partial_payment | 1 (4%) | 1–20% | 1 (4%) | 10 (4%) | inside |
| installments | 5 (20%) | 9–39% | 5 (20%) | 38 (15%) | inside |
| wait | 6 (24%) | 11–43% | 7 (28%) | 62 (25%) | inside |
| not_recommended | 7 (28%) | 14–48% | 7 (28%) | 71 (28%) | inside |
| **spending changes used** | **3 (12%)** | **4–30%** | **1 (4%)** | **7 (3%)** | **OUTSIDE** |
| safe amount capped at the request | 4 (16%) | 6–35% | 5 (20%) | 83 (33%) | inside, near the upper bound |
| safe amount = 0 | 0 (0%) | 0–13% | 0 | 1 (0.4%) | inside |
| binding day ≥ 60 days out | 5 (20%) | 9–39% | 5 (20%) | 56 (22%) | inside |
| salary projection stopped by an "employment/contract ended" message | 1 (4%) | 1–20% | 1 (4%) | 12 (5%) | inside |

## Input mix (what differs between the two sets)

| Input | Samples | Evaluation |
|---|---|---|
| currency USD | 1 (4%) | 39 (16%) |
| currency EUR | 8 (32%) | 54 (22%) |
| allows_partial_payment = false | 13 (52%) | 170 (68%) |
| methods = full + partial | 2 (8%) | 38 (15%) |
| methods = full + partial + installments | 5 (20%) | 23 (9%) |
| methods = partial only | 3 (12%) | 16 (6%) |
| request dated after the 12th of its month | 0 | 3 |

## Flags to act on or accept

1. **Spending changes are under-recommended, and this generalizes.**
   * **On the samples:** truth uses a spending change in 3/25 samples; we produce 1/25. We miss request_06 (we
     recommend waiting) and request_21 (we find it safe without changes).
   * **On the eval set:** we recommend changes on 7/250 (3%), below the samples' 95% interval.
   * **Cause:** a spending change only helps when full payment today is a near miss. Our variable-spend estimate
     errs in both directions (`residuals.md`), and small shortfalls are exactly where that error decides the outcome.
   * **Expected cost on the hidden set:** if the samples' rate holds, 20–30 evaluation rows should carry a change and
     we emit 7. Each missed row usually costs status, method, plan, changes and explanation together.
2. **More capped safe amounts and affordable_now.**
   * 33% of eval rows are capped, against 16–20% on samples; affordable_now is 25% against 12–16%.
   * Both are inside the sample interval, but they move together.
   * The input mix explains part of it: more full-payment-accepting users, and fewer partial-only users.
   * It is still the direction a too-low spend estimate would push, so it is worth watching, not proof of an error.
3. **USD is barely calibrated.** 39 evaluation requests are in USD against 1 sample (request_21, itself a miss). USD
   users with foreign-currency payroll rely on dated FX conversion that the samples barely exercise.
4. **Three late-month requests** (day > 12) are the only rows where the calendar-month horizon rule and the old
   82-day constant could diverge. They produce identical output today.

Everything else sits well inside the sample ranges.
