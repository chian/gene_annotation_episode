# Expression NMF component verification

Final owned-source checkpoint: `check003`, 55 tests passed in 50.90 seconds.
The original handle was polled and collected with return code 0 and terminal,
quiescent status. Current owned Python/test files were byte-compared with that
frozen snapshot and match. The run uses 20 GiB RAM, zero swap, a 4 GiB monitored
scratch allocation and hard per-file limit, and no wall-time limit. Scratch
monitoring can overshoot and is not a filesystem sandbox.

This is component/native verification for fixed row
`B-L128-perform_gene_expression_nmf_analysis`; it is not complete production
Workflow verification and does not increase a completed-tool tally.

## Retained evidence

* `check003/receipt.json`: original handle/unit, return code, terminal/quiescent
  outcome, actual local enforcement and unchanged source/dependency/stdlib/
  interpreter pins.
* `check003/execution_audit.json`: zero imports outside frozen roots, zero
  unbound executable mappings, unchanged native/system library pins.
* `check003/native_library_resolution.json` and before/after pins: actual ELF
  dependency resolution before scientific imports plus after-run identity checks.
* `check003/native-software.json`: prepared exact software binding for root.
* `check003/selected-native-plan.json` and `selected-native-outcome.json`: actual
  selected native driver reservation, original physical handle and its result.
  The plan's attempt_directory/native-output contains the exact manifest and
  complete raw/prepared/factor artifacts.
* `check003/native-none`, `native-column_sum_1000`, `native-nonconvergence`:
  retained real sklearn outputs on the declared synthetic matrix. The first
  two include populated sheet and numerical-calculation examples.
* `check003/junit.xml`: all 55 current-source cases; do not add older overlapping
  test totals to this count.

`HANDOFF.md` specifies exact callable interfaces, artifact versions, metadata
joins, ownership, and the numerical field meanings and denominators.

## Checkable numerical examples

The exact supplied-factor fixture is W=[[1,0],[0,1],[1,1]],
H=[[1,2,0],[0,1,3]], X=[[1,2,0],[0,1,3],[1,3,3]]. It gives SSE=RMSE=MAE=0,
component loading sums [2,2], and sample position 1 contributions [4,2] with
fractions [2/3,1/3]. Increasing only X[0,1] to 3 gives SSE=1, RMSE=1/3,
MAE=1/9 and relative Frobenius residual=1/sqrt(39). These are supplied factor
arithmetic tests, explicitly separate from a fitted biological dataset.

Real scikit-learn 1.7.2 fits on that synthetic matrix, rank=2 and seed=42:

| Selected preprocessing | Native iterations | Native reconstruction_err_ | Recomputed Frobenius | SSE | RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| none | 17 | 0.0001383408514600178 | 0.00013834085146004034 | 1.9138191182688943e-08 | 4.611361715334678e-05 |
| column_sum_1000 | 17 | 0.025173612182756894 | 0.025173612182777073 | 0.0006337107503288622 | 0.008391204060925693 |

The explicit max_iter=1, tol=1e-12 fit returned native n_iter_=1 and
reconstruction_err_=1.3370720902046347 with actual
`sklearn.exceptions.ConvergenceWarning`. Complete factors were retained and the
outcome is qualified. It was not silently retried or called an annotation
probability. Each valid fit records exactly one fit_transform call.

## Coverage and limits

The checks cover exact arithmetic, signed residuals, factor reciprocal-rescaling
invariance, full raw/scaled matrix retention, normalization denominators, all
zero versus missing values, rank above min(shape), duplicate gene/sample labels
with positional metadata, unknown/conflicting metadata, malformed/nonfinite
input cells, raw negatives under both preprocessing modes, explicit zero-column
scaling failure, native fit failure with no fabricated factors, real native
nonconvergence, axis/shape/input/source identity mismatches, missing/malformed/
partial factors, malformed manifest result types, and independent data retention.

Overflow tests retain finite reconstruction/normalized components when loading
sums overflow, and retain finite norms/RMSE/MAE when squared sums overflow.
An unused raw column-sum overflow under normalization=none remains qualified
without deleting original cells. Original bytes survive a selected simulated
parser-memory failure. That simulated exception is not a claim of a real OOM.

Saved-sheet recalculation is tested with native fitting, network/socket calls,
subprocess creation, file opening and sheet re-population forbidden. It still
returns the exact fixture SSE=0. Receiver views retain requested occurrence
positions, numerical rows, explicit filtering and row-window counts.

The local selected-driver case exercises pending-start validation, immutable
reservation, actual existing native_lifecycle dispatch/collection, same-handle
replay, native artifacts, parser/calculator, output presence and selected log
windows. Its narrow pending-state object is an explicit fixture. It does not
replace root's required real PracticalState/ExecutionEpisodes/Workflow tests,
typed-return admission, parent/child observation accounting, saved-recalculation
credit checks or exact-zero practical terminal expectation checks.

No live API or HPC execution, no model-directed annotation investigation, no
literature grader, no W05 aggregation, no estimator/controller change and no
progress/inventory update was performed by this workload.

## Preserved earlier outcomes and installation scope

`install001` installed the isolated selected stack successfully without changing
an active shared environment. It froze the full copied pip/site-packages,
interpreter and stdlib closure and ran inside the bounded lifecycle. It did not
perform the later native/ELF-library audit before installation; no retroactive
installation ELF-pin claim is made. The native scientific checks did perform
that before/after audit, including the actual loaded dependency closure.

`check001` finished with 46 passing tests and one failure. Its selected driver
rejected an environment mismatch before fitting because the existing local
worker overrides TMPDIR/TMP/TEMP to the monitored cwd. The driver was corrected
to authenticate that actual lifecycle environment. The failed original handle
and immutable receipt were retained. `check002` passed 47 tests after that fix.
`check003` verifies the current source and eight additional edge cases. All
three preserve their distinct frozen sources and original handles; elapsed time
or a polling timeout never caused a replacement submission.

The original objective and complete 16-principle block were reread verbatim
from the original user attachment after substantive native-source/output
examination and again with the tool contract before this component handoff.
GOAL.md was never read or used as authority.
