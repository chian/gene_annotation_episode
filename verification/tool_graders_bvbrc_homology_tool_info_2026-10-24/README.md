# Homology scientific tool information

The production resource catalog now declares two actual commission-only modes:
`bvbrc.homology.database_identification` and
`bvbrc.homology.pairwise_correspondence`. Each uses the existing API assignment
or existing results assignment, with the selected native Homology application,
configured resource and mode-specific adapter parameters. No direct execution
tool, episode type, prompt template or scientific formula was added.

Eleven distinct focused cases passed: ten in `tests.log`, followed by the
corrected library-selection case in `selection_followup.tests.log`. The earlier
fixture passed the parent's three-field display rows to a selector that accepts
name/resources or the complete four-field child information; it now uses the
actual two-field choice and verifies that the library supplies the frozen full
instructions. Another initial fixture assertion treated ToolRegistry.catalog's
dictionary as a list; correcting the assertion required no production change.
No failed test was removed.

Verified: both scientific modes; real launch and results payloads; wrong
application, launch resource, service, result mode, adapter and pairwise model
rejection; absent/unknown adapter exclusion; two explicitly configured resource
routes; literal-test retrieval; the parent's name/description/resources display;
the child's exact name/description/resources/instructions; matching frozen
invocation contracts; changed instruction rejection; no transport during any
catalog or retrieval operation; and absence from the direct ToolRegistry.

Only the exact configured installed adapter enables these declarations. This
does not establish live BV-BRC authentication or deployed software. These tests
verify the real catalog and frozen-library boundaries, not a complete scientific
episode. The separately owned composed Workflow test must establish selection,
construction, execution and numeric delivery together. Pairwise full Workflow,
live native outputs, other application families and presentation verification
remain separate requirements.
