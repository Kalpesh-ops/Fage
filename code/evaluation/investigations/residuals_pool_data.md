# Series vs pool diagnostic

Ratio = truth-implied estimated component / our estimated component, up to our binding day (21 uncapped samples). Current model: occurrences at mean amount for every varying series.

| model | min | max | median | stdev | within 2% | within 5% | exact |
|---|---:|---:|---:|---:|---:|---:|---:|
| current (occurrences) | 0.817 | 1.397 | 1.027 | 0.133 | 3 | 11 | 0 |
| pool thr=0.5 basis=span days=incl_request_day round=none | 0.823 | 1.312 | 0.980 | 0.120 | 3 | 7 | 0 |
| pool thr=0.5 basis=span days=incl_request_day round=unit | 0.823 | 1.312 | 0.979 | 0.120 | 3 | 7 | 0 |
| pool thr=0.8 basis=span days=incl_request_day round=none | 0.823 | 1.312 | 0.979 | 0.120 | 2 | 7 | 0 |
| pool thr=0.8 basis=span days=incl_request_day round=unit | 0.823 | 1.312 | 0.977 | 0.120 | 2 | 7 | 0 |
| pool thr=0.5 basis=trailing90 days=incl_request_day round=none | 0.846 | 1.348 | 1.045 | 0.125 | 2 | 9 | 0 |
| pool thr=0.8 basis=trailing90 days=incl_request_day round=none | 0.846 | 1.348 | 1.036 | 0.125 | 2 | 10 | 0 |
| pool thr=0.5 basis=span_plus_gap days=incl_request_day round=none | 0.846 | 1.351 | 1.018 | 0.125 | 4 | 10 | 0 |
| pool thr=0.5 basis=trailing90 days=incl_request_day round=unit | 0.846 | 1.348 | 1.045 | 0.125 | 2 | 9 | 0 |
| pool thr=0.8 basis=span_plus_gap days=incl_request_day round=none | 0.846 | 1.351 | 1.014 | 0.125 | 5 | 10 | 0 |
| pool thr=0.8 basis=trailing90 days=incl_request_day round=unit | 0.846 | 1.348 | 1.036 | 0.125 | 2 | 10 | 0 |
| pool thr=0.5 basis=span_plus_gap days=incl_request_day round=unit | 0.846 | 1.351 | 1.018 | 0.125 | 4 | 10 | 0 |
| pool thr=0.8 basis=span_plus_gap days=incl_request_day round=unit | 0.846 | 1.351 | 1.014 | 0.125 | 5 | 10 | 0 |
| pool thr=0.5 basis=complete_months days=incl_request_day round=none | 0.832 | 1.349 | 1.017 | 0.132 | 4 | 10 | 0 |
| pool thr=0.8 basis=complete_months days=incl_request_day round=none | 0.832 | 1.349 | 1.015 | 0.132 | 5 | 10 | 0 |
| pool thr=0.5 basis=complete_months days=incl_request_day round=unit | 0.831 | 1.348 | 1.017 | 0.132 | 4 | 10 | 0 |
| pool thr=0.8 basis=complete_months days=incl_request_day round=unit | 0.831 | 1.348 | 1.016 | 0.132 | 5 | 10 | 0 |
| pool thr=0.5 basis=span days=excl_request_day round=unit | 0.875 | 1.389 | 1.008 | 0.139 | 6 | 8 | 0 |
| pool thr=0.5 basis=span days=excl_request_day round=none | 0.876 | 1.390 | 1.008 | 0.139 | 6 | 8 | 0 |
| pool thr=0.8 basis=span days=excl_request_day round=unit | 0.875 | 1.389 | 1.003 | 0.140 | 6 | 8 | 0 |
| pool thr=0.8 basis=span days=excl_request_day round=none | 0.876 | 1.390 | 1.003 | 0.140 | 6 | 8 | 0 |
| pool thr=0.5 basis=trailing90 days=excl_request_day round=unit | 0.901 | 1.437 | 1.071 | 0.144 | 4 | 7 | 0 |
| pool thr=0.8 basis=trailing90 days=excl_request_day round=unit | 0.901 | 1.437 | 1.061 | 0.145 | 4 | 8 | 0 |
| pool thr=0.5 basis=span_plus_gap days=excl_request_day round=unit | 0.898 | 1.427 | 1.056 | 0.145 | 2 | 9 | 0 |
| pool thr=0.8 basis=span_plus_gap days=excl_request_day round=unit | 0.898 | 1.427 | 1.056 | 0.145 | 2 | 9 | 0 |
| pool thr=0.5 basis=span_plus_gap days=excl_request_day round=none | 0.899 | 1.427 | 1.056 | 0.146 | 2 | 9 | 0 |
| pool thr=0.8 basis=span_plus_gap days=excl_request_day round=none | 0.899 | 1.427 | 1.056 | 0.146 | 2 | 9 | 0 |
| pool thr=0.5 basis=trailing90 days=excl_request_day round=none | 0.899 | 1.450 | 1.071 | 0.146 | 4 | 7 | 0 |
| pool thr=0.8 basis=trailing90 days=excl_request_day round=none | 0.899 | 1.450 | 1.061 | 0.147 | 4 | 8 | 0 |
| pool thr=0.5 basis=complete_months days=excl_request_day round=unit | 0.888 | 1.465 | 1.059 | 0.154 | 3 | 8 | 0 |
| pool thr=0.5 basis=complete_months days=excl_request_day round=none | 0.885 | 1.469 | 1.059 | 0.154 | 4 | 8 | 0 |
| pool thr=0.8 basis=complete_months days=excl_request_day round=unit | 0.888 | 1.465 | 1.059 | 0.155 | 3 | 8 | 0 |
| pool thr=0.8 basis=complete_months days=excl_request_day round=none | 0.885 | 1.469 | 1.059 | 0.155 | 4 | 8 | 0 |

