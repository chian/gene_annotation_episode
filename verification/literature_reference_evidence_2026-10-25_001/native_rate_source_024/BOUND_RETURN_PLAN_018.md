# Native bound-return correction proposed before edits

Parent review and the independent child probe `BOUND_PROJECTION_GAP_017.json`
confirmed that native saved extraction retained `< approximately 12 nmol/min/mg`
as canonical threshold 0.012 umol/min/mg, `lt`, approximate true, but the actual
22-field requested individual-cell return and provider text lost threshold and
relation. The final121 tests did not cover this connected-boundary loss.

Proposed native-only correction:

1. Add required `threshold: number|null` and `bound: none|lt|le|gt|ge` to native
   cells and the native projection's closed return schema (24 fields). Legacy
   fifteen-field schema, reasons, CSV cells and outputs stay exact.
2. For `reference_rate` / `test_rate` only, retain the corresponding censored
   row's canonical threshold and relation; the point `value` stays null. If its
   canonical unit is unknown, threshold is null but the known relation remains.
   Other components carry null/none. No difference/ratio/profile bound is guessed.
3. Persist these cells in the original numerical sheet and outcome. Projection
   copies saved fields. Exact returned-value validation, requested subsets,
   native received-table storage, saved-only reopen and ordinary provider text
   carry them. No unrequested other-arm quantity is added to a requested cell.
4. Test actual admission/subsets/reopen/provider text and rejection of altered
   threshold/relation, plus lower/upper/approximate and unavailable-unit cases.
   Existing `_source_result` already renders bound/threshold; typed native rows
   already flow through ordinary `_values`. No renderer or C7 change is planned.

Shared source release is PAUSED pending parent review of this plan and its
implementation. This supersedes the release status in `FINAL_VERIFICATION_016.json`
and `IMPLEMENTATION_REVIEW_011.md` without rewriting those temporal facts.
The native lexical helper module alone is stable at SHA256
`264328313d32a8ed0315eb4a80388be775a8c7c2b51ad25041aad071a295dc67`
and released for read-only reuse under `NATIVE_LEXICAL_API_015.md`.
