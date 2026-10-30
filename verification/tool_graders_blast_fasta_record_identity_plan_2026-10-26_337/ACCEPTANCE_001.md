# Accepted original FASTA record contract and first coding boundary

Root read the complete337 proposal and verification report, inspected both
current public conflict maps, the reference-qualification consumer, and the
complete existing FASTA parser. The proposal addresses a reproduced missing
input distinction: two original records in one FASTA file currently collapse
onto one empty file pointer. Both sequence and description/metadata identities
must preserve that distinction. The proposal is accepted with the precise
clarifications below. The original proposal and its retained reproduction are
unchanged.

The implementation still preserves full original bytes and explicit separate
function-assignment provenance. An ordinal never supplies a function. Numerical
formulas, duplicate-sequence grouping, reference weights, evidence axes, credit,
episode ownership and existing frozen v1 results remain unchanged.

## New shared parser port and validation

Use the name `parse_blast_fasta_source_records(contents: bytes) -> dict` for
the proposed shared FASTA parser. This replaces only the proposed name
`read_blast_fasta_source_records`; its specified return fields and meanings stay
the same. Use parser terminology to distinguish this work from literature work.

The other new port is exactly:

    blast_record_identity(*, source_ref: str, pointer: str,
        record_locator: dict | None) -> tuple[str, str, str | int]

Preserve the existing source and pointer conventions: source_ref is a nonempty
string and is not normalized; pointer is an RFC6901 string using the current
empty-or-leading-slash and valid-tilde-escape checks. Do not strengthen existing
v1 source-string validation as part of this fix. A locator is null or the exact
two-field FASTA object, with an integer ordinal excluding Boolean. Non-null
locator requires empty pointer. Closed helper errors are
`blast_record_source_invalid`, `blast_record_pointer_invalid`,
`blast_record_locator_invalid`, and `record_locator_pointer_conflict`.
The parser requires bytes and otherwise raises `blast_fasta_bytes_required`.
Content failures use the existing parser codes and the proposal's per-record
or whole-file result fields, rather than dropping valid sibling records.

The helper only validates representation and creates an address. M owns actual
source receipt, whole-file identity, format, ordinal existence, full-symbol
proof and explicit source relationships. The public numerical functions must
not acquire or parse external files to prove those facts.

## Existing signatures, expanded from the proposal's placeholders

    prepare_native_blast_database_inputs(
        *, job, bundle, artifact_catalog, metadata_payloads, subject_snapshots)

    populate_native_blast_database_sheets(
        collection, *, prepared_inputs, artifact_catalog, native_convergence=None)

    build_database_sheet(
        result: dict, *, reference_metadata: list[dict] | None = None,
        target_context: dict | None = None, database_profile: dict | None = None,
        description_bindings: list[dict] | None = None,
        sequence_identity_bindings: list[dict] | None = None,
        geometry_program: str | None = None,
        calculation_context: dict | None = None) -> dict

    calculate_database_probabilities(sheet: dict, *, model: dict | None = None) -> dict

Their arguments and outputs otherwise retain the proposal's explicitly
versioned nested input changes and unchanged numerical components. No new
required argument, implicit source matching or arbitrary future schema admission
is authorized.

## Assignment and ownership

Fresh339 owns proposal workloads A and B together: the new shared pure helper
and test, `blast_sequence_database.py`, `blast_database_grader.py`, and their
existing focused tests. It implements the two corrected identity maps,
description-to-sequence cross-record check and explicit v1/v2 scientific sheet
dispatch. Its concrete handoff is the two shared ports, exact v2 row/schema
admission and public numerical examples. It must not edit M, N, R, E, iteration,
VDB, knowledge, accounting or historical records.

This combines two tightly connected coding workloads under one owner without
changing their modular ports. C/D metadata preparation and I integration are
later distinct assignments; neither is silently assigned to339. They can build
against these exact ports without waiting for the whole339 task. Current
concurrency also includes E336 integration verification and338 VDB planning.

While E336 verifies its stabilized dependency snapshot,339 may add its new
helper and new tests. Before editing the two existing scientific modules, it
must obtain the end of that specific source-pin window from E336. This is an
edit coordination constraint, not a dependency between complete workloads.
Preserve before/after hashes and all real test outcomes. Do not stop another
subagent or reinterpret a timeout as its completion.

Acceptance authorizes the first coding boundary, not a completed capability or
count increment. All337 verification cases and the full fixed308 goal remain.
