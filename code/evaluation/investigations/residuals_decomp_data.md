# Exact decomposition search

## request_02 (IDR) binding 2025-08-13; our counts dining=0, entertainment=0, groceries=1, healthcare=1, transport=1, utilities=1
target estimated total (pending kept) = 7,803,300.00; solutions (fewest shifts first): 0

## request_03 (IDR) binding 2019-09-14; our counts dining=1, groceries=1, shopping=1, transport=0, utilities=1
target estimated total (pending kept) = 894,900.00; solutions (fewest shifts first): 0

## request_04 (IDR) binding 2024-06-13; our counts dining=1, entertainment=1, groceries=1, transport=1, utilities=1
target estimated total (pending kept) = 9,676,700.00; solutions (fewest shifts first): 0

## request_05 (ZAR) binding 2026-02-04; our counts groceries=13, healthcare=3, shopping=3, transport=7, utilities=3
target estimated total (pending kept) = 16,929.00; solutions (fewest shifts first): 1
- shifts=3 | pending kept | stat=mean round=ceil | healthcare-1,shopping+1,transport-1

## request_06 (EUR) binding 2026-01-13; our counts dining=2, entertainment=0, groceries=1, shopping=1, transport=2, utilities=1
target estimated total (pending kept) = 235.00; solutions (fewest shifts first): 32
- shifts=1 | pending kept | stat=last round=round | utilities-1
- shifts=1 | pending kept | stat=mean_last3 round=floor | dining-1
- shifts=2 | pending kept | stat=min round=floor | shopping-1,utilities+1
- shifts=3 | pending kept | stat=last round=round | groceries+1,transport-1,utilities-1
- shifts=3 | pending kept | stat=last round=round | groceries-1,transport+1,utilities-1
- shifts=3 | pending kept | stat=mean_last3 round=floor | dining+1,shopping-1,utilities-1

## request_07 (INR) binding 2024-09-20; our counts dining=1, groceries=1, transport=1, utilities=1
target estimated total (pending kept) = 22,120.00; solutions (fewest shifts first): 0

## request_08 (EUR) binding 2025-02-13; our counts dining=1, groceries=1, transport=1, utilities=0
target estimated total (pending kept) = 148.00; solutions (fewest shifts first): 2
- shifts=2 | pending kept | stat=median round=ceil | dining-1,groceries+1
- shifts=4 | pending kept | stat=mean_last4 round=ceil | dining-1,groceries-1,transport+1,utilities+1

## request_10 (INR) binding 2025-03-06; our counts dining=6, entertainment=3, groceries=13, transport=12, utilities=3
target estimated total (pending kept) = 345,190.00; solutions (fewest shifts first): 0

## request_11 (IDR) binding 2025-05-14; our counts dining=1, entertainment=0, groceries=1, healthcare=1, transport=1, utilities=1
target estimated total (pending kept) = 9,332,800.00; solutions (fewest shifts first): 0

## request_13 (EUR) binding 2024-05-14; our counts dining=5, entertainment=3, groceries=10, transport=9, utilities=2
target estimated total (pending kept) = 2,165.00; solutions (fewest shifts first): 8
- shifts=2 | pending kept | stat=mean_last3 round=round | groceries+1,transport+1
- shifts=3 | pending kept | stat=mean_last4 round=ceil | dining-1,entertainment+1,utilities+1
- shifts=4 | pending kept | stat=mean round=round | dining+1,entertainment+1,groceries+1,utilities-1
- shifts=4 | pending kept | stat=mean_last3 round=ceil | dining+1,entertainment-1,transport-1,utilities+1
- shifts=4 | pending kept | stat=mean_last3 round=floor | dining+1,entertainment+1,groceries+1,transport-1
- shifts=4 | pending kept | stat=mean_last3 round=floor | dining-1,entertainment-1,groceries+1,utilities+1

## request_14 (EUR) binding 2025-08-14; our counts groceries=1, healthcare=1, shopping=1, transport=1, utilities=1
target estimated total (pending kept) = 544.00; solutions (fewest shifts first): 14
- shifts=2 | pending kept | stat=last round=ceil | shopping+1,utilities-1
- shifts=2 | pending kept | stat=mean round=round | shopping-1,utilities+1
- shifts=2 | pending kept | stat=mean_last4 round=ceil | groceries+1,healthcare-1
- shifts=3 | pending kept | stat=mean_last3 round=floor | groceries+1,shopping-1,transport+1
- shifts=3 | pending kept | stat=min round=ceil | healthcare+1,shopping+1,utilities-1
- shifts=3 | pending kept | stat=min round=round | healthcare-1,shopping+1,transport+1

