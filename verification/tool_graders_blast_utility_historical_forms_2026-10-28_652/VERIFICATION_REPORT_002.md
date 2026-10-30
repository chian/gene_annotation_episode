# Exact historical BLAST utility forms 652

Implemented the historical-form owner in 646/BINDING_AND_REPLAY_PORTS_004.md.
The current user goal remains authoritative. This is implementation evidence,
not a goal or scope amendment.

`communication._compile_closed_schema` now accepts either the exact current
registered utility fact schema or an exact source-pinned historical registration.
The new pure `blast_utility_historical_fact_schemas.py` holds immutable serialized
schema documents and returns detached copies. It never imports a verification
snapshot or executes historical source. The 11 fact sources have 14 distinct
historical schema documents. Current result views remain the authority for
values and meaningful relationships; the original parent schema additionally
constrains its original enum population. Nested bindings, altered registrations,
generic free text and arbitrary narrower schemas remain rejected.

The complete inspected path was communication's compiler, payload validation and
reference-semantic traversal, the full current utility result views,
NativeBLASTUtilityReturns and its EpisodeReturnRecords base. The return reader
first validates the actual unchanged parent form, then validates its rows using
the current registered descriptors and shared value validator. Its frozen-fact
check still compares source identities against the original runtime records.
No return-reader edit or other consumer repair was needed in the exercised path.
Execution, ownership, credit, continuation and runtime prompts were not changed.

## Actual historical registrations

The specified check101 source snapshot contains the required prior registered
schemas. Its saved masking Workflows contain no utility fact returns. The actual
utility Workflow in check096 has six saved parent deliveries: five results-child
returns and one scientific-parent return. Its older UtilityFailure code enum
also affects its checks and prepared-database schemas. The parent explicitly
confirmed preserving both exact source-pinned versions after this difference
was demonstrated. Neither saved request was rewritten or derived by narrowing
the current schema.

| Source snapshot | Complete registered-schema SHA256 |
| --- | --- |
| check096_blast_utility_full_workflow | 14ca7759d577dc7f2d3947fd2e11ac90741b3ef5ddebb78c2fcc0e3a21cab99e |
| check101_mask_conversion_workflow | 2d79aa19613ffd5688618ca2dcb25086031628b5a49703826eb16ea1a0b6c6af |

Both snapshots' `blast_utility_result_views.py` hash is
`8af8bcad56a21c572c6d07627220dfbcc3ce1491c4b0cc357795e9ecf2285cab`.
Their `blast_utility_contracts.py` hashes are respectively
`d52b3fc090e3a30c280208cdce1912716e022a81ad17f8dd89aefea828e4ad0d` and
`f02195dccbeba56b8e5b02b2f5766e96233c4f74964a74b2d43dd398a5548abf`.
The complete six-module dependency-source pins are retained in the runtime
provenance accessor and EXTRACTION_001.json.

## Verification

Every application import, schema extraction, saved-state read and test used
bounded529 with check005 dependencies, explicit support paths and test basename
`test_blast_utility_historical_forms_652.py`. No BLAST executable was selected or
rerun. All four attempts have terminal, quiescent collected receipts:

| Attempt | Actual result |
| --- | --- |
| check111_historical652 | Fixture-discovery assertion failed: check101's three saved masking states contain no utility-form deliveries. |
| check111b_historical652 | Fixture-identity assertion failed: check096 saved checks have a smaller failure-code enum than check101. |
| check111c_historical652 | 1 extraction/defect-reproduction test passed; all six actual old saved forms were rejected before repair. |
| check111d_historical652 | 43 tests passed in 7.11 seconds; final owned source hashes match the tested snapshot. |

The final suite verifies all current and historical registrations through the
actual `_values` method; six original saved requests and populated returns;
current requests over the same retained values; a clearly synthetic v2 subject;
strict historical enum differences; narrower/expanded/open/type-mutated and
source-mismatched schema rejection; top-level-only x-source binding; detached
registry access and compilation-cache mutation rejection; current numerical and
relationship validation; reference-resolution failure; conflicting duplicate
fact fields; and foreign-source rejection against actual frozen child facts.
The registry path also works when file opening is prohibited.

Retained numerical examples remain unchanged: database sequence count 3,
residue count 33, and two original extracted rows each with native length 12,
returned length 6 and normalized sequence `ATTGCA`. The repeated extracted rows
remain their original records; they are not treated as independent biological
sources or annotation confidence.

The final receipt records 20 GiB memory, 4 GiB scratch, zero swap and unlimited
wall time. Observed scratch was 687116288 bytes. All source, dependency, stdlib
and binary pins were unchanged. The audit reports no outside modules or unbound
mappings and unchanged original retained fixtures. VERIFICATION_002.json records
the exact receipt, audit and current owned-file hashes. Host AST and whitespace
inspection also passed; this workspace has no Git repository for git diff.

This establishes the assigned schema compatibility and actual saved-form reader
path. It does not establish a fresh full Workflow run, complete receiving-chain
replay, new native execution, live-resource verification or the full R1–R7 goal.
Those integration and live-resource obligations remain with the parent task.
