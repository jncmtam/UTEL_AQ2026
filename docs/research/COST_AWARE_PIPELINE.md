# Cost-aware proposal and admission mode

Date: 2026-11-04. Implementation follow-up to IMPROVEMENT_PROTOCOL.md.

`budget_search.cost_aware_request` supplies a one-layer schema plus measured qubit,
total-CX and logical-depth limits from the verified reference circuit. It leaves
financial coefficients and the compiler-owned preparation/COST unchanged.
`admit_cost_aware_program` checks that schema, lowers and independently verifies
the gates, and rejects any compiled resource overrun before angle fitting. There
is no silent baseline substitution or attribution of classical edits to the model.

The Modal dispatcher supports `--cost-aware` with a fresh run ID. The opt-in path
creates bounded requests and enforces admission, and its uniform control fixes the
same mandated bits without enumerating the universe. Legacy mode/defaults and
completed raw runs are preserved. Changing the flag on an existing completed ID
raises an error rather than scheduling compute or ignoring the setting.

A new GPU experiment requires its own frozen protocol and run ID. No such GPU
experiment was launched here: the published-US CPU benchmark did not qualify a
useful overall circuit frontier against the strong local-search reference. The
new mode has software/controlled-program tests, not live-model qualification.

The new standalone budget search uses the conserved executor and has been exercised
at N20/K5,15,504 supports. It retains all observed samples and actual allocation
cost. This is classical simulation and does not establish hardware advantage.

Read results/research/improvement_v1/RESULTS.md and INSIGHTS.md for measured
resource reductions, quality-by-budget curves and the outstanding limitations.

`guidance.guided_request` is a further optional library API, with an explicit
feature-to-decision procedure and per-parent evidence links. Its adapter performs
evidence checks before the same cost-aware quantum/resource admission. Eight
requests were prepared locally under DATA_GUIDANCE_PROTOCOL.md. This API is not
wired into the deployed Modal entry point and has no live-model result; a future
experiment must freeze the version and tokenize inputs before any dispatch.