## request_15 (EUR) binding 2026-01-14; our counts dining=1, groceries=1, transport=2, utilities=1
target estimated total (pending kept) = 233.00; solutions (fewest shifts first): 4
- shifts=2 | pending kept | stat=mean round=ceil | dining+1,groceries-1
- shifts=2 | pending kept | stat=min round=floor | groceries+1,transport-1
- shifts=3 | pending kept | stat=mean round=floor | dining+1,transport+1,utilities-1
- shifts=4 | pending kept | stat=min round=round | dining+1,groceries+1,transport+1,utilities-1

## request_17 (INR) binding 2026-03-14; our counts dining=1, groceries=2, transport=2, utilities=1
target estimated total (pending kept) = 43,240.00; solutions (fewest shifts first): 0

## request_18 (EUR) binding 2026-07-14; our counts dining=0, groceries=1, healthcare=1, transport=1, utilities=1
target estimated total (pending kept) = 488.00; solutions (fewest shifts first): 5
- shifts=4 | pending kept | stat=mean round=floor | dining+1,healthcare+1,transport-1,utilities-1
- shifts=4 | pending kept | stat=mean_last3 round=floor | dining+1,groceries+1,healthcare-1,transport+1
- shifts=4 | pending kept | stat=mean_last3 round=round | dining+1,groceries+1,healthcare-1,transport+1
- shifts=4 | pending kept | stat=mean_last4 round=floor | dining+1,healthcare-1,transport+1,utilities+1
- shifts=4 | pending kept | stat=min round=floor | dining+1,healthcare+1,transport+1,utilities-1

## request_19 (INR) binding 2024-09-14; our counts groceries=1, healthcare=1, shopping=1, transport=1, utilities=1
target estimated total (pending kept) = 29,580.00; solutions (fewest shifts first): 0

## request_20 (INR) binding 2026-02-13; our counts dining=0, entertainment=1, groceries=1, healthcare=1, transport=1, utilities=0
target estimated total (pending kept) = 18,312.00; solutions (fewest shifts first): 0

## request_21 (USD) binding 2026-04-12; our counts dining=0, groceries=1, shopping=1, transport=0, utilities=1
target estimated total (pending kept) = 457.00; solutions (fewest shifts first): 4
- shifts=2 | pending kept | stat=last round=ceil | dining+1,transport+1
- shifts=2 | pending kept | stat=mean_last3 round=floor | dining+1,transport+1
- shifts=4 | pending kept | stat=mean_last3 round=round | dining+1,shopping+1,transport+1,utilities-1
- shifts=5 | pending kept | stat=min round=round | dining+1,groceries+1,shopping+1,transport+1,utilities-1

## request_22 (EUR) binding 2024-12-14; our counts dining=1, entertainment=0, groceries=1, transport=1, utilities=1
target estimated total (pending kept) = 86.00; solutions (fewest shifts first): 52
- shifts=0 | pending kept | stat=last round=floor | no shift
- shifts=0 | pending kept | stat=mean round=ceil | no shift
- shifts=1 | pending kept | stat=min round=round | entertainment+1
- shifts=2 | pending dropped | stat=last round=round | groceries+1,transport+1
- shifts=2 | pending dropped | stat=last round=round | transport+1,utilities+1
- shifts=2 | pending dropped | stat=mean round=round | entertainment+1,groceries+1

## request_23 (ZAR) binding 2025-05-14; our counts groceries=1, healthcare=1, shopping=1, transport=0, utilities=1
target estimated total (pending kept) = 8,104.80; solutions (fewest shifts first): 0

## request_24 (INR) binding 2026-01-13; our counts dining=1, entertainment=1, groceries=1, shopping=1, transport=2, utilities=1
target estimated total (pending kept) = 14,730.00; solutions (fewest shifts first): 2
- shifts=2 | pending kept | stat=last round=round | dining+1,shopping-1
- shifts=5 | pending kept | stat=last round=floor | dining+1,entertainment-1,shopping-1,transport-1,utilities+1

## request_25 (IDR) binding 2024-03-14; our counts dining=1, entertainment=1, groceries=1, shopping=1, transport=1, utilities=1
target estimated total (pending kept) = 5,654,400.00; solutions (fewest shifts first): 0


## Summary

Samples with an exact integer decomposition: 10/21.

Minimal-shift solutions by (pending mode, stat, rounding) — count of samples where that combo is among the minimal solutions:

- ('pending kept', 'mean', 'ceil'): 3
- ('pending kept', 'mean_last3', 'floor'): 3
- ('pending kept', 'last', 'round'): 2
- ('pending kept', 'mean_last3', 'round'): 2
- ('pending kept', 'last', 'ceil'): 2
- ('pending kept', 'min', 'floor'): 2
- ('pending kept', 'median', 'ceil'): 1
- ('pending kept', 'mean', 'round'): 1
- ('pending kept', 'mean_last4', 'ceil'): 1
- ('pending kept', 'mean', 'floor'): 1
- ('pending kept', 'mean_last4', 'floor'): 1
- ('pending kept', 'last', 'floor'): 1
