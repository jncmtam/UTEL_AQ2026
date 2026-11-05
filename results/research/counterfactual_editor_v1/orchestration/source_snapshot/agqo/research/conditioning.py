"""Paper Eq8 RMS conditioning, implemented as coordinates on a locked Hamiltonian."""

from time import perf_counter
import numpy as np

VERSION = "paper_rms_v1"
SOURCE = "https://arxiv.org/html/2305.15201v3#S3.SS2"


def coordinates(ir, h, mode="none"):
    start = perf_counter()
    if mode not in ("none", VERSION):
        raise ValueError("Unsupported optimizer conditioning.")
    a = 1.0
    if mode == VERSION:
        linear = np.asarray(h["linear_z"], float)
        linear = linear[linear != 0]
        pairs = np.asarray([term["coefficient"] for term in h["quadratic_zz"]], float)
        degrees = [float(np.mean(v**2)) for v in (linear, pairs) if len(v)]
        a = float(np.sqrt(sum(degrees)))
        if not np.isfinite(a) or a <= 0:
            raise ValueError(
                "Constant or nonfinite Hamiltonian cannot use RMS conditioning."
            )
    scale = np.array([1 / a if p["kind"] == "cost" else 1 for p in ir["parameters"]])
    return scale, {
        "version": mode,
        "equation8_coefficient": a,
        "physical_angle_scales": scale.tolist(),
        "optimizer_loss_scale": 1 / a,
        "source": SOURCE if mode == VERSION else None,
        "hamiltonian_hash_unchanged": h["hamiltonian_hash"],
        "preprocessing_seconds": perf_counter() - start,
        "uses_truth_table_or_optimum": False,
    }
