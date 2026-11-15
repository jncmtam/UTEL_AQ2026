# Methods

This page gives the exact mathematics behind every number in [RESULTS.md](RESULTS.md).
Code references point to the module that implements each step.

AGQO = **AI-guided quantum optimisation**. **Phase 1** extracts decision-relevant structure from the
market data and the investor's instruction (`agqo/insight.py`, `agqo/llm/tasks.py`). **Phase 2**
turns that structure into a QAOA circuit by fixed rules plus a learned schedule model
(`agqo/quantum/design.py`). Classical solvers and exact enumeration are the yardstick throughout.
Every calibration uses 2023 only; every reported result is from 2024 onward.

## 1. Data (`agqo/download.py`, `agqo/data.py`)

* Daily OHLCV, Jan 2022 – Nov 2026, from the keyless DNSE chart API, for **every stock that
  was ever a VN30 member** in that period (40 stocks), the VN30 and VN-Index levels, and the
  three VN30 ETFs (E1VFVN30, FUESSV30, FUEKIV30). SHA-256 and coverage in `data/vn30/manifest.json`.
* Point-in-time membership from HOSE review announcements (source URL per row). At each
  rebalance date only the 30 members effective that day are eligible; a member needs 180 of
  the previous 250 sessions to be usable (`MarketData.universe`).
* Equity prices are provider back-adjusted for stock dividends and splits: across 40 stocks
  and nearly five years, a handful of moves exceed the ±7 % HOSE daily limit, and those are
  listed for review in the manifest. Returns are therefore usable; historical price *levels*
  (and so historical lot costs) are lower than the prices traded at the time.
* Days without a trade carry the last price for valuation (`MarketData.px`).

## 2. The decision (`backtest.build_rounding_instance`)

A retail account with NAV $V$ (default 100 million VND) tracks VN30 in whole **board lots**
of 100 shares, rebalanced on the first trading day of each quarter. Commission is 0.15 % per
side, sale tax 0.1 %.

1. A continuous minimum-tracking-error QP over all usable members allowed by the investor's
   mandate (§8) gives target weights $w^c$, subject to its caps.
2. Converting $w^c$ to lots, the 16 stocks where rounding matters most (lot value × distance
   of the fractional lot count from an integer) each get one qubit: $x_k = 1$ adds one lot of
   stock $j(k)$ to its floor. Every other stock takes its nearest lot.
3. **Constraint-aware register.** A stock in a capped group (a sector cap or a per-stock cap)
   only gets a qubit if the group's floor weight plus one lot for *every* qubit in the group still
   fits under the cap; otherwise it stays at its floor lot and the qubit goes to the next stock.
   The fixed part is trimmed until it fits too. Hence every one of the $2^n$ states obeys the
   investor's caps by construction, and the Hamiltonian stays exactly the financial objective
   (pairwise conflict penalties were tried first and failed: three extra lots can break a cap
   that every pair respects, and a QUBO cannot penalise triples). The minimum-cash rule is
   checked exactly on every sample.

Weights are affine in the bits, $w = w_{\text{base}} + A x$, with $A_{j(k),k}=a_k = 100P_{j(k)}/V$.

## 3. Objective: exact, not a proxy (`portfolio.Instance`)

With $S$ the joint covariance of $[r_1..r_n, r_{\text{VN30}}]$ over 250 sessions before the
date, shrunk 5 % towards its diagonal (blocks $\Sigma$, $c$, $\sigma_b^2$):

$$F(w) = 252\,(w^\top\Sigma w - 2w^\top c + \sigma_b^2) + \gamma\,\lVert w - w_{\text{prev}}\rVert^2,\qquad \gamma=0.002 .$$

The QUBO $E(x)=x^\top Qx+h^\top x+\text{const}$ **is** $F$ plus one budget penalty
$\lambda(\mathbf 1^\top w-t)^2$ with $t$ the invested target. `test_qubo_is_exact_objective_plus_penalty`
checks the identity to $10^{-12}$ on all 65,536 bitstrings. Affordability (cash after trades,
commission and tax $\ge 0$) is checked exactly on every sample; infeasible bitstrings are
never executed; if no sample passes, the floor-rounded portfolio (always inside every cap) is
executed and counted as a fallback. The Ising form uses $x=(1-z)/2$ (`Instance.ising`).

