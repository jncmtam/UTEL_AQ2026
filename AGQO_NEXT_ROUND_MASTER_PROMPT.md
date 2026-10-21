# AGQO Next-Round Master Planning Prompt

**Purpose:** A copy-ready execution brief for turning AGQO from a working hybrid prototype into a rigorously tested, financially relevant, quantum-specific research result.

---

## Mission

Act as a senior quantitative-finance researcher, quantum-optimization scientist, machine-learning engineer, data-provenance auditor, and scientific-visualization designer working together on this repository.

Do not stop at saying the pipeline runs. Develop and execute a defensible research program that answers this falsifiable question:

> **Can market- and solver-aware AI choose a QAOA configuration that creates measurable incremental value over fixed and rule-based choices, while the resulting portfolio remains competitive after realistic trading costs and the quantum solver meets a useful quality/resource target?**

The project must connect three claims with separate evidence:

1. **Financial value:** Does the portfolio deliver better net risk-adjusted outcomes out of sample?
2. **AI value:** Does the AI controller improve policy selection over a non-LLM controller under matched information and compute budgets?
3. **Quantum value:** Does QAOA provide a useful quality, feasibility, latency, or resource trade-off against the strongest practical classical alternatives at the tested scale?

If the evidence does not support one of these claims, report that result clearly and narrow the claim. Do not relabel integration, a successful API call, or a valid circuit as financial alpha or quantum advantage.

## Project baseline to inspect and preserve

Read the current README, technical note, source code, configuration, tests, and results before changing anything. Treat stored result JSON as the source of truth and recompute summarized values from it.

Current known baseline:

- The stored market dataset has 37,308 daily OHLCV rows for 30 equities plus VN30 and VN-Index from 2022-01-04 to 2026-10-19.
- The current VN30 constituent snapshot is applied retrospectively. OHLCV corporate-action adjustment status is unverified. Current liquidity uses close multiplied by volume as a proxy.
- The portfolio experiment has 16 monthly periods from 2025-06-02 to 2026-10-01, simulated capital of VND 100 million, 25 basis points per side, and an ADTV-based participation cap.
- AGQO currently reports 18.81% net CAGR, 0.80 Sharpe, and -11.90% maximum drawdown. VN30 reports 24.58%, 1.17, and -9.22%. The rule selector reports 19.98% CAGR and 0.84 Sharpe. The strongest stored classical full-universe result, Ledoit–Wolf with exact enumeration, reports 49.68% CAGR and 1.53 Sharpe, with -15.92% maximum drawdown.
- The stored active-return confidence intervals versus VN30 include zero. Previous project iterations have seen the same period; it is not an untouched final holdout.
- The volatility classifier's monthly Brier score is 0.237 against a 0.217 prevalence baseline. Its Brier skill is negative.
- The current English Qwen3-8B prompt produced 16 valid decisions without format repairs or supervisor substitutions. It selected two XY-ring policies. This proves the controller returned valid choices, not that its choices created economic value.
- In the 12-qubit catalog, X p=1 has about 0.28% mean normalized objective regret and 40.81% feasible samples; XY correlation p=2 has about 2.53% mean regret, 100% feasible samples, and about 240 logical two-qubit gates. These are different quality/resource trade-offs, not evidence of financial profit.
- On the 30-stock snapshot, exact classical enumeration covered 593,775 six-stock combinations in about 5.76 seconds on the recorded research environment. The current scale does not establish a need for QAOA.
- QAOA results are statevector simulations on CPU. No QPU result or quantum advantage has been established.
- The raw OHLCV file and Modal credentials must remain excluded from Git and from any remote payload unless the user explicitly authorizes otherwise.

Verify every baseline number against the present repository before reusing it. If a code or data change invalidates a number, regenerate the report and figures from the new result artifacts.

## Research thesis and preregistered hypotheses

Write a short, testable primary hypothesis before tuning the next experiment. Use a fixed information cutoff for every decision.

Recommended primary hypothesis:

> On a locked chronological evaluation set, an AI-guided policy selector improves after-cost portfolio utility over the best ex-ante fixed policy and a rule-based selector, using the same candidate universe, objective, solver budget, execution assumptions, and risk limits.

Separate secondary hypotheses:

