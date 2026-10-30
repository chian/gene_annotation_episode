# Additive reader clarification 002: observed inconsistency is retained data

This clarifies, and takes precedence over ambiguous validation wording in
`LEGACY_REPORT_READER_CONTRACT_001.md`. It records root's review direction on
2026-10-25. It does not change the immutable goal or authorize producer changes.

Schema validity and native scientific consistency are separate.

1. A lexically valid native number is a `present` cell even when it contradicts
   another observed number. For example, `Identities = 12/10` retains numerator12
   and denominator10 as present integer cells. An endpoint outside the observed
   sequence length stays a present coordinate cell. The parser does not replace
   those values with null, clamp them, recompute them, or drop the HSP.
2. An unparseable numeric token is an `invalid` cell with null value and retained
   native text/location, accompanied by `invalid_native_number`. Truly absent
   native text is a `missing` cell. These states remain distinct.
3. Closed schemas validate JSON type, primitive numeric lexical grammar, cell
   state, exact keys, hierarchy, source binding and offsets. They do not reject a
   saved result merely because actual native counts/coordinates conflict.
4. Relationship validation recomputes the applicable consistency checks from
   present native values and **requires** the corresponding issue records. For
   example: numerator above denominator -> `count_out_of_bounds`; different HSP
   denominators -> `alignment_denominator_mismatch`; endpoints versus nongap
   symbols -> `coordinate_symbol_count_mismatch`; endpoint outside full sequence
   length -> `coordinate_out_of_bounds`; decreasing protein endpoints ->
   `nonprotein_coordinate_order`; mismatched displayed traceback widths ->
   `traceback_width_mismatch`. It accepts the preserved observed values when the
   required issues are present. Omitting an applicable issue makes the projected
   result invalid; it does not make the native observation disappear.
5. The parser sets `parse_state=partial` for those inconsistencies and retains all
   unaffected queries, subjects, HSPs and cells. A native contradiction is not a
   whole-result `failure` when supported query information remains.
6. Later calculators decide which specific measurements remain computable.
   Observed scores/counts can remain inspectable while a contradictory traceback
   blocks residue correspondence or coverage for that HSP. They must not convert
   native inconsistency into zero measurements or successful complete execution.

`validate_directional_report` raises the contract error only for a malformed
projection, inconsistent source/ordinal relationships, or missing required
consistency issues. A faithful projection of a malformed native block is a valid
partial result. Add tests for both cases: accepted contradictory source with its
required issue(s), and rejected projection that removed those required issue(s).

Both contract001 and this correction002 must be supplied to the reader implementer.
