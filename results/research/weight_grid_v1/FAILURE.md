# Preserved input-adapter failure

The initial local entry point stopped at `inputs["dataset_manifest"]`; the existing
prepared-input contract uses `source_manifest`. Input and source snapshots were
saved. No allocation or encoding-quality evaluations, Modal calls or LLM calls
were performed. This partial run is retained. Corrected controller: weight_grid_v2.
