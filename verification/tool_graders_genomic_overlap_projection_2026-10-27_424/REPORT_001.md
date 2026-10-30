# G3a requested-field projection verification

2026-10-27. Scope: only the pure `project_genomic_overlap_result` function for
`B-L123-analyze_genomic_region_overlap`. This is not completion of the scientific
tool, a native binding, a results host, or episode communication.

## Implemented boundary

Owned production source is `gene_annotation_episode/genomic_overlap_result_views.py`;
owned tests are `tests/test_genomic_overlap_result_views.py`. The function consumes
G1's record aliases, strict schema validator, and canonical sheet hash helper.
It validates the sheet/component hash, exact selector parameters, request order,
set/comparison/reference/occurrence joins, native edge membership, selector keys,
and allowed measurement fields. It copies selected measurements and required
denominator, extent, reference and lower-bound qualifications. It does not repeat
interval calculations, acquire files, execute native work, call a model, or grant
artifact/execution access.

Selection precedes paging. `page.total_rows` is the number of available filtered
component rows, never an estimate of missing scientific input rows. Extent is
computed before paging. A requested missing measurement remains present with its
null or ratio missing representation and a located failure. Returned objects are
detached from caller inputs.

The original packet left aggregate extent and failure/page scope implicit. Root
resolved these without schema changes in packet422's
`PROJECTION_CLARIFICATIONS_001.md` and `PROJECTION_CLARIFICATIONS_002.md`.
Those rules are implemented: failure order follows original input order; an
explicit known-occurrence span selection depends on its own input; coverage and
partner values depend on both operands/native output; an all-occurrences request
retains unavailable-input qualifications. Off-page calculation failures are not
dumped into a returned page.

## Concrete supplied-data example

Packet418's hand-worked input has A=[0,10),[5,15), B=[7,12), native widths 3 and 5.
Its retained components include pairwise overlap sum 8, shared union 5, combined
union 15, and one selected pair under minimum overlap 4. The Jaccard-only return
is exactly:

```json
{
  "unfiltered.jaccard_bp": {
    "numerator": 5,
    "denominator": 15,
    "value": 0.3333333333333333,
    "missing_reason": null
  }
}
```

It retains extent `complete` and reference relation `unknown`. Pairwise sum,
selected counts, edges and occurrence tables are absent from that return.
`check002/worked_projection.json` equals the supplied requested-return fixture.
These are supplied synthetic bytes and hand-worked components, not a new native
execution or captured scientific observation.

The joined test independently calls G1's real supplied-byte readers, reference
extractor, sheet builder and calculator, using the supplied-output receipt with
null workflow execution identity. The resulting Jaccard projection is 5/15;
the retained calculator result separately holds pairwise sum 8 and selected pair
count 1. This verifies the pure joined interface without claiming native action
authority.

## Executed verification

| Attempt | Executed scope | Outcome |
| --- | --- | --- |
| `check001` | Projection against packet418 components while G1 stabilized; joined test excluded | 35 passed, 1 deselected, 0.74 s pytest duration |
| `check002` | Fresh snapshot after G1 readiness; final projection tests plus actual supplied reader/calculator join | 41 passed, 1.03 s pytest duration |

Both attempts and their original receipts are retained. No failed pytest attempt
occurred. Neither run reused a changing checkout as its executed source.
`source_pins_before.json` and `source_pins_after.json` match in both attempts;
each receipt also reports zero checkout source drift during its run.

Tests cover exact Jaccard-only selection, set and occurrence fields, filtering
before paging, requested-order rejection, detached containers, schema/type
rejection, stale sheet hashes, exact parameter differences, wrong joins,
duplicate selectors, missing ratios, retained lower bounds, irrelevant failures,
off-page failures, explicit span/coverage dependencies, unavailable inputs with
zero available rows, and complete analytic empty inputs with a 0/0 ratio.
Projection I/O/network/process calls are disabled in the purity test.

All tests and projection/calculation examples ran through `local_jobs` using
`LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)`.
Both receipts verify cgroup memory max 21474836480, swap max 0, and runtime max
`infinity`. Scratch enforcement is the existing monitored visible allocated-byte
limit with possible overshoot, plus the hard per-file limit; it is not a filesystem
sandbox. Check002 observed scratch usage was 22044672 bytes. No local database
BLAST, remote call, native overlap invocation, or HPC job was performed.

## Final executed source pins

These are `check002`'s executed SHA-256 values, also equal to the checkout at the
post-run comparison. Later edits by other owners require their own qualification.

| Source | SHA-256 |
| --- | --- |
| `genomic_overlap_result_views.py` | `ed3df0764f95ff07505a9ea47bae488785d0d64d5755acda731299619097739b` |
| `test_genomic_overlap_result_views.py` | `600d85e0e85014ab90702e0c2aa18dcfe8c2a2e35e491ea953eaa9351f9d2088` |
| G1 `genomic_overlap_contracts.py` | `1bde770d3360feb38d2d3c77a5ab8c44f2c810cd86dbbf9cf15d0b658d4a906e` |
| G1 `genomic_overlap_inputs.py` | `f5f8a28c70bd45819860bd7c806fbb63eb8f74efa3275e402ceeae5b018a778a` |
| G1 `genomic_overlap_calculations.py` | `9ebbc3913969da86e3c1329039c4e2ddcbcd0339bd36fc89a2a7b72571ec594c` |

The exact test request, stdout/stderr, JUnit XML, lifecycle records, read-only
source snapshot and before/after pins remain under each attempt directory.
The launcher and worker are also pinned as executed sources.

## Authority and remaining work

Read the entire immutable attached goal with verified SHA-256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`, AGENTS.md,
the tool-grader principles, the relevant inventory row, complete packet418
CONTRACT/HANDOFF/data definitions/worked chain, packet422 ROOT_CONTRACT and both
clarifications. Read the complete G1 reader/calculator paths consumed by the
joined test and the local_jobs verification interface. The immutable objective
and all sixteen principles are reread verbatim at the required reset, followed
by the accepted contract before handoff.

No results host, returns/binding module, renderer, prompt, runtime, accounting,
inventory, original planning record, or G1 production source was changed here.
Packet410 was not changed. Literature and W05 remain excluded.

Original-action custody, actual saved-component admission, production selected
tool/resource child binding, full Workflow return validation, replay and live
resource verification remain with their separately assigned owners. This pure
projection does not prove those paths or increase the completed-tool count.
