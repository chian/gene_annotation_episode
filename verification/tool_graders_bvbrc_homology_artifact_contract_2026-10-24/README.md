# BV-BRC Homology interface evidence

This directory supports the proposal in
`docs/TOOL_GRADER_BVBRC_HOMOLOGY_ARTIFACT_PROPOSAL_2026-10-24_001.md`.
It is **not** a production Homology implementation or proof of a deployed
BV-BRC job/result format.

`sources/` contains five official helper-source files missing from the earlier
retained application study. `source_retrieval_receipts.json` records their exact
official URLs, HTTP statuses, SHA256 and Git tree/blob identities. These were
the only network requests during this assignment. They acquired code, not
scientific data. The original producer/spec/entry point remain in
`../tool_graders_bvbrc_application_artifacts_2026-10-24/`.

Every file under `examples/` is **SYNTHETIC**, including invented identifiers,
organisms, function labels, native-shaped scores, input sequences and missing
or malformed cases. Literal function labels are supplied within synthetic
metadata and never inferred as biology. No fixture represents an actual BV-BRC
task or Workspace object. No actual native archive was manufactured. The TSV
is hand-authored to the source's declared columns; its identifier spelling is
not claimed to have been observed from a live formatter.

Run offline with:

```bash
python3 verification/tool_graders_bvbrc_homology_artifact_contract_2026-10-24/build_examples.py
```

The harness uses only the standard Python library, existing pure BLAST modules,
and core Perl JSON::PP. It executes exactly the retained source methods
`massage_blast_json` and `decode_title` in isolation on synthetic bytes. Their
source is extracted verbatim; the surrounding test object provides only their
JSON interface. It does not import the service or execute BLAST, makeblastdb,
blast_formatter, a database search, network acquisition, or episode runtime.
It also checks existing BLAST readers/calculators on explicitly authored
single-query projections and an explicit manual metadata bridge. These are
not tests of the proposed Homology readers or the new opt-in join path.

`CHECK_RESULTS.json` records fifteen listed checks, all passed. It distinguishes
synthetic source-transformation checking, shared existing BLAST calculations,
and current reader rejections from unverified new parsers and unverified
production integration. Saved per-query numerical sheets and temperature-1/2
calculation outputs permit inspection without repeating an analysis.

Key numerical answers:

- Three HSPs for the first hit contain twelve pair representations but six
  unique mappings: query paired coverage 0.6, reference paired coverage 0.75.
- The synthetic source function weights are 2/3 and 1/3 at T=2, and 0.8/0.2
  after offline recalculation at T=1. Unassigned reference mass is retained;
  no database population correction is available.
- The reverse translated example maps three amino acids to nine original
  query nucleotides, with half-open intervals [12,15), [9,12), [6,9).
- The source metadata-collision case demonstrates an overwritten sidecar
  entry while raw alignments remain. The proposed reader must retain metadata
  ambiguity; no new reader was run on that case here.

Actual native BV-BRC artifacts tested: 0. Native jobs executed: 0.
Production files edited: 0. New production parsers, explicit joins, shared
grouping extension and complete typed episode path remain unimplemented.
