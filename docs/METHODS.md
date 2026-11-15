# Methods

This page gives the exact mathematics behind every number in [RESULTS.md](RESULTS.md).
Code references point to the module that implements each step.

The pipeline has two phases. **Phase 1** extracts decision-relevant structure from the
market data (`agqo/insight.py`). **Phase 2** turns that structure into a QAOA circuit and
optimiser by fixed, explainable rules (`agqo/quantum/design.py`). Classical solvers and
exact enumeration are the yardstick throughout.

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

1. A continuous minimum-tracking-error QP over all usable members gives target weights $w^c$.
2. Converting $w^c$ to lots, the 16 stocks where rounding matters most (lot value × distance
   of the fractional lot count from an integer) each get one qubit: $x_k = 1$ adds one lot of
   stock $j(k)$ to its floor. Every other stock takes its nearest lot.

Weights are affine in the bits, $w = w_{\text{base}} + A x$, with $A_{j(k),k}=a_k = 100P_{j(k)}/V$.

## 3. Objective: exact, not a proxy (`portfolio.Instance`)

With $S$ the joint covariance of $[r_1..r_n, r_{\text{VN30}}]$ over 250 sessions before the
date, shrunk 5 % towards its diagonal (blocks $\Sigma$, $c$, $\sigma_b^2$):

$$F(w) = 252\,(w^\top\Sigma w - 2w^\top c + \sigma_b^2) + \gamma\,\lVert w - w_{\text{prev}}\rVert^2,\qquad \gamma=0.002 .$$

The QUBO $E(x)=x^\top Qx+h^\top x+\text{const}$ **is** $F$ plus one budget penalty
$\lambda(\mathbf 1^\top w-0.98)^2$. $\lambda$ is chosen on the 2023 training quarters only:
the smallest value in $\{0.001,\dots,0.02\}$ whose QUBO ground state is the affordable
near-optimum (`experiment._calibrate_penalty`). `test_qubo_is_exact_objective_plus_penalty`
checks the identity to $10^{-12}$ on all 65,536 bitstrings. Affordability (cash after trades,
commission and tax $\ge 0$) is checked exactly on every sample; infeasible bitstrings are
never executed. The Ising form uses $x=(1-z)/2$ (`Instance.ising`).

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

**Hamiltonian insight** (what the market structure implies for the 16-qubit problem):

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

Only four scalars are calibrated: $p\in\{1..6\}$, $\epsilon$, $\Delta_\gamma$, $\Delta_\beta$, by grid
search on the four 2023 quarters (`design.calibrate`, `results/*/design_calibration.csv`).
They are then **frozen** and transferred to every later quarter: the deployed circuit runs
with no classical optimisation loop. A second variant polishes the transferred angles with
40 COBYLA steps on CVaR$_{0.1}$ of the full QUBO energy (Barkoutsos et al. 2020).

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

Comparators on the same quarters: random guessing, **warm start only** (the R1 state
measured with zero quantum layers), textbook QAOA (uniform start, X mixer, p = 2, COBYLA),
random search over the whole design space with the same training data (3 seeds), simulated
annealing, and exact enumeration.

## 7. Financial evaluation

* 16 quarterly decisions, Jan 2023 – Oct 2026; the first 4 (2023) are the only data used for
  any calibration. Every strategy runs its own account from 100M VND cash.
* Strategies: QP + nearest-lot rounding (practitioner), equal weight 1/N in lots, QP + exact
  lot rounding (classical reference), QP + textbook QAOA, **AGQO: QP + insight-designed QAOA**,
  and buy-and-hold of each VN30 ETF in whole lots.
* Tracking error vs VN30 = annualised std of daily (portfolio − index) returns. Because VN30
  is a price index, "active return vs VN30" includes dividends; the **vs ETF** columns compare
  against E1VFVN30, which includes distributions and fund costs.

## 8. Known limitations

* Historical lot costs use back-adjusted prices (understated in the past); today's decision
  uses actual prices. Cash-dividend treatment by the provider is not independently verified.
* 16 quarters is a short sample; differences of a few basis points of tracking error are not
  statistically established (no confidence intervals yet).
* The 16-qubit problem is enumerable classically in milliseconds: results show design quality,
  not quantum advantage. Simulated annealing also finds the optimum.
* The designed circuit's depth is chosen for success in noiseless simulation; deep circuits
  will lose fidelity on today's hardware.

## References

* Egger, Mareček, Woerner (2021). Warm-starting quantum optimization. *Quantum* 5, 479.
* He et al. (2023). Alignment between initial state and mixer improves QAOA performance for constrained optimization. *npj Quantum Information* 9, 121.
* Sureshbabu et al. (2024). Parameter setting in quantum approximate optimization of weighted problems. *Quantum* 8. arXiv:2305.15201.
* Montañez-Barrera, Michielsen (2025). Towards a universal QAOA protocol: evidence of a scaling advantage in solving some combinatorial optimization problems. *npj Quantum Information* 11, 131. arXiv:2405.09169.
* Barkoutsos et al. (2020). Improving variational quantum optimization using CVaR. *Quantum* 4, 256.
* (2024). The better solution probability metric: optimizing QAOA to outperform its warm-start solution. arXiv:2409.09012.
* Mantegna (1999). Hierarchical structure in financial markets. *Eur. Phys. J. B* 11, 193.
* Meucci (2009). Managing diversification. *Risk* 22(5), 74.
* Hodson et al. (2019). Portfolio rebalancing experiments using the Quantum Alternating Operator Ansatz. arXiv:1911.05296.
* Brandhofer et al. (2023). Benchmarking the performance of portfolio optimization with QAOA. *Quantum Information Processing* 22, 25.
* Stopfer, Wagner (2025). Quantum portfolio optimization: an extensive benchmark. arXiv:2509.17876.
