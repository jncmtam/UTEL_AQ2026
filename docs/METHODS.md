# Methods

This page gives the exact mathematics behind every number in [RESULTS.md](RESULTS.md).
Code references point to the module that implements each step.

## 1. The decision

A retail account with NAV $V$ (default 100 million VND) tracks the VN30 index with a
small basket bought in whole **board lots** of 100 shares. Every quarter it decides how
many lots of each stock to hold. Commission is 0.15 % per side and the sale tax is 0.1 %.

The market-analysis step (LLM or rule) chooses a **register** of $n=8$ candidate stocks.
For stock $i$ the decision is an integer number of *position units* $q_i \in \{0,1,2,3\}$,
encoded with $b=2$ qubits: $q_i = x_{i,0} + 2x_{i,1}$. One unit is $u_i$ lots, sized by
the compiler so a unit is roughly $V \cdot 0.98 / (1.5\,n)$ (`backtest.build_instance`).

Weights are linear in the bits:

$$w_i = a_i q_i,\qquad a_i = \frac{u_i \cdot 100 \cdot P_i}{V},\qquad w = A x .$$

## 2. Objective: exact, not a proxy (`portfolio.Instance`)

Using 250 trading days of returns strictly before the decision date, let $S$ be the joint
covariance of $[r_1..r_n, r_{\text{VN30}}]$ shrunk 5 % towards its diagonal (keeping it PSD),
with blocks $\Sigma$ (assets), $c$ (asset–index) and $\sigma_b^2$ (index). Cash earns zero.

$$F(w) = \underbrace{252\,(w^\top\Sigma w - 2w^\top c + \sigma_b^2)}_{\text{tracking error}^2}
\;-\; \eta\,\mu^\top w \;+\; \gamma\,\lVert w - w_{\text{prev}}\rVert^2$$

* $\mu$: Black–Litterman active views (zero prior relative to the index) built from the
  analyst's views $v_i\in\{-2..2\}$ and confidences $c_i$: $P=I$, $q=0.025\,v$,
  $\Omega=\text{diag}((1-c)/c\cdot\tau\sigma_i^2)$, $\tau=0.05$ (`portfolio.black_litterman`).
* $\eta = 0.02$, $\gamma = 0.002$.

Because every term is quadratic in $w=Ax$, the QUBO
$E(x) = x^\top Q x + h^\top x + \text{const}$ **is** the discrete objective plus one
calibrated penalty $\lambda(\mathbf 1^\top w-0.98)^2$, $\lambda=0.005$. The test
`test_qubo_is_exact_objective_plus_penalty` checks this identity to $10^{-12}$ on all
65,536 bitstrings. (AGQO v1 optimised an equal-weight proxy whose optimum lost 3–11 %
after allocation; that gap is gone by construction.)

Affordability is checked exactly: cash after buying, selling, commission and tax must be
non-negative (`Instance.cash_after`). Infeasible bitstrings are never executed.

The Ising form for the circuit uses $x=(1-z)/2$ (`Instance.ising`), verified against the
QUBO in `test_ising_matches_qubo`.

## 3. Ground truth and the success metric

With 16 qubits every bitstring is enumerated (`portfolio.landscape`), giving the exact
constrained optimum $F^\*$ and the median affordable portfolio $F_{\text{med}}$. The
**normalised gap** of a portfolio is

$$g(x)=\frac{F(x)-F^\*}{F_{\text{med}}-F^\*}\quad(0=\text{optimal},\;1=\text{typical random portfolio}).$$

A measurement **succeeds** when $x$ is affordable and $g(x)\le 0.05$. Typically 5–12 of the
65,536 bitstrings qualify, so random guessing succeeds with ≈0.01 % per shot.
Reported quantum metrics: success probability per shot, probability that a 512-shot batch
contains a success $1-(1-p)^{512}$, feasible probability mass, and the gap of the best
sampled portfolio.

## 4. The circuit and its design space (`quantum/spec.py`, `quantum/simulator.py`)

QAOA with $p$ layers: $|\psi\rangle = \prod_k U_M(\beta_k)\,e^{-i\gamma_k H_C}|\psi_0\rangle$,
with $H_C$ the Ising Hamiltonian scaled to unit maximum coefficient (so angles transfer
across dates). The LLM chooses a `CircuitSpec`:

| field | options | meaning |
|---|---|---|
| `layers` | 1–6 | QAOA depth $p$ |
| `initial_state` | `uniform`, `warm_start` | $\lvert+\rangle^{\otimes n}$ or $\bigotimes R_y(\theta_i)\lvert0\rangle$, $\theta_i=2\arcsin\sqrt{c_i}$ from the convex relaxation |
| `mixer` | `x`, `warm_x` | $e^{-i\beta X}$ or the warm-start mixer $R_y(\theta)R_z(-2\beta)R_y(-\theta)$ of Egger et al. (2021) |
| `warm_start_epsilon` | 0–0.5 | clip relaxed values to $[\epsilon,1-\epsilon]$ |
| `coupling_keep_fraction` | 0.1–1 | keep the strongest ZZ terms in the phase separator (fewer CX); scoring always uses the full objective |
| `angle_init`, `ramp_dt` | ramp / constant | annealing-like initial schedule |
| `optimizer`, `max_iter` | COBYLA, Nelder–Mead, none | classical loop (none = fixed schedule) |
| `cvar_alpha` | 0.02–1 | CVaR training loss (Barkoutsos et al. 2020) |

The **verifier** rejects specs that are out of range, misaligned (`warm_x` without its
eigenstate as the initial state, following He et al. 2023), or above the 1,500 two-qubit
gate budget (2 CX per kept coupling per layer) before any simulation.

Simulation is an exact numpy statevector; `test_statevector_normalised_and_qiskit_agrees`
confirms the Qiskit compilation (`quantum/export.py`) gives identical probabilities.

## 5. LLM agents (`llm/`)

**Market analyst.** Input: point-in-time features computed by code (liquidity share, beta,
correlation, 60-day volatility, 20/60/250-day returns, drawdown, relative strength, lot
value) for every usable VN30 member, plus a benchmark summary. Tickers are replaced by
shuffled ids (S01…) and dates are hidden, so the model cannot recall later prices of a
named stock. Output (JSON-schema constrained): regime, exactly 8 ids, views with
confidence, short rationale. Invalid ids are repaired from the greedy rule and every
repair is logged.

**Circuit architect.** An evolutionary loop in the style of FunSearch/AlphaEvolve:
round 0 proposes 6 specs from a numerical summary of the training Hamiltonians; each later
round sees the scored leaderboard plus rejected specs with reasons and proposes 6 more.
Every proposal passes the verifier and an exact evaluator. The best spec is **frozen** and
reused on unseen dates with no further LLM calls.

**Controls with the same budget** (4 rounds × 6 designs): textbook default, uniform random
search, and classical mutation-based evolution. This isolates what the LLM adds beyond
search itself.

## 6. Evaluation protocol

* Rebalance dates: first trading day of each quarter, Jan 2023 – Jul 2026 (15 dates).
* Circuit design uses only the first 4 quarters (2023). Quantum diagnostics are reported on
  the remaining 11 quarters.
* Each strategy runs its own account from 100M VND cash, with exact lots, commission and
  tax; holdings drift with prices between rebalances.
* Realised tracking error = annualised standard deviation of daily (portfolio − VN30)
  returns, Jan 2023 → Oct 2026.
* Baselines: continuous min-TE over all members with nearest-lot rounding and budget trim
  (practitioner), liquidity top-8, greedy tracking-error top-8 (strong classical), the exact
  discrete optimum, simulated annealing.

## 7. Known limitations

* Prices are provider-adjusted closes; lot costs before 2026 use adjusted prices.
* 1–5 historical members per date lack a price file (listed in `coverage.csv`); the
  universe is therefore slightly survivor-biased.
* VN30 is a price index, while adjusted closes include distributions.
* 16 qubits are simulated exactly; this demonstrates design quality, not quantum advantage.
  Exhaustive enumeration solves the same instance instantly.
* LLM pre-training may contain market history; anonymisation reduces but cannot remove this.

## References

* Egger, Mareček, Woerner (2021). Warm-starting quantum optimization. *Quantum* 5, 479.
* He et al. (2023). Alignment between initial state and mixer improves QAOA performance for constrained optimization. *npj Quantum Information* 9, 121.
* Barkoutsos et al. (2020). Improving variational quantum optimization using CVaR. *Quantum* 4, 256.
* Hodson et al. (2019). Portfolio rebalancing experiments using the Quantum Alternating Operator Ansatz. arXiv:1911.05296.
* Tyagin et al. (2025). QAOA-GPT: efficient generation of adaptive and regular QAOA circuits. arXiv:2504.16350.
* Novikov et al. (2025). AlphaEvolve: a coding agent for scientific and algorithmic discovery. arXiv:2506.13131.
* Yu et al. (2025). QUASAR: quantum assembly code generation using tool-augmented LLMs via agentic RL. arXiv:2510.00967.
* Lee et al. (2025). LLM-enhanced Black–Litterman portfolio optimization. arXiv:2504.14345.
* Agliardi et al. (2025). Portfolio construction using a sampling-based variational quantum scheme (IBM/Vanguard). arXiv:2508.13557.
* Stopfer, Wagner (2025). Quantum portfolio optimization: an extensive benchmark. arXiv:2509.17876.
* Koch et al. (2025). Quantum Optimization Benchmarking Library — the intractable decathlon. arXiv:2504.03832.
