# Accepted B1 input-extraction contract

Root reviewed proposal001 and additive correction002 in full. The five B1
signatures, inputs, exact declared formats, output fields and failure meanings
are accepted as written in those two records. Correction002 takes precedence
for metadata identity/domains, exact FASTA headers/intervals, complete invalid
sequence retention and incomplete nulls. Preserve the original records.

The installed data-only schema is the transitive closure of the ten roots in
FREEZE_RECEIPT_001.json:33definitions, unchanged from proposal002. Its SHA256 is
`01f8987b1d35754056d6e0337d12868d77e4f9df336d0c72edcb7d9ec998d951`.
Existing version string literals are deliberately preserved. This freeze does
not install or accept B2/B3/B4/E as working implementations.

Fresh B1 coding ownership is exclusively
`gene_annotation_episode/bvbrc_proteome_inputs.py`,
`tests/test_bvbrc_proteome_inputs.py`, and a new dedicated verification directory.
Root owns the new B0 schema and relationship-validation module. The B1 worker
imports `proteome_data_schema` / `validate_proteome_data` /
`ProteomeDataError` from that module, whose implementation is being finished
concurrently. It must not bypass validation to make a test pass. A missing B0
implementation blocks integration testing only; the frozen shapes and original
examples permit independent extraction work and test construction now.

B1 implements supplied-byte FASTA inventory, supplied feature/genome/sequence
metadata snapshots, and recorded original-input indexing. No joins, numerical
aggregate calculator, request execution, schema expansion, production registry,
prompt, evidence-axis or annotation-credit work belongs to B1. Return envelopes
are exactly the frozen status/value/requirements/diagnostics shapes.

Required tests include exact source-byte bindings; duplicates and full sequence
groups; CRLF and multibyte header offsets; invalid/empty sequences; partial last
records; unknown versus complete sources; metadata scalar/null/blank failures;
duplicate JSON members; optional identities; explicit coordinate conventions;
native numeric lexemes; original input/reference ordering; supplied versus
effective parameters; and immutable source/saved values. No acquired output or
producer execution may be fabricated. Use supplied synthetic input fixtures
with that identity and keep native-output claims separate.

The full goal remains unfinished. Input witnesses, full reports, numerical
sheets/calculators, tool information and actual application result integration
are still required; this module does not make their absence acceptable as a
final result.
