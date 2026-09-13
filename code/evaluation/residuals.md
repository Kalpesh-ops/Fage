# amount_safe_to_pay residual investigation

Scope: the 25 public samples, forecaster as it stood during the investigation (`monthly_window_days=82`,
`skip_request_day_periodic=True`, mean estimator, cached image amounts). No solver code was changed during it.

> Update: the 82-day window was later replaced by the calendar-month rule (request month + 2 months; see
> calibration.md, "Monthly horizon: rule vs constant"). Output is byte-identical on all 25 samples and 250 requests, so
> every number below still holds. Section 7 is only partly resolved. The calendar-month rule names a mechanism for
> *which* rents fall outside the horizon, but the samples cannot tell it apart from the 82-day constant. The
> opposite-sign residuals on request_05 and request_10 remain estimator error either way.

Reproduce:

```bash
python code/evaluation/investigations/residuals.py         # table, sign, ledger search, backed-out binding day, rounding -> residuals_data.md
python code/evaluation/investigations/residuals_deep.py    # fixed/estimated decomposition, fractional-part test, subset search, estimator grid -> residuals_deep_data.md
python code/evaluation/investigations/residuals_decomp.py  # exact integer decomposition search -> residuals_decomp_data.md
```

Definitions: **headroom** = projected balance − `minimum_balance_to_keep`. **Binding day** = argmin of daily headroom.
**Residual** = truth − our raw headroom on the binding day (before capping at `requested_amount`). Positive residual
means truth leaves more money, i.e. we deduct too much.

## Short answer

The premise doesn't hold. This is not one small mechanical offset.

* **No rounding fixes it.** Eight rounding modes, applied to the final value or to every projected amount, give 4 or
  5 exact matches out of 25, the same as today.
* **It isn't a window-boundary slip.** Our binding day is the right day. In 16 of 21 uncapped samples the day whose
  headroom is closest to truth is our binding day. No shift of the window start or end reproduces truth, except for
  two samples that are already within 3 units.
* **It isn't one missing or double-counted term.** Residuals go both ways (14 under-deduct, 7 over-deduct). Only 2 of
  21 match a combination of up to 3 nearby projected occurrences, and even those are approximate (within 0.3%), not
  exact.
* **The error is in the estimated terms: variable and varying-amount spend.** The fixed terms (constant-amount
  series, pending, scheduled, image amounts) look right. Evidence: the fractional part of the truth's deduction equals
  the fractional part of our fixed terms in 20 of 21 samples. The truth's estimated terms are whole currency units
  (IDR in hundreds), while their size runs from 0.82× to 1.40× ours. No single history statistic, with any rounding
  and a ±1 occurrence shift per series, reproduces the truth exactly for any IDR or INR sample.
* **"14/25 within 5%" flatters the result.** In relative terms the misses reach −26% (request_04), −64% (request_20)
  and −118% (request_10), because a small safe amount amplifies an absolute error.

## 1. Residual table

