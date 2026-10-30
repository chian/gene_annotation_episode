# Source requirements retain their actual meaning

Root accepted this additive correction during final review on 2026-10-25.
The frozen records, signatures and formulas are unchanged.

The initial coordinate/coverage implementation treated any missing member
binding as missing staged source bytes. That was too broad: the source binder
also records unknown invocation, missing path proof and incomplete record
populations, which need scientific metadata or input metadata instead.

Coordinate and coverage outputs now preserve the supplied binding's actual
requirements and diagnostics verbatim. Missing source cells link to the supplied
requirements associated with their scoped reason codes. Requirement identifiers
remain opaque; the calculators do not reconstruct or decode the binder's hash
convention. Multiple supplied requirements for one shared reason remain
inspectable with the original scoped diagnostics. A local missing-binding
diagnostic may be added, but missing bytes are not invented from missing
metadata. With no binding supplied, the explicit staged-input requirement
remains appropriate. A saved unresolved binding without a supplied requirement
gets a generic scientific-metadata binding requirement, without guessing that
bytes are missing.

Independent valid numerical cells retain their values. Inverse native-position
search does not require a resolved source association and therefore does not
inherit irrelevant source-acquisition needs. Known source lengths still constrain
the caller's inverse query bounds.

The prior 377-pass suite, source snapshots, replay receipt, implementation/test
files and affected bound-result examples are preserved in
`before_requirement_reporting_correction/`. `SAVED_RECALCULATION_INITIAL.json`
also preserves the earlier successful replay receipt. The original 82-pass,
two-fail joint test output remains in `TEST_INITIAL_JOINT.json`; those two
failures were incorrect expectations, not hidden implementation passes:
the combined member-3 cooccupied exclusion is native position27 at aligned
column28, and the larger native file contains2/2/1/1/1 rows per block.

No episode, acquisition, credit, resource choice or new runtime gate is added.
