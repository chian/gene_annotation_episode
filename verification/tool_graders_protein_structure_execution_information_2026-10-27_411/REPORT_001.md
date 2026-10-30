# Protein execution/result information

Implemented additive380/023 in the pure description helper and a protein-only
branch of ExecutionTargetReader.describe_target. The latter still authenticates
the ordinary original handoff before describing it.412 separately owns use of
the copied authenticated target for saved work/replay after handoff byte loss.

The information now names actual status/collect operations, selected native
format and output paths, actual parser/validator/calculator functions and exact
four protein fact sources. It no longer advertises generic file-window reads
for these results. It distinguishes original recorded calculations from later
saved-sheet recalculation and preserves the selected return without adding
fields. Generic monitoring still uses its resource task and progress.observe.
No producer observation, input acquisition, score computation or prompt is
performed by this information builder.

check001 passed48 cases in3.20 seconds: the new information tests plus existing
selector tests. The new tests cover inspection, extraction, both comparison
modes, saved parameters, no implicit projection, incompatible selectors,
defensive copies, forbidden byte/observation/calculation access, the actual
describe_target branch and unchanged ordinary-local information. The two target
description tests inject the already-authenticated target and handoff bytes;
they test description dispatch, not authentication or a native execution.

The local_jobs policy was20GiB RAM/4GiB scratch/zero swap/no wall-time budget.
Executed snapshot pins remained unchanged; there was no checkout drift. Exact
source pins are in VERIFICATION_001.json and the full run packet. The existing
target-reader preimage was recovered from the already verified409 snapshot,
matched against its recorded SHA and compared in target_description_changes_001.diff.
It is not represented as a pre-edit copy created during411.

Receiver text rendering remains unfinished. Root printed the proposed recurring
results TASK, separate selected tool information and a requested2Å/1pair example
for the user's feedback; no prompt change was made.410 owns the complete
Workflow test and412 the retained-target consumer repair. Neither is established
by these48 description/selector checks. No complete tool or accepted binding was
added;112/308 remains unchanged.