- **AI ablation:** Full RAG-grounded Qwen guidance adds value over the same controller without RAG, a deterministic rule selector, and a fixed policy selected only on training/validation data.
- **News ablation:** Timestamped, source-grounded news features add incremental predictive or decision value beyond price, liquidity, breadth, and volatility features.
- **QAOA ablation:** Mixer, topology, depth, and initialization choices change feasible-sample probability and normalized regret at a controlled shot, optimizer-call, and hardware-resource budget.
- **Economic translation:** Improvements in solver quality or feasibility translate into improved net portfolio utility after fees, taxes, slippage, turnover, and capacity limits.
- **Scaling:** Any quantum claim is limited to a tested problem size where a fair comparison with strong classical solvers is made.

Define the primary metric, benchmark, risk guardrails, confidence procedure, and minimum meaningful effect before opening the locked evaluation results. Do not choose the winning metric after inspecting the test set.

## Workstream A — Repair data validity before adding complexity

1. Build a point-in-time equity universe with historical VN30 membership, delisted securities where available, and effective dates. Do not use today's constituent list as if it had always existed.
2. Obtain and verify split-, dividend-, and rights-adjusted prices or construct a documented total-return series. Record ticker changes, suspensions, delistings, missing sessions, stale prices, and corporate actions.
3. Record for every field: source, license or redistribution status, observation date, publication time, collection time, timezone, adjustment method, units, missing-value policy, and file hash.
4. Retain a reproducible local data manifest. Do not place raw licensed or restricted data in Git. Do not send raw market or news data to Modal unless required and explicitly permitted.
5. Use multiple market regimes and chronological folds. Because the existing 2025–2026 period has already been inspected, label it diagnostic. Reserve a truly new period for final evaluation when it becomes available.
6. Use purging or an embargo around overlapping forward labels and holding periods. Every feature and article must be available by the decision timestamp.
7. Audit survivorship bias, look-ahead bias, stale prices, constituent changes, rebalancing calendars, and delisting returns before fitting any model.

Do not add indicators merely to make the feature table look large. Each feature must have a financial rationale, a point-in-time definition, a missing-data rule, and a planned ablation.

## Workstream B — Add useful, nonredundant market and event indicators

Candidate indicators to evaluate, not to assume useful:

- **Return and trend:** 1-, 3-, 6-, and 12-month momentum with an explicitly tested skip-month variant; moving-average distance; trend slope; cross-sectional rank.
- **Risk:** 20-, 60-, and 120-session realized volatility; downside deviation; rolling drawdown; beta; tail loss; cross-sectional dispersion; market breadth.
- **Dependence and concentration:** rolling correlation and covariance; sector concentration; correlation-network concentration; number and strength of common risk clusters.
- **Liquidity and capacity:** ADTV, turnover, spread if reliable quotes exist, Amihud-style price-impact proxy when data quality supports it, participation rate, and estimated unfilled fraction.
- **Macro context:** only point-in-time series with a defensible link to Vietnamese equities, such as rates, FX, or relevant commodity prices. Record source and release time.
- **Fundamentals:** only if historical filing values and publication dates are available. Never backfill a later report into an earlier decision.
- **News and events:** ticker-linked event type, direction, novelty, source tier, number of independent sources, sentiment, model confidence, and time since publication. Distinguish company disclosure, exchange/regulator notice, macro event, analyst opinion, rumor, and general commentary.

Use nested time-series validation, redundancy/correlation checks, feature ablations, and stability analysis to control indicator fishing. Compare a small, interpretable feature set with a richer one. Keep a feature only when it improves a preregistered out-of-sample metric or a documented decision-quality measure.

## Workstream C — Build a timestamp-safe external-news layer

News may explain a market move, but it must not create a post-hoc story or leak future information.

1. Prefer primary sources: company filings and announcements, exchange notices, regulators, and official macro releases. Use reputable news publishers as secondary context.
2. Confirm current access terms, licensing, API availability, and publication timestamps before collection. Do not bypass access controls or archive full copyrighted articles without permission.
3. Store a compact, auditable record: source name and tier, canonical URL, headline, ticker/entity mapping, event category, published_at, collected_at, timezone, permitted excerpt or model-generated metadata, content hash, and extraction version.
4. At decision time t, retrieve only items published by t. Exclude articles whose publish time is unknown or ambiguous from the primary test. Treat later edits and corrections as separate versions.
5. Use retrieval augmented generation with locally versioned finance and market-method notes. The LLM may summarize only retrieved, timestamp-valid material and must return evidence IDs and source URLs. It must label uncertainty and conflicting coverage.
6. Keep article interpretation separate from measured market response. Use event studies with predeclared windows and suitable market/sector controls before making causal statements. Correlation between a headline and a price move is not proof that the headline caused it.
7. Test news value by ablation: market data only, market plus news metadata, and market plus news plus LLM. Report coverage, missing-source rate, latency, token use, and cost.
8. If trustworthy timestamped news cannot be acquired, document the limitation and keep the feature disabled. Do not fabricate articles, sentiment, events, or citations.

