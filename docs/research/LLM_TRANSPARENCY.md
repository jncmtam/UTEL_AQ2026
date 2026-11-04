# Everything the LLM receives, chooses and produces

This guide distinguishes saved live evidence from prepared prompts. No prompt
quoted here is evidence of financial benefit. The new live-guidance study's status
and results belong to its own protocol/receipts, not the older integration run.

## Exact prompts and full inputs

The latest completed run is **live_edge_v2**: [exact system prompts](../../results/research/live_edge_v2/SYSTEM_PROMPTS.md),
[eight full requests/schemas](../../results/research/live_edge_v2/orchestration/prepared_requests.json),
[verbatim model outputs](../../results/research/live_edge_v2/ACTUAL_RESPONSES.md),
[GPU proof](../../results/research/live_edge_v2/GPU_EXECUTION_PROOF.md), and
[measured interpretation](../../results/research/live_edge_v2/FINDINGS.md).
It admits8/8 executable programs, but every arm/case produces the same first-free-
qubit star/group1 template. Explicit guidance has no observed architecture or
financial effect, and some explanations are false. No production model is qualified.

| Material | Exact artifact | Execution status |
|---|---|---|
| Earlier integration system prompt | [LIVE_SYSTEM_PROMPT.txt](../../results/research/llm_transparency_v1/LIVE_SYSTEM_PROMPT.txt) | Actually used for the first small synthetic integration case |
| Its numerical user message | [LIVE_USER_PAYLOAD.json](../../results/research/llm_transparency_v1/LIVE_USER_PAYLOAD.json) | Actual saved payload, including coefficients and constraints |
| Its output schema | [LIVE_RESPONSE_SCHEMA.json](../../results/research/llm_transparency_v1/LIVE_RESPONSE_SCHEMA.json) | Structured-decoding contract |
| Both logical chat messages | [LIVE_LOGICAL_MESSAGES.json](../../results/research/llm_transparency_v1/LIVE_LOGICAL_MESSAGES.json) | Reconstructed exactly from saved fields, not token IDs |
| Its real output, tokens and receipt | [LIVE_ACTUAL_RESPONSE.json](../../results/research/llm_transparency_v1/LIVE_ACTUAL_RESPONSE.json) | Real Qwen output, not an illustrative response |
| Original offline guided prompt | [GUIDED_UNTESTED_SYSTEM_PROMPT.txt](../../results/research/llm_transparency_v1/GUIDED_UNTESTED_SYSTEM_PROMPT.txt) | Never executed under that exact contract |
| Original guided full context/schema | [GUIDED_UNTESTED_REQUEST.json](../../results/research/llm_transparency_v1/GUIDED_UNTESTED_REQUEST.json) | Eight development requests were prepared offline |
| New matched live prompts | [SYSTEM_PROMPTS.md](../../results/research/live_guidance_v1/SYSTEM_PROMPTS.md) | Check the new study's dispatch/receipts for execution |
| New eight full requests | [prepared_requests.json](../../results/research/live_guidance_v1/orchestration/prepared_requests.json) | Four US development cases, two prompt arms |

The saved offline prompt contained inherited depth1..2/preparation wording followed
by stricter one-layer/common-preparation instructions. The new live study replaces
that with one consistent common system prompt. Earlier evidence is unchanged.

## Model and runtime

The completed integration used `Qwen/Qwen3-Coder-30B-A3B-Instruct`, revision
`b2cff646eb4bb1d68355c01b18ae02e7cf42d120`, self-hosted on Modal A10080GB with
vLLM0.15.0/BF16. It is a pretrained checkpoint; this project did not fine-tune it.
The first saved response records6290 input/273 output tokens. Its request used
seed100, temperature0.4 and output allowance2048. The worker config uses top_p0.9
and context16384. New live requests retain the model and temperature but allow4096
output tokens and use seeds100..103, matched within each context/guided pair.

No model is production-qualified. The new study holds checkpoint and grammar fixed
to test procedure guidance, not a model-size comparison. Earlier 80B/30B/QUASAR
experiments have separate scopes and raw records; their scores are not pooled.

## How a model call is assembled

```python
messages = [
    {"role": "system", "content": request["system"]},
    {"role": "user", "content": json.dumps(request["payload"], ensure_ascii=False)},
]
```

The checkpoint tokenizer applies its chat template. The JSON response schema is
also passed through vLLM structured decoding. The logical message JSON alone does
not describe the entire decoder configuration or tokenizer's special tokens.
Real-request CPU tokenization must fit input plus output allowance into16384;
the GPU worker independently checks again. No silent input truncation.

## What is in the user payload?

