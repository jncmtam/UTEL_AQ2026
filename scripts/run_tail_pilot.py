"""Run/resume the frozen local CPU tail-fitting pilot; no paid inference."""

import json
from agqo.research.tail_study import run

if __name__ == "__main__":
    summary = run()
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "raw_sha256_files"}, indent=2
        )
    )
