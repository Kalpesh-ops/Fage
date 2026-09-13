# amount_safe_to_pay residual investigation (25 public samples)

Analysis only: `python code/evaluation/investigations/residuals.py`. Same evidence + forecast path as `main.py` (offline, cached image amounts, current PARAMS). Residual = truth − our raw headroom (balance − minimum at the binding day, before the cap at `requested_amount`). Positive residual = truth leaves **more** money than we do (we over-deduct). Binding day = argmin of daily headroom; offset = days after `request_date`.

## 1. Table

| request | cur | request_date | predicted | truth | residual | resid % of truth | binding day (offset) |
|---|---|---|---:|---:|---:|---:|---|
| request_01 | ZAR | 2024-03-03 | 25,256.00 | 25,256.00 | capped |  | 2024-03-13 (+10) |
| request_02 | IDR | 2025-08-05 | 18,336,765.49 | 17,229,139.20 | -1,107,626.29 | -6.4% | 2025-08-13 (+8) |
| request_03 | IDR | 2019-09-03 | 971,737.00 | 873,000.00 | -98,737.00 | -11.3% | 2019-09-14 (+11) |
| request_04 | IDR | 2024-06-04 | 10,609,286.07 | 8,401,800.00 | -2,207,486.07 | -26.3% | 2024-06-13 (+9) |
| request_05 | ZAR | 2025-11-06 | 32.81 | 737.00 | 704.19 | 95.5% | 2026-02-04 (+90) |
| request_06 | EUR | 2026-01-03 | 550.80 | 603.30 | 52.50 | 8.7% | 2026-01-13 (+10) |
| request_07 | INR | 2024-09-05 | 86,237.22 | 87,170.56 | 933.34 | 1.1% | 2024-09-20 (+15) |
| request_08 | EUR | 2025-02-07 | 285.20 | 284.57 | -0.63 | -0.2% | 2025-02-13 (+6) |
| request_09 | EUR | 2026-07-04 | 166.61 | 166.61 | capped |  | 2026-09-25 (+83) |
| request_10 | INR | 2024-12-06 | 27,733.57 | 12,700.00 | -15,033.57 | -118.4% | 2025-03-06 (+90) |
| request_11 | IDR | 2025-05-03 | 12,319,866.62 | 12,510,645.00 | 190,778.38 | 1.5% | 2025-05-14 (+11) |
| request_12 | ZAR | 2026-04-05 | 65,164.00 | 65,164.00 | capped |  | 2026-06-26 (+82) |
| request_13 | EUR | 2024-03-07 | 490.78 | 433.40 | -57.38 | -13.2% | 2024-05-14 (+68) |
| request_14 | EUR | 2025-08-04 | 616.29 | 597.74 | -18.55 | -3.1% | 2025-08-14 (+10) |
| request_15 | EUR | 2026-01-06 | 65.19 | 83.05 | 17.86 | 21.5% | 2026-01-14 (+8) |
| request_16 | INR | 2023-08-12 | 122,500.00 | 122,500.00 | capped |  | 2023-09-14 (+33) |
| request_17 | INR | 2026-03-01 | 240,640.31 | 243,849.58 | 3,209.27 | 1.3% | 2026-03-14 (+13) |
| request_18 | EUR | 2026-07-07 | 546.05 | 462.00 | -84.05 | -18.2% | 2026-07-14 (+7) |
| request_19 | INR | 2024-09-04 | 30,022.77 | 28,820.00 | -1,202.77 | -4.2% | 2024-09-14 (+10) |
| request_20 | INR | 2026-02-07 | 8,851.68 | 5,400.00 | -3,451.68 | -63.9% | 2026-02-13 (+6) |
| request_21 | USD | 2026-04-03 | 1,574.40 | 1,543.35 | -129.78 | -8.4% | 2026-04-12 (+9) |
| request_22 | EUR | 2024-12-05 | 477.75 | 475.46 | -2.29 | -0.5% | 2024-12-14 (+9) |
| request_23 | ZAR | 2025-05-07 | 10,092.65 | 9,152.00 | -940.65 | -10.3% | 2025-05-14 (+7) |
| request_24 | INR | 2026-01-04 | 13,539.29 | 13,420.00 | -119.29 | -0.9% | 2026-01-13 (+9) |
| request_25 | IDR | 2024-03-06 | 1,410,760.78 | 1,425,000.00 | 14,239.22 | 1.0% | 2024-03-14 (+8) |