| request | cur | request_date | predicted | truth | residual | % of truth | binding day (offset) |
|---|---|---|---:|---:|---:|---:|---|
| request_01 | ZAR | 2024-03-03 | 25,256.00 | 25,256.00 | capped | | 2024-03-13 (+10) |
| request_02 | IDR | 2025-08-05 | 18,336,765.49 | 17,229,139.20 | −1,107,626.29 | −6.4% | 2025-08-13 (+8) |
| request_03 | IDR | 2019-09-03 | 971,737.00 | 873,000.00 | −98,737.00 | −11.3% | 2019-09-14 (+11) |
| request_04 | IDR | 2024-06-04 | 10,609,286.07 | 8,401,800.00 | −2,207,486.07 | −26.3% | 2024-06-13 (+9) |
| request_05 | ZAR | 2025-11-06 | 32.81 | 737.00 | 704.19 | 95.5% | 2026-02-04 (+90) |
| request_06 | EUR | 2026-01-03 | 550.80 | 603.30 | 52.50 | 8.7% | 2026-01-13 (+10) |
| request_07 | INR | 2024-09-05 | 86,237.22 | 87,170.56 | 933.34 | 1.1% | 2024-09-20 (+15) |
| request_08 | EUR | 2025-02-07 | 285.20 | 284.57 | −0.63 | −0.2% | 2025-02-13 (+6) |
| request_09 | EUR | 2026-07-04 | 166.61 | 166.61 | capped | | 2026-09-25 (+83) |
| request_10 | INR | 2024-12-06 | 27,733.57 | 12,700.00 | −15,033.57 | −118.4% | 2025-03-06 (+90) |
| request_11 | IDR | 2025-05-03 | 12,319,866.62 | 12,510,645.00 | 190,778.38 | 1.5% | 2025-05-14 (+11) |
| request_12 | ZAR | 2026-04-05 | 65,164.00 | 65,164.00 | capped | | 2026-06-26 (+82) |
| request_13 | EUR | 2024-03-07 | 490.78 | 433.40 | −57.38 | −13.2% | 2024-05-14 (+68) |
| request_14 | EUR | 2025-08-04 | 616.29 | 597.74 | −18.55 | −3.1% | 2025-08-14 (+10) |
| request_15 | EUR | 2026-01-06 | 65.19 | 83.05 | 17.86 | 21.5% | 2026-01-14 (+8) |
| request_16 | INR | 2023-08-12 | 122,500.00 | 122,500.00 | capped | | 2023-09-14 (+33) |
| request_17 | INR | 2026-03-01 | 240,640.31 | 243,849.58 | 3,209.27 | 1.3% | 2026-03-14 (+13) |
| request_18 | EUR | 2026-07-07 | 546.05 | 462.00 | −84.05 | −18.2% | 2026-07-14 (+7) |
| request_19 | INR | 2024-09-04 | 30,022.77 | 28,820.00 | −1,202.77 | −4.2% | 2024-09-14 (+10) |
| request_20 | INR | 2026-02-07 | 8,851.68 | 5,400.00 | −3,451.68 | −63.9% | 2026-02-13 (+6) |
| request_21 | USD | 2026-04-03 | 1,574.40 | 1,543.35 | −129.78 | −8.4% | 2026-04-12 (+9) |
| request_22 | EUR | 2024-12-05 | 477.75 | 475.46 | −2.29 | −0.5% | 2024-12-14 (+9) |
| request_23 | ZAR | 2025-05-07 | 10,092.65 | 9,152.00 | −940.65 | −10.3% | 2025-05-14 (+7) |
| request_24 | INR | 2026-01-04 | 13,539.29 | 13,420.00 | −119.29 | −0.9% | 2026-01-13 (+9) |
| request_25 | IDR | 2024-03-06 | 1,410,760.78 | 1,425,000.00 | 14,239.22 | 1.0% | 2024-03-14 (+8) |

Four samples are capped (truth equals the requested amount), and our raw headroom also exceeds the request for all
four. request_21's "predicted" value is capped too: raw headroom 1,673.13, request 1,574.40.

## 2. Is the sign consistent?

No. Of 21 uncapped samples, 14 are negative (we under-deduct) and 7 are positive (we over-deduct).

The imbalance does have a shape. The largest under-deductions (02, 04, 18, 20, 21, 23) all bind 6–9 days after the
request, just before a salary. Over-deductions come from mixed situations: two long horizons (05 at +90, 13 at +68,
though 13 is negative) and a few short ones (06, 15, 11, 25). No single term would produce both signs.

## 3. Ledger search for the residual

For each residual I searched every event amount, every projected series amount, and the history min/max/last. Each
was tested at ½×, 1×, 2× and 3×, within max(1 unit, 0.5%). I also searched combinations of up to 3 projected
occurrences within ±10 days of the binding day, plus the request-day occurrences we deliberately skip.

* **No exact match anywhere.** The hits listed in `investigations/residuals_data.md` are coincidences of tolerance. For example,
  request_02's residual of 1,107,626 is close to 3 × cloud storage 369,550 = 1,108,650, but cloud storage occurs once
  before that binding day.
* **Only two near-matches from combinations:**
  * request_04: music + delivery + one grocery occurrence = 2,209,124 vs 2,207,486 (0.07% off).
  * request_21: streaming + one grocery occurrence = 130.63 vs 129.78.

  Neither is exact, and each needs a different mechanism, so I read them as coincidence too.
* **Not one grocery occurrence either.** No residual equals one occurrence of a weekly or biweekly series, so "off by
  one occurrence" is not what's happening.

## 4. Backed-out binding day

For each sample I tested three things:
1. Which day's headroom equals truth.
2. Which window end makes the running minimum equal truth.
3. Which window start makes the suffix minimum equal truth.

