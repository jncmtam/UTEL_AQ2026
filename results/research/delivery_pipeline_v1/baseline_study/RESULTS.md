# Non-LLM development study

All resource counts include initialization and cost. Dicke synthesis is a dense small reference; gradient access is exact classical simulation.

| Case | Method | Valid | CX | Feasible probability | Expected proxy regret |
|---|---|---|---:|---:|---:|
| development_n6 | exchange_full_penalty | True | 76 | 0.8581304789273392 | 8.882429107308992e-05 |
| development_n6 | exchange_certified_subspace | True | 76 | 0.8581304789273392 | 8.882429107308992e-05 |
| development_n6 | dicke_dense_reference | True | 121 | 0.9500102889650656 | 4.12984570042464e-05 |
| development_n6 | gradient_adaptive_exchange | True | 68 | 0.9975583336827072 | 1.8338559708506877e-05 |
| development_n8 | exchange_full_penalty | True | 114 | 0.789371518896705 | 2.8271530050811678e-05 |
| development_n8 | exchange_certified_subspace | True | 114 | 0.7893715188967041 | 2.8271530050811637e-05 |
| development_n8 | dicke_dense_reference | True | 349 | 0.9867729693653019 | 2.2229250204272262e-05 |
| development_n8 | gradient_adaptive_exchange | True | 98 | 0.937511858141277 | 2.9025612944777634e-06 |
| development_n10 | exchange_full_penalty | True | 160 | 0.5002294324778941 | 8.149379413388502e-06 |
| development_n10 | exchange_certified_subspace | True | 160 | 0.5002294324778944 | 8.149379413388505e-06 |
| development_n10 | dicke_dense_reference | True | 1161 | 0.9871051587554039 | 1.9551803842243728e-05 |
| development_n10 | gradient_adaptive_exchange | True | 136 | 0.6963267983197738 | 3.314436517112371e-06 |

This development study cannot qualify a model or a market strategy. Full-penalty and certified-subspace encodings are equivalent only on the proven asset subspace. See protocol and raw records for exact budgets.
