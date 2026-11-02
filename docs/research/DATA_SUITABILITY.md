# Dataset suitability before financial or circuit experiments

Date: 2026-11-02. Decision: **retain as an audit candidate, not an approved dataset**.

## Question and assessment boundary

Can a free historical US-equity panel support a defensible study of constrained
portfolio maintenance, and which measured structures justify a technical choice?

The candidate is the proposed 30-security DJIA cohort effective 2013-09-23, plus
DIA as an ETF total-return proxy. It is a fixed cohort, not reconstructed DJIA
membership, and not a representative sample of all US stocks. The [2013 official
announcement](https://press.spglobal.com/2013-09-10-Goldman-Sachs-Visa-Nike-Set-to-Join-the-Dow-Jones-Industrial-Average)
confirms three replacements; it does not by itself verify our full security master.
The [DIA issuer](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-dow-jones-industrial-average-etf-trust-dia)
identifies a 30-stock, price-weighted benchmark and ETF expenses. DIA returns are
therefore an accessible investable proxy, not the official frictionless index.

Assessment uses existing local downloads only. No new model inference, portfolio
optimization, trading backtest or paid data acquisition was performed. Descriptive
return statistics use 2014–2018 development data. Later data is inspected only for
coverage, keeping it out of technical feature/strategy fitting.

## Reproducible measured findings

Source: [generated assessment](../../results/data_assessment/ASSESSMENT.md),
[machine-readable statistics](../../results/data_assessment/assessment.json), and
[analysis script](../../scripts/assess_us_dataset.py).

| Finding | Measurement | What it means | What it does not mean |
|---|---:|---|---|
| Download coverage | 29/30 requested stocks, plus DIA | 30 raw files exist; UTX is missing. | The missing security can be dropped or replaced without changing the study. |
| Verified permanent identities | 0/30 | Historical identity work is still required for the entire cohort. | A provider ticker with many historical rows certifies lineage. |
| Development observations | 1,257 complete returns | No missing rows in the available diagnostic subset after the initial price difference. | The full original 30-stock universe is complete. |
| Historical contextual evidence | 0 records | The current dataset is price/event metadata, not rich point-in-time business context. | Adding a filings API adapter already supplies verified context. |
| Pair correlation | min 0.207; Q1 0.325; median 0.375; Q3 0.431; max 0.827 | Broad shared variation and some highly correlated pairs. | Any one correlation-motivated mixer edge is optimal. |
| Covariance participation ratio | 5.200 / 29 assets | Variance is concentrated in common directions; computed as trace(Sigma)^2/trace(Sigma^2). | Exact rank is five, or the portfolio has only five meaningful constraints. |
| Sample / shrunk covariance condition | 69.401 / 65.094 | Shrinkage modestly improves conditioning in this development sample. | Shrinkage guarantees out-of-sample tracking or QAOA trainability. |
| Ledoit–Wolf shrinkage | 0.011647 | Data-driven regularization is small here. | The same shrinkage applies to every future window. |
| Nonzero tracking pair interactions | 100% above absolute 1e-12 before K scaling | The exact quadratic tracking cost is dense. | Dense QUBO is necessarily hard for MIP or permits silent sparsification. |
| Rolling participation ratio | 3.535–13.441 | The same securities exhibit materially different covariance concentration over 252-session windows. | These windows are independent experiments. |
| Rolling mean pair correlation | 0.139–0.502 | A fixed topology deserves comparison against structure-adaptive proposals. | Adaptation has already demonstrated a benefit. |

Rolling windows have 252 sessions and stride 63, so they overlap. These statistics
are descriptive diagnostics, not hypothesis tests. All currently downloaded stocks
are used for diagnostics; none was chosen by LLM or return performance.

## Advantages and limits of this data type

**Advantages:** US large-company equities and a matching benchmark family give a
clear account-maintenance setting; daily observations support monthly decisions;
repeated windows allow controlled structural change; existing free downloads permit
source-level checks. A small cohort permits exact small-instance references before
more expensive experiments.

**Limits:** free price providers do not automatically deliver a historical security
master, delisting proceeds, spin-off entitlements, historical sector labels, or
as-published fundamental records. Current provider names for DD and GE show why
symbol continuity alone is insufficient. We have not established that their returns
are wrong, but neither have we established that they represent the specified
historical holdings correctly. UTX cannot be replaced by a modern ticker on intuition.

A fixed 2013 cohort also drifts away from the evolving index. Decompose observed
tracking limitations into universe restrictions, mandate restrictions, selection
approximation and solver error before attributing performance to circuit design.
Comparison against DIA also embeds ETF-specific tracking and expenses.

## How to exploit properties without changing the problem

| Data property | Proposed experiment | Required control / guard |
|---|---|---|
| Common covariance factors | Ledoit–Wolf covariance; factor-aware classical search as a comparator | Preserve the full canonical objective; any factor approximation is a separate study. |
| Correlated substitutes | LLM exchange scheduling with explicit pair descriptors | Fixed/rule/adaptive designs using the same information and resource budget. |
| Dense tracking interactions | Direct RZ/RZZ compilation; count routed two-qubit depth | No LLM coefficient deletion; preserve exact coefficients and report transpilation overhead. |
| Structure changes across windows | Reuse old circuit versus redesign versus bounded edits | Same financial state and data; include design/search cost and angle retuning. |
| Limited, auditable cohort | Full-universe instance when resource-feasible; exact tests on declared smaller families | Smaller families are benchmark instances, not LLM-selected finalists. Compilation success is not N=30 execution. |
| Missing business context | Add real mandate/state changes plus timestamped evidence | Do not infer investment restrictions from generic company text without a verified policy mapping. |

## What rich context must contain

- **Market:** adjusted/total-return lineage, estimation cutoff, benchmark definition,
  covariance stability, liquidity evidence if used by the cost model.
- **Account:** actual previous holdings and cash, drift, prior trades, transaction
  costs and explicit no-trade comparison.
- **Mandate:** required/excluded assets, count quotas, weight limits, turnover,
  effective dates and conflicts. Synthetic mandates must be labeled as scenarios.
- **Evidence:** historical security identifier and filing accession, publication or
  acceptance timestamp, units, source and checksum.

[SEC submissions/XBRL APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
provide useful source material, but need as-of filtering and filing-version control.
A period-end date is not the public availability date. More tokens of company prose
do not add combinatorial variables by themselves. If narrative does not influence
verified constraints or a tested design hypothesis, leave it out.

## Data admission gates and concrete next audit

1. Reconstruct and source the complete inception membership and permanent identifiers.
2. Resolve UTX, DD, GE and all other identity/action histories; define treatment of
   successor shares, cash distributions and securities outside the initial cohort.
3. Reconcile splits/dividends/spin-offs against independent primary event sources;
   distinguish adjusted-return mode from explicit corporate-action accounting.
4. Establish historical sector classification or disclose a fixed vintage.
5. Produce aligned prices with a checksum and missing-data log. Do not fill or delete
   unexplained observations. Report all raw acquisition failures.
6. Add verified mandates/account states and as-published context evidence.
7. Re-run the data gate, then determine whether the proposed period/cohort is usable.

If free evidence cannot support the full period, first narrow the period with an
explicit revised protocol. Do not silently replace the cohort with surviving names.
Only after the data gate passes should financial optimizer difficulty, support/
allocation mismatch and walk-forward performance be measured.

**Current decision:** the downloaded panel is suitable for detecting data-quality
issues and proposing development hypotheses. It is not yet suitable for investment
performance claims, dataset finalization, or model qualification.

## Primary-source checks of the identified lineage risks

These are evidence leads, not completed security-master reconciliation:

| Holding | Primary evidence checked | Consequence for our dataset |
|---|---|---|
| UTX | [RTX issuer annual-report record](https://investors.rtx.com/static-files/e2c0b07c-9373-470f-9172-01c1522aa510) describes the April 2020 separation of Carrier and Otis and the RTX listing. | An original holding can produce multiple successor holdings. A ticker rename alone is not a sufficient return/accounting policy. |
| GE | [GE Vernova SEC registration statement](https://www.sec.gov/Archives/edgar/data/1996810/000119312524131304/d783090ds1a.htm) describes distribution of one Vernova share per four GE shares on April 2, 2024. | Verify spin-off entitlement, ex-date valuation and whether the provider return already embeds the distribution. |
| DD | [DuPont issuer completion announcement](https://www.investors.dupont.com/news-and-media/press-release-details/2019/DuPont-Becomes-Independent-Company-Uniquely-Positioned-to-Drive-Innovation-Led-Growth-and-Shareholder-Value/default.aspx) describes the 2019 separation and 1-for-3 reverse split. | Reconstruct the earlier DuPont/DowDuPont chain and distributed securities; present-day DD metadata cannot establish inception identity. |

These checks strengthen the reason for the audit gate. They do not prove Yahoo
returns are incorrect or certify how Yahoo handled the events. The current EDA
therefore remains a diagnosis of provider series, including potentially stitched
history. Resolving those histories may change the measured correlations and ranks.
