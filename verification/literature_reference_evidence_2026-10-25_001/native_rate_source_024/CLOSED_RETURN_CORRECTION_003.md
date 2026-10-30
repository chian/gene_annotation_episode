# Actual closed-form boundary supersedes optional native fields

The first joined native input/storage check produced 36 passes and one failure
at `form_with_facts`: `communication._compile_closed_schema` requires every
declared object property to be required, and rejects optional properties with
`open_object`. The failure is preserved in NATIVE_TESTS_002.xml. No shared
communication behavior was changed to avoid it.

The parent directed a separate CLOSED native return projection, while retaining
one rate sheet, ten numerical components, the calculator/provider and operations
table. This supersedes the optional-property mechanism approved in addendum 002.

- Legacy `literature_rate_cells` schema, unavailable reasons and emitted v1
  rows remain exact, including their original required field set.
- New `literature_rate_source_cells` has the same numerical component meanings
  and required native metadata: nullable per-arm subject/construct/preparation
  refs and the `approximate` boolean. All fields are declared, required and
  closed. New native unavailable reasons belong only to this projection.
- A native return view shares the actual repository and saved operation table,
  and owns a separate received-subset table. Projecting the wrong saved version
  is an explicit mismatch, never a lossy conversion.
- C7 partitions actual v1/v2 saved sheets into their declared return sources and
  validates/adopts/forwards each through its corresponding return view. The same
  requested_rate_components selects the same numerical components.
- The native operation description identifies its actual native return source
  before parents select a child's form. No second numerical scoring sheet,
  evidence axis, score, model call or continuation behavior is introduced.

The parent also approved preserving approximately printed point estimates with
an explicit native flag. A rate point, its mean-based contrast and profile carry
the qualifier from their actual mean operands. SEM/SD/count-only uncertainty
components do not become approximate solely because a mean is approximately
printed. Signed finite rates remain signed. This is separate from censoring.

All refinements remain engineering over synthetic data. No primary source was
read or interpreted. The independent root probes identified composite qualifier
and same-artifact representation issues; meaningful regressions retain those
cases in the native suite. Partner parser modules remain unchanged.
