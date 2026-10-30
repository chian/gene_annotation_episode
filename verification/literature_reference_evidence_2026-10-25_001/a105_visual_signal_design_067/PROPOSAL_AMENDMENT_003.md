# Final additive declaration correction003

Final normative schemas are REQUEST_SCHEMA_003, EXTRACTION_SCHEMA_003,
SHEET_SCHEMA_003 and RETURN_SCHEMA_003. Earlier001/002 are preserved design
history.003 includes002's three corrections and strengthens the typed return:

- signal_use preserves whether this is an experimental-comparability control,
  the measured endpoint, another role, unknown or conflicting.
- meaning_statuses preserves known/unknown/conflicting for every actual entity,
  condition, endpoint and normalization binding. A null reference alone cannot
  distinguish unknown identity from contradictory source identity.
- physical_identity_states/reference_identity_states explicitly qualify any
  owner references. They supply no preparation count or independence assertion.
- uncertainty_kind is unknown, with uncertainty_evaluation explicitly stating
  numeric_uncertainty_reader_unimplemented. The new finite relative-signal
  route does not parse numerical SD/SEM/CI/covariance/counts. A compound printed
  expression or available uncertainty that it cannot parse stays retained and
  partially unavailable; do not relabel that as a paper-level unreported fact.
  Adding numeric uncertainty extraction requires its own declared operands and
  implementation. This is unfinished broader scope, not a hidden claim that
  seven descriptive cells constitute a complete experimental-validity score.

The request/result v2 version names denote this proposed new interface; no saved
v2 scientific data or implementation is being migrated between drafts. Parent
must review this final declaration generation and its explicit limits. No old
v1 result, descriptor, scientific sheet or other-session file is changed.