- FinancialSpec: anonymous asset register, incumbent weights, K, include/exclude,
  exposure limits, turnover/cost settings, cutoff, provenance and units.
- Numerical data descriptors: correlations/covariance/spectrum in older prompts;
  the new guided context uses compact exchange means/RMS, correlation and window
  stability, plus selected global descriptors. Code computes them.
- Hamiltonian: compiler-owned problem/hash, terms, scaling and encoding. Larger
  prompts may project descriptor context; all cost coefficients remain in compiler.
- Domain: free/frozen qubits, allowed parent choices, edge identifiers and ordering.
- Resource budget: measured physical qubits, CX and depth in the new study.
- Feedback/previous_program: interface supports these, but the latest integration
  used one proposal per case with empty feedback, not an executed repair loop.
- Schema and evidence rules: exact fields, constants, enums and output limits.

Raw price tables, future returns and solver-optimum labels are not needed as
language-model input here. Current inference is not news reading, retrieval-
augmented analysis or price prediction. Any future retrieval must be documented.

## What the LLM actually decides

In latest v2 the model chooses one edge ID/group per child; the compiler derives
evidence links and a greedy disjoint schedule. There is no separate parent/citation
copy to contradict. The table below describes earlier grammar fields; archived
v1 remains0/8 full-contract acceptance. Changed schema, scheduler and resource caps
prevent attributing the v1-v2 acceptance change solely to model/prompt improvement.

| Output | Meaning |
|---|---|
| parents.pChild | Which smaller-index free parent connects to this child |
| schedule | Ordering of the chosen exchange edges |
| groups | Which exchanges share a beta angle within a layer |
| depth | Earlier live grammar allowed1..2; new live schema fixes1 |
| preparation | Literal compiler_counter_dicke_v1, not a model-designed preparation |
| rationale | Short justifications using allowed generic feature identifiers |
| evidence | New grammar: actual pair links plus schedule/sharing hypotheses/falsifiers |

The LLM does not choose stock winners, continuous weights, financial coefficients,
the gate decomposition of COST, or optimized numerical angles in this grammar.
It designs a supported exchange program; the compiler produces executable gates.
The current parent<child domain is order-restricted and is not every possible tree.

## A real response, interpreted

The first saved integration response chose parent indices0,1,2,3,4 for children1..5:
`0--1--2--3--4--5`. It used schedule0..4, alternating beta groups0/1 and depth2.
For the first layer, the compiler therefore emits exchanges on(0,1),(1,2),(2,3),
(3,4),(4,5), each lowered to paired RXX(2*beta),RYY(2*beta). COST and preparation
come from numerical compiler code. Angles are subsequently numerically optimized.

Its rationale said the path aligned with correlations/clusters and depth2 reflected
spectral characteristics. Those are the model's assertions, not established
mechanistic findings. All three old live proposals chose path-shaped depth2
circuits. Their validity does not establish meaningful data-driven adaptation.

## Verification, financial feedback and costs

Schema validity is only the first check. An independent adapter verifies gate-to-
feature links, lowering, quantum semantics and physical resource caps. Sampled
supports go to the common allocator; final financial scoring uses allocated F.
COST still represents proxy B. F feedback is classical, not a coherent quantum
F oracle. Invalid proposals are rejected explicitly; no baseline is relabeled LLM.

Actual request/response hashes, raw text, finish reason, token usage, checkpoint,
call IDs, failures, reservations and runtime are retained. Reservations are not
invoices; account billing deltas are not isolated job bills. The current live
ablation has one request per arm/case with no automatic repair or size escalation.
Compile/angle/allocator effort and rejected attempts also matter to overall value.

## Code map

- [live_guidance.py](../../agqo/research/live_guidance.py): clean matched live prompts and evaluation.
- [guidance.py](../../agqo/research/guidance.py): exact features, evidence schema and admission.
- [design.py](../../agqo/research/design.py): connected exchange grammar and gate lowering.
- [modal_gate_synthesis.py](../../modal_gate_synthesis.py): tokenizer and GPU chat execution.
- [client.py](../../agqo/synthesis/client.py): generic historical prompt plus shared live transport/cache.
- [budget.py](../../agqo/synthesis/budget.py): registry, pinned revisions and reservation policy.
- [run_live_guidance.py](../../scripts/run_live_guidance.py): checkpointed Modal orchestration.
- [LIVE_GUIDANCE_PROTOCOL.md](LIVE_GUIDANCE_PROTOCOL.md): frozen comparison and stop rule.

For Markdown images in the desktop preview, the generated local
`.local-previews/TAIL_FITTING.md` uses absolute image paths. Canonical research
reports retain portable relative links and original evidence hashes.
