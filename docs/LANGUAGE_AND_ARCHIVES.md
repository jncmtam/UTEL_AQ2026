# English workflow and historical archives

Updated: 2026-11-04.

The maintained US-equity research CLI, decision application, financial/quantum
modules, current prompts, status reports, README and visual gallery use English.
The compatibility portfolio-repair interface and its generated report/error text
have also been translated to English. Legacy two-way turnover remains explicit;
translation does not change financial semantics or re-score historical results.

## Current reading paths

| Subject | English entry point |
|---|---|
| Project and reproduction | [README](../README.md) |
| Measured findings and blockers | [Qualification status](research/QUALIFICATION_STATUS.md) |
| Research claims | [Research register](../AGQO_RESEARCH_REGISTER.md) |
| Technical architecture | [Technical guide](../TAI_LIEU_KY_THUAT_AGQO.md) |
| Interface behavior | [Frontend requirements](../FRONTEND_YEU_CAU.md) |
| Agent resumption | [AGENTS.md](../AGENTS.md) and [continuation brief](../AGQO_NEXT_ROUND_MASTER_PROMPT.md) |
| Charts and source hashes | [Visual gallery](../results/research/evidence_gallery_v1/GALLERY.md) |

Historical filenames remain as compatibility links; their maintained content is
English. Four superseded root documents were copied byte-for-byte to `docs/legacy/`
before replacement. Earlier archived documentation remains unchanged.

## Evidence that keeps its original language

Original model responses, requests, investment text, raw provider payloads,
historical protocols/results and run source snapshots retain their original bytes.
Translating them in place would break hash identity and scientific reproducibility.
The archive includes Vietnamese documents and older VN30 prototype material.
English status pages explain which records are historical and what they can prove.

The bilingual parser and a labeled Vietnamese gold-input fixture remain supported.
They are accepted user inputs, not untranslated English UI text. Figure validation
accepts original Vietnamese caption markers and new English markers; newly composed
captions use English.

Older VN30-specific modules and asset-generation utilities remain historical
compatibility code, including their original presentation catalogs. They are not
the maintained US workflow. This migration does not claim every historical byte
in the repository has been translated or every old generator produces English.
Use `agqo-research` and the current gallery for the English research application.

## Check the maintained surface

Run `.venv/bin/python scripts/audit_english_surface.py`. The scan checks Vietnamese
diacritics in the maintained source/doc/UI scope and records the two explicit
legacy-input exceptions. It is a presentation check, not a scientific correctness
test, a general natural-language classifier or a translation of immutable evidence.