## Workstream D — Test models and prompts instead of assuming a larger model is better

Keep OpenAI API dependence out of the pipeline. Compare feasible Qwen3 sizes (for example 8B, 14B, and a larger candidate only if current official model cards and Modal GPU memory support it) using the same frozen decision set.

For each candidate, measure:

- Correct schema and allow-list rate.
- Evidence citation precision and unsupported-claim rate.
- Policy-selection value versus rule, fixed, and no-RAG ablations.
- Stability across repeated decoding seeds or deterministic settings.
- End-to-end latency, GPU memory, tokens, Modal cost, and failure/retry rate.
- Whether any decision changes actually improve the preregistered financial or solver metric.

Verify model IDs, revisions, quantization support, and hardware capacity from official documentation before deployment. Do not equate parameter count with finance knowledge. A larger model is accepted only if its measured gain justifies its latency and GPU cost.

The system prompt must be English and versioned. It must tell the model:

- It is a constrained optimizer-policy selector, not an autonomous investment adviser.
- The date-cutoff payload and retrieved evidence are the only authority.
- It must not infer unavailable fundamentals, invent causal news narratives, or extrapolate unverified model probabilities.
- It may select only an eligible catalog entry and must cite supplied evidence IDs.
- It must compare net return, Sharpe/Sortino, drawdown, CVaR, fees, turnover, feasible-sample rate, normalized regret, and gate/resource cost when those measures are available.
- It must abstain or return a safe fallback when evidence is missing, stale, contradictory, or outside the validated range.
- It must return strict structured JSON, not hidden reasoning or free-form market commentary.

Validate the schema locally, verify every evidence ID against the actual payload, and generate user-facing explanations from checked numbers in code. Preserve prompt version, model revision, retrieval set, inputs, output, usage, latency, and validation result for each decision.

Do not train a contextual bandit or reinforcement-learning controller on 16 correlated monthly outcomes and call it robust. If a learned selector is tested, define the sampling unit, handle overlapping outcomes, use chronological evaluation, and compare with transparent rules.

## Workstream E — Make the quantum problem financially meaningful

Keep the current mean–variance/cardinality objective as a baseline. Then evaluate additional constraints only when their business meaning and data are defensible:

- Exact cardinality and position caps.
- Sector caps or sector balance.
- Turnover limits relative to previous holdings.
- Minimum liquidity or participation constraints.
- Cash allowance or minimum investment constraints.
- A downside-risk or robust-estimation variant if it can be estimated without leakage.

For each added constraint, document its business rationale, units, penalty calibration, feasibility condition, and effect on qubit count. Do not claim an XY mixer preserves a new constraint unless the implemented mixer provably preserves it. Quantify slack-qubit overhead and penalty sensitivity. Keep a classical exact or best-known solution for every instance where feasible.

The financial objective should state units and normalization. Explain expected-return estimation risk, covariance shrinkage, the role of lambda and alpha, transaction cost, and the relationship between the surrogate objective and realized portfolio returns. Include an out-of-sample test of whether objective score predicts realized utility.

Design circuit families from explicit hypotheses, not decorative gate layouts:

- Cardinality-preserving XY mixers for exact-K feasibility.
- Correlation-informed interaction graphs when covariance structure justifies the edges.
- Sector-aware or turnover-aware constraints only with a valid constrained-mixer or penalty construction.
- Different initial states or warm starts only when the information used to build them is available at the signal cutoff.
- Compare p=1 and p=2 first; increase depth only when the quality gain survives gate, noise, and runtime costs.

For every circuit actually used, persist policy ID, signal date, candidate-to-qubit mapping, initial state, cost terms, mixer edges, mixer layout, p, angle values, gate list/counts, two-qubit depth, shots, optimizer evaluations, seed, solver version, and measured bitstrings or sufficient sampling summaries.

## Workstream F — Use fair and strong baselines

### Financial baselines

Run the same dates, universe, position constraints, execution rules, and costs for:

- VN30 and VN-Index.
- Equal weight and liquidity-weighted portfolios.
- Minimum variance, risk parity, and a clearly specified mean–variance optimizer.
- Ledoit–Wolf shrinkage with exact or best-available classical optimization.
- Momentum and low-volatility strategies with parameters selected on training data only.
- The best fixed AGQO policy selected ex ante on training/validation data.
- The rule-based AGQO selector.
- Full AGQO, with and without RAG, news, regime model, and historical solver feedback.
- A random eligible-policy selector as a diagnostic.
- A hindsight oracle only as a labeled, nondeployable upper bound.

Avoid unfairly comparing a 30-stock full-universe classical strategy with a 12-stock QAOA candidate strategy without explicitly reporting the universe difference. Include both a like-for-like comparison and a full-universe benchmark.

### Solver baselines

For identical objective coefficients and constraints, compare QAOA to exact enumeration where feasible and to strong practical solvers such as greedy/local search, simulated annealing, tabu search, and an appropriate mixed-integer or quadratic solver. Record solver versions and hardware. Equalize wall-clock or total evaluation/shot budgets as well as possible; report both quality-at-equal-budget and time-to-target.

Do not use an intentionally weak classical baseline. If a commercial solver is unavailable, use a strong reproducible open alternative and clearly state the gap.

## Workstream G — Upgrade economic and statistical evaluation

Use after-cost portfolio returns as the primary outcome. Include:

- CAGR and arithmetic active return versus each benchmark.
- Annualized volatility, Sharpe with an explicit risk-free-rate assumption, Sortino, maximum drawdown, recovery time, monthly VaR/CVaR, and positive-period fraction.
- Turnover, fee/tax/slippage breakdown, spread assumptions, unfilled fraction, capacity by participation rate, and break-even transaction cost.
- Paired active-return series, confidence intervals using an appropriate block bootstrap, effect sizes, and fold-by-fold stability.
- Sensitivity to transaction costs, liquidity caps, rebalancing frequency, covariance window, lambda, alpha, and market regime.
- Multiple-testing and policy-selection bias controls. Keep the locked holdout untouched until the pipeline and report are frozen.

For solver outcomes, report mean/median normalized regret, probability of a feasible sample, probability of reaching a predeclared regret tolerance, best-of-seed and seed distribution, objective value, number of function evaluations, wall-clock, logical gates, transpiled two-qubit gates/depth, hardware noise, and resource cost.

Predeclare decision gates, not post-hoc thresholds. At minimum, a positive financial claim requires a positive and economically meaningful after-cost result on a locked holdout with uncertainty disclosed. An AI-value claim requires improvement over both fixed and rule-based policy selection. A QAOA-value claim requires a meaningful quality/resource advantage over strong classical solvers at a relevant scale. If gates fail, report “not established.”

## Workstream H — Rebuild the visual story around evidence

Create a polished, accessible figure suite with varied views of the actual data and actual decisions. Use a color-blind-safe palette, legible axis labels, units, legends, timestamps, source notes, and a visible colorbar where color encodes value.

For each figure, inspect the data range, unique values, missingness, and color-scale limits. Use a diverging scale centered at zero for signed returns and active performance; sequential scales for nonnegative volume or risk; clustered and annotated correlation matrices; robust percentile clipping only when labeled. If a series is genuinely constant or has low variation, say so and show the numeric range. Never alter data, invent variation, or hide a constant matrix behind a misleading palette.

Build a figure suite that includes, when data support it:

1. **System pipeline map:** detailed path from sources and timestamps through features, news retrieval, regime model, RAG/prompt, Qwen, schema validation, supervisor, QAOA circuit builder, optimizer, classical baselines, execution simulator, metrics, and artifacts. Show local versus Modal execution, information cutoffs, data boundaries, and fallback/error paths.
2. **Data-quality dashboard:** coverage and missingness by ticker and time, adjustment status, constituent history, liquidity sufficiency, and source freshness.
3. **Market regime timeline:** index price/returns, realized volatility, drawdown, breadth, regime probability, and dated macro/news events on aligned axes.
4. **Cross-sectional return heatmap:** ticker by month or regime with a zero-centered diverging scale, sector labels, and actual values.
5. **Correlation structure:** clustered heatmap or network with labeled high-correlation pairs and sector grouping.
6. **Risk and portfolio view:** efficient frontier or risk-return scatter, factor/sector exposures, rolling volatility, drawdowns, turnover, and costs.
7. **LLM decision audit:** date, eligible policies, current evidence, policy selected, rule/fixed alternatives, realized later outcome shown only as an evaluation annotation, and supervisor result.
8. **Circuit comparisons:** actual gate diagrams for at least three preselected contrasting market/constraint contexts; label qubit-to-asset mapping, mixer edges, p, gate count, and the insight that motivated each design. Diagrams must be generated from the circuit metadata of the corresponding result, not illustrative stand-ins.
9. **QAOA quality/resource frontier:** normalized regret versus feasible-sample rate, wall-clock, shots, and logical/transpiled gate cost, with classical solvers on the same chart.
10. **Economic scorecard:** net equity curves, benchmark-relative returns, confidence intervals, cost sensitivity, capacity, and drawdown.
11. **Ablation and robustness:** market-only versus news, no-LLM versus rule versus Qwen variants; results by time fold, regime, seed, and cost scenario.