| request | our binding day | day(s) with headroom = truth | closest day (gap) | window end giving truth | window start giving truth |
|---|---|---|---|---|---|
| request_02 | 2025-08-13 | none | 2025-08-13 (1,107,626.29) | none | none |
| request_03 | 2019-09-14 | none | 2019-09-14 (98,737.00) | none | none |
| request_04 | 2024-06-13 | none | 2024-06-13 (2,207,486.07) | none | none |
| request_05 | 2026-02-04 | none | 2026-02-03 (−289.85) | none | none |
| request_06 | 2026-01-13 | none | 2026-01-11 (20.48) | none | none |
| request_07 | 2024-09-20 | none | 2024-09-20 (−933.34) | none | none |
| request_08 | 2025-02-13 | 2025-02-13, 2025-02-14 | 2025-02-13 (0.63) | 2025-02-13 | 2025-02-07 |
| request_10 | 2025-03-06 | none | 2025-03-06 (15,033.57) | none | none |
| request_11 | 2025-05-14 | none | 2025-05-14 (−190,778.38) | none | none |
| request_13 | 2024-05-14 | none | 2024-05-14 (57.38) | none | none |
| request_14 | 2025-08-14 | none | 2025-08-14 (18.55) | none | none |
| request_15 | 2026-01-14 | none | 2026-01-13 (13.90) | none | none |
| request_17 | 2026-03-14 | none | 2026-03-13 (2,068.77) | none | none |
| request_18 | 2026-07-14 | none | 2026-07-14 (84.05) | none | none |
| request_19 | 2024-09-14 | none | 2024-09-14 (1,202.77) | none | none |
| request_20 | 2026-02-13 | none | 2026-02-13 (3,451.68) | none | none |
| request_21 | 2026-04-12 | none | 2026-04-12 (129.78) | none | none |
| request_22 | 2024-12-14 | 2024-12-14 | 2024-12-14 (2.29) | 2024-12-14 | 2024-12-05 |
| request_23 | 2025-05-14 | none | 2025-05-14 (940.65) | none | none |
| request_24 | 2026-01-13 | none | 2026-01-13 (119.29) | none | none |
| request_25 | 2024-03-14 | none | 2024-03-14 (−14,239.22) | none | none |

**Read:** the closest day is our binding day in 16 of 21 samples. Where it differs (05, 06, 15, 17), it is 1–2 days
earlier. All four are over-deduction cases, and a day earlier only moves the value partway toward truth. The level is
wrong, not the day. This rules out an inclusive/exclusive boundary at either end.

## 5. Rounding re-score (exact matches out of 25)

| rounding | exact |
|---|---:|
| final value, as computed (2dp half-up) | 4 |
| final value, floor to 2dp | 4 |
| final value, floor to integer | 4 |
| final value, round half-up to integer | 4 |
| final value, currency-specific floor (IDR 100, INR/ZAR 1, EUR/USD 0.01) | 4 |
| every projected recurring amount, ceil to integer | 4 |
| every projected recurring amount, round to integer | 4 |
| every projected recurring amount, floor to integer | 5 |

The single extra exact match under per-flow floor is request_08, which was already off by only 0.63.

## 6. What the truth's arithmetic reveals

Split our deduction up to the binding day into two parts:
* **fixed:** pending, scheduled, image-filled, and constant-amount series;
* **estimated:** series whose history amounts vary, projected at our mean.

Then back out `truth est = D_truth − fixed + income`.