## 2. Sign

Uncapped samples: 21. Truth higher (we over-deduct): 7 (05, 06, 07, 11, 15, 17, 25). Truth lower (we under-deduct): 14 (02, 03, 04, 08, 10, 13, 14, 18, 19, 20, 21, 22, 23, 24). Exact: 0.

Binding-day offsets for uncapped samples: 02:+8, 03:+11, 04:+9, 05:+90, 06:+10, 07:+15, 08:+6, 10:+90, 11:+11, 13:+68, 14:+10, 15:+8, 17:+13, 18:+7, 19:+10, 20:+6, 21:+9, 22:+9, 23:+7, 24:+9, 25:+8

## 3. Ledger search for |residual|

Match = single event amount, projected series amount, or history min/max/last, times ½, 1, 2 or 3, within max(1 unit, 0.5%).

- **request_02** residual -1,107,626.29 IDR: event event_111 Shared storage plan (cloud_storage, settled, 2025-03-13) 369550 x3x; event event_119 Shared storage plan (cloud_storage, settled, 2025-04-13) 369550 x3x; event event_127 Shared storage plan (cloud_storage, settled, 2025-05-13) 369550 x3x; event event_135 Shared storage plan (cloud_storage, settled, 2025-06-13) 369550 x3x; event event_143 Shared storage plan (cloud_storage, settled, 2025-07-13) 369550 x3x; event event_158 Grocery delivery (groceries, settled, 2025-06-20) 2222527.88 xhalf
- **request_03** residual -98,737.00 IDR: no single-term match
- **request_04** residual -2,207,486.07 IDR: no single-term match
- **request_05** residual 704.19 ZAR: event event_384 Municipal utilities (utilities, settled, 2025-09-06) 706.37 x1x; event event_436 Metro and bus fares (transport, settled, 2025-10-15) 352.46 x2x
- **request_06** residual 52.50 EUR: event event_442 Vehicle insurance premium (insurance, settled, 2025-08-08) 26 x2x; event event_449 Water and power payment (utilities, settled, 2025-09-07) 52.62 x1x; event event_450 Vehicle insurance premium (insurance, settled, 2025-09-08) 26 x2x; event event_458 Vehicle insurance premium (insurance, settled, 2025-10-08) 26 x2x; event event_466 Vehicle insurance premium (insurance, settled, 2025-11-08) 26 x2x; event event_473 Water and power payment (utilities, settled, 2025-12-07) 51.86 x1x
- **request_07** residual 933.34 INR: no single-term match
- **request_08** residual -0.63 EUR: no single-term match
- **request_10** residual -15,033.57 INR: event event_872 Local taxi (transport, settled, 2024-07-19) 7530.3 x2x; event event_880 Local taxi (transport, settled, 2024-09-13) 5018.36 x3x; event event_889 Metro and bus fares (transport, settled, 2024-11-15) 4990.01 x3x
- **request_11** residual 190,778.38 IDR: no single-term match
- **request_13** residual -57.38 EUR: event event_1059 Music subscription (music_subscription, settled, 2023-10-11) 29 x2x; event event_1067 Music subscription (music_subscription, settled, 2023-11-11) 29 x2x; event event_1075 Music subscription (music_subscription, settled, 2023-12-11) 29 x2x; event event_1083 Music subscription (music_subscription, settled, 2024-01-11) 29 x2x; event event_1090 Music subscription (music_subscription, settled, 2024-02-11) 29 x2x; event event_1097 Fresh food shop (groceries, settled, 2023-09-19) 114.9 xhalf
- **request_14** residual -18.55 EUR: event event_1229 Parking and tolls (transport, settled, 2025-03-10) 37.65 xhalf
- **request_15** residual 17.86 EUR: event event_1305 Metro and bus fares (transport, settled, 2025-09-03) 37.01 xhalf; event event_1307 Commuter pass (transport, settled, 2025-09-17) 35.61 xhalf; event event_1313 Fuel refill (transport, settled, 2025-10-29) 34.86 xhalf; event event_1316 Ride-hailing trip (transport, settled, 2025-11-19) 36.7 xhalf; event event_1320 Metro and bus fares (transport, settled, 2025-12-17) 36.86 xhalf; event event_1328 Takeaway order (dining, settled, 2025-09-20) 36.23 xhalf
- **request_17** residual 3,209.27 INR: event event_1513 Local taxi (transport, settled, 2025-11-08) 6420.35 xhalf; event event_1523 Rail pass (transport, settled, 2026-01-17) 6406.38 xhalf
- **request_18** residual -84.05 EUR: event event_1548 Building maintenance payment (housing, settled, 2026-02-04) 167 xhalf; event event_1554 Building maintenance payment (housing, settled, 2026-03-04) 167 xhalf; event event_1560 Building maintenance payment (housing, settled, 2026-04-04) 167 xhalf; event event_1566 Building maintenance payment (housing, settled, 2026-05-04) 167 xhalf; event event_1572 Building maintenance payment (housing, settled, 2026-06-04) 167 xhalf; event event_1577 Building maintenance payment (housing, settled, 2026-07-04) 167 xhalf
- **request_19** residual -1,202.77 INR: no single-term match
- **request_20** residual -3,451.68 INR: no single-term match
- **request_21** residual -129.78 USD: no single-term match
- **request_22** residual -2.29 EUR: event event_1862 Music service subscription (music_subscription, settled, 2024-07-12) 6 xhalf; event event_1863 Food delivery membership (delivery_membership, settled, 2024-07-14) 5 xhalf; event event_1869 Music service subscription (music_subscription, settled, 2024-08-12) 6 xhalf; event event_1870 Food delivery membership (delivery_membership, settled, 2024-08-14) 5 xhalf; event event_1876 Music service subscription (music_subscription, settled, 2024-09-12) 6 xhalf; event event_1877 Food delivery membership (delivery_membership, settled, 2024-09-14) 5 xhalf
- **request_23** residual -940.65 ZAR: no single-term match
- **request_24** residual -119.29 INR: no single-term match
- **request_25** residual 14,239.22 IDR: no single-term match
- **request_01**: truth capped at requested amount; our raw headroom 30,241.27 (>= request: True)
- **request_09**: truth capped at requested amount; our raw headroom 241.96 (>= request: True)
- **request_12**: truth capped at requested amount; our raw headroom 72,162.23 (>= request: True)
- **request_16**: truth capped at requested amount; our raw headroom 139,110.89 (>= request: True)

