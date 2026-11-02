# US Equity Dataset: Measured Development Diagnostics

Status: **candidate; financial evaluation blocked**.

This report describes raw provider series. Security lineage and total-return treatment remain unverified.
The statistics below use 2014–2018 only. Later years are checked for coverage, not used for strategy design.

Requested stocks: 30. Downloaded stocks: 29. Benchmark: DIA.
Missing requested ticker: UTX. Verified security identities: 0.
Development complete observations: 1257. Context evidence records: 0.

| Diagnostic | Value |
|---|---:|
| Pair correlation quartiles [min,Q1,median,Q3,max] | [0.20681802657735845, 0.32511865006699975, 0.3751061236160029, 0.4311633149811397, 0.8270891059032124] |
| Covariance participation ratio | 5.200 |
| Sample covariance condition | 69.401 |
| Ledoit–Wolf covariance condition | 65.094 |
| Ledoit–Wolf shrinkage | 0.011647 |
| Nonzero pair fraction at 1e-12 | 1.000 |

## Coverage and identity warnings

| Inception ticker | Downloaded | Provider name now | Dates | Rows | >20% moves (development only) |
|---|---|---|---|---:|---:|
| AXP | True | American Express Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| BA | True | The Boeing Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| CAT | True | Caterpillar Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| CSCO | True | Cisco Systems, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| CVX | True | Chevron Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| DD | True | DuPont de Nemours, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| DIS | True | The Walt Disney Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| GE | True | GE Aerospace | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| GS | True | The Goldman Sachs Group, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| HD | True | The Home Depot, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| IBM | True | International Business Machines Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| INTC | True | Intel Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| JNJ | True | Johnson & Johnson | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| JPM | True | JPMorgan Chase & Co. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| KO | True | The Coca-Cola Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| MCD | True | McDonald's Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| MMM | True | 3M Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| MRK | True | Merck & Co., Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| MSFT | True | Microsoft Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| NKE | True | NIKE, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| PFE | True | Pfizer Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| PG | True | The Procter & Gamble Company | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| T | True | AT&T Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| TRV | True | The Travelers Companies, Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| UNH | True | UnitedHealth Group Incorporated | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| UTX | False | missing |  /  | 0 |  |
| V | True | Visa Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| VZ | True | Verizon Communications Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| WMT | True | Walmart Inc. | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| XOM | True | ExxonMobil Holdings Corporation | 2012-01-03 / 2025-12-31 | 3520 | 0 |
| DIA | True | State Street SPDR Dow Jones Industrial Average ETF Trust | 2012-01-03 / 2025-12-31 | 3520 | 0 |

## Interpretation and actions

- UTX is missing. Replacing it with a current ticker or deleting it would change the historical universe.
- DD and GE resolve to present-day provider names. Their historical entity/action lineage needs source-level reconstruction.
- Shared return structure motivates testing covariance shrinkage and correlation descriptors; it does not select a mixer.
- Dense quadratic interactions motivate direct RZ/RZZ resource accounting. No cost coefficient may be deleted by the LLM.
- Compare profile-informed designs against rules and adaptive classical designs on identical problems.
- Add point-in-time positions, mandates and evidence records to study decisions; OHLCV alone is not rich financial context.
- No final universe, sector labels, corporate-action correctness, or investment claims are approved by this report.

Machine-readable evidence and formulas: [assessment.json](assessment.json).
Reproduce: `.venv/bin/python scripts/assess_us_dataset.py`. Raw provider files stay local; publish checksums only.
