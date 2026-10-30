# Saved membership/sample relationship correction

Root reproduced an actual validation defect in342. The original whole-sequence
fixture reports samples S0, S1 and S2. Changing the saved derived sample groups
and matching entity sample keys to invented-shared-sample, while leaving every
original member, dataset and metadata record unchanged, was accepted by the
saved-sheet validator. `probe_run_001` and its complete original/changed sheets
retain this counterexample. The probe exited0 and reports rejected=false; that
is evidence of the defect, not a successful validation claim.

The correction compares saved membership, original bindings, sample groups,
sample identities, metadata associations and their counts with the original
retained relations. It reuses the unchanged v1 pure `_members`/`_samples` joins
for relationship validation. It never invokes the native parser, whole v1
component calculator, FunctionSheet populator, I/O or a candidate-function model,
and does not overwrite any saved value. The original342 source is preserved in
before/ with its SHA2565ed8026865ec3090a59c5eeec02cb747eaa6ca419a277dc6418381ad26d4b5f9.

Final input source:
8c6b6ad052aecb3410c97d93a2ad2b690c9d232b5e9089f2c8dae6cf369a1dab.

`run_001` passed97 tests in1.54s: all81 original342 cases and16 new relationship
checks. The actual local_jobs receipt records returncode0, service duration
2.236462592s,20GiB RAM,4GiB scratch and no wall cap. Before/after source pins
match. New cases reject invented/shared existing labels, substituted sample
identifiers, metadata keys, member/row membership, omitted/duplicated origin
records and false counts. All three frozen complete sheets validate unchanged
with native parsing, original population and the main base calculator forbidden.

No old fixture, receipt, goal, v1 scientific calculation, execution behavior or
annotation credit was changed. No live VDB/API/HPC run occurred. The optional
source-block calculator still requires its own final dependency verification.
The two VDB rows remain outside the108-row numerical-grader tally.
