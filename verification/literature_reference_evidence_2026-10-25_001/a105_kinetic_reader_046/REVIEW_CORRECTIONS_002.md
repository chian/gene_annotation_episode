# Reader046 parent review corrections and final limits

Additive to INTERFACE_PROPOSAL_001; earlier proposal remains unchanged.

Parent read the first398-line implementation and403-line tests, then found:

1. An outside-witness comparator or approximation before a selected `95%`
   could be lost, producing an exact confidence level. The reader now rejects
   such confidence levels, including recognized postfix bounds, through
   `qualified_source_confidence_unsupported`. The structured error retains the
   verified raw witness; caller selections remain unchanged. No bounded or
   approximate level is promoted to exact. Complete literal percent syntax is
   still required; no probability-unit guess or level default is introduced.
2. Reversed exact CI endpoints could round to equal floats before ordering.
   Ordering is now checked using exact decimal Fractions before float output.
   Distinct ordered endpoints that would collapse to false zero width also
   leave the canonical interval unavailable with `source_numeric_range`, while
   retaining the exact original interval and raw endpoints.

Expected dependency fingerprints in the module are release expectations, not
runtime attestations. The pure function performs no implementation-file IO.
The final receipt records actual frozen helper and045 calculator hashes used
during the focused checks. Future selected storage must pin/authenticate those
dependencies and saved input/output bindings rather than treating these static
strings as proof. This workload changes no storage or episode implementation.

Implemented finite input syntax: exact UTF8 original/text witnesses; literal
signed decimal/e notation; supported case-sensitive SI kinetic units; recognized
native limits/approximation; source selected uncertainty statistic/count/basis;
complete `[lower, upper]` or `(lower, upper)` CI intervals and complete literal
percentage confidence levels. Unsupported complete parameter units retain raw
inputs and a specific missing canonical operand. Malformed/clipped selections
are repairable errors. Other interval forms, arithmetic expressions, unprinted
curve fitting, image quantification, covariance/model extraction and implicit
parameter derivations remain unimplemented.

Investigation judgments and numerical arithmetic remain separate. Quote matching
does not prove molecular identity, control comparability, physical observation
identity, fit validity or physiological specificity. Missing preparation and
independent-replication knowledge remain unknown. No literal spread/count supplies
a covariance or observation model. No source-to-target/final credit is computed.

Pending integration boundary: a future selected LiteratureEpisodes path must
preserve exact requested numerical subsets and source qualifications through
ordinary typed reporting. Scientific labels/witnesses must not automatically
leak unrequested numbers. This pure reader has no renderer, selected catalog
operation, repository, typed return, runtime observation or model invocation.

Development checks first exposed invalid synthetic reference IDs and ambiguous
fixture unit/count locations; those fixture defects were corrected before
nonnull coverage was claimed. Additional adversarial cases led to explicit
count-as-parameter, compound-unit, unsupported adjacent-unit and plus/minus
common-unit guards. Only the final terminal group is reported as final coverage;
intermediate groups overlap and are not summed.
