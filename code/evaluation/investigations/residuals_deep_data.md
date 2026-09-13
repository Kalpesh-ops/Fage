# Deep residual analysis

## (a) Decomposition up to our binding day

D = total net deduction from balance to binding day. `fixed` = pending, scheduled, image-filled, constant-amount series; `estimated` = series whose history amounts vary (our mean). `truth est` = truth D − fixed − income (what the truth must have used for the estimated terms if everything else matches).

| request | cur | D ours | D truth | fixed | income | est ours | truth est | ratio | D truth frac | fixed frac |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| request_02 | IDR | 12,888,723.71 | 13,996,350.00 | 6,193,050.00 | 0.00 | 6,695,673.71 | 7,803,300.00 | 1.165 | 0.00 | 0.00 |
| request_03 | IDR | 2,169,863.00 | 2,268,600.00 | 1,373,700.00 | 0.00 | 796,163.00 | 894,900.00 | 1.124 | 0.00 | 0.00 |
| request_04 | IDR | 10,911,063.93 | 13,118,550.00 | 3,441,850.00 | 0.00 | 7,469,213.93 | 9,676,700.00 | 1.296 | 0.00 | 0.00 |
| request_05 | ZAR | 33,342.29 | 32,638.10 | 15,709.10 | 0.00 | 17,633.19 | 16,929.00 | 0.960 | 0.10 | 0.10 |
| request_06 | EUR | 591.60 | 539.10 | 304.10 | 0.00 | 287.50 | 235.00 | 0.817 | 0.10 | 0.10 |
| request_07 | INR | 39,708.34 | 38,775.00 | 16,655.00 | 0.00 | 23,053.34 | 22,120.00 | 0.960 | 0.00 | 0.00 |
| request_08 | EUR | 451.37 | 452.00 | 304.00 | 0.00 | 147.37 | 148.00 | 1.004 | 0.00 | 0.00 |
| request_10 | INR | 497,021.43 | 512,055.00 | 166,865.00 | 0.00 | 330,156.43 | 345,190.00 | 1.046 | 0.00 | 0.00 |
| request_11 | IDR | 17,071,328.38 | 16,880,550.00 | 7,547,750.00 | 0.00 | 9,523,578.38 | 9,332,800.00 | 0.980 | 0.00 | 0.00 |
| request_13 | EUR | 998.74 | 1,056.12 | 1,578.20 | 2,687.08 | 2,107.62 | 2,165.00 | 1.027 | 0.12 | 0.20 |
| request_14 | EUR | 1,115.45 | 1,134.00 | 590.00 | 0.00 | 525.45 | 544.00 | 1.035 | 0.00 | 0.00 |
| request_15 | EUR | 504.86 | 487.00 | 254.00 | 0.00 | 250.86 | 233.00 | 0.929 | 0.00 | 0.00 |
| request_17 | INR | 143,639.27 | 140,430.00 | 97,190.00 | 0.00 | 46,449.27 | 43,240.00 | 0.931 | 0.00 | 0.00 |
| request_18 | EUR | 539.95 | 624.00 | 136.00 | 0.00 | 403.95 | 488.00 | 1.208 | 0.00 | 0.00 |
| request_19 | INR | 76,722.23 | 77,925.00 | 48,345.00 | 0.00 | 28,377.23 | 29,580.00 | 1.042 | 0.00 | 0.00 |
| request_20 | INR | 29,257.37 | 32,709.05 | 14,397.05 | 0.00 | 14,860.32 | 18,312.00 | 1.232 | 0.05 | 0.05 |
| request_21 | USD | 438.22 | 568.00 | 111.00 | 0.00 | 327.22 | 457.00 | 1.397 | 0.00 | 0.00 |
| request_22 | EUR | 154.71 | 157.00 | 71.00 | 0.00 | 83.71 | 86.00 | 1.027 | 0.00 | 0.00 |
| request_23 | ZAR | 14,865.25 | 15,805.90 | 7,701.10 | 0.00 | 7,164.15 | 8,104.80 | 1.131 | 0.90 | 0.10 |
| request_24 | INR | 20,505.71 | 20,625.00 | 5,895.00 | 0.00 | 14,610.71 | 14,730.00 | 1.008 | 0.00 | 0.00 |
| request_25 | IDR | 7,273,189.22 | 7,258,950.00 | 1,604,550.00 | 0.00 | 5,668,639.22 | 5,654,400.00 | 0.997 | 0.00 | 0.00 |

