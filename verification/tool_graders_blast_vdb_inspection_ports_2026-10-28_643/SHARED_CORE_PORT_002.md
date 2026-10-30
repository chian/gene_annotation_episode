# VDB utility shared contracts after preparation integration

This is an additive implementation interface, not a goal or scope change.
643/IMPLEMENTATION_PORTS_001.md remains the complete native-input and field
meaning specification. The original user attachment and explicit formatter
removals remain authoritative. No runtime prompt or episode type changes here.

## Concrete current-code differences

Preparation integration now occupies operation v2 and inspection v2. Preserve
their exact version-specific schemas and validators, including the nine 646
program/mode pairs, saved deliveries and 654's original interrupted run.
The VDB operation uses `blast_utility_operation_v3`; its inspection uses
`blast_database_inspection_v3`. Its extraction uses the previously unoccupied
`blast_sequence_extraction_v2`. These belong to the existing Operation,
DatabaseInspection and SequenceExtraction families, not separate scoring sheets.

The future native requested-job branch will be `native_blast_utility_job_v3`;
the preparation job v2 stays exact. This core task does not implement that
execution branch or advertise it as available.

Shared lexical parsing is already implemented and tested by 655. Both the
legacy scientific metadata parser and the new supporting parser consume
`read_blast_vdb_sequence_table`. The new supporting parser need not call the
legacy wrapper, whose extraction/search context has different ownership.
Do not fabricate a search context or duplicate its lexical implementation.

## One core owner's files

- New `gene_annotation_episode/blast_vdb_utility_contracts.py`: pure schemas
  and relationship validation for the 643 shapes with the versions above.
- `gene_annotation_episode/blast_utility_contracts.py`: install additive shared
  union branches, exact version dispatch and common validation ports.
- `gene_annotation_episode/blast_database_extraction.py`: expose its existing
  sequence-symbol calculation as the common public function below. Preserve
  the entire existing classic parser output and exceptions.
- New `tests/test_blast_vdb_utility_contracts_662.py` and task662 verification
  directory. No native/result hosts, projections, runtime, tools or prompts.

Do not mutate existing nested schema objects to add VDB formats or fields.
Construct additive branches using shared component definitions; preserve exact
old version-schema outputs. The shared registry accepts the new branches while
`blast_utility_schema_for_version` still returns each original version exactly.
In particular, do not append VDB roles to an enum referenced by old frozen forms.

## Public ports and exact common output

`build_vdb_utility_schemas(base: dict) -> dict` returns the new branches under
ArtifactOccurrence, NativeField, Operation, SequenceExtraction,
DatabaseInspection, VDBUtilityContext and VDBMember. It receives the existing
common schemas and does not modify them. Reuse shared native outcome, failures,
checks, sequence fields and native-field definitions. The new native-field
branches are exactly the VDB fields/units/populations in 643 section 4.

`validate_vdb_utility_operation(value: dict) -> dict` validates the closed v3
operation and the seven exact parameter variants in 643 section 2. Program is
always blast_vdb_cmd; molecule is dna. No other program or implicit option is
admitted. Preserve selected input order and duplicate selector occurrences.

`validate_vdb_utility_context(value: dict, *, operation: dict,
database_binding: dict | None = None,
operation_input_occurrences: list[dict] | None = None) -> dict` validates the
closed context in 643 section 4 and its relationships to the exact selection.
No source lookup or identity inference. Dataset/member links remain supplied,
source-bound facts, with unresolved identities left null.

`validate_vdb_sequence_extraction(value: dict) -> dict` and
`validate_vdb_database_inspection(value: dict) -> dict` validate their closed
common-family results and return detached copies. Shared `validate_blast_utility_result`
and the version registry dispatch to these functions by exact version/program.
Preserve the usual `blast_utility_` ContractError prefix and stable existing
failure meanings; do not introduce a numerical-success gate.

`normalize_blast_utility_sequence_symbols(original: str, molecule: str)
-> tuple[str, int | None]` is the existing `_sequence_symbols` implementation
exposed publicly. Preserve its normalization, whitespace, alphabet, empty and
invalid behavior exactly. The old private name may delegate for compatibility;
classic and VDB parsers must have this same calculation authority.

VDB SequenceExtraction contains exactly the existing extraction top-level
fields plus `operation_input_occurrences`, `vdb_context`, `scope` and
`stderr_occurrence`. Its version and operation use the versions above.
`scope` is `{kind: selected_entries|all_native_sequences|all_references}`.
Each record has the existing common record fields plus nullable `vdb_member`
with the precise supplied member shape from 643. No native OID, title, range,
genomic coordinate or read identity is inferred.

For selected entries, exact/explicit/unresolved association meanings remain
unchanged. For an all selection, association is `not_applicable`, selector
ordinals and missing selectors are empty, and unexpected_record_keys is empty.
This avoids describing an intentionally unselected row as an association error.
All-mode records still retain their native row identity and any actual member
binding or explicit uncertainty. A complete captured successful enumeration
may have zero rows; it proves that enumeration, not a complete biological run.

VDB DatabaseInspection contains exactly the original inspection fields plus
`operation_input_occurrences`, `vdb_context`, `stderr_occurrence`,
`path_sections` and `path_records`. Info has empty path arrays; paths modes have
empty native_fields. Path shapes/order/duplicates/None-section handling are
exactly as in 643. A path report cannot authorize reading additional files.

Both result types retain stderr as an explicit output occurrence because
located native diagnostics must reference actual known output, not a phantom
input or an omitted artifact. Known occurrence relationships include database
occurrences, independent selected operation-input occurrences and both output
streams, with no duplicate occurrence identities. Input batch/list occurrences
are not database membership. Each source/binding pointer remains constrained
and does not itself grant artifact access.

New formats are blast_vdb_cmd_table_v1, blast_vdb_info_text_v1 and
blast_vdb_paths_text_v1. The new input role is entry_batch; database_list already
exists. Keep all legacy format/role interpretations and versions exact.

## Verification and dependent work

Before editing, retain exact current version-schema outputs and representative
classic/preparation results under bounded529. Compare them after the change.
Read the complete affected modules and consumers of the schema/version ports,
not just their exported names. Build failure/partial/identity/order cases from
the 643 list; synthetic cases stay labeled as such and do not establish native
verification. Test original ordinals around malformed rows, nullable identities,
input versus database membership, exact native length versus validated symbol
count, contradictory member provenance, same sequence normalization for both
consumers, and exact per-program result-version dispatch.

Use bounded529 check122_vdb_core662 and necessary suffixes, 20 GiB RAM,
4 GiB scratch, zero swap, no wall cap. No application imports/tests or native
execution on the host. No acquisition, DB BLAST or changes to old run files.

The parser owner can build against these exact shapes and the 655 lexical port.
The native owner needs the new exact operation/job shape plus actual offline
resource evidence. Result projection/return ownership follows these saved
schemas and original captures. Each remains a separate explicit unfinished
dependency; core tests do not count them as connected or completed.

Reread the original user attachment in full before work. After every tool and
substantial external/native reading, reread its objective and ENTIRE OPERATING
PRINCIPLES block verbatim. Never GOAL.md or a mutable goal/scope-amendment file.
Reread this port and 643 before claiming completion. Report exact source pins,
selected checks, numerical meanings and remaining native/integration limits.
