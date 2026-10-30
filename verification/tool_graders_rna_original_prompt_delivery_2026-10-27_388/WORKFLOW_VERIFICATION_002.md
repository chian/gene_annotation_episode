# Current RNA Workflow verification after message integration

This adds terminal results to MESSAGE_VERIFICATION_001.md without rewriting its
earlier pending statement or the retained failure receipts.

`check004_workflow` passed all 18 one-input tests against the current 388 shared
message integration. It then failed before the first native prediction started:
the snapshot harness omitted the pre-existing 357 dependency probe. Its overall
receipt remains exit 1 (18 passed, 1 failed), 325.34 seconds in pytest.

The one-input tests used the actual original supplied-topology Workflow followed
by the selected retained one-input request. They verified the exact sequence and
dot-bracket return, original received authority, removed producer files, replay,
one collect/one observation, zero new acquisition credit, immediate zero future
expectation, and complete TASK through actual provider updates and restored
frames. These are the same 18 tests as 385, now running with 388 wiring.

All 845 executed snapshot pins stayed unchanged. Four concurrent live changes
were confined to the protein contracts, formats, metadata and sequences modules;
WORKFLOW_LIVE_SOURCE_DRIFT_004.json records exact hashes. No RNA/shared message
source changed during that run.

The harness correction includes the actual existing dependency probe and
installed native-site bytes in the snapshot. `check005_native` reruns only the
three affected original native modes. It passed **3 tests in 109.41 seconds**,
exit 0, with all **860 live and executed source pins unchanged**. Memory 20 GiB,
scratch 4 GiB, zero swap, no wall-time limit were enforced by local_jobs.

The three real selected Workflow paths were MFE prediction, supplied-structure
native energy evaluation, and supplied topology without energy. They checked
launch/local execution, captured native artifacts, sheet/components, requested
typed return, scientific forwarding, resource contracts, monitoring/acquisition
description, one-action observation accounting and practical endpoints.

Actual current numeric returns for synthetic input `GGGAAACCC` contain pair count
3, paired fraction 2/3, stack count 2 and closed-loop mean 3 nt. Prediction returns
MFE -1.2000000476837158 kcal/mol. Supplied native evaluation returns its separately
named evaluated energy -1.2000000476837158 kcal/mol. Topology-only returns the
requested energy as unavailable, without inventing zero. Full selected rows and
exact receipts are preserved in FILLED_CURRENT_NATIVE_RETURNS_002.json.

Together with accepted 354/357/358/360/366–383 components and the 387 presenter,
388's 278 passing message checks and these current Workflow checks close the
remaining original RNA message/one-input integration work. The two original RNA
tool rows can now enter the numerical-grader tally under its existing meaning.
No additional row is invented for comparison, scans or presentation.

This is not a full-repository pass. The eight historical receipt-test failures,
remaining tool rows and unfinished resource deployments stay open. No live
model, API/HPC execution, literature grader or W05 annotation formula was added.
The immutable objective/all 16 principles and current 384 input/output/numerical
message contract were reread before this scoped acceptance.