| request | cur | fixed | est ours | truth est | truth / ours | frac(D truth) | frac(fixed − income) |
|---|---|---:|---:|---:|---:|---:|---:|
| request_02 | IDR | 6,193,050.00 | 6,695,673.71 | 7,803,300.00 | 1.165 | .00 | .00 |
| request_03 | IDR | 1,373,700.00 | 796,163.00 | 894,900.00 | 1.124 | .00 | .00 |
| request_04 | IDR | 3,441,850.00 | 7,469,213.93 | 9,676,700.00 | 1.296 | .00 | .00 |
| request_05 | ZAR | 15,709.10 | 17,633.19 | 16,929.00 | 0.960 | .10 | .10 |
| request_06 | EUR | 304.10 | 287.50 | 235.00 | 0.817 | .10 | .10 |
| request_07 | INR | 16,655.00 | 23,053.34 | 22,120.00 | 0.960 | .00 | .00 |
| request_08 | EUR | 304.00 | 147.37 | 148.00 | 1.004 | .00 | .00 |
| request_10 | INR | 166,865.00 | 330,156.43 | 345,190.00 | 1.046 | .00 | .00 |
| request_11 | IDR | 7,547,750.00 | 9,523,578.38 | 9,332,800.00 | 0.980 | .00 | .00 |
| request_13 | EUR | 1,578.20 | 2,107.62 | 2,165.00 | 1.027 | .12 | .12 (income 2,687.08) |
| request_14 | EUR | 590.00 | 525.45 | 544.00 | 1.035 | .00 | .00 |
| request_15 | EUR | 254.00 | 250.86 | 233.00 | 0.929 | .00 | .00 |
| request_17 | INR | 97,190.00 | 46,449.27 | 43,240.00 | 0.931 | .00 | .00 |
| request_18 | EUR | 136.00 | 403.95 | 488.00 | 1.208 | .00 | .00 |
| request_19 | INR | 48,345.00 | 28,377.23 | 29,580.00 | 1.042 | .00 | .00 |
| request_20 | INR | 14,397.05 | 14,860.32 | 18,312.00 | 1.232 | .05 | .05 |
| request_21 | USD | 111.00 | 327.22 | 457.00 | 1.397 | .00 | .00 |
| request_22 | EUR | 71.00 | 83.71 | 86.00 | 1.027 | .00 | .00 |
| request_23 | ZAR | 7,701.10 | 7,164.15 | 8,104.80 | 1.131 | .90 | .10 |
| request_24 | INR | 5,895.00 | 14,610.71 | 14,730.00 | 1.008 | .00 | .00 |
| request_25 | IDR | 1,604,550.00 | 5,668,639.22 | 5,654,400.00 | 0.997 | .00 | .00 |

What this shows:

1. **Our fixed terms match the truth.** The fractional part of the truth's deduction equals the fractional part of
   our fixed terms net of income in 20 of 21 samples. The cents come from rows like rent 254.10, the image amount
   822.05, and salaries 1,343.54 × 2. request_20 in particular confirms the image-extracted 822.05 (late amount) is
   what the truth used.
2. **The truth's estimated terms are whole units.** They are whole numbers in EUR/USD/INR/ZAR and multiples of 100 in
   IDR. So the ground truth rounds each spending estimate, but that rounding is worth at most about one unit per
   occurrence, far smaller than the residuals.
3. **request_23 is the one exception** (.90 vs .10). Dropping the pending pharmacy charge of 1,553.20 would make the
   fractions agree, but then its level residual would grow. That's unexplained; I would not generalise from one
   sample.
4. **The size of the estimated terms is where the error lives:** 0.82× to 1.40× ours, median about 1.03×.

**Exact decomposition test** (`investigations/residuals_decomp_data.md`). I searched for one shared statistic (mean, median, last,
max, min, mean of last 3 or 4), rounded to the currency unit (ceil, floor or half-up), with each series' occurrence
count shifted by −1/0/+1, and with pending kept or dropped.

* Only 10 of 21 samples reproduce the truth exactly under any combination.
* All 7 IDR and INR samples have zero solutions, and those are the only ones with enough digits to be discriminating.
* The EUR "solutions" are combinatorial noise. request_22 alone has 52 solutions and request_06 has 32, and no
  combination recurs across samples (the most common appears 3 times).

**Conclusion:** the truth does not estimate variable spend as a rounded history statistic of the series the way we
group and cadence them. Something differs in grouping or cadence. For example, per-description sub-series inside a
category, a different anchor for weekly or 10-day items, or an amount the data generator knew and we can only
approximate. The largest ratios (1.17–1.40) all sit in 6–9 day windows before a salary. In a window that short, one
more or one fewer occurrence of a large item swings the total a lot, but no ±1 occurrence shift with a shared
statistic lands exactly.

## 7. What this means for the 82-day cap

The cap was chosen because the truth appears to exclude rent falling on days 83–90 for the long-horizon users. The
residuals weaken that reading:

| request | horizon | rent at the end of the window | residual with cap | what truth needs |
|---|---|---|---:|---|
| request_05 | binds at +90, no income | 4,972 on day 88 (excluded by cap) | +704.19 (we still over-deduct) | rent excluded **and** 4% less estimated spend, or rent included and about 28% less |
| request_10 | binds at +90, no income | 69,100 on day 87 (excluded by cap) | −15,033.57 (we under-deduct) | rent excluded **and** 4.6% more estimated spend, or rent included and about 16% less |
| request_09 | capped (truth ≥ request) | 211.20 on day 90 | — | with rent included, headroom 30.76 vs 166.61 needed |
| request_12 | capped | 11,792 on day 87 | — | with rent included, headroom 60,370 vs 65,164 needed |