Never force a heatmap or include a chart just to increase figure count. The selection goal is information density and honest variation, not decoration.

### Mandatory caption rule for every image

Every embedded result image in README and reports must have all three items directly underneath it, in this order:

1. A numbered, descriptive figure name.
2. A short paragraph explaining what is plotted, the key takeaway, and what decision it informs.
3. A compact source, date range, and caveat where relevant.

Use this pattern:

    ![Accessible description of the chart](path/to/figure.png)

    **Figure 1. Descriptive figure name.** The paragraph explains the axes, the actual result, and why it matters for the financial or solver decision. Source: ... Period: ... Caveat: ...

Generate a figure catalog containing file path, title, caption, data source, period, units, and the result JSON fields used. Add a validation check that every Markdown image reference has an existing file and a nonempty title and explanation. Do not leave plots with only an alt label.

## Workstream I — Produce a complete, reviewable deliverable

Deliver all of the following:

- Updated, tested source code with clean separation of data, news retrieval, features, model, prompt/RAG, policy selection, QAOA, classical baselines, execution, and reporting.
- Versioned data and news manifests; no secrets or unlicensed raw content.
- A reproducible configuration with explicit dates, fees, universe, feature set, model revision, prompt version, retrieval corpus version, policies, seeds, shots, solver budgets, and execution assumptions.
- A figure catalog and the full figure suite with mandatory captions.
- A judge-ready Vietnamese README written as a financial research report, with the investment thesis, numerical evidence, metric interpretation, system pipeline, circuit/solver evidence, limitations, and next steps.
- A detailed technical report that records methods, equations, baselines, and per-fold results.
- Machine-readable JSON/CSV artifacts for daily or monthly returns, active returns, drawdowns, costs, regime probabilities, news evidence IDs, LLM choices, circuit metadata, solver outcomes, and ablations.
- A short oral-defense script and concise answers to the expected finance, AI, data-integrity, and quantum questions.
- A reproduction guide for local execution and Modal deployment, including current GPU memory assumptions and any required user-supplied placeholders.
- Tests for temporal cutoffs, news provenance, schema and citation validation, objective/constraint correctness, deterministic replay, visualization captions and file links, and data-leakage cases.

Keep existing classical and fixed-policy methods as baselines. Remove obsolete outputs only when the new equivalent is generated, referenced, and verified.

## Execution order and completion criteria

Work in this order:

1. Inspect the repository, current outputs, data rights, and environment; write an experiment map and risk register.
2. Validate and repair data provenance and time alignment before adding new signals.
3. Register hypotheses, primary metrics, comparator set, holdout, cost assumptions, and decision gates.
4. Add news and indicators behind independently testable feature flags.
5. Compare model sizes and prompt/RAG ablations on a frozen, time-valid decision set.
6. Implement and verify the financial objective and every added constraint against exact small instances.
7. Run fair QAOA/classical comparisons at matched budgets and capture actual circuit metadata.
8. Run chronological portfolio experiments with costs, confidence intervals, and ablations.
9. Generate the pipeline diagram, figure suite, mandatory captions, report, and machine-readable artifacts from the same result files.
10. Audit every plot, caption, URL, date, metric, and stated claim against its source artifact. Confirm no single-color charts are unexplained and no post-cutoff news enters any decision.
11. Run the repository's relevant checks and report their output. Do not claim completion if a required data source, license, hardware, or holdout is unavailable; name the blocker and finish all independent work.

The final presentation should make one clear argument: **AGQO earns a place only if its AI policy selection improves financially meaningful outcomes and its QAOA component earns its resource cost against strong classical alternatives.** State exactly which part has passed, which has failed, and what new evidence would change the conclusion.
