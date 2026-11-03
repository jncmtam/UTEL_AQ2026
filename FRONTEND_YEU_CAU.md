# Decision interface requirements

The maintained application is the English US-equity portfolio-repair interface.
The historical filename is retained so existing links continue to work.

## User decisions

Show the existing portfolio, verified investment requirements, feasibility diagnosis,
proposed trades, tracking/cost trade-offs and supporting circuit evidence. Make hold,
joint SCIP, allocation-aware swaps and QAOA comparable on the same specification.
A blocked historical dataset must display its actual reasons and clear old synthetic
holdings and decisions. Never display a failed or skipped model as successful.

## Evidence views

The [visual gallery](results/research/evidence_gallery_v1/GALLERY.md) explains data
coverage, unresolved actions, model readiness, objective distortion and circuit
resources. Its [offline HTML view](results/research/evidence_gallery_v1/index.html)
filters evidence by topic. Figures link to source hashes. Planning illustrations
must be distinguishable from measured observations.

## Execution and review

Use `python -m agqo.research serve --output results/research/delivery_pipeline_v1`
for the maintained decision application. UI actions are local synthetic comparisons
or saved replay; bounded Modal experiments remain separate reviewed CLI operations.
Inspect desktop and mobile layouts, keyboard controls, stale-evidence clearing,
units and explicit software/model/financial claim boundaries.

Read [the user guide](docs/USER_GUIDE.md), [result semantics](docs/RESULTS_SPEC.md)
and [current status](docs/research/QUALIFICATION_STATUS.md). The original Vietnamese
brief is preserved [in the archive](docs/legacy/root_FRONTEND_YEU_CAU.md).
