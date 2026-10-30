# Separate pending NCBI BLAST verification

This observation is outside the active tool-grader goal and is not goal completion evidence.

RID `DTKE1D4G016` returned native **WAITING** at **2026-10-24T20:53:40.876588+00:00**. The HTTP response was 200. Hit availability is unknown: the native response contains no `ThereAreHits` field. No cause or completion estimate is inferred.

## Completed

- Verified the original RID against `job.json` and the native `submission.body`.
- Decoded the original retained POST request and verified the submitted sequence equals `query.faa`, with identifier `gene_001` and length 253 amino acids; verified `blastp`, `swissprot`, hit-list size 50, contact `chia@anl.gov`, and tool `gene-annotation-episode`.
- Verified the original wire-request SHA-256 and retained query SHA-256. The recorded query SHA-256 is `ccdcdb50cfb0a7f24498c807adbbf38ae504c88b7437a01fc78fdc6ba213288b`.
- Made exactly one new status observation through the existing `PublicClients.blast("status")` binding, which invokes the installed BLAST skill's `get_search_info` operation. Used the original shared provider-access directory and its request-spacing checks.
- Verified the actual HTTP request was GET `Blast.cgi` with `CMD=Get`, `FORMAT_OBJECT=SearchInfo`, and the original RID/contact/tool parameters.
- Retained the exact native response bytes and request/response provenance. Verified every prior file in `live_api` still has its original SHA-256 digest.

## Native status

```text
Status=WAITING
```

Response SHA-256: `d74fd197b1260d4b2a36f0a9b5c3fd737297b4ced3972addebd68e6be3d9148a`.

## Still unverified

The job has not reported READY. No result fetch was attempted, so the original complete result, result-level query/program/database identity, parseability, and numerical grader output remain unverified. No polling loop, resubmission, cancellation, scientific-credit assignment, tests, goal/accounting changes, or production-source changes occurred.

## Evidence

- [Native status response](status_20261024T205340876588Z.body)
- [Exact request/response provenance](status_20261024T205340876588Z.metadata.json)
- [Separate verification receipt and preserved prior-artifact digests](separate_verification_20261024T205340876588Z.json)
- Original immutable inputs: `job.json`, `request.json`, `query.faa`, `submission.body`, and `submission.metadata.json`.

Installed skill client: `/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/ncbi-blast-skill/scripts/ncbi_blast.py`.

Installed skill client SHA-256: `74970756e0a03edaa8ed92328a41c173e50f976829ea8918e6ca973823f1bc1a`.
