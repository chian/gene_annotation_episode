# Initial failures and attribution

All logs are retained as observed. Final passing evidence is separate; earlier
failed runs have not been overwritten or relabeled as passing.

## Production defects reported to the owners

1. `native_hmmer_fact_sources` / the actual closed parent-return schema rejected
   `rows[].record_key` with `unsupported schema keyword` during Workflow
   commissioning. The initial production schema used `minLength`; nullable
   references and several enums also did not fit the existing communication
   subset. Evidence: `initial-workflow-tests.log`. Worker 066 and root repaired
   the exported closed form and exact native-row resolver without loosening the
   shared communication validator.
2. `publish_selected_native_hmmer_rows` treated an explicit same-length wrong
   biological subject sequence as `unbound`. The retained failure was
   `native_hmmer_subject_sequence_mismatch`, yet the original result's `complete`
   was true. Evidence: `faults-second.log` and
   `wrong-binding-initial-receipt.json`. Worker 066 now preserves absent binding
   as unbound and marks supplied invalid mappings invalid; valid sibling rows
   survive. The actual Workflow counterexample passed after the repair in
   `faults-after-repairs.log`.
3. `validate_original_bundle` accepted a successful return-code-zero manifest
   after the declared stdout output row was removed; capture reported complete.
   Evidence: `omitted-output-first.log`. Root now requires every declared output
   role for a successful, failure-free attempt. Tests include explicitly chosen
   optional `included_msa`, and separately confirm that a truthful failed
   manifest may preserve its available partial files. The repair passed in
   `faults-after-repairs.log`.

## Verification-fixture corrections

These failures did not establish production defects:

- Calling `Store.create_problem` more than once, assuming archived controller
  history had the live representation, and reconstructing a manual context with
  unsorted scope: corrected by using one original multi-record FASTA, reading
  archived `controller_step.marginal_credit`, and using the saved exact request.
- Assuming the saved B003 hmmscan population was the same size as the 064 tiny
  native request: replaced with an exact query/target/occurrence/axis/coordinate
  association before comparing all available scalar components. B003 contained
  four input queries; the retained 064 request selected one.
- Comparing a direct binding replay to a Workflow outcome without accounting
  for runtime-owned `pending_work_after_action`: the binding-owned receipt and
  all its outputs must match; the runtime snapshot is outside that binding.
- Attempting to close deliberately partial fault cases through the controller
  factory: production practical estimation replaces that factory estimator.
  Fault tests now explicitly supply a fixture base estimate to the test
  binding while retaining the real completion verifier and operational credit.
  They do not claim production completion or continuation for partial work.
- Requiring a semantic capture-journal mismatch code when the existing
  immutable byte seal rejects the altered file first. The final test accepts
  the exact immutable-seal rejection or the corresponding semantic conflict;
  it still requires qualification and resolution to reject every mutation.

`workflow-expanded-second.log` is an exploratory run whose loaded test code
predated a fixture correction; it contains 11 passing native numerical mode
cases followed by the stale fixture replay assertion. No stable-source claim
is made for that run. The final run independently hashes production and test
files before and after execution.
