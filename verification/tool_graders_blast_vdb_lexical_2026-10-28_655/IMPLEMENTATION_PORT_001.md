# Shared VDB sequence-table parsing port

This is an implementation interface for the remaining blast_vdb_cmd path. It
does not change the user-entered goal, scope, scoring or episode behavior.
The formatter utilities remain excluded by the user's explicit instruction.

## Boundary and ownership

Owner655 exclusively edits gene_annotation_episode/blast_vdb_inputs.py,
tests/test_blast_vdb_sequence_table_655.py and this verification directory.
Do not edit utility result schemas, native execution, existing test files,
calculators, publication, prompts, inventories or another owner's files.

Add the pure public function:

    read_blast_vdb_sequence_table(
        contents: bytes, *, source_ref: str, source_version: str
    ) -> dict

It reads only the declared four columns `%i TAB %a TAB %l TAB %s`. It does not
infer invocation scope, source datasets, member identities, selection matches,
native completion, biological confidence or sequence normalization. Both the
existing specific-entry metadata parser and the future supporting extraction
path must use this same lexical reader. No fabricated search context is needed.

Return these exact top-level keys:

    schema: blast_vdb_sequence_table_v1
    source_ref: the supplied nonblank string
    source_version: the supplied nonblank string
    input_identity: {sha256: original-byte digest, size_bytes: original-byte count}
    native_text: exact UTF-8 text, or null if decoding fails
    rows: list of the rows below
    issues: the existing located format_unsupported issue on invalid UTF-8

Each row has exactly:

    row_ordinal: zero-based position in native_text.splitlines()
    line_number: row_ordinal + 1
    cells: the complete unmodified line.split("\t") result
    fields: null unless there are exactly four cells; otherwise
        {native_identifier, native_accession, length_lexeme, sequence_symbols}
        containing the four original strings, including empty strings or N/A
    native_reported_length: integer parsed by the existing _native_integer,
        or null for unavailable/invalid width or invalid integer spelling
    issues: ordered lexical issues described below

All decoded lines remain rows, including blank, malformed and N/A lines. No
compaction, deduplication, inferred fifth field or guessed identifier splitting.
Preserve CRLF and final-newline text in native_text while row locations follow
the existing splitlines convention. Empty input has no rows. Zero is a parsed
native integer, not an assertion of successful biological extraction.

Row issues use exactly {code, field}, where field is null or one of the four
fields above. Width != 4 yields only {code: column_count_invalid, field: null}.
Otherwise visit the four fields in column order: empty yields field_empty;
literal N/A yields field_unavailable. A present non-N/A length that fails
_native_integer yields integer_lexeme_invalid after the field checks. These
are lexical facts, not output/capture/selection completeness classifications.

## Existing consumer preservation

Refactor parse_blast_vdb_member_sequences to consume the shared lexical rows
and reported integer. Preserve its entire existing return value, exceptions,
specific-entry context validation, compacted record_key convention, original
native_record.row_ordinal, identifiers, matching, sequence validation, issues
and saved reparse behavior. In particular, its legacy handling of U, zero length,
N/A, duplicate selectors and gnl|SRA| remains unchanged. Do not convert old
results, fix unrelated semantics or teach the old parser to accept entry=all.

Read the entire affected module and all actual consumers, especially _reparse,
bind_blast_vdb_metadata and native_blast_database_metadata._vdb_units. Retain the
current legacy parser outputs as explicit test fixtures before editing it, using
bounded application execution. Runtime must never execute old snapshot code.

## Verification and handoff

Cover valid rows on both sides of malformed/blank/N/A rows, CRLF/trailing newline,
duplicate IDs, malformed and zero integers, exact original hashes/text/ordinals,
lowercase and U symbols retained without lexical normalization, invalid UTF-8,
detached return records, and forbidden filesystem/network/process access.
Compare legacy outputs and saved metadata binding/reparse against retained
prechange expected outputs and run the affected existing VDB input/binding tests.
Do not rerun unrelated native operations or claim authentic native verification.

Use bounded529 for every application import/test, with 20 GiB RAM, 4 GiB scratch,
zero swap and no wall cap. Reserve check115_vdb_lexical655 and distinct suffixes
for genuinely necessary followups. Host stdlib source/hash inspection is allowed.
Never run database BLAST or acquire VDB data as part of this workload.

Read the original user attachment in full first. After each tool/substantial
external/native read, reread its objective and ENTIRE OPERATING PRINCIPLES
verbatim. Never read GOAL.md or create a goal or scope-amendment file. Reread this
contract before reporting. Report exact source pins, fixtures, checks and limits;
this port alone does not establish a selectable VDB utility or episode integration.
