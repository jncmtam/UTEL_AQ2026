# User guide

## Run a decision comparison

Start `.venv/bin/python -m agqo.research serve --output results/research/repair_trajectory_v2`
and open http://127.0.0.1:8765/. Edit the number of holdings, an exclusion, a sector
weight cap and one-way turnover. The application shows incumbent positions,
interpreted requirements, infeasibility diagnosis, comparable solver results,
proposed trades, and verification/resource metadata. All interface calculations
are local synthetic demonstrations. A saved QUASAR design, when present, is
revalidated against the current instance and labeled as replay.

Selecting the market candidate invokes the audit and explains the blocker. It
never silently replaces missing US securities or substitutes synthetic returns.

## Data admission contract

`data/us_equities/dataset_manifest.json` identifies the proposed historical cohort,
raw-source checksums and acquisition failures. To admit a market dataset, supply:

- Unique asset IDs and permanent identifiers, sourced ticker-effective histories,
  and explicit identity verification for every cohort member.
- Corporate-action entitlement and return reconciliation, including distributions
  to securities outside the inception cohort; an explicit treatment policy.
- Dated sector evidence (`sector`, `sector_effective_from`, `sector_source`) and
  a disclosed classification policy.
- A `review` record containing reviewer, review date, identity policy, corporate-
  action policy and sector policy, backed by the referenced evidence files.
- `processed_prices`: relative path and SHA256 of a CSV with sorted unique dates,
  one audited adjusted-total-return price per asset ID, and a DIA column. No missing
  or nonpositive prices. Include at least 253 observations.
- Verified membership/actions/sector flags only after source review. Setting flags
  is an attestation, not automatic proof of the source claims.
- Context records with source, publication/acceptance time, accession and checksum.
  They are filtered as of each decision; fiscal period-end is not publication time.

Run `agqo-research audit`. A failed gate returns exit code 2 and records the reasons.
Market trajectory execution produces the complete artifact contract even when
blocked. Raw provider data stays local; metadata and checksums are versioned.

## Model experiments

The evidence-based shortlist and checkpoint revisions are in the evidence review.
`probe --mode modal --models quasar4 --output NEW_DIRECTORY` tests native code and
GateIR transfer separately. The output contract is frozen before inference and
all failed outputs are saved. This is a bounded development probe, not model
qualification or reproduction of the original paper's full benchmark.

`smoke` supports development/validation/test structural splits, profile ablations,
and none/verifier/quality feedback. The three structural sizes are diagnostic;
they do not replace a sufficiently powered held-out market study. Cost includes
CPU prefetch, inference, invalid proposals and angle/allocator work. Specialist
runtime support for Mistral 24B is implemented but not qualified by a live run.

## Published US algorithm benchmark

Install `.[published-data]`, then run `agqo-research published-fetch` and
`agqo-research published-study --output NEW_DIRECTORY`. The pinned source has
252 observations and 386 identifiers. No R installation is needed. The decoder
preserves source dates, matrices and checksums; raw data stays local.

The command is CPU-only and rejects `--mode modal`. It compares three circuit
controls with uniform samples, allocation-aware swaps and SCIP, including a
30-asset/6-holding case. Families are chosen by a predeclared hash of source labels,
not by an LLM or future performance. The universe is conditioned on full-year
membership: the study cannot establish unbiased historical investment performance.

`published_development_v3` is the canonical current development bundle. It includes
the actual source snapshot and package versions. To reproduce those exact source
bytes, overlay `source_snapshot/agqo` on a checkout or set `PYTHONPATH` to the
snapshot while running from a checkout with the pinned local data. Keep any rerun
in a new output directory. Earlier v1/v2 intermediate runs are preserved.

`scripts/analyze_published_study.py NEW_DIRECTORY` audits proxy faithfulness and
covariance after the run; `scripts/plot_published_study.py NEW_DIRECTORY` creates
figures from those records. These are labeled post-run diagnostics, not a fresh
held-out experiment. The saved native specialist diagnostic is under
`results/research/quasar_native_diagnostics_v1`; no original probe score is changed.

## Reading results

Compare the original financial objective after common allocation. Inspect both
feasible probability and conditional quality; inspect support-proxy distortion.
Energy offsets, penalty energy, annualized tracking statistics and Sharpe values
have different meanings and cannot be interchanged.

`baseline` reports initialization resources, certified encoding and gradient-
adaptive controls. `trajectory` carries each method's account through drift and
fees with one-session execution lag. It starts with the same existing portfolio;
the first asset is excluded from the second decision onward. Hold is a true
no-trade action, even when that action becomes noncompliant.

`replay` validates the artifact contract and reads a saved report without model
calls. Use new output directories after changing a frozen protocol.

## Follow-up controls

`preparation-study` compares sparse exchange initialization with a compiler-owned
sequential counter-Dicke block and classical uniform draws. Workspace is counted
in QASM/resources even though ideal simulation removes it after proven cleanup.
`formulation-audit` enumerates small supports for continuous and explicitly
equal-weight target policies; it does not silently change the primary mandate.

`conditioning-study` compares raw and published Eq8 RMS optimizer coordinates with
a matched2176-draw classical reference under both financial policies. Numerical
code retains the canonical Hamiltonian and exports physical gamma angles. Direct
API calls may opt in using `evaluate(..., conditioning="paper_rms_v1")`; legacy
defaults are unchanged. All three commands are CPU-only and reject Modal mode.

Read `results/research/control_summary_v1/FINDINGS.md` before a new model run. The
current three-seed comparisons are descriptive, source-snapshotted development
evidence. They cannot qualify model superiority or an unbiased investment strategy.