## Per-sample ratios: current vs best-spread pool variant (0.5, 'span', 'incl_request_day', 'none')

| request | cur | binding offset | pool categories (distinct descs / top share) | truth est | ours now | ratio now | pool est | ratio pool |
|---|---|---:|---|---:|---:|---:|---:|---:|
| request_02 | IDR | +8 | dining (7/0.33), groceries (8/0.22), transport (6/0.31) | 7,803,300.00 | 6,695,673.71 | 1.165 | 6,760,480.98 | 1.154 |
| request_03 | IDR | +11 | dining (5/0.22), groceries (7/0.22), transport (6/0.33) | 894,900.00 | 796,163.00 | 1.124 | 853,417.28 | 1.049 |
| request_04 | IDR | +9 | dining (7/0.23), groceries (8/0.23), transport (7/0.23) | 9,676,700.00 | 7,469,213.93 | 1.296 | 8,206,366.25 | 1.179 |
| request_05 | ZAR | +90 | groceries (8/0.15), transport (7/0.23) | 16,929.00 | 17,633.19 | 0.960 | 18,025.82 | 0.939 |
| request_06 | EUR | +10 | dining (8/0.24), groceries (8/0.22), transport (8/0.23) | 235.00 | 287.50 | 0.817 | 285.39 | 0.823 |
| request_07 | INR | +15 | dining (6/0.33), groceries (8/0.31), transport (5/0.33) | 22,120.00 | 23,053.34 | 0.960 | 23,440.96 | 0.944 |
| request_08 | EUR | +6 | dining (7/0.31), groceries (7/0.27), transport (7/0.23) | 148.00 | 147.37 | 1.004 | 127.93 | 1.157 |
| request_10 | INR | +90 | groceries (7/0.27), transport (8/0.24) | 345,190.00 | 330,156.43 | 1.046 | 344,983.49 | 1.001 |
| request_11 | IDR | +11 | dining (6/0.22), groceries (8/0.22), transport (5/0.31) | 9,332,800.00 | 9,523,578.38 | 0.980 | 9,348,308.20 | 0.998 |
| request_13 | EUR | +68 | dining (8/0.23), groceries (7/0.19), transport (8/0.19) | 2,165.00 | 2,107.62 | 1.027 | 2,210.56 | 0.979 |
| request_14 | EUR | +10 | groceries (8/0.19), transport (8/0.15) | 544.00 | 525.45 | 1.035 | 584.32 | 0.931 |
| request_15 | EUR | +8 | dining (7/0.23), groceries (8/0.24), transport (8/0.24) | 233.00 | 250.86 | 0.929 | 237.86 | 0.980 |
| request_17 | INR | +13 | dining (7/0.23), groceries (8/0.35), transport (8/0.19) | 43,240.00 | 46,449.27 | 0.931 | 45,697.36 | 0.946 |
| request_18 | EUR | +7 | dining (7/0.23), groceries (7/0.28), transport (8/0.38) | 488.00 | 403.95 | 1.208 | 425.97 | 1.146 |
| request_19 | INR | +10 | groceries (8/0.24), transport (6/0.23) | 29,580.00 | 28,377.23 | 1.042 | 31,032.51 | 0.953 |
| request_20 | INR | +6 | dining (6/0.33), groceries (7/0.22), transport (8/0.23) | 18,312.00 | 14,860.32 | 1.232 | 13,960.57 | 1.312 |
| request_21 | USD | +9 | dining (5/0.22), groceries (6/0.22), transport (6/0.22) | 457.00 | 327.22 | 1.397 | 398.91 | 1.146 |
| request_22 | EUR | +9 | dining (6/0.23), groceries (8/0.23), transport (8/0.20) | 86.00 | 83.71 | 1.027 | 98.13 | 0.876 |
| request_23 | ZAR | +7 | groceries (7/0.20), transport (6/0.31) | 8,104.80 | 7,164.15 | 1.131 | 8,044.13 | 1.008 |
| request_24 | INR | +9 | dining (8/0.15), groceries (6/0.33), transport (8/0.19) | 14,730.00 | 14,610.71 | 1.008 | 15,723.63 | 0.937 |
| request_25 | IDR | +8 | dining (8/0.24), groceries (8/0.22), transport (8/0.19) | 5,654,400.00 | 5,668,639.22 | 0.997 | 6,467,739.63 | 0.874 |

## Classifier on all sample users (threshold 0.5 and 0.8)

- thr=0.5: cloud_storage series=15; debt_repayment series=10; delivery_membership series=8; dining pool=20; dining series=1; education series=7; entertainment series=10; family_support series=4; groceries pool=25; gym series=4; healthcare series=8; housing series=4; insurance series=7; music_subscription series=9; rent series=21; shopping series=14; streaming series=9; transport pool=25; utilities series=25; work_expense series=1
- thr=0.8: cloud_storage series=15; debt_repayment series=10; delivery_membership series=8; dining pool=21; education series=7; entertainment series=10; family_support series=4; groceries pool=25; gym series=4; healthcare series=8; housing series=4; insurance series=7; music_subscription series=9; rent series=21; shopping series=14; streaming series=9; transport pool=25; utilities series=25; work_expense series=1
