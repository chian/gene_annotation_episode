# Implementation clarifications agreed with D2b

This separate additive record preserves the exact 007 contract pinned by
accounting update092.

Pure plan validation checks closed shapes/types, FileIdentity consistency, the
declared C request/software and calculation parameters, and lexical path/overlap
relationships. A structurally valid retained FileIdentity with the wrong
operation-specific format becomes a typed invalid retained-result outcome
(`unsupported_format`) in the runner, rather than an invented scientific value.

Saved sheet/components errors use artifact_role null and the relevant existing
field; they are not renamed as received-transform operands. If C validates an
original native envelope but B rejects its scientific arithmetic, keep that
native file for diagnosis with invalid worker state and null sheet/components.
The host must not extract comparison numbers from this rejected native value.

A saved sheet that validates independently can remain diagnostic partial output
when its required original baseline is absent or inconsistent. Components stay
null and the calculator is not called. The sheet_file alone then establishes
neither a valid saved-sheet descriptor nor delivered scientific measurements.
These distinctions preserve valid retained data without authorizing its use as
an accepted numerical result.
