# Non-LLM development study

All resource counts include initialization and cost. Dicke synthesis is a dense small reference; gradient access is exact classical simulation.

| Case | Method | Valid | CX | Feasible probability | Expected proxy regret |
|---|---|---|---:|---:|---:|
| development_n6 | exchange_full_penalty | True | 76 | 0.8581304789273392 | 8.882429107309002e-05 |
| development_n6 | exchange_certified_subspace | True | 76 | 0.8581304789273392 | 8.882429107309e-05 |
| development_n6 | dicke_dense_reference | True | 121 | 0.9500102889650655 | 4.129845700424647e-05 |
| development_n6 | gradient_adaptive_exchange | True | 68 | 0.9373190001291769 | 6.199369495648436e-05 |
| development_n8 | exchange_full_penalty | True | 114 | 0.789371518896705 | 2.827153005081167e-05 |
| development_n8 | exchange_certified_subspace | True | 114 | 0.7635588997593201 | 2.761767104889544e-05 |
| development_n8 | dicke_dense_reference | True | 349 | 0.986772969365302 | 2.222925020427227e-05 |
| development_n8 | gradient_adaptive_exchange | True | 98 | 0.9375118581412769 | 2.902561294477772e-06 |
| development_n10 | exchange_full_penalty | True | 160 | 0.5002294324778938 | 8.14937941338851e-06 |
| development_n10 | exchange_certified_subspace | True | 160 | 0.5002294324778942 | 8.149379413388514e-06 |
| development_n10 | dicke_dense_reference | True | 1161 | 0.9871051587554038 | 1.955180384224373e-05 |
| development_n10 | gradient_adaptive_exchange | True | 136 | 0.6963267983197738 | 3.314436517112371e-06 |

This development study cannot qualify a model or a market strategy. Full-penalty and certified-subspace encodings are equivalent only on the proven asset subspace. See protocol and raw records for exact budgets.
