# Post-run matched-draw classical audit

This comparator was added after opening results, to challenge rather than promote the quantum finding. It does not change the frozen circuit rows.

| N | Method | Mean allocated training objective | Support draws | Allocator cap |
|---:|---|---:|---:|---:|
| 10 | three_pair | 2.6450897e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 10 | counter_dicke | 2.7329588e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 10 | uniform | 2.7036691e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 10 | uniform_total_shots | 2.6450897e-05 | 2176 | 32 |
| 30 | three_pair | 2.0790048e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 30 | counter_dicke | 1.7264618e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 30 | uniform | 1.87669e-05 | 128 final; circuit methods also use up to2048 optimizer shots | 32 |
| 30 | uniform_total_shots | 1.6385629e-05 | 2176 | 32 |

The total-draw comparator uses the same maximum draw count as the circuit evaluation, while circuit postprocessing used only128 final samples. Optimizer bitstrings were not pooled in the frozen method. This is a protocol limitation, not a quantum advantage.

Means over three seeds on each opened case are descriptive. Instances, not seeds, are the independent research units. No significance test or model selection is justified.

## Cost-phase diagnostic

- N=10: normalized cost range=0.0337853; standard deviation=0.00758883; phase span at |gamma|=pi is 0.10614 radians.
- N=30: normalized cost range=0.0178915; standard deviation=0.00205367; phase span at |gamma|=pi is 0.0562078 radians.

Any cost rescaling must be a declared optimizer-conditioning study: rescaling H and inversely rescaling gamma leaves the physical unitary unchanged. It cannot be sold as a new quantum algorithm or repair the allocated-objective distortion.

Next comparisons should predeclare how all observed optimizer/final samples are used, retain matched total-draw and time references, and fix the financial formulation before spending on models.
