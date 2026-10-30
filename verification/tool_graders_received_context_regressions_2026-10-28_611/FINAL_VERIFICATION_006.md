# Final direct received-context regression verification

The reviewed direct regression passed in
`check065_received_context_direct_final`: one test, 5.03 seconds pytest time,
3.799891955917701 seconds for the test call. The bounded receipt reports
return code 0, terminal and quiescent state, unchanged source, dependencies,
stdlib and binaries. The execution audit reports no outside modules or unbound
mappings, unchanged native pins and retained fixtures. The run used 20 GiB RAM,
4 GiB scratch, zero swap and no wall-time cap. It selected no native scientific
executables and did not repeat the saved-evidence collector.

Only `test_different_parent_scalar_does_not_grant_unreceived_information_to_child`
and its two obsolete scorer imports changed in `tests/test_episode_receipts.py`.
Removing those allowed spans from the before/after sources leaves byte-identical
text. All production files pinned at the start, `test_runtime.py`, and
`test_runtime_decision_exchanges.py` remain unchanged. The current edited test
and runtime match the final run's frozen source snapshot. The test SHA-256 is
`3453a929b9c7b2e5f0daf71c275b8a77fae9503924a5e2d75ba28d370a13aa62`.

The passing assertions establish:

- The custom parent callable lacks `requires_episode_receipts` and receives
  only its existing store/scope arguments.
- Root and child both receive the immutable received-record view. Neither sees,
  admits or inherits the pre-existing finding. The initial known-reference list
  remains empty, and no automatic `decision_input` receipts are added.
- Both episodes start at zero and finish with zero gain. The child performs one
  nonempty hypothesis-only reasoning action; the parent performs one
  commissioning action. Each receives exactly one local observation.
- There is exactly one reasoning commit, zero tool operations, and one
  successful typed child return with `local_progress=0`. The original finding
  survives unchanged as the only scoped assessment.
- The run remains on the direct protocol; no decision-protocol marker is added.

The prior `check062_received_context_direct` evidence remains preserved. It
passed the original direct fixture and a read-only collector of all twelve
check061 failure databases. The collector ran inside the bounded runner, and
all original and staged database hashes remain unchanged. The reviewed fixture
is established by check065; repeating that one test does not add unique coverage.

`FAILURE_CLASSIFICATION_004.json` and its Markdown companion give each of the
twelve exact node IDs, saved causes, completed work and smallest proposed
repairs. Case 6 failed at the retired constructor before runtime. The remaining
eleven depend on tool actions forbidden by the already-present root action
boundary. Complete source comparisons against check060 establish that the
blocking guards predate the received-context repair. In the receipt-based
cases the relevant context branch was already active; the four exchange cases
have no receipts ledger. This is a comparison of saved rows and complete source
paths, not an execution of those tests against check060. These failures establish
no new production defect.

## Additive review refinement for cases 7 and 8

The case004 proposals remain preserved as originally written. Root's later
principle-6 review refines both failed-form/interruption repairs: replace the
child's `episode.credit` action as well as the forbidden final parent lookup
with legal nonempty reasoning that earns zero finding progress. Use only supplied
or actually received hypotheses. Preserve the original finding and original
scientific child commit identity, both interruption variants, two actual child
actions, two actual root actions, four total observations, root decision indices
`[0, 2]`, root deltas `[0, 3]`, and two report attempts. Redelivery adds no action
or observation. The repaired fixture will have three actual reasoning commits:
the original scientific child contribution, zero-gain child reasoning, and
zero-gain parent reasoning. These are distinct from duplicated scientific work.
Neither test has been edited under this assignment.

Machine-readable receipts, hashes, scope checks, assertion coverage and the
review refinement are in `FINAL_VERIFICATION_006.json`. The other eleven tests
remain unchanged and unverified after their proposed repairs. No broader suite
pass, live-resource verification or completion of the original tool-grader goal
is claimed. No network, HPC or original native scientific analysis was run.
