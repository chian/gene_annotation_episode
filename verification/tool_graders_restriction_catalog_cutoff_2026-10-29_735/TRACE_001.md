# Bounded own-catalog identity735

Implemented only the assigned ActionRecords API under736 CONTRACT_001.md.
The original user attachment remains the goal authority. No goal/scope change,
new scientific sheet, calculation, ToolInfo, episode prompt or workflow layer.

`own_enzyme_reference(context, reference, *, before_decision_index=None,
through_receipt_index=None)` retains the old own-episode path when both cutoffs
are None. Otherwise both operands must be exact nonnegative integers. Its
existing context authentication still proves run/path/request/role/scope.

The existing `_query` now has optional cutoff operands. The bounded branch adds
two conjunctive predicates before result ordering/limits: action decision index
must be strictly below the supplied commission index; an actual own-source
receipt must have the same run/episode/source, kind own_action, matching action
source_index and receipt index at or below the supplied original cutoff. This
is an EXISTS join, so receipt multiplicity cannot duplicate selected actions.
An earlier action completed after a child's frozen receipt prefix is excluded.
Unknown receipt history is an explicit failure, not a fresh-state fallback.

Only eligible rows reach unchanged `_authenticated`: original operation key,
name/arguments/scope/outcome, job publication proof, retained source/sequence,
native file and mapping availability relationships, and original operand
receipts retain their existing validation. Enzyme names still come from that
validated catalog, falling back to the original native catalog when needed.
Arguments, source labels, mapping guesses and other episode actions supply no
catalog authority. Exact case-sensitive string identity is preserved.

The existing own_action_results, its requested selection and pagination, frozen
facts, publication/native parsing,719 calculations and723 numerical projection
are untouched.735 performs no record/receipt/history write or credit operation.
Root736 consumes the bounded API to validate original explicit initial forms;
that receiving proof and all full scientific/public paths are outside735.

The verification file reuses729's explicitly synthetic namespace authority
seam, including a tiny unmeasured catalog. No test calls native execution,
719 calculation, an external model/network service, or the original scientific
Store. Tests distinguish actual metadata/SQL proof from scientific result proof.
This component alone establishes neither ToolInfo installation nor a complete
native scientific episode path. All R1–R7 and prior FBA work remain open.
