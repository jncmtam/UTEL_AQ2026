# AGQO: questions a judge may ask, with answers

Every answer below uses numbers measured in this repository. "Evidence" points to the file that
holds the number. Figures are in [docs/figures](figures/). Test period: 12 quarterly decisions,
2024-01-02 → 2026-10-01, held to 2026-11 (711 trading days). Calibration uses 2023 only.

**Contents**

1. [The 60-second answer](#1-the-60-second-answer)
2. [Finance: the problem and who benefits](#2-finance-the-problem-and-who-benefits)
3. [Finance: results and how to read them](#3-finance-results-and-how-to-read-them)
4. [Data and bias](#4-data-and-bias)
5. [The LLM: what it does and how it is called](#5-the-llm-what-it-does-and-how-it-is-called)
6. [The AI guidance of the circuit](#6-the-ai-guidance-of-the-circuit)
7. [The quantum formulation](#7-the-quantum-formulation)
8. [The circuit and the QAOA optimiser](#8-the-circuit-and-the-qaoa-optimiser)
9. [Evaluation and statistics](#9-evaluation-and-statistics)
10. [Hardware, noise and scaling](#10-hardware-noise-and-scaling)
11. [Honest negatives](#11-honest-negatives)
12. [Engineering, cost and deployment](#12-engineering-cost-and-deployment)
13. [Regulation, ethics and responsibility](#13-regulation-ethics-and-responsibility)

---

## 1. The 60-second answer

**Q. What is AGQO in one sentence?**
An AI-guided quantum optimiser that turns an index-tracking portfolio into whole 100-share lots a
small Vietnamese investor can actually buy, under that investor's own rules, and verifies every
decision exactly.

**Q. What exactly is new?**
1. A **cap-safe qubit register**: the investor's caps shape which stocks get a qubit, so every one
   of the 2¹⁶ states obeys the caps and the Hamiltonian stays exactly the financial objective (no
   penalty approximation for the caps).
2. A **data-insight circuit design**: five rules (warm start, aligned mixer, coupling pruning, RMS
   scaling, linear ramp), each driven by a statistic of the current problem, plus a guidance model
   trained on 2023 that picks the schedule, and a noise-aware version for IBM Heron hardware.
3. An **LLM that compiles Vietnamese investor language into exact constraints** and explains each
   decision with every number checked by code.
4. An **evaluation that a sceptic can audit**: exact enumeration as ground truth, strong classical
   baselines (including a greedy heuristic and odd-lot trading), paired tests on unseen quarters,
   and a list of what we do not claim.

**Q. What is the headline result?**
| claim | result | evidence |
|---|---|---|
| circuit vs its own classical warm start | 6.9× more near-optimal shots, 12/12 quarters, p = 0.0005 | `results/final/quantum_stats.json` |
| circuit vs textbook QAOA | 19×, 12/12, p = 0.0005 | same |
| 20M VND account vs naive rounding | tracking error 6.8 % vs 12.1 %, 95 % CI of the gap −6.9 to −3.8 pp | `run_manifest.json` (`sweep_ci`) |
| personal rules | 0 violations in 3 mandates × 12 quarters | `results/final/mandates.csv` |
| LLM mandate compiler | 35/35 correct vs 68.6 % for keyword rules | `results/final/llm/mandate_eval.json` |
| noise-aware circuit on Heron noise | 1.6× its warm start, 11/12, p = 0.0010 | `results/final/extras/hardware_aware.csv` |

**Q. Is there a quantum advantage?**
No, and we do not claim one. Exact enumeration of the 65,536 states takes 0.12 s. A single short
simulated-annealing run lands within 5 % of the optimum in 12/12 test quarters (exact in 6/12). The
contribution is a verified, data-guided way to design and run the circuit, and a working pipeline
that would carry over when the register outgrows enumeration (see §10).

---

## 2. Finance: the problem and who benefits

**Q. What is the real-world problem?**
HOSE stocks trade in board lots of 100 shares. One lot of a VN30 stock costs 1–24 % of a 100M VND
account and 10–110 % of a 20M VND account (VIC: one lot ≈ 22M VND on 2026-10-01). A portfolio
optimiser gives fractional weights; the investor must turn them into whole lots under a cash budget,
fees (0.15 % per side) and sale tax (0.1 %). Which stocks get "one more lot" is a binary choice
with 2ⁿ options. Done badly, a 20M VND account ends up holding one stock and 90 % cash
([A4](figures/A4_one_decision.png)).

**Q. Who is the user?**
A domestic retail investor with a small account who wants "VN30, my way": index-like risk, but
with personal rules an ETF cannot follow (no real estate, banks at most 30 %, at most 12 stocks,
keep 5 % cash). Vietnam had over 14.3 million domestic individual securities accounts at the end of
October 2026, more than 14 % of the population (VSDC, reported by Doanh nhân / Báo Pháp luật,
6 Nov 2026). Most such accounts are small, which is exactly where lot granularity bites.

**Q. Why not just buy a VN30 ETF?**
For an investor without personal rules, an ETF is the right answer, and we say so: E1VFVN30 returned
about 1.1 %/yr more than AGQO over the test period because it is cheaper to hold and reinvests
dividends ([09](figures/09_vs_etf.png)). AGQO is for the investor whom an ETF cannot serve: one who
excludes a sector, caps banks, limits the number of holdings or wants to own the shares directly.
Two side facts: AGQO tracks the VN30 *index* more closely than the ETF's *traded price* (weekly TE
3.2 % vs 5.2 %; ETF prices deviate from NAV), and the three VN30 ETFs have daily TE of 9–18 %
against the index.

**Q. Why not trade odd lots (1–99 shares) instead?**
HOSE has allowed odd-lot orders since 12 Sep 2022 (continuous matching, limit orders, a separate
order book). We tested it: buying the ideal weights with odd lots tracks better than any whole-lot
portfolio (TE 2.5 % at 20M vs 6.8 %). It only loses on return if the odd-lot part costs more than
about **6.8 % (20M) or 2.6 % (100M)** extra (wider spreads, worse fills). We do not model fill risk
(odd-lot books are thin, orders may not fill). Honest conclusion: odd lots are a real alternative;
AGQO is the better tool when odd-lot liquidity is poor, when a broker charges a minimum fee per
order, or when the investor wants board-lot orders only. A production version should offer
"whole lots + odd-lot top-up" as one more register option ([A7](figures/A7_robustness.png), right).

**Q. Why is tracking error the objective and not return?**
The investor asked for "VN30, my way". Tracking error is the measurable promise: how far the
account strays from the index it is meant to follow. Chasing return would be an active bet that
no backtest of 12 quarters can validate. Return is reported, not optimised.

**Q. How do you track VN30 without its official weights?**
We do not need them. The continuous step minimises the variance of (portfolio − VN30) returns over
the previous 250 sessions, using the price history of the point-in-time members and the index
itself. This regression-style tracking also handles the free-float and cap rules of the index
implicitly.

**Q. What does a 5.4 pp lower tracking error mean in money?**
For a 20M VND account, a TE of 12.1 % means a typical yearly deviation from VN30 of about
±2.4M VND; 6.8 % means about ±1.4M VND. The investor gets far closer to the index they asked for.

**Q. How often does it rebalance and what does it cost?**
Quarterly by default, on the first trading day. Fees are part of the objective and of every
feasibility check. At 100M VND, 12 quarters cost 0.57M VND in fees in total; at 20M, 0.17M VND.
Monthly rebalancing and commissions of 0.10 % or 0.25 % do not change the conclusions
([A7](figures/A7_robustness.png), left).

**Q. Does it handle existing holdings?**
Yes. The objective includes a turnover term γ‖w − w_prev‖², and the register adds or removes lots
relative to what the investor already holds; sales pay the 0.1 % tax.

**Q. Does it trade for the user?**
No. It proposes a trade list in whole lots with a Vietnamese explanation. The investor places the
orders. It is decision support, not investment advice.

---

## 3. Finance: results and how to read them

**Q. Where does AGQO actually help financially?**
In small accounts. Against naive nearest-lot rounding (the same target, each stock rounded to its
nearest lot, trimmed to fit cash):

| account | naive TE | AGQO TE | gap (95 % CI) |
|---|---:|---:|---:|
| 20M VND | 12.14 % | 6.77 % | −5.37 pp (−6.93, −3.84) |
| 50M VND | 4.43 % | 3.83 % | −0.60 pp (−1.09, −0.19) |
| 100M VND | 3.03 % | 2.96 % | −0.07 pp (−0.19, +0.04) |
| 200M VND | 2.70 % | 2.50 % | −0.20 pp (−0.40, −0.04) |
| 500M VND | 2.51 % | 2.47 % | −0.05 pp (−0.10, −0.00) |

The smaller the account, the more the integer decision matters ([08](figures/08_account_size.png)).

**Q. Isn't naive rounding a straw man?**
It is what a person does by hand, so it is the practitioner baseline, but we added a stronger one:
**greedy lot filling** (start from the floor lots, repeatedly add the single lot that most lowers
TE² + turnover while cash allows). Greedy closes most of the gap: 7.47 % TE at 20M vs 6.77 % for
the exact/AGQO decision. The remaining gap is −0.69 pp (CI −1.53 to +0.02, borderline) with
quarterly rebalancing and −1.28 pp (CI −1.99 to −0.62, significant) with monthly rebalancing. At
100M the two are indistinguishable. We report this openly: most of the small-account gain comes
from *optimising the lot decision at all*; solving it exactly adds a smaller, sometimes significant
improvement.

**Q. Greedy returned 26 %/yr at 20M and AGQO 16 %. Isn't greedy better?**
Not for this mandate. Greedy's return came from concentration: in the 2026-10-01 example
([A4](figures/A4_one_decision.png)) it puts 36 % of a new 20M account in one stock (MWG) because
that lot happens to fit. That bet paid off in this sample; it is
not repeatable and not what the investor asked for. Its tracking error is higher (7.5 % vs 6.8 %).
Over 12 quarters with 1–2 lots per stock, realised returns at 20M range from 12 % (naive) to 26 %
(greedy) mostly by luck of which lots land where, which is why we judge by tracking error with
paired bootstrap intervals and do not claim return.

**Q. At 100M VND the gain is not significant. So why bother?**
Because the same machinery is what makes personal rules work. At 100M, AGQO tracks better than
naive rounding under all three mandates (6.74 % vs 6.98 %, 3.93 % vs 4.21 %, 6.74 % vs 6.82 %) with
zero rule violations. And small accounts are the majority. We state that at 100M without rules the
improvement is within noise.

**Q. What does a personal rule cost?**
Shown to the investor: excluding real estate and capping banks at 30 % raises TE by about 3.8 pp
(from 2.96 % to 6.74 %), because those sectors are a large part of VN30. "At most 12 stocks, 10 %
each, 5 % cash" costs about 1 pp. The LLM explainer can tell the user this trade-off in Vietnamese.

**Q. How do you know the rules were respected?**
Caps are built into the qubit register (§7), the minimum-cash rule is checked exactly on every
sample, and compliance is re-checked on every executed portfolio at decision time.
Result: 0 violations and 0 fallbacks across 3 mandates × 12 quarters ([10](figures/10_mandates.png)).

**Q. Sharpe ratio? Drawdown?**
Not the objective. Correlation with VN30 is 0.988 at 100M and 0.936 at 20M; daily values are in
`results/final/daily_values.csv` for any risk statistic a judge wants. A tracking portfolio's
Sharpe and drawdown are the index's plus noise; tracking error is the honest measure.

---

## 4. Data and bias

**Q. What data do you use?**
Daily OHLCV from the keyless DNSE chart API (`services.entrade.com.vn/chart-api/v2/ohlcs`),
2022-01 → 2026-11-15: all 40 stocks that were ever VN30 members in the period, the VN30 and
VN-Index levels, and three VN30 ETFs (E1VFVN30, FUESSV30, FUEKIV30). 52,686 rows; SHA-256 and
coverage in `data/vn30/manifest.json`. The OHLCV file is git-ignored (redistribution rights are not
granted); `python -m agqo download` rebuilds it.

**Q. Survivorship bias?**
Avoided: membership is point-in-time from HOSE review announcements (source URL per row). On each
rebalance date only the 30 members effective that day are eligible, including stocks later
removed (e.g. NVL, PDR, KDH, POW). A stock needs 180 of the previous 250 sessions to be usable.

**Q. Look-ahead bias?**
Each decision uses only data before its date: covariance from the previous 250 sessions, membership
effective that day. All calibration (budget penalty λ, the 1,080-schedule table, the guidance model,
the polish decision, the noise-aware schedule) uses 2023 only. Test quarters start in 2024.

**Q. Are prices adjusted?**
The provider back-adjusts for stock dividends and splits, so returns are right. Historical price
*levels* are therefore lower than traded at the time, which understates historical lot costs; this
makes the backtest *conservative* for AGQO's main claim (real lots were coarser). Today's decision
uses actual prices. Cash-dividend treatment by the provider is not independently verified.

**Q. Liquidity and price limits?**
VN30 members are the most liquid HOSE stocks; one or a few lots per stock are far below daily volume.
We execute at the close of the rebalance day with fees and tax but no slippage model, which is
standard for daily backtests of retail-size orders. Price-limit days (±7 %) are not modelled.

**Q. What does the market look like statistically?**
Average pairwise correlation 0.36, one market factor explains about 40 % of daily variance, and
VN30 behaves like about 13 independent bets (effective number of bets, Meucci 2009; range 10.4–15.0
across test quarters) ([02](figures/02_market_structure.png)). That is why ~20 whole-lot holdings can
track the index, and why the lot decisions of different stocks are coupled.

---

## 5. The LLM: what it does and how it is called

**Q. Which LLM and why?**
**Qwen3.8-27B**, the official FP8 checkpoint (`Qwen/Qwen3.8-27B-FP8`, revision `c3a462cc…` pinned).
Reasons: open weights (the investor's text never leaves our infrastructure, and the run is
reproducible from a pinned revision), strong Vietnamese, and it fits one H100 (~31 GB of weights)
within a 30 USD cloud budget. Larger open models (e.g. GLM-5.3, ~756 GB) were rejected on cost; the
compiler already scores 35/35, so a larger model would not change the measured result.

**Q. How is it hosted and called? (the plumbing)**
- `modal_app.py` defines a Modal class `Engine` on one **H100**, image `vllm/vllm-openai:v0.32.0`,
  weights in a Modal Volume `agqo-qwen38-weights`.
- `@modal.enter` loads `vllm.LLM(model=..., kv_cache_dtype="fp8", max_model_len=32768,
  max_num_seqs=32, gpu_memory_utilization=0.90)` once per container.
- `Engine.generate(requests)` receives a **batch**; each request carries a system prompt, the user
  text, a **JSON schema**, a seed, a temperature and a token limit. It calls `llm.chat(...)` with
  `SamplingParams(temperature, top_p=0.8, top_k=20, seed, max_tokens,
  structured_outputs=StructuredOutputsParams(json=schema))` and Qwen's **non-thinking mode**
  (`enable_thinking=False`), so the grammar applies from the first token.
- The local client (`agqo/llm/client.py`) calls
  `modal.Cls.from_name("agqo-llm", "Engine")().generate.remote(payload)` and appends every call to
  `results/final/llm/llm_log.jsonl`: request hash, prompts, raw text, parsed JSON, status, tokens,
  model, revision, GPU, wall time.
- `--llm replay` re-reads that log by request hash: the LLM steps are reproducible with no GPU.

**Q. What does the LLM do, exactly?**
Two language jobs; it never produces a weight, a lot or a trade.
1. **Mandate compiler.** Input: a Vietnamese instruction plus the ticker/sector list. Output (JSON
   schema): excluded tickers and sectors, sector caps, a per-stock cap, maximum holdings, minimum
   cash, or a clarifying question when a limit has no number (live answer: "Đừng mua quá nhiều cổ
   phiếu ngân hàng" → "Bạn muốn giới hạn tỷ trọng cổ phiếu ngân hàng tối đa là bao nhiêu phần
   trăm?"). Temperature 0, 512 tokens max.
2. **Explainer.** Input: a code-built evidence pack for the quarter (trades in lots, tracking errors,
   sector weights, quantum success, market insight). Output: a 3–5 sentence Vietnamese summary,
   trade notes and risk notes. Temperature 0.3, 1,200 tokens max.

**Q. How do you stop hallucination?**
Four layers. (1) **Constrained decoding**: tickers and sectors are JSON-schema enums, numbers have
bounds; the model cannot emit a ticker that is not in the list. (2) **Code validation**: every field
is parsed and checked (`parse_mandate`); invalid answers become an empty mandate and are counted.
(3) **Clarify, don't guess**: vague limits produce a question, not an invented number (2/2 vague
test items handled). (4) **Number verification** of explanations: every number in the text must
appear in the evidence pack and every trade note must match an executed trade, and a **meaning
check** requires each tracking error to be stated against VN30 in its sentence and forbids attributing
VN30 market statistics to the investor's portfolio (`verify_explanation`). Numbers 12/12, meaning 11/12.

**Q. How good is the mandate compiler?**
On 35 hand-labelled Vietnamese instructions: **100 %** of effective constraints correct (94.3 %
strict JSON match; the two strict misses wrote a no-op "0 % cash"), 0 invalid outputs, 35/35
correct clarify-or-not decisions. A keyword-rule parser scores **68.6 %**: it fails on Vietnamese
typed without diacritics ("khong mua co phieu ngan hang qua 25%"), fractions ("một phần ba", "1/4"),
sectors named in everyday words (energy, aviation, securities, insurance), caps phrased as "hạn chế …
ở mức 5%", and it cannot ask a clarifying question.

**Q. Is the number check enough?**
No, and we found out the hard way. The first prompt passed the number check 12/12, but a meaning check
we added later failed **0/12**: it called the 5.39 % tracking error (which is against VN30) "so với lý
tưởng" (vs the ideal) or even "chỉ số AGQO", and placed the 34.6 % VN30 market-factor share "trong danh
mục" (in the portfolio). Cause: the evidence field was called `tracking_error_pct`, without its
reference. Fix: every evidence field now names its reference (`tracking_error_vs_vn30_index_pct`,
`vn30_market_structure`), carries a Vietnamese label, sector names are in Vietnamese, and the prompt
says in which sentence each number must sit. Re-run live: numbers 12/12, **meaning 11/12**. The
remaining flag (2025-07) writes "chỉ số" (the index) without naming VN30. In production a failed
explanation would be regenerated or replaced by a template, never shown silently.

**Q. Token use, latency and cost?**
| task | requests | input tokens | output tokens | batch wall time (incl. cold start) |
|---|---:|---:|---:|---:|
| mandate compiler | 35 | 22,644 | 3,228 | 363 s (cold) |
| explainer | 12 | 11,778 | 8,153 | 16 s (warm; 13 s generation) |

Mandate input tokens are recounted with the Qwen3.8 tokenizer (the first live log under-counted them,
a bug fixed in `modal_app.py`; the explainer re-run logs them correctly), see
`results/final/extras/llm_usage.json`. A cold start loads the 31 GB model in about 5 minutes; a warm
container answers a batch in seconds. On an H100 at about 4 USD/hour, all live LLM runs of the project
(including three explainer runs) cost about 1–2 USD.

**Q. Why not GPT or Claude through an API?**
Investor instructions are personal financial data; an open-weight model on our own GPU keeps them in
our infrastructure and makes the result reproducible from a pinned checkpoint. A hosted API would
work technically (the client has one interface), but the contest asked us to own the AI component.

**Q. Did you let the LLM design the quantum circuit?**
We tried it in an earlier version and removed it. A circuit generated from text cannot be verified
as better before it runs, and our experiments showed no measured value. Circuit design is driven by
statistics of the problem and a trained model (§6), which can be tested and cross-validated.

**Q. Is the test set biased?**
It was written by the team (35 instructions covering exclusions, caps, fractions in words, holdings,
cash, vague limits). It is not a sample of real user requests; the next step is collecting real
instructions from users.

---

## 6. The AI guidance of the circuit

**Q. What is "AI-guided" about the quantum part?**
Phase 2a computes **five insight features** of each problem without solving it: warm-start
confidence (mean |2x*−1|), share of decided qubits, log(RMS field / RMS coupling), coupling
concentration (pairs holding 90 % of ΣJ²), mean lot weight. Phase 2b, a **k-nearest-neighbour
model**, maps those features to a schedule (depth p, warm-start clip ε, coupling mass m, ramp
heights Δγ, Δβ), by averaging the success of each of 1,080 schedules over the k most similar
training problems ([04](figures/04_ai_guidance.png)).

**Q. How was it trained?**
On 48 problems: the first trading day of each month of 2023 × 4 account sizes (50, 100, 200, 500M).
Each of 1,080 schedules was simulated exactly on each problem (no optimiser), giving a success
table. k ∈ {3, 5, 10, 20, all} was chosen by leave-one-month-out cross-validation: k = 10, 16.1 %
CV success vs 15.7 % for one frozen schedule (k = all).

**Q. Does the learned model beat a single frozen schedule on test?**
No: 7/12 quarters, p = 0.47. We report it as "no gain". What carries the result is the
**insight-driven structure** (warm start + aligned mixer + RMS scaling + ramp), which every arm
shares. The guidance layer earns its keep on **hardware**: choosing for expected *noisy* success
from the same 2023 table picks a 2-layer, 25 %-coupling circuit (16 native CZ gates) that keeps
1.6× its warm start under Heron noise, while the noiseless choice collapses to random (§10).

**Q. Is k-NN really "AI"?**
It is supervised learning from data to a decision, chosen by cross-validation, the same idea as
instance-similarity parameter transfer in the QAOA literature (Galda 2021, Shaydulin 2023). We keep it
deliberately small so that it can be audited and so that 48 training problems are enough.

**Q. What is the "polish"?**
A 40-step COBYLA optimisation of the circuit angles on CVaR₀.₁ of the energy (Barkoutsos 2020),
started from the chosen schedule. A pre-registered rule decided on training data whether to use it
(train success 15.8 % → 17.3 %, 45/48 problems), so AGQO uses it. On test it did not help (21.3 % vs
24.0 % without it, p = 0.42). Reported as a negative result.

---

## 7. The quantum formulation

**Q. What does one qubit mean?**
Qubit k = "buy one more lot of stock j(k) than its floor". The 16 stocks where rounding matters most
(lot value × distance of the fractional lot count from an integer) get a qubit; every other stock
takes its nearest lot. Weights are affine in the bits: w = w_base + A·x with A_{j(k),k} = 100·P/NAV.

**Q. What is the Hamiltonian?**
The QUBO is exactly the financial objective plus one budget penalty:
E(x) = 252·(wᵀΣw − 2wᵀc + σ_b²) + γ‖w − w_prev‖² + λ(1ᵀw − t)²,
with Σ, c, σ_b² the shrunk covariance blocks of members and VN30 over 250 sessions, γ = 0.002,
λ = 0.01 (calibrated on 2023), t the invested target. A unit test checks E(x) = F(x) + penalty to
10⁻¹² on all 65,536 bitstrings. The Ising form uses x = (1 − z)/2. Fields h come from each stock's
own risk and budget; couplings J_kl from co-movement (on average 89 % of coupling mass) and the
budget (11 %) ([03](figures/03_problem_structure.png), [A2](figures/A2_circuit.png) right).

**Q. How do you enforce the investor's caps without penalty terms?**
Penalties failed in an earlier version: three extra lots can break a sector cap that every pair
respects, and a QUBO cannot penalise triples. So caps shape the **register**: a stock in a capped
group gets a qubit only if the group's floor weight plus one lot for *every* qubit in the group
still fits under the cap; otherwise it stays at its floor and the qubit goes to the next stock. Hence
all 2¹⁶ states obey the caps by construction. Affordability (cash after fees and tax ≥ 0) and
minimum cash are checked exactly on each sample; if none passes, the floor-rounded portfolio
(always feasible) is executed and counted as a fallback (0 fallbacks in the test).

**Q. Why 16 qubits?**
16 is the largest size we can enumerate exhaustively for every decision in the backtest
(65,536 states, 0.12 s), which gives exact ground truth for every claim. The scaling study runs
8–20 qubits (§10). A full VN30 problem with two lots per stock is about 60 qubits.

**Q. Why is the decision binary and not integer?**
The continuous target sits between a stock's floor lot and the next one, so "+0 or +1 lot" is the
rounding decision. Larger moves (two or more extra lots) would need more qubits per stock (unary or
binary encoding). This is not implemented; the "30 stocks × 2 lots = 60 qubits" figure is the size
estimate for that extension.

---

## 8. The circuit and the QAOA optimiser

**Q. Walk me through the circuit.** ([A2](figures/A2_circuit.png))
- **R1 warm start** (Egger et al. 2021): solve the continuous relaxation of the QUBO on [0,1]¹⁶,
  get x*; prepare each qubit with R_y(θ_k), sin²(θ_k/2) = clip(x*_k, ε, 1 − ε).
- Each layer k = 1..p:
  - **phase separator** e^{−iγ_k H_C/s}: R_z(2γ h_k / s) on every qubit and ZZ(2γ J_kl / s) on the
    kept pairs (each ZZ = CX·R_z·CX);
  - **R2 aligned mixer** (He et al. 2023): R_y(θ_k)·R_z(−2β_k)·R_y(−θ_k), whose ground state is the
    warm-start state, so the circuit starts in the mixer's ground state as adiabatic reasoning
    requires.
- **R3 coupling pruning**: keep the strongest pairs that hold a fraction m of ΣJ² (the scoring
  always uses the full Hamiltonian).
- **R4 RMS scaling** (Sureshbabu et al. 2024): divide H_C by the RMS s of its kept coefficients so
  one schedule transfers between quarters and account sizes.
- **R5 linear ramp** (LR-QAOA, Montañez-Barrera & Michielsen 2025): γ_k = Δγ(k+½)/p,
  β_k = Δβ(1 − (k+½)/p): two numbers instead of 2p free angles.
- Measure all qubits, 512 shots.

**Q. Why a warm start? Doesn't it make QAOA redundant?**
The warm start alone (zero layers, measured) is our main quantum baseline. AGQO beats it 6.9× in
near-optimal shots, so the layers add real value. The right metric for a warm-started circuit is
whether it beats its starting classical solution (the "better solution probability",
arXiv:2409.09012): 40 % of AGQO shots are affordable and better than naive rounding vs 16 % for the
warm start.

**Q. How are the angles optimised?**
They mostly are not, by design. R5 reduces the angles to (Δγ, Δβ); the AI guidance picks them with
p, ε and m from the 2023 table. The optional polish runs 40 COBYLA steps on CVaR₀.₁. Textbook QAOA,
in contrast, needs about 100 optimiser calls and still scores 19× lower. Fewer optimiser calls also
means far fewer hardware jobs.

**Q. Which simulator and which Qiskit?**
Exact statevector simulation in NumPy (`agqo/quantum/simulator.py`); Qiskit 2.5.2 for compilation
and export (`agqo/quantum/export.py`). A unit test checks the Qiskit circuit gives the same
probabilities as the simulator. Noise studies use qiskit-aer 0.17.2 and qiskit-ibm-runtime 0.50
`FakeKingston` (§10).

**Q. How big is the circuit?**
AGQO's noiseless choice: p = 6, all 120 pairs, 1,440 logical two-qubit gates. On IBM Heron after
routing: 4,355 native CZ, depth 4,863. The noise-aware choice: p = 2, 25 % of coupling mass,
11 logical → 16 native CZ.

**Q. How do you pick the final decision from 512 shots?**
Every sample is checked exactly for cash, fees, tax and caps; the affordable sample with the lowest
objective is executed. In all 12 test quarters the 512 shots contained the exact optimum
(best sampled gap 0, [06](figures/06_rounding_quality.png)).

**Q. How long does one decision take?**
On a laptop (2026-10-01, 20M VND): build the problem 0.008 s, enumerate all 65,536 states 0.12 s,
simulate the circuit and polish 1.0 s (`results/final/extras/examples.json`). The full 12-quarter
experiment with all baselines and 1,080-schedule training takes about 20 minutes on 8 CPU cores.

---

## 9. Evaluation and statistics

**Q. What is "success"?**
Success per shot = probability that one measurement gives an affordable lot decision within 5 % of
the exact optimum, on a normalised gap scale where 0 = optimal and 1 = a typical (median) affordable
portfolio. Exact enumeration of all 65,536 states gives the optimum and the median for every quarter.

**Q. Which baselines?**
Quantum (12 test quarters, same problems): random guessing (0.2 %), warm start only (3.1 %),
textbook QAOA p = 2 with COBYLA (1.1 %), random search over the design space, 3 seeds (7.7 %),
frozen schedule (23.8 %), oracle schedule that uses the test answer (25.2 %, an upper bound),
simulated annealing, exact enumeration. AGQO: 21.3 %.
Finance: naive nearest-lot rounding, greedy lot filling, equal weight 1/N in lots, exact rounding,
textbook-QAOA rounding, odd-lot execution, and buy-and-hold of three VN30 ETFs.

**Q. Where does the probability go?** ([A3](figures/A3_probability_flow.png))
AGQO puts 21 % of shots within 5 % of the optimum (3 % exactly optimal), 27 % over budget. Random
guessing puts 0.2 % near-optimal and 48 % over budget; textbook QAOA 1 % and 41 %. The circuit
moves probability from bad and unaffordable portfolios to good ones.

**Q. Which statistical tests?**
- Circuits: paired per quarter, **Wilcoxon signed-rank** (two-sided) and a bootstrap interval for
  the ratio of means. With 12 quarters, 12/12 wins gives the smallest possible p = 0.0005.
- Tracking error: **moving-block bootstrap** of the paired daily active returns (21-day blocks,
  2,000 resamples; Künsch 1989), 95 % percentile interval for the TE difference. Blocks keep the
  autocorrelation and volatility clustering of daily returns.

**Q. Multiple comparisons?**
The three main circuit comparisons each have p = 0.0005; Bonferroni over all 7 circuit tests on the
board would still leave them at p ≤ 0.004. The finance claim at 20M has a CI far from zero. Results
near the line (greedy at 20M, 100M vs naive) are labelled "not significant".

**Q. Could the schedule have been tuned on the test set?**
No. Every choice was fixed on 2023 before testing, and the oracle arm shows how much a test-tuned
schedule would add (25.2 % vs 21.3 %): little. The frozen schedule beats the learned one on test,
which is the opposite of what overfitting to test would produce.

**Q. Why only 12 test quarters?**
Quarterly decisions from 2024 to 2026 give 12. Daily returns between decisions (711 days) feed the
tracking-error bootstrap, and monthly rebalancing (one decision per month) is in the robustness
study.

---

## 10. Hardware, noise and scaling

**Q. Did you run on a real quantum computer?**
Not yet; it needs an IBM token and queue time, and the command is ready
(`python -m agqo hardware --qasm results/final/circuits/<file>.qasm --confirm`). Instead we
transpiled every circuit to **FakeKingston**, a 156-qubit IBM Heron r2 backend with calibrated
error rates (median CZ error 0.18 %), at optimisation level 3, and ran full **Aer noise
simulations** (1,000 shots) on 3 test quarters ([A5](figures/A5_hardware.png)).

**Q. What happens under noise?**
| circuit | native CZ | ESP | noiseless success | noisy success (ESP model) | Aer |
|---|---:|---:|---:|---:|---:|
| warm start only | 0 | 0.92 | 4.5 % | 4.2 % | 5.0 % |
| textbook QAOA p = 2 | 1,393 | 0.05 | 1.8 % | 0.2 % | — |
| AGQO deep (p = 6, all pairs) | 4,355 | 0.0002 | 32.1 % | 0.1 % (≈ random) | — |
| AGQO shallow (p = 2, 75 %) | 189 | 0.58 | 9.2 % | 7.3 % | 7.8 % |
| **AGQO noise-aware (p = 2, 25 %)** | **16** | **0.88** | 7.7 % | 6.6 % | 7.8 % |

(Means over the 3 quarters run in Aer.) ESP = Π(1 − error) over all gates; noisy success = ESP ×
noiseless + (1 − ESP) × random. The full Aer simulation lands close to, and slightly above, the ESP
model. The deep circuit is the best in noiseless simulation and useless on today's hardware.

**Q. So what is the hardware-ready circuit?**
The **noise-aware AI guidance**: fit log ESP = a + b × logical CX on the transpiled circuits
(b = −0.0060 per gate), then choose, from a supplementary 2023 table (p ∈ {1,2}, ε, m ∈ {0.25, 0.5,
0.75, 1.0} and ramps), the schedule with the best *expected noisy* success on the 48 training
problems. It picks p = 2, ε = 0.02, m = 0.25, Δγ = 0.35, Δβ = 1.0. On all 12 test quarters its noisy
success is 4.5 % vs 2.8 % for the warm start (**1.6×, 11/12, p = 0.0010**). On the 3 Aer quarters the
75 % shallow variant does slightly better (7.3 % vs 6.6 %); the noise-aware choice was fixed on 2023.

**Q. When would the deep circuit work?**
To keep half its noiseless advantage (ESP 0.5), the two-qubit error would have to fall to about
0.016 %, about 11× below today's median 0.18 %. That is the hardware milestone the design needs.

**Q. How does it scale?** ([A6](figures/A6_scaling.png))
| qubits | states | enumeration | statevector | warm start | AGQO frozen 2023 schedule |
|---:|---:|---:|---:|---:|---:|
| 8 | 256 | 0.5 ms | 0.6 ms | 6.9 % | 30.0 % |
| 12 | 4,096 | 6.7 ms | 2.6 ms | 3.2 % | 22.0 % |
| 16 | 65,536 | 0.13 s | 0.04 s | 1.6 % | 17.1 % |
| 20 | 1,048,576 | 2.4 s | 2.5 s | 0.8 % | 12.9 % |

The same 2023 schedule, applied unchanged, beats its warm start 4.3× at 8 qubits and 16.7× at 20:
the advantage *over the warm start* grows with size. Enumeration time grows as 2ⁿ (60 qubits would
take ~10⁵ years at this rate); the circuit grows as n² gates per layer. Simulated annealing stays
near-optimal at 20 qubits (within 5 % in 11/12 quarters, exact in 1/12), so the classical heuristic
remains the bar to beat.

**Q. Where could a quantum advantage come from, if ever?**
Not at 16 qubits. The honest path: larger registers (full VN30 with multi-lot encoding, ~60 qubits;
multi-period rebalancing), shallow noise-aware circuits as error rates fall, and comparison with the
best classical heuristics at each size. AGQO's pipeline (exact objective, cap-safe register,
data-driven design, noise-aware selection) is built to make that comparison fair when it becomes
possible.

---

## 11. Honest negatives

| finding | status |
|---|---|
| No quantum advantage: enumeration is exact in 0.12 s, annealing near-optimal | not claimed |
| Learned schedule vs frozen schedule on test: 7/12, p = 0.47 | no gain |
| Training-chosen polish on test: 21.3 % vs 24.0 % without it, p = 0.42 | no gain |
| 100M VND without rules: −0.07 pp TE, CI −0.19 to +0.04 | not significant |
| Greedy lot filling at 20M (quarterly): −0.69 pp, CI −1.53 to +0.02 | not significant (monthly: significant) |
| Return vs E1VFVN30: −1.1 %/yr | trails |
| Deep circuit on Heron noise: ESP ≈ 0.0002 | fails today |
| Odd lots track better unless they cost > 6.8 % (20M) / 2.6 % (100M) extra | alternative |
| Explainer meaning check: first prompt 0/12, fixed prompt 11/12 (one sentence omits "VN30") | fixed, 1 flagged |

All of these are on the evaluation board ([A8](figures/A8_evaluation_board.png)).

---

## 12. Engineering, cost and deployment

**Q. How do I reproduce everything?**
```bash
pip install -e '.[quantum,llm,dev]'
python -m agqo download          # data
python -m agqo mandates --llm replay
python -m agqo run               # ~20 min, 8 cores
python -m agqo explain --llm replay
python -m agqo extras            # judge studies: hardware, scaling, robustness, odd lots, greedy
python -m agqo report            # figures + docs/RESULTS.md
pytest -q
```
`--llm replay` uses the logged answers (no GPU); `--llm modal` re-runs Qwen3.8 live.

**Q. How much did it cost?**
LLM: about 1–2 USD of H100 time for all live runs (plus a one-off 31 GB weight download). Quantum:
CPU only. The whole project ran within a 30 USD Modal trial.

**Q. Is it ready for users?**
The pipeline produces a decision for today (`results/final/latest_trades.csv`) with a Qiskit circuit
and a Vietnamese note. Before a public release: real user instructions for the LLM test set, an
odd-lot option in the register, regeneration of explanations that fail a check, a broker-API order preview (orders
stay with the user), and a live IBM hardware run of the noise-aware circuit.

**Q. How is the code checked?**
22 unit tests, including: the QUBO equals the financial objective plus penalty on all 65,536 states;
every register state obeys the caps; the Qiskit circuit matches the simulator; the explainer
verifier catches invented numbers; the greedy baseline buys only affordable whole lots.

---

## 13. Regulation, ethics and responsibility

**Q. Is this investment advice?**
No. AGQO proposes trades for the investor to review and executes nothing. The explainer is told not
to promise returns or give advice, and every number it writes is checked.

**Q. Privacy?**
The LLM runs on open weights in our own Modal account; investor instructions are not sent to a third-
party model provider. The log stores prompts for reproducibility; a production version would store
only hashes for user data.

**Q. Fairness to small investors?**
The method's main benefit is for small accounts, which institutional tools ignore. It also shows the
investor the price of personal rules (e.g. +3.8 pp TE for excluding real estate and capping banks),
so the choice is informed.

**Q. Did you use AI to build this?**
Yes, an AI coding assistant helped write code and documents under the team's direction; the team
chose the method, reviewed every result and can explain every component. The product's own LLM is
the open-weight Qwen3.8-27B.

---

**Sources for market facts.** Account numbers: VSDC data reported by Doanh nhân / Báo Pháp luật,
6 Nov 2026 ("Nhà đầu tư trong nước mở thêm hơn 252.000 tài khoản chứng khoán trong tháng 10").
Odd-lot trading on HOSE since 12 Sep 2022: HOSE announcement, reported by VnBusiness; broker guide
(DSC, "Hướng dẫn giao dịch lô chẵn, lô lẻ"). Literature: see [METHODS.md](METHODS.md#references).