## 4. Backed-out binding day

`exact days` = days whose headroom equals truth; `window end` = first window end at which the running minimum equals truth; `window start` = first start day whose suffix minimum equals truth.

| request | our binding day | exact-match days | closest day (gap) | window end giving truth | window start giving truth |
|---|---|---|---|---|---|
| request_02 | 2025-08-13 | none | 2025-08-13 (1,107,626.29) | none | none |
| request_03 | 2019-09-14 | none | 2019-09-14 (98,737.00) | none | none |
| request_04 | 2024-06-13 | none | 2024-06-13 (2,207,486.07) | none | none |
| request_05 | 2026-02-04 | none | 2026-02-03 (-289.85) | none | none |
| request_06 | 2026-01-13 | none | 2026-01-11 (20.48) | none | none |
| request_07 | 2024-09-20 | none | 2024-09-20 (-933.34) | none | none |
| request_08 | 2025-02-13 | 2025-02-13, 2025-02-14 | 2025-02-13 (0.63) | 2025-02-13 | 2025-02-07 |
| request_10 | 2025-03-06 | none | 2025-03-06 (15,033.57) | none | none |
| request_11 | 2025-05-14 | none | 2025-05-14 (-190,778.38) | none | none |
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
| request_25 | 2024-03-14 | none | 2024-03-14 (-14,239.22) | none | none |

## 5. Rounding re-score (exact matches out of 25)

| rounding | exact |
|---|---:|
| final value: as computed (2dp half-up) | 4 |
| final value: floor 2dp | 4 |
| final value: floor integer | 4 |
| final value: round half-up integer | 4 |
| final value: currency (IDR 100, INR/ZAR 1, EUR/USD 0.01) floor | 4 |
| per-flow ceil integer (applied to every projected recurring amount) | 4 |
| per-flow round integer (applied to every projected recurring amount) | 4 |
| per-flow floor integer (applied to every projected recurring amount) | 5 |
