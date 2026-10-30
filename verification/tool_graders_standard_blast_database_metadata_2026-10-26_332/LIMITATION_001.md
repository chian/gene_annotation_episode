# Existing multi-record FASTA source-address limitation

Counterexample (synthetic; no database execution):
[inputs](check009/temporary/pytest/test_M3_multiple_fasta_records0/supplied_inputs.json),
[sheets](check009/temporary/pytest/test_M3_multiple_fasta_records0/sheets.json),
[components](check009/temporary/pytest/test_M3_multiple_fasta_records0/components.json).

The single received FASTA has two complete, different ten-residue records.
Both source-qualified proofs are available, keep original record ordinals0 and1,
and agree with the supplied complete symbols, lengths and SHA256 values.
Both unchanged `sequence_identity_bindings[].binding.pointer` values are the
original empty pointer for the same source_ref.

The public metadata schema's sequence proof supports
`representation='fasta_record'` with record_ordinal. Its separate sequence binding
does not carry that ordinal: fields include source_ref and pointer. In the public
`validate_native_blast_database_metadata_payload` path, `_lower_payload.provenance`
allows a nonempty non-JSON locator only for declared supported parser formats;
FASTA is not one of them. The existing `_proof_bindings` path consequently
requires binding.pointer=='' for FASTA. M preserves that exact wire meaning.

In the actual303 calculation, `blast_database_grader._sequence_links` groups
record identities by `(binding.source_ref, binding.pointer)` and marks different
digest/molecule/length identities at that same address as
`blast_sequence_binding_source_identity_conflict`. A record ordinal in the
separate M proof cannot change that public303 identity key.

M therefore retains both full proofs and their original bytes, reports
`full_sequence_source_identity_conflict`, and excludes the conflicting identity
links from whole-sequence grouping. Native hit/HSP measurements survive (the
counterexample's maximum bit score remains20). It does not invent a JSON pointer,
change the original source_ref, or select the first FASTA record.

A single-record FASTA source, or JSON with distinct original record pointers,
has an unambiguous current binding and is verified separately. Supporting
multiple distinct FASTA records at one source through303 would require a
separately scoped source-address/wire contract change. This task makes no such
shared change and does not claim that capability.
