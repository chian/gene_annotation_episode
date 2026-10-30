# Shared VDB sequence-table lexical port: verified implementation

The public pure reader `read_blast_vdb_sequence_table(contents: bytes, *,
source_ref: str, source_version: str) -> dict` is implemented in
`gene_annotation_episode/blast_vdb_inputs.py`. The existing specific-entry
parser consumes its rows and native integer results. The frozen001 interface
remains unchanged on disk; additive002 records the lead agent's conversion-limit
clarification.

The reader retains the original byte digest/size, exact decoded text, every
splitlines row and its original ordinal, complete tab cells and literal fields.
It supplies lexical issues only. It does not request a search context or infer
selection, dataset/member identity, biological validity or native completion.
For example, `0004` becomes the native integer 4 while its original spelling is
retained; `0` remains integer 0; lowercase `acgu` remains exactly `acgu`.

Before changing the parser, bounded check115 captured 37 complete legacy parse
outputs and saved reparse results, 10 exact caller errors, and 6 complete metadata
binding variants. The retained `legacy_expected.json` is 464,925 bytes with SHA256
`5d52daf89d5c0c341befbe1873f1312057933c31d6f8adc98bd26e46d4b76593`.
`PRECHANGE_CAPTURE.json` records its receipt and the original parser source pin
`2fd07240433aac07523fa63e6c570e9879cc1f7b5cdd67808de994f5d5d5cbdf`.
Regression tests consume these static observations; they never execute historical
parser source. The mixed CRLF fixture still emits legacy record ordinals 0 and 1
from native row ordinals 0 and 5. Binding both saved records remains available;
altered context, source hash, native ordinal and sequence facts retain their
previous rejection behavior. Legacy U handling, zero-length handling, N/A
filtering, duplicate selectors, `gnl|SRA|` matching and entry=all rejection remain
unchanged in the recorded cases.

The additional conversion-limit cases follow the inspected prechange control
flow and the unchanged `_native_integer`, rather than a new historical run.
The reader retains an oversized ASCII decimal lexeme with null integer and the
distinct `integer_conversion_unavailable` issue. The legacy wrapper skips that
row when it already has empty/N/A/width defects, preserving valid neighbors.
An otherwise eligible row delegates to the unchanged integer function and raises
the same ValueError. No process integer limit was changed.

| Check | Purpose | Result |
| --- | --- | --- |
| check115_vdb_lexical655 | Prechange observation capture | 1 passed in 0.30 s |
| check115b_vdb_lexical655 | Initial lexical port and existing input/binding paths | 140 passed in 1.51 s |
| check115c_vdb_lexical655 | Final code including conversion-limit clarification | 145 passed in 1.37 s |

All attempts are under
`verification/tool_graders_hmmer_map_verification_2026-10-28_529/` and were
collected from their original handles after reaching terminal/quiescent state.
All use 20 GiB RAM, 4 GiB scratch, zero swap and no wall cap. Every receipt reports
unchanged source, dependency, stdlib and binary pins. Every execution audit has
no outside modules or unbound mappings and reports native mappings unchanged.
No scientific executable was selected or invoked.

The final 145 cases comprise 113 tests in
`tests/test_blast_vdb_sequence_table_655.py`, all 28 existing
`tests/test_blast_vdb_inputs.py` cases, and four existing
`tests/test_native_blast_database_metadata.py` cases (the three native parser
routes and the VDB duplicate/sample numerical case). The unchanged numerical
fixture still reports 2 origin-bound subjects, 1 demonstrated sequence group,
1 duplicate representation, 2 origin samples and full-query coverage 1.
The new cases cover exact row fields/issues/order, malformed and blank rows,
N/A, CRLF/trailing newline, duplicated identifiers, zero and malformed lengths,
lowercase/U preservation, invalid UTF-8, detached outputs, saved binding/reparse,
forbidden filesystem/network/process access, and the conversion-limit exception.

Inspection covered the entire affected `blast_vdb_inputs.py` module, including
`_parsed_start`, `_native_integer`, `_extraction_context`, `_emit`, `_reparse`,
`_recheck_metadata`, `bind_blast_vdb_metadata` and sheet validation. The complete
direct consumer functions read in `native_blast_database_metadata.py` were
`_validate_vdb_metadata`, `_parser_locator_supported`,
`_record_locator_qualification`, `_check_parser_location`,
`_qualify_parser_locations`, `_vdb_dataset_matches`, `_vdb_units` and
`populate_native_blast_database_sheets`; the calculator's complete `_metadata`
consumer was also read. The full existing VDB input test module and the relevant
native metadata route/binding test functions were inspected. Related module
references and worker module lists were searched to identify direct consumers;
that search is not claimed as a full inspection of unrelated workers.

The existing native-metadata path still receives caller-selected parser/context
and retained artifact bytes, records the full parse result, validates native
record pointers and supplied bindings, and passes the same metadata into the
existing sheet/calculators. Saved metadata still replays from retained input text
without opening its source reference. The change adds no selection, episode,
controller, credit, publication or prompt behavior and adds no scoring function.

Current verified source pins:

- `gene_annotation_episode/blast_vdb_inputs.py`:
  `d6b4d0ff419db354e40ef6e5815e8ecba98aaf347e2b9c206c31444fb29fcc29`
- `tests/test_blast_vdb_sequence_table_655.py`:
  `0f9d148863342023977dbf6693aea591f72a85745e192a542bfe6a9fe6a8d3d6`

`VERIFICATION_RECORD.json` contains exact receipts, selected tests, source and
contract pins. Current source bytes were compared to the final tested snapshot.

Completion is limited to this shared lexical port and preservation of the
existing supplied-data metadata paths exercised above. These are synthetic
fixtures, not authentic native-output verification. No VDB acquisition, database
BLAST, supporting-utility selection, resource execution or full episode requested
return was added or verified. Utility schemas, native execution, calculators,
publication, prompts, inventories and other owners' tests were not edited.