Training problems: the first trading day of each month of 2023 × account sizes {50, 100, 200,
500}M VND = 48 problems. $\lambda$ is the largest value in $\{0.001,\dots,0.02\}$ whose QUBO ground
state is the affordable optimum on the most training problems (a stronger penalty keeps more
sampled mass affordable without moving the optimum).

## 4. Phase 1 — value extracted from the data (`agqo/insight.py`)

**Market insight** (per rebalance date, data before the date):

| quantity | definition | why it matters |
|---|---|---|
| average correlation | mean off-diagonal daily-return correlation | how much the members move as one |
| market-factor share | $\lambda_{\max}(C)/n$ of the correlation matrix | one factor dominating means few stocks can track the index |
| effective bets | $\exp(-\sum_i s_i \ln s_i)$, $s_i=\lambda_i/\sum\lambda$ (Meucci 2009) | how many independent risks the index really has |
| correlation clusters | average-linkage on $d=\sqrt{2(1-\rho)}$, cut at $\rho=0.5$ (Mantegna 1999) | groups whose lot decisions interact |
| lot cost | one lot as % of NAV | how coarse whole lots are for this account |
| rounding cost | TE of nearest-lot rounding vs the continuous optimum and the exact whole-lot optimum | how much value naive rounding leaves |

**Hamiltonian insight** (what the market structure implies for the lot problem's qubits):

| quantity | definition | used by |
|---|---|---|
| warm-start probabilities $x^*$ | continuous relaxation of the QUBO on $[0,1]^{16}$ | R1, R2 |
| warm-start confidence | mean $\lvert 2x^*-1\rvert$ | diagnostic of R1 |
| coupling decomposition | $J_{kl}= \tfrac12 a_k a_l\,(252\,\Sigma_{j(k)j(l)}) + \tfrac12 a_k a_l\,\lambda$ = co-movement + budget | R3 |
| coupling concentration | fewest pairs holding 90 % of $\sum J^2$ | R3 |
| RMS scale | $\sqrt{\text{mean}(h_k^2, J_{kl}^2)}$ | R4 |

Fields that need the enumerated answer (feasible fraction, number of near-optimal states,
gap of nearest rounding) are **diagnostics only**; the designer never reads them.

## 5. Phase 2 — insight-driven circuit and optimiser (`agqo/quantum/design.py`)

QAOA with $p$ layers, $|\psi\rangle=\prod_k U_M(\beta_k)\,e^{-i\gamma_k H_C/s}|\psi_0\rangle$:

| rule | element | choice | source |
|---|---|---|---|
| R1 | initial state | $\bigotimes_k R_y(\theta_k)\lvert0\rangle$, $\sin^2(\theta_k/2)=\text{clip}(x^*_k,\epsilon,1-\epsilon)$ | Egger, Mareček & Woerner 2021 |
| R2 | mixer | $R_y(\theta_k)R_z(-2\beta)R_y(-\theta_k)$, whose ground state is the R1 state | He et al. 2023 (alignment) |
| R3 | phase separator | fields $h_k$ plus the strongest ZZ pairs covering 90 % of $\sum J^2$ | data-driven pruning; scoring keeps all terms |
| R4 | scale | $s$ = RMS of the kept coefficients, so one schedule fits every quarter | Sureshbabu et al. 2024 |
| R5 | schedule | $\gamma_k=\Delta_\gamma\tfrac{k+1/2}{p}$, $\beta_k=\Delta_\beta(1-\tfrac{k+1/2}{p})$ | LR-QAOA, Montañez-Barrera & Michielsen 2025 |

**AI guidance of the schedule.** A schedule is $s=(p,\epsilon,m,\Delta_\gamma,\Delta_\beta)$ with
$p\in\{2,4,6,8\}$, $\epsilon\in\{0.02,0.05,0.10\}$, coupling mass $m\in\{0.75,0.90,1.00\}$ and six by
five ramp heights: 1,080 schedules, each run with no optimiser on each of the 48 training problems
(exact statevector), giving a success table $S_{i,s}$. A new quarter is described by five insight
features computed without enumeration: warm-start confidence, share of decided qubits,
$\log(\text{RMS}(h)/\text{RMS}(J))$, coupling concentration, mean lot weight. The model picks
$\arg\max_s \tfrac1k\sum_{i\in\text{kNN}} S_{i,s}$ over the $k$ most similar training problems in standardised
feature space (instance-similarity parameter transfer). $k\in\{3,5,10,20,\text{all}\}$ is chosen by
leave-one-month-out cross-validation; $k$ = all is one frozen schedule.

**Optimiser.** A 40-step COBYLA polish on CVaR$_{0.1}$ of the full QUBO energy (Barkoutsos et al.
2020) is applied only if it raises mean success on the 48 training problems (`polish_check`); the
AI-chosen schedule with that decision is **AGQO's circuit**. Ablations: the frozen schedule, the
opposite polish decision, and an *oracle* that picks the best schedule using the test answer (an
upper bound, not a method).

The Qiskit compiler (`quantum/export.py`) uses the same pruning and scale as the simulator;
`test_designed_circuit_is_valid_and_qiskit_agrees` checks identical probabilities.

## 6. Ground truth and quantum metrics

Every one of the $2^{16}$ bitstrings is enumerated (`portfolio.landscape`), giving the exact
constrained optimum $F^*$ and the median affordable portfolio $F_{\text{med}}$. The
normalised gap is $g(x)=(F(x)-F^*)/(F_{\text{med}}-F^*)$. Reported per quarter:

* **success per shot**: P(affordable and $g\le 0.05$);
* **beats rounding**: P(affordable and $F(x) < F(x_{\text{nearest}})$), where $x_{\text{nearest}}$ is the
  practitioner's nearest-lot rounding: the "better solution probability" of arXiv:2409.09012,
  the right test for a circuit that starts from a classical solution;
* P(≥ 1 success in 512 shots), feasible mass, best sampled gap, optimiser calls, CX gates.

Comparators on the same 12 test quarters: random guessing, **warm start only** (the R1 state
measured with zero quantum layers), textbook QAOA (uniform start, X mixer, p = 2, COBYLA),
random search over the whole design space (24 designs on the four 2023 quarters, 3 seeds),
the frozen schedule, simulated annealing, and exact enumeration. Circuits are compared per
quarter with the Wilcoxon signed-rank test and a bootstrap interval for the ratio of means
(`agqo/stats.py`).

## 7. Financial evaluation

* 12 quarterly decisions, Jan 2024 – Oct 2026, held to the latest data. Every strategy runs its
  own account from cash.
* Strategies: practitioner (the same QP, nearest whole lot, trimmed until affordable), equal
  weight 1/N in lots, exact lot rounding (classical reference), textbook QAOA rounding,
  **AGQO** (AI-guided QAOA rounding), and buy-and-hold of each VN30 ETF in whole lots.
* Tracking error vs VN30 = annualised std of daily (portfolio − index) returns; weekly TE is
  also reported because ETF market prices carry daily noise around NAV. VN30 is a price index,
  so "active return" includes dividends; "vs ETF" compares with E1VFVN30, which includes them.
* TE differences: moving-block bootstrap of the paired daily active returns (21-day blocks,
  2,000 resamples; Künsch 1989), 95 % percentile interval.
* Account-size sweep: 20M, 50M, 100M, 200M, 500M VND on the same quarters.
* **Greedy lot filling** (`extras.greedy_target`), a strong classical heuristic: start from the
  floor lots of the QP target and repeatedly add the single lot that lowers $F$ (tracking
  variance + turnover) the most, while the spend stays within
  $V(1-2c)\min(0.985,\ t+0.005)$; stop when no affordable lot lowers $F$.

## 8. Investor mandates and the LLM (`agqo/mandate.py`, `agqo/llm/`)

The LLM (Qwen3.8-27B, official FP8 checkpoint pinned to revision `c3a462cc`, vLLM 0.32 on one
Modal H100, non-thinking mode, JSON-schema-constrained decoding, top-p 0.8, top-k 20, fixed seed per
request) has two jobs; neither can change a number that reaches the optimiser unchecked. The mandate
compiler runs at temperature 0, the explainer at 0.3.

1. **Mandate compiler.** Input: a Vietnamese instruction plus the ticker/sector list. Output:
   excluded tickers and sectors, sector caps, per-stock cap, maximum holdings, minimum cash, or a
   clarification question when a limit has no number. Code validates every field and applies
   it: exclusions remove qubits and weights, caps become QP constraints and shape the qubit
   register (§2.3), maximum holdings re-solves the QP on the largest weights, minimum cash lowers
   the invested target and is checked on every sample. Compliance is re-checked on every executed
   portfolio (weights at the decision-time NAV). Evaluated on
   35 hand-labelled instructions against a keyword-rule parser; reported as strict JSON match and
   effective-constraint match (limits that cannot bind, such as 0 % cash, count as absent).
2. **Explainer.** Input: a code-built evidence pack per quarter (trades in lots, tracking errors
   of AGQO vs nearest rounding vs fractional ideal, sector weights, quantum success and gap,
   market insight). Every evidence field names its reference (`tracking_error_vs_vn30_index_pct`,
   `vn30_market_structure`, ...) and carries a Vietnamese label (`describe_evidence`). Output: a
   Vietnamese summary, trade notes and risk notes. **Number check:** every number in the text must
   appear in the evidence, and every trade note must match an executed trade. **Meaning check:** a
   tracking-error value must sit in a sentence that names VN30, and a VN30 market statistic must not
   share its clause with "danh mục" (portfolio); a consequence clause ("…, nghĩa là danh mục …") is
   allowed. Both pass rates are reported.

Every prompt, raw answer and token count is in `results/final/llm/llm_log.jsonl`;
`--llm replay` reproduces the results without a GPU.

## 9. Studies added for the judges (`agqo/extras.py`, `python -m agqo extras`)

All use the same data, test quarters and 2023 calibration; outputs in `results/final/extras/`.

**Measurement distributions** (`distributions.csv`). For each test quarter and circuit, the full
probability over the 65,536 decisions binned by normalised gap: optimal, ≤ 5 %, 5–25 %, 25–100 %,
worse than the median affordable portfolio, over budget.

**Hardware noise** (`hardware.csv`). Each circuit is transpiled to `FakeKingston`
(qiskit-ibm-runtime 0.50; 156-qubit IBM Heron r2 with calibrated gate errors) at optimisation
level 3, seed 7, for 3 test quarters. The estimated success probability is
$\text{ESP}=\prod_{g}(1-\varepsilon_g)$ over all transpiled gates and readouts, and the noisy
success is modelled as $\text{ESP}\cdot s_{\text{ideal}}+(1-\text{ESP})\cdot s_{\text{uniform}}$
(a global depolarising approximation). The warm-start and shallow circuits are also run in full
qiskit-aer 0.17 noise simulation with the backend's noise model (1,000 shots).

**Noise-aware guidance** (`hardware_aware.csv`, `hardware_aware.json`). Fit
$\log\text{ESP}=a+b\cdot n_{\text{CX}}$ on the transpiled circuits ($n_{\text{CX}}$ = logical
two-qubit gates; fitted $b=-0.0060$). Simulate a supplementary 2023 schedule table ($p\in\{1,2\}$,
$\epsilon\in\{0.02,0.05,0.10\}$, $m\in\{0.25,0.5,0.75,1.0\}$, ramp heights) on the 48 training
problems and choose the schedule with the largest mean *expected noisy* success
$e^{a+b n_{\text{CX}}}s_{\text{ideal}}+(1-e^{a+b n_{\text{CX}}})s_{\text{uniform}}$. Evaluate it on the
12 test quarters against the warm start under the same model (Wilcoxon), and in Aer on 3 quarters.
The two-qubit error that would give the deep circuit ESP 0.5 is
$\varepsilon^\*=1-0.5^{1/n_{\text{CZ}}}$ with $n_{\text{CZ}}$ its native CZ count.

**Scaling** (`scaling.csv`). Registers of 8, 12, 16, 20 qubits on the 12 test quarters: enumeration,
statevector and simulated-annealing times; success of random guessing, the warm start and the frozen
2023 schedule (RMS scaling makes it size-independent); logical CX count $2p\binom{n}{2}$.

**Robustness** (`robustness.csv`). Independent accounts walked forward from cash at 20M and 100M VND
for: commission 0.15 % (base), 0.10 %, 0.25 %; quarterly vs monthly rebalancing. Each scenario
compares the exact whole-lot decision with naive rounding and with greedy lot filling
(block-bootstrap CIs as in §7). The exact decision stands in for AGQO because AGQO's best sample
equalled it in 12/12 test quarters; it avoids re-simulating the circuit for every scenario.

**Odd-lot execution.** HOSE has matched odd lots (1–99 shares) since 12 Sep 2022. The odd-lot
account buys the ideal continuous weights in single shares; every trade pays the normal commission
and tax, and the odd-lot part of each trade (|Δshares| mod 100) pays an extra premium $\pi\in\{0,0.5,1,2\}\,\%$ of its
value for wider spreads. The break-even premium is where a straight-line fit of the return
difference (odd lots − AGQO) against $\pi$ crosses zero (`visuals.odd_lot_break_even`). Fill risk and
the thinner odd-lot order book are not modelled.

**One decision up close** (`examples.json`). A new account of 20M and 100M VND on the latest test
date: ideal, naive, greedy and AGQO weights, ex-ante TE of each, the coupling matrix and timings.

**LLM usage** (`llm_usage.json`). Input tokens recounted with the Qwen3.8 tokenizer (the live log
under-counted them; fixed in `modal_app.py`).

## 10. Known limitations

* Historical lot costs use back-adjusted prices (understated in the past); today's decision
  uses actual prices. Cash-dividend treatment by the provider is not independently verified.
* 12 test quarters is a short sample; the bootstrap intervals in RESULTS.md say which
  tracking-error differences are distinguishable from noise.
* The mandate test set (35 instructions) was written by the developers; it covers common
  phrasings but is not a sample of real user requests.
* The 16-qubit problem is enumerable classically in 0.12 s: results show design quality, not
  quantum advantage. One short simulated-annealing run is within 5 % of the optimum in 12/12 test
  quarters (exact in 6/12).
* The noiseless choice (p = 6) is too deep for today's hardware (ESP ≈ 0.0002 on Heron r2); only
  the noise-aware choice (16 native CZ) keeps an advantage under simulated noise. No run on real
  hardware yet.
* The explanation meaning check is rule-based (references of tracking errors and market statistics),
  not a full semantic review; 11/12 pass.

## References

* Egger, Mareček, Woerner (2021). Warm-starting quantum optimization. *Quantum* 5, 479.
* He et al. (2023). Alignment between initial state and mixer improves QAOA performance for constrained optimization. *npj Quantum Information* 9, 121.
* Sureshbabu et al. (2024). Parameter setting in quantum approximate optimization of weighted problems. *Quantum* 8. arXiv:2305.15201.
* Montañez-Barrera, Michielsen (2025). Towards a universal QAOA protocol: evidence of a scaling advantage in solving some combinatorial optimization problems. *npj Quantum Information* 11, 131. arXiv:2405.09169.
* Barkoutsos et al. (2020). Improving variational quantum optimization using CVaR. *Quantum* 4, 256.
* Künsch (1989). The jackknife and the bootstrap for general stationary observations. *Ann. Statist.* 17, 1217.
* Galda et al. (2021). Transferability of optimal QAOA parameters between random graphs. *IEEE QCE*.
* Shaydulin et al. (2023). Parameter transfer for quantum approximate optimization of weighted MaxCut. *ACM TQC* 4(3).
* (2024). The better solution probability metric: optimizing QAOA to outperform its warm-start solution. arXiv:2409.09012.
* Mantegna (1999). Hierarchical structure in financial markets. *Eur. Phys. J. B* 11, 193.
* Meucci (2009). Managing diversification. *Risk* 22(5), 74.
* Hodson et al. (2019). Portfolio rebalancing experiments using the Quantum Alternating Operator Ansatz. arXiv:1911.05296.
* Brandhofer et al. (2023). Benchmarking the performance of portfolio optimization with QAOA. *Quantum Information Processing* 22, 25.
* Stopfer, Wagner (2025). Quantum portfolio optimization: an extensive benchmark. arXiv:2509.17876.
