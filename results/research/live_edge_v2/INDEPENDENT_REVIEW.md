# Independent read-only review of live edge program v2

Date: 2026-11-04, Asia/Ho_Chi_Minh. Scope: implementation, saved requests,
responses, admissions and summary artifacts. No new remote/model call, circuit
simulation, allocator query or financial experiment was performed for this review.
Only this additional review document was written. Prepared execution sources and
original evidence were not changed.

## Assessment

No blocking correctness issue was found in the reviewed execution path. The
engineering result is eight admitted executable programs under the revised
contract. There is **no demonstrated incremental value of explicit numerical
guidance** in this batch: context-only and guided arms produce the same physical
GateIR in every case and tie all12 paired portfolio outcomes.

More specifically, all eight programs implement a constant **star on the first
free asset**, with every exchange sharing beta group1. This holds across both
asset sizes, families and mandate scenarios. Exclusion changes the first free
asset from qubit0 to qubit1 through the mandated domain. This is not evidence
that the model selected a data-specific hub or used the exchange statistics well.
It does not prove the model ignored its input; it establishes no observed useful
architectural adaptation in these cases.

## Exact deterministic-star equivalence

Using only saved request domains and cost identities, I constructed the expected
single-layer star GateIR: paired RXX/RYY exchanges from the first free qubit to
each later free qubit, angle2*beta_0_1, common counter-Dicke preparation, canonical
COST(gamma_0), and the recorded initial/register mapping. All star edges overlap,
so compiler disjoint-round ordering remains child order. This pure dictionary
construction makes no simulator or allocation call.

For all eight admitted programs, every GateIR field except free-text `rationale`
exactly equals that deterministic construction. The SHA256 below hashes sorted,
compact JSON of that physical GateIR projection. Both arms have the same digest.

| Case | Hub qubit | Free qubits | Physical projection SHA256, both arms |
|---|---:|---:|---|
| family0_n12_base | 0 | 12 | `4648bf87c9f5e0345d51fbd4b13d020f9758007e6ace80e53a6aa6ccd1e691ff` |
| family0_n12_exit | 1 | 11 | `50d45db7343ad9fa3a40b4ee5fc4e075beb61a8e3c1c0e6ea9edc4f68e7192a7` |
| family1_n20_base | 0 | 20 | `722e000970fdccf633d439fda6d31c16b1fd574355e5b36e2317360574b42af3` |
| family1_n20_exit | 1 | 19 | `e43bbfb3f7fc846d6129db1a52b1bcbd8129e2515540e65ba22d08db7c1f4bdd` |

Consequently a deterministic star rule can reproduce these physical candidate
circuits without LLM inference. This is structural equivalence, not a separately
executed star-baseline experiment or a new performance result.

## Model explanations are not verified financial facts

Examples from the saved raw responses:

- family0_n12_exit/guided claims a star centered on “ASSET_00 (frozen qubit 0).”
  Actual selected edges and compiled gates have hub qubit1; qubit0 is excluded.
- family0_n12_exit/context_only likewise names excluded ASSET_00 as the root.
- family0_n12_base/context_only says its construction preserves “sector weight
  caps and position bounds.” XY exchanges preserve cardinality, not those weight
  inequalities; the common allocator must enforce them.
- That same response compares allocated F with “minimum empirical feasibility”
  in its falsifier. An objective score and a feasibility fraction are different
  quantities. The statement is not an implemented acceptance criterion.

Some explanation strings end mid-sentence under their bounded field lengths.
Normal decoder completion and successful circuit admission therefore do not
establish coherent or correct explanations. Publish these texts as **model
assertions**, with the independent correction, rather than decision justifications.

## What the comparison supports

The saved analysis pools four cases and three seeds: guided versus fixed scheduled
is-1.29% mean allocated training objective; versus conditioned uniform-1.20%;
versus allocation-aware swap+3.57%. Those are not N20-only figures. Guidance versus
context-only is exactly0.00%, with12 ties. The strongest direct classical search
is never beaten in these12 pairs (six ties/six losses).

The star circuits also use more depth than scheduled fixed controls:501 vs429,
462 vs398,1618 vs1482 and1540 vs1412. Same observation counts do not imply same
complete inference/compile/simulation/allocation cost. These findings do not qualify
an overall financial or resource advantage.

## Scope and implementation checks

- The v2 schema selects each edge once and its group in the same record. The
  compiler derives parent references, performs disjoint scheduling and constructs
  preparation/COST. Source maps accurately distinguish these responsibilities.
  Correct mapping is by construction, not evidence of LLM reasoning.
- Original v1 remains0/8 admitted. Its failed CPU reservation and diagnosed
  recovery are preserved. V2 changes grammar, scheduling ownership and depth caps
  to the saved unscheduled baseline; the acceptance gain cannot be attributed to
  prompting alone. Within-v2 context/guided inputs/schema/seeds/caps are matched.
- Frozen numerical transport validates source-bound statistics against platform
  reconstruction, then requires exact original Hamiltonian reproduction. The
  existing canonical verifier check remains exact. This fixes numerical transport,
  not the distinction between proxy B and allocated F.
- The two ledgers report combined reservations USD4.686350, including failed CPU
  work, below the declared combined ten-USD envelope. These are reservations,
  not an invoice or available-credit balance.
- Data remains opened conditional2010 US development data, with full-year
  membership conditioning and artificial policy buckets. No independent investment
  history or quantum hardware advantage is established.

No additional finance/model experiment is recommended or scheduled by this review.
Retain the engineering result and negative guidance finding without another sweep.

## Reviewed source and evidence identities

Paths are relative to the repository root. SHA256 recorded at this review:

| Path | SHA256 |
|---|---|
| `agqo/research/edge_program.py` | `d2f8056fef563a5da265c6c5eb1d2fd2162a4a98083c454d687f119eb7e93e63` |
| `agqo/research/frozen_numerics.py` | `009aae7b341aa3b7945ba99610bf2a068697614c1a726d54ab216224f910329f` |
| `agqo/research/live_guidance.py` | `b18fd8cadc1fc4e1981833f82e44e2fa533527f314c6132c2be31323252545df` |
| `scripts/run_live_guidance.py` | `bb19908efa6378bfc6803adffc19e29eb77ae6d335871f6cb59b50e3b82adcec` |
| `docs/research/EDGE_PROGRAM_PROTOCOL.md` | `9c9e09ce56f088177f078910965d2fd2d6a56ad095dbcdd23358306518f95195` |
| `docs/research/LIVE_GUIDANCE_RECOVERY.md` | `d437442e7423ac7716f8ba86348ccc293fad43d62a53556d751de3ab6d715265` |
| `results/research/live_edge_v2/evaluation/admissions.json` | `855d407a0da613a899b3f4ffaa1349d0944a545ca428062584f867a8f93c9eac` |
| `results/research/live_edge_v2/orchestration/prepared_requests.json` | `ce4a2ac8411165f05bdd1faf9ca0e7ce090ce1cf98a0f3ae3b4c5ead802ad042` |
| `results/research/live_edge_v2/orchestration/answers.json` | `de3bd3d08dc64fdccc3b24721c5f9604556ce19b9d55b8ae52cecf8c6e7d8864` |
| `results/research/live_edge_v2/analysis.json` | `dccd16f07ca2368f294a7f57e1a4cd925c8cbdffb4edeaf62aaccb902fed6a4c` |
| `results/research/live_guidance_v1/evaluation/admissions.json` | `b017314030fbbfccf1ac307d800d428a13eac42ef984dfe487a4817a3405d037` |
