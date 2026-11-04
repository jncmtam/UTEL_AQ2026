"""Extract saved logical LLM messages and contracts; never run model inference."""

from pathlib import Path
import hashlib
import json


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "results/research/llm_transparency_v1"
    if output.exists():
        raise ValueError(
            "Existing transparency bundle retained; use a separate revision."
        )
    output.mkdir(parents=True)
    live = json.loads(
        (root / "results/research/modal_e2e_v1/prepared.json").read_text()
    )["requests"][0]
    guided = json.loads(
        (
            root
            / "results/research/data_guidance_v1/cases/family0_n20_base/request.json"
        ).read_text()
    )
    answer = json.loads(
        (root / "results/research/modal_e2e_v1/inference_answers.json").read_text()
    )[0]
    for prefix, request in [("LIVE", live), ("GUIDED_UNTESTED", guided)]:
        (output / f"{prefix}_SYSTEM_PROMPT.txt").write_text(request["system"])
        for name, value in [
            ("REQUEST", request),
            ("USER_PAYLOAD", request["payload"]),
            ("RESPONSE_SCHEMA", request["schema"]),
            (
                "LOGICAL_MESSAGES",
                [
                    {"role": "system", "content": request["system"]},
                    {
                        "role": "user",
                        "content": json.dumps(request["payload"], ensure_ascii=False),
                    },
                ],
            ),
        ]:
            (output / f"{prefix}_{name}.json").write_text(
                json.dumps(value, indent=2) + "\n"
            )
    (output / "LIVE_ACTUAL_RESPONSE.json").write_text(
        json.dumps(answer, indent=2) + "\n"
    )
    metadata = {
        "live_source": "results/research/modal_e2e_v1/prepared.json requests[0]",
        "guided_source": "results/research/data_guidance_v1/cases/family0_n20_base/request.json",
        "live_request_hash": live["request_hash"],
        "guided_request_hash": guided["request_hash"],
        "model": answer["model"],
        "revision": answer["revision"],
        "new_model_calls": 0,
        "scope": "Exact saved request fields and reconstructed logical messages; tokenizer-rendered token IDs are not claimed.",
        "sha256_files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.iterdir())
        },
    }
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    # Local app preview uses absolute links. Canonical evidence remains portable.
    preview = root / ".local-previews"
    preview.mkdir(exist_ok=True)
    source = root / "results/research/tail_fitting_v1/RESULTS.md"
    text = source.read_text()
    for name in (
        "quality-by-budget.png",
        "tail-versus-mean.png",
        "feasibility-and-allocations.png",
    ):
        text = text.replace(f"]({name})", f"](<{source.parent / name}>)")
    (preview / "TAIL_FITTING.md").write_text(text)
    print(f"Saved LLM transparency bundle: {output}")
    print(f"Absolute-image local preview: {preview / 'TAIL_FITTING.md'}")


if __name__ == "__main__":
    main()