Ratio summary (truth est / our est): 02:1.17, 03:1.12, 04:1.30, 05:0.96, 06:0.82, 07:0.96, 08:1.00, 10:1.05, 11:0.98, 13:1.03, 14:1.04, 15:0.93, 17:0.93, 18:1.21, 19:1.04, 20:1.23, 21:1.40, 22:1.03, 23:1.13, 24:1.01, 25:1.00

## (c) Subset search (≤3 terms within ±10 days of binding day, plus request-day occurrences we skip)

- **request_02** residual -1,107,626.29: no combination
- **request_03** residual -98,737.00: no combination
- **request_04** residual -2,207,486.07: out|music_subscription@2024-06-10(in) + out|delivery_membership@2024-06-12(in) + out|groceries@2024-06-08(in) = 2,209,124.48; out|music_subscription@2024-06-10(in) + out|delivery_membership@2024-06-12(in) + out|groceries@2024-06-15(after) = 2,209,124.48; out|music_subscription@2024-06-10(in) + out|delivery_membership@2024-06-12(in) + out|groceries@2024-06-22(after) = 2,209,124.48
- **request_05** residual 704.19: no combination
- **request_06** residual 52.50: out|insurance@2026-01-08(in) + out|transport@2026-01-08(in) = 52.98; out|insurance@2026-01-08(in) + out|transport@2026-01-13(in) = 52.98; out|insurance@2026-01-08(in) + out|transport@2026-01-18(after) = 52.98
- **request_07** residual 933.34: no combination
- **request_08** residual -0.63: no combination
- **request_10** residual -15,033.57: no combination
- **request_11** residual 190,778.38: no combination
- **request_13** residual -57.38: no combination
- **request_14** residual -18.55: no combination
- **request_15** residual 17.86: no combination
- **request_17** residual 3,209.27: no combination
- **request_18** residual -84.05: no combination
- **request_19** residual -1,202.77: no combination
- **request_20** residual -3,451.68: no combination
- **request_21** residual -129.78: out|streaming@2026-04-09(in) + out|groceries@2026-04-06(in) = 130.63; out|streaming@2026-04-09(in) + out|groceries@2026-04-16(after) = 130.63; out|streaming@2026-04-09(in) + out|dining@2026-04-17(after) = 130.44
- **request_22** residual -2.29: no combination
- **request_23** residual -940.65: no combination
- **request_24** residual -119.29: no combination
- **request_25** residual 14,239.22: no combination

## (d) Estimator statistic × rounding for varying series

| stat | rounding | exact (25) | within max(1 unit, 1%) |
|---|---|---:|---:|
| mean | ceil | 5 | 8 |
| last | floor | 5 | 7 |
| mean | none | 4 | 8 |
| mean | round | 4 | 8 |
| mean | floor | 4 | 8 |
| mean_last4 | ceil | 4 | 8 |
| last | none | 4 | 7 |
| last | round | 4 | 7 |
| last | ceil | 4 | 7 |
| mean_last4 | none | 4 | 7 |
| median | none | 4 | 6 |
| median | round | 4 | 6 |
| median | ceil | 4 | 6 |
| mean_last3 | none | 4 | 6 |
| mean_last3 | ceil | 4 | 6 |
| mean_last3 | floor | 4 | 6 |
| mean_last4 | round | 4 | 6 |
| mean_last4 | floor | 4 | 6 |
| mean_last8 | none | 4 | 6 |
| mean_last8 | round | 4 | 6 |
| mean_last8 | ceil | 4 | 6 |
| mean_last8 | floor | 4 | 6 |
| median | floor | 4 | 5 |
| mean_last3 | round | 4 | 5 |
| min | none | 4 | 4 |
| min | round | 4 | 4 |
| min | ceil | 4 | 4 |
| min | floor | 4 | 4 |
| max | none | 1 | 3 |
| max | round | 1 | 3 |
| max | ceil | 1 | 3 |
| max | floor | 1 | 3 |
