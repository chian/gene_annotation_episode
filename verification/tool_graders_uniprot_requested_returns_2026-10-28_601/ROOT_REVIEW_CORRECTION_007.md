# Correction to selected-return verification 006

Verification 006 incorrectly lists repeated `assigned_page` clauses as a host
repair. `validate_uniprot_return_selection` already calls
`_unique(selection["pages"], "selection.pages", selector="publication")`.
Consequently, two clauses for the same assigned publication are invalid inputs,
including clauses that request different fields. Multiple requested fields
belong within that one page clause. The host's deduplication does not suppress a
valid second assigned-page clause; no production change is required for this
case. Root raised the concern before checking the existing uniqueness guard.

The distinct missing-sequence-artifact concern remains: valid selected fields
must survive when one requested sequence artifact is unavailable. The host
worker has written the narrow handling and targeted checks; this correction
does not claim those new changes have passed runtime verification.

Earlier evidence and the goal remain unchanged. This is an additive correction
to root's review finding, not a change to the selection contract or task scope.
