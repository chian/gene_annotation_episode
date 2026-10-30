# Additive parser identity and malformed-field decisions

These root decisions supplement ACCEPTED_PURE_INTERFACES_001, leaving its
original bytes and the reviewed proposal untouched.

1. The common NativeNumber shape has five keys; NumericCell has eleven keys.
   The explicit named shapes control; the prose counts in 001 were mistaken.
   No field is added or removed by this correction.
2. MetaCATS document_id kind strings are exactly `metacats_chisq_table`,
   `metacats_pair_table`, `metacats_raw_r_table`, `metacats_metadata`, and
   `metacats_adjusted_matrix`. Identity parameters are all applicable parser
   arguments excluding data/artifact. MSA frequency kind is `msa_frequency_table`
   with alphabet, layout and encoding parameters.
3. A native MSA cell identity is table_id plus a JSON pointer to that cell,
   e.g. `table_id + '/rows/' + str(row_index) + '/score'`. row_index is the
   original zero-based data-row index, not a reindexed list position after
   excluding malformed rows. In the entropy components, native_observation_ids
   contains the matching row Score identity (all candidate Score identities
   on duplicate-coordinate conflict). No arbitrary duplicate is selected.
   The score residual remains null on duplicate or unusable observations.
   Future provider extraction preserves this exact identity convention for
   every separately retained native numerical cell.
4. ReferenceBinding.native_ref_type is a nonempty original producer token,
   not an invented enum or a scientific interpretation. The reference's source
   identity and row association remain separately validated.
5. Raw R wrapper_column_token and wrapper_row_token preserve literal quoted
   tokens, e.g. `"resultCST"`, `"1"`. Section heading is the unquoted native
   heading text. site_token preserves surrounding original spaces; position
   NativeNumber contains only its exact digit substring. Parsing never evaluates R.
6. Current/legacy omnibus trailing group columns are retained in order,
   including an empty heading/cell in the retained legacy format. Empty or
   malformed group semantics are qualified and never assigned a made-up group.
   Extra columns in fixed-width pair/raw R records cause partial status and
   an unparsed offending row, with original bytes/location retained; later
   readable rows keep original row indices. Do not silently discard columns.
7. A malformed MSA protein Detail fragment without '=' remains a detail item:
   raw_token and raw_residue_token are the complete fragment, symbol is null,
   count is native_number('') at the zero-width end of that fragment (the count
   is absent). Add a malformed_detail diagnostic and partial status. Do not
   force a syntactically valid number to claim malformed numeric syntax, and
   do not treat the fragment as a known residue or count. Unknown=2 remains an
   unresolved residue token with its actual count2.