The two uncapped long-horizon samples err in **opposite** directions even with the cap in place. The two capped ones
only bound the truth from one side. Every one of them can be explained as "rent is included and our estimated spend
is too high over 90 days" just as well as "rent is excluded". So the cap is plausibly **absorbing estimator error on
the four long-horizon users rather than describing a real boundary**. It also changed request_08's decision (rent on
day 83 after a mid-April payment), so it's load-bearing for decisions, not only amounts.

Until the estimator is understood, the cap should be treated as a fitted parameter with 4–5 samples behind it, not a
rule.

## 8. Suggested next steps (not done)

1. **Re-run the decomposition with per-description sub-series** for groceries, transport and dining (grouping by
   description instead of category), and with cadence anchored on weekday rather than last date + gap. If the IDR/INR
   samples start decomposing exactly, that is the mechanism.
2. **Test a daily-rate model** (category spend per day × days to the binding day, rounded to the unit). On request_08
   by hand it gave 443 vs a truth of 452, worse than occurrences, but it is untested elsewhere.
3. **Only after 1–2, re-sweep `monthly_window_days` against 90.** If a better estimator makes the day-90 fit work,
   drop the cap.

## 9. Series-vs-pool hypothesis: tested, spread did not collapse (no forecaster change)

Reproduce: `python code/evaluation/investigations/residuals_pool.py` → `investigations/residuals_pool_data.md`.

**Hypothesis.** Categories whose spend arrives as many rotating one-off descriptions are pools, not series, and should
be projected as a per-day category spend rate over the observed history span. If this were the structural error, the
0.82–1.40 spread of truth/ours on the estimated component should collapse toward 1.0 before any tuning.

**Classifier (data-driven, no category list).** A category is a series when its most frequent description covers at
least a threshold share of its occurrences; otherwise it is a pool.
* The split is sharp. Pools have top share 0.15–0.38 with 5–8 distinct descriptions; every series has share 1.00.
* At both 0.5 and 0.8 it classifies groceries, transport and dining as pools and everything else (rent, utilities,
  loans, subscriptions, shopping, healthcare, …) as series. Only one sample user's dining changes class between the
  two thresholds.
* The observed span matches the brief: user_05 groceries last − first = 175 days.

**Variants tested** (32): threshold 0.5 or 0.8; rate basis per day over (last − first), per day over (last − first +
median gap), per day over the trailing 90 days, or complete calendar months; request day included or excluded;
per-category projection rounded to whole units or not.

| model | min | max | median | stdev | within 2% | within 5% | exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| current: occurrences at mean | 0.817 | 1.397 | 1.027 | 0.133 | 3 | 11 | 0 |
| best pool variant by stdev (span, request day included, no rounding) | 0.823 | 1.312 | 0.980 | 0.120 | 3 | 7 | 0 |
| best pool variant by within-2% (span, request day excluded) | 0.875 | 1.389 | 1.003–1.008 | 0.139 | 6 | 8 | 0 |
| best pool variant by within-5% (span + gap or complete months, included) | 0.832–0.846 | 1.349–1.351 | 1.014–1.017 | 0.125–0.132 | 4–5 | 10 | 0 |

**Read.**
* **No collapse.** The best stdev falls only from 0.133 to 0.120, and the range stays at 0.82–1.31.
* **The share within 5% of 1.0 goes down.** No pool variant beats the current model's 11 samples; the best manage 10.
* **No variant reproduces any sample exactly.**
* **Per sample the change is mixed, not directional:**
  * improves: request_03 1.12→1.05, 04 1.30→1.18, 10 1.05→1.00, 11 0.98→1.00, 21 1.40→1.15, 23 1.13→1.01;
  * gets worse: request_08 1.00→1.16, 20 1.23→1.31, 22 1.03→0.88, 25 1.00→0.87.
* **A pool rate cannot produce the short-window outliers.** Most samples bind 6–11 days after the request, and truth's
  estimated terms there are whole units. A pool rate is smooth, while whole-unit terms that swing ±20–40% in a week look
  like discrete occurrences with specific amounts.

**Conclusion.** The series/pool distinction is real in the data, but "pool = per-day rate" is not how the ground truth
estimates variable spend, so the hypothesis as stated is rejected. Per instruction nothing was tuned or implemented,
and the calendar-month horizon was not re-swept, since that step depended on a fixed estimator.

**Caveat.** Ratios use our current binding day. A pool model smooths spend, so it could move the binding day only on
long horizons (request_05, 10, 13). Those three land at 0.94, 1.00 and 0.98 under the span rate, which is not enough
on its own to rescue the hypothesis.
