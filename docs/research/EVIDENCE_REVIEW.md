# Evidence review before model or algorithm selection

Review date: 2026-11-02. Status: decision evidence, not a model qualification.

## Reading order and evidence rules

1. Read this review for published measurements and their limits.
2. Read [DATA_SUITABILITY.md](DATA_SUITABILITY.md) for the actual downloaded data.
3. Read [TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) for the resulting choices.
4. Read [WORKLOG.md](WORKLOG.md) for completed actions, open questions and changes.

Reported paper results, our measured diagnostics, and our proposed design choices
are different kinds of evidence. A source result is not an AGQO result. A model
card is implementation evidence, not independent validation. This is a targeted
review of nearby work, not a claim of exhaustive coverage or a global best model.
Searches covered LLM quantum architecture/program generation, evaluator audits,
constrained QAOA, portfolio benchmarks and sparse tracker maintenance. Sources
were checked on the review date; exact paper versions are given below.

## Published experimental evidence

| ID / source | What was evaluated and measured | What can transfer | What cannot transfer |
|---|---|---|---|
| E1: [QGAS, arXiv:2307.08191v1, Table I](https://arxiv.org/html/2307.08191) | LLM-assisted ansatz search; portfolio example has four assets/qubits. QGAS: 31 gates, objective -0.01347, reference -0.0149; TwoLocal with three repetitions: 34 gates, -0.01303. | Architecture search can be evaluated by joint cost and gate resources. | Four-asset energy results do not establish portfolio performance, classical advantage or novelty of LLM-generated finance circuits. |
| E2: [Agent-Q, arXiv:2504.11109v2, Evaluation](https://arxiv.org/html/2504.11109v2) | Fine-tuning on graph optimization/QASM; syntactic correctness 171/200 = 85.5%. | Domain data and explicit execution checks are relevant. | Syntax is not optimality. These are not US equity mandate-repair tasks. |
| E3: [QUASAR, arXiv:2510.00967v1, Table 1](https://arxiv.org/html/2510.00967) | Qwen3-4B with SFT and agentic GRPO. Pass@1: syntactic correctness 99.31%; expectation-based success 22.41%; high-quality distribution ratio 17.24%. Pass@10 quality ratio 27.24%. | Quantum-specific post-training and simulator feedback justify including a small specialist. | Syntax success cannot be advertised as financial/circuit-design success. Energy and KL thresholds are specific to the paper, not AGQO thresholds. |
| E4: [QuanBench+, arXiv:2604.08570, Appendix B](https://arxiv.org/html/2604.08570) | 42 aligned tasks in three frameworks. Qiskit: Gemini-3-Pro 59.5% one-shot / 73.8% feedback; GPT-5.1 57.1% / 83.3%; DeepSeek-R1 50.0% / 71.4%. Up to five repairs are allowed. | Framework APIs and repair budgets materially affect results; use executable tests. | Different frameworks, token budgets and repair protocols cannot be merged into one universal ranking. No finance utility is measured. |
| E5: [Benchmarking the Quantum Leap, arXiv:2610.28678, Tables 2–3 and evaluator audit](https://arxiv.org/html/2610.28678) | Preprint: five suites, 530 tasks, plus 96 QBE tasks. Qiskit Hard: highest recorded pass@1 63.8%; no top-two comparison across the five suites survives within-suite multiplicity correction. Reports evaluator defects producing false passes/failures. | Audit the evaluator, use paired comparisons and report uncertainty before interpreting rankings. | The reported leaderboard is conditional on its harness, decoding and unresolved evaluator issues; first place is not proven superiority. |
| E6: [Quantum Verifiable Rewards, arXiv:2508.20907v1](https://arxiv.org/html/2508.20907) | Synthetic quantum problem/test pairs and DPO/GRPO post-training; experiments assess Qiskit-HumanEval and Hard. | Verification-driven training is an evidence-backed future option once valid training tasks exist. | Its training recipe is not evidence that untrained AGQO models understand mandates or that fine-tuning is currently necessary. |
| E7: [Extensive Portfolio Benchmark, arXiv:2509.17876v3, Abstract and Section 6](https://arxiv.org/html/2509.17876v3) | 270 real-data instances, up to 1,000 assets; quantum cases at most 30. MIP solves all studied instances to proven optimality in seconds; specialized heuristic beats quantum at fixed runtime. | Strong exact and problem-specific classical references are essential. | The result concerns the studied portfolio variants, not every possible finance problem. Nor does a huge combination count establish practical hardness. |
| E8: [Direct indexing with XY, arXiv:2602.14827v1, Sections IV–V](https://arxiv.org/html/2602.14827v1) | Ten US stocks, 2025 backtest, Dicke/XY selection and continuous allocation. Reports Sharpe 1.81 and monthly turnover 76.8%; uses SA/HRP references. Candidate rescoring accesses full simulated probabilities. | Provides a nearby end-to-end reference and highlights turnover. | No strong MIP comparison or LLM design study. Full-statevector candidate access is not a finite-shot hardware protocol. Sharpe is not a target to copy. |
| E9: [Low-Turnover Rebalancing, arXiv:2512.22109v2, Table 1](https://arxiv.org/html/2512.22109v2) | Classical maintenance of sparse trackers. Reports mean holding-window RMSE 20.556 bp, total sequential one-way turnover 5%, final 55 names. | Hold/repair decisions and turnover–tracking trade-offs need maintenance baselines. | Support size is not fixed at our K; turnover is cumulative over that horizon, not monthly. Values cannot be directly compared to AGQO. |
| E10: [ADAPT-QAOA, PR Research / arXiv:2005.10258v3](https://arxiv.org/abs/2005.10258) | Adaptive operator construction tested on Max-Cut; lower gate and parameter requirements than standard QAOA in its experiments. | A non-LLM adaptive architecture comparator is needed. | Max-Cut improvements do not establish improvement on constrained portfolios. A random mutation heuristic is not an ADAPT replication. |
| E11: [Dynamic-ADAPT-QAOA, PRA 109, 032420 (2024)](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.109.032420) | Density-matrix experiments, 6–10 qubits, dynamic decisions about costly operations; reports gate-error threshold above 1e-3 for its comparison. | Resource-aware operator selection and noise evaluation are relevant. | This is not a portfolio result; neither its threshold nor its approximation comparator transfers unchanged. |
| E12: [XY topology and warm starting, arXiv:2505.18396v2](https://arxiv.org/html/2505.18396v2) | Analyzes mixer generator algebras and evaluates restricted-generator pretraining/warm starting, including portfolio experiments. Restricted XY+RZ and full RZZ cost have different algebraic behavior. | Topology, parameter sharing and warm start deserve separate controlled comparisons. | A sparse mixer does not prove the full financial cost is efficiently trainable; correlation-based edges are a hypothesis, not a theorem. |
| E13: [Deterministic Dicke preparation, FCT 2019 / arXiv:1904.07358](https://arxiv.org/abs/1904.07358) | Gives an explicit preparation construction with O(kn) gates and O(n) depth, without ancillas. | A principled cardinality-state baseline exists; count its preparation resources. | Dense StatePreparation from an enumerated vector is not automatically the same efficient construction. |

## Consequences for novelty

Already established: LLM-assisted quantum finance architecture search (E1),
LLM/verifier loops (E2–E6), portfolio Dicke/XY selection plus allocation (E8),
low-turnover maintenance (E9), adaptive QAOA operator selection (E10–E12).
None should be claimed as a first contribution by AGQO.

Candidate contribution, still requiring a deeper novelty check: evidence-conditioned
circuit editing when a verified portfolio mandate changes, with conserved financial
semantics, explicit selection/allocation distortion, and comparisons against
classical adaptive design under complete resource accounting.

The contribution is useful only if an intervention demonstrates that the supplied
structure affects design quality on new cases. An explanation paragraph or a
larger model does not establish that relationship.

## Model evidence: candidates, not a chosen winner

| Candidate | Source and availability | Role and limitations | Current decision |
|---|---|---|---|
| QUASAR specialist | [Public checkpoint](https://huggingface.co/Benyucong/rl_quantum_4b), linked to E3; card lists Apache-2.0. | Most direct published QASM/optimization-domain evidence among this shortlist. Its native QASM interface differs from GateIR. | First specialist candidate. Check checkpoint provenance, native prompt, tokenizer and frozen revision before any inference. Native reproduction and GateIR transfer are distinct experiments. |
| Mistral-Small-3.2-24B-Qiskit | [Publisher model card](https://huggingface.co/Qiskit/mistral-small-3.2-24b-qiskit); Apache-2.0; trained for Qiskit 2.1. | Qiskit-specific engineering candidate; card results are publisher evidence. V3 uses a newer local SDK and a different design task. | Secondary specialist candidate, subject to runtime/interface verification. No claim it is best for portfolio architecture. |
| Existing Qwen Coder 30B | [Publisher card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct); existing pinned worker. | Cheap operational reference and existing exploratory evidence; no reviewed paper here validates this checkpoint for our financial circuit task. | Keep as general coder control; do not promote it by infrastructure convenience. |
| Existing Next-FP8 80B | [Publisher card](https://huggingface.co/Qwen/Qwen3-Coder-Next-FP8); existing pinned worker. | Larger general coding comparator; quantized checkpoint needs its own measurements. | Conditional escalation only after failure analysis predicts a relevant benefit. |
| 397B / 480B workers | Existing deployment configurations only. | No verified AGQO quality evidence and no paper-to-task justification identified in this review. | Defer. Worker availability and parameter count are insufficient reasons to spend. |

No global best LLM is established by the reviewed evidence. This review selects
an evidence-based comparison set, not a production model. Hosted model scores in
E4/E5 are contextual literature results, not a recommendation to buy additional
APIs or evidence that those exact endpoints are available in this environment.

## Open evidence gaps

- Verify exact specialist revision, licensing and native inference instructions.
- Inspect released evaluator code before reusing any benchmark scores.
- Check whether mandate-conditioned circuit editing is already covered by nearby
  publications; avoid an exclusive research-gap claim until that review is complete.
- Obtain robust primary evidence for the complete historical security lineage.
- Set financial non-inferiority margins from a stated account use case, not by
  copying energy/KL/Sharpe numbers from unrelated papers.

No more GPU model comparison is justified until the decision gates in
[TECHNICAL_DECISIONS.md](TECHNICAL_DECISIONS.md) are satisfied.

## Follow-up source review (2026-11-03)

The [author's sparseIndexTracking package](https://github.com/dppalomar/sparseIndexTracking)
and [CRAN record](https://stat.ethz.ch/CRAN/web/packages/sparseIndexTracking/index.html)
link to Benidis, Feng and Palomar, IEEE TSP 66(1), 155–170,
[DOI 10.1109/TSP.2017.2762286](https://doi.org/10.1109/TSP.2017.2762286).
Joint stock selection and weighting motivates our proxy audit. Its pinned
INDEX_2010 corpus supplies a conditional US algorithm comparison; the author's
full-year membership filter rules out treating it as unbiased investment evidence.
Package performance is not an AGQO measurement.

[Wang et al., XY mixers](https://arxiv.org/abs/1904.09314) study fixed-cardinality
mixing and the effect of initial states. This motivates symmetry-preserving
simulation and preparation controls. It does not guarantee broad exploration by a
single ordered exchange sweep, nor better financial outcomes on our corpus.
The measured contrary evidence and next gate are in
[COMPLETION_REPORT.md](COMPLETION_REPORT.md).

### Artifact identity check (no weights loaded)

Hugging Face's public model metadata API was queried on 2026-11-02:

| Checkpoint | Observed revision | Gated / disabled |
|---|---|---|
| `Benyucong/rl_quantum_4b` | `b9581279345436e2b7eadcdf80e4f1417748eb8b` | false / false |
| `Qiskit/mistral-small-3.2-24b-qiskit` | `0c541958022de04bd7c200b14a4b7a58977ae751` | false / false |

This verifies public artifact identity only. No weights were downloaded, model
loaded or GPU probe launched. Runtime compatibility and native-format fidelity
remain open. Preserve these revisions in any future registered experiment.
