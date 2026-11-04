# What the improved benchmark tells us

## 1. There is a concrete engineering improvement

The recorded LLM circuits did not need their second layer on the three opened
integration cases. Removing it and grouping disjoint exchanges reduced total CX
by24–34% and logical depth by19–31%, while all12 edited runs retained the original
selected allocated objective. Fewer parameters also fit the small optimization
budget more comfortably. This is a tested classical edit of LLM output, not
proof that the model learned better circuit design or that one layer always suffices.

The pipeline now exposes a cost-aware contract: exactly one layer, a measured
reference resource budget and independent admission before fitting. Excess gates,
depth or qubits cause an explicit rejection; a baseline is never relabeled as an
LLM result. This prevents valid but unnecessarily expensive designs being accepted
solely for validity. No model generated under this new contract in this study.

## 2. The new curves reveal a crossover hidden by the old score

N20 mean paired allocated-training-objective difference against conditioned uniform:

| Observed supports | Fixed path | Scheduled path | Allocation-aware local swap |
|---:|---:|---:|---:|
| 8 | -6.76% | -7.63% | -16.74% |
| 24 | -2.56% | -6.76% | -13.70% |
| 48 | +1.71% | -0.80% | -9.95% |
| 88 | +3.11% | +1.88% | -10.12% |

Negative means better training objective, not higher realized returns. These are
12 related case/seed pairs, not independent market observations or significance.
The first8 observations precede angle adaptation, so their result cannot be credited
to learned optimization or LLM reasoning.

Circuit structure offers a useful early sampling bias against an uninformed uniform
control, but that benefit does not persist here as the budget grows. Strong local
search is already better on the aggregate early and final checkpoints. The old
20/70-support test hid these distinctions by letting all methods reach the same endpoint.

## 3. Data-informed rules and direct financial feedback are hypotheses

The correlation-tree rule does not reliably improve allocated quality. Correlated
assets alone do not determine the best exchange topology. The direct-F and proxy
feedback paths also differ across cases; direct F uses the right scoring units but
is not a guarantee of useful finite-budget search.

One remaining design issue is that mean sampled F guides angle fitting while the
reported decision uses the best portfolio observed. Those criteria need not rank
sampling distributions identically. This is a mathematical distinction and a
candidate explanation, not a causal conclusion established by this experiment.

## 4. The actual decision now supported

Keep the cost-aware admission, compact/scheduled controls, conditioned classical
sampler, all-shot accounting and budget curves. Use allocation-aware local search
as a strong reference for further formulation work. The current evidence does not
justify a larger model or a financial-benefit claim for QAOA.

The next technical question is whether the representation and training objective
can create a useful probability of good allocated supports against strong informed
classical search at complete matched cost. That should be settled before another
LLM sweep. Historical identity/action/sector reconstruction remains a separate
prerequisite for an investable test.
