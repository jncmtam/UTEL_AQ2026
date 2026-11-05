# Findings from the live GPU run

The registered architecture-usefulness target is **unsupported**. This is distinct from financial qualification, which remains unestablished.

Actual live GPU generations:12; admitted:12; completed intended runs:88/88. All raw generations, failed/rejected runs and design-search effort are retained.

- LLM versus random_selected: -0.766% mean paired allocated-F difference (8/8 valid pairs; lower is better).
- LLM versus fixed_path: -1.075% mean paired allocated-F difference (8/8 valid pairs; lower is better).
- LLM versus fixed_star: -1.259% mean paired allocated-F difference (8/8 valid pairs; lower is better).
- LLM versus uniform_conditioned: -2.209% mean paired allocated-F difference (8/8 valid pairs; lower is better).
- LLM versus allocation_swap: +3.160% mean paired allocated-F difference (8/8 valid pairs; lower is better).

First-enum choices do not comprise a majority, but enum-order bias is not ruled out; no controlled counterfactual isolates causal data/feedback adaptation.

Feedback and changed architecture are mechanisms tested here, not proofs of reasoning quality. Matched random search is the architecture-value test; allocation-aware swap is the stronger direct finance reference. Star/path comparisons have smaller design budgets. Numerical circuit admission is not a financial win.

Read RESULTS.md for complete budgets, audit evidence and scope; ACTUAL_RESPONSES.md exposes exact model text. No physical quantum computer or independent investment evaluation was used.
