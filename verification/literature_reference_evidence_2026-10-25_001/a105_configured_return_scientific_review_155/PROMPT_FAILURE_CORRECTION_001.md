# Correction of the provisional production-display diagnosis

The broad runs reported a failing synthetic provider-transport test asserting
that a generated curve accession should be absent. Root initially described
this as a production display defect. That diagnosis was premature and is
withdrawn. The failure is real for the manually assembled test input, which
omits the reference's recorded `origin` metadata; it does not establish a defect
in the production storage-to-prompt path.

Fresh workload158 traced the complete applicable path: Store publication and
retrieval, ordinary model record view, Workflow working state, scoped received
record display, selected record rendering and provider frame reconstruction.
The actual tool-generated reference retains `origin=tool` throughout. The
existing provenance-aware renderer already suppresses its internal accession.
It deliberately preserves public or external scientific accessions, including
hash-shaped strings. Root independently read the complete renderer and the
failing fixture. The same fixture also fails against untouched pin151, whose
relevant prompt files are byte-identical to current.

The approved correction is to make the manual synthetic fixture supply its
actual generated-record provenance, retaining the original no-leak assertion.
New tests use genuinely persisted selected-operation results, actual working
and received views, original typed forms and controlled provider transport.
No production fallback, renderer change, generic hash/numeral filter, custody
rewrite or new runtime rule is adopted. The earlier fixture and failed runs
are retained. Verification results are recorded by158 and root's later check.

The two production repairs remain the missing-selected-input semantics and
structural scalar reading. Neither this fixture correction nor those repairs
adds assay coverage or proves A105 adequate.
