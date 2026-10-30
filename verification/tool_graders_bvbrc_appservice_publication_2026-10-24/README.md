# AppService host/publication integration checkpoint

The host now retains original acquisition receipts, frozen publication inputs,
complete artifact bundles and separate Homology sheets/components. A configured
installed Homology implementation receives only retained bytes and authenticated
supplied metadata. The selected download performs publication without another
action, model request or observation. Reads preserve the original saved
calculation; explicit recalculation consumes its saved sheet.

`root_tests.log` records **114 passed in 396.77 seconds** across publication,
ordinary AppService Workflow, adapter selection, service and contract tests.
This run began before the subsequent metadata and Homology return-hook fixes;
it establishes its named tests, not the final Homology numerical-return path.
The ordinary Workflow uses controlled native responses and the shared loop.

The results metadata correction preserves the original task while allowing
metadata inspection of a supplied input that is not a generated output. Any
present task/output association must still match. The packaged resolved-input
schema now permits the typed original task for metadata, optional because the
same operation is available before submission. The first post-fix group passed
97 tests and failed one obsolete assertion that every schema property was
mandatory. After correcting that assertion, the complete contract/input group
passed **63 tests in 202.35 seconds**. The initial log and follow-up are retained
separately; their overlapping cases are not added as unique test coverage.

The submission receipt validator also preserves native precedence when task
parameters override container settings from start parameters. The original
operands and effective returned values remain separately recorded. The focused
follow-up log records the two supported override fields.

Further full Workflow tests exposed binding-specific report-resolution errors:
the monitor target was rejected before the monitor's original custody proof,
and Homology results fields were incorrectly checked as received child facts
instead of their own publication. Repairs preserve the existing shared runtime
and original typed forms. Monitor interruption/recovery now passes in its own
verification directory. Homology numeric delivery and composed-library execution
are separate tests and must not be inferred from this 114-test checkpoint.

No live BV-BRC request, configured model, HPC run, NCBI job verification or
annotation-score change occurred. The current fixed ledger separately records
source, bindings, numerical component tests, complete-path tests and missing
live-resource evidence. Other application-specific graders remain unfinished.
