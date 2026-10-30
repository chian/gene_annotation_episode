# Infernal authenticated return verification, workload 227

Implemented only `gene_annotation_episode/native_infernal_returns.py`,
`tests/test_native_infernal_returns.py`, and this verification directory.

The existing five numerical families remain separate. Incoming generic
`execution_result_refs` belongs to this provider only when the actual
immediate child is an Infernal results owner. The parent's separately requested
`execution_infernal_result_refs` source forwards only references that crossed
its own authenticated child forms. This additional source was directed by root
during coordination and exposed through root-owned ExecutionEpisodes/results
hooks. Other providers' generic references remain unhandled here.

Reference-only forms return no numerical groups from `received_context` and
resolve no native row, sequence-name, or model-name identifiers. Numerical forms
continue to admit their explicit source, observation, and model references.
Completion-only forms admit no references. Saved result bodies are read through
the existing validated-results port; source possession never expands a result
into additional numerical rows.

Original runtime context, immediate parent/child relationship, original
commission scope/schema/purpose, results assignment and role, successful return,
frozen facts, and original frozen form are checked. Original role and results
assignment are also checked on redelivery. Scientific child construction
materializes tool information in its assignment, so exact selected-action versus
child assignment equality is deliberately restricted to results assignments,
matching their actual copy contract. Existing shared authentication retains the
scientific child's immutable recorded request.

The adapter now uses the existing synchronous form-validation frame to reuse an
authenticated received snapshot during a single form check. This is not a
persistent cache. The dedicated test confirms one child-facts read for a form
containing several identifiers and references, then a fresh read and rejection
after stored authority changes before the next form check.

Final focused command:

```text
.venv/bin/python verification/tool_graders_infernal_returns_2026-10-26_227/run_tests.py run_005 -x
```

Result: **43 passed in 153.55 seconds**. The existing local runner enforced
20 GiB memory, zero swap, 4 GiB monitored scratch with its documented possible
overshoot, and no wall-time limit. Full native lifecycle metadata, command,
environment, stdout/stderr, and JUnit results are retained in
`run_005/verification-receipt.json` and `run_005/tests.xml`.
`VERIFICATION_001.json` records all executed cases and final source hashes.

Executed controlled examples preserve search-hit bitscore 1.25 with an explicitly
not-measured E-value, search-sequence hit count 0, alignment-sequence native bit
score 1.25, and alignment-column/pair row count 3. These are synthetic return
fixtures, not Infernal measurements. The tests use real Store, Journal,
EpisodeReceipts, BindingContext, and typed forms with a controlled validated-results
input port. They cover bound/unbound values where applicable; five-family
separation; direct and nested reference-only forms; completion-only returns;
other-provider isolation; forged values, missing states, sources, identifiers
and subjects; sibling isolation; original commission tampering on first delivery
and redelivery; changed frozen forms/facts, requests, children, delivery identity
and missing closure; exact redelivery deduplication; absence of unrequested
numerical rows; conflicting aliases; and snapshot expiry.

Database dumps remain unchanged across adapter reads, validation and admission
reference projection. Redelivery introduces no runtime action or observation.
Network access, subprocess creation, acquisition, parsing and calculation are
forbidden by the focused test fixture. No scientific program or configured model
was launched by this workload. Actual native receipts and the shared Workflow
path are owned by workload 226 and are not claimed from these tests.

Earlier failed runs are retained unchanged:

- `run_001`: 37 failed, 6 passed. The controlled observation fixture incorrectly
  supplied incomplete native provenance. Corrected the fixture to use explicitly
  controlled ordinary Store observations.
- `run_002`: 1 failed, 22 passed before stopping. Corrected the fixture's
  unsupported Journal.row keyword argument.
- `run_003`: 1 failed, 40 passed. The snapshot test deliberately changed its
  authority fixture and then compared an aliased expected dictionary. Detached
  that expected fixture value.
- `run_004`: 1 failed, 41 passed. A forged role is rejected by the immutable
  BindingContext constructor before the adapter can inspect it. Corrected the
  expected rejection location.
- `run_005`: 43 passed. No production adapter change was required by those
  fixture failures.

Root hook status: the provider-specific source descriptor and own result-fact
alias were missing initially; root supplied both before final verification.
No missing functional hook remains identified for this return interface.
One performance consumer was reported separately: the root-owned
`ExecutionEpisodes.received_form_references` generic-reference loop resolves
each reference again outside the form-validation frame. It can reuse the
existing synchronous frame or its already-authenticated admission references.
That advisory does not weaken any required authentication and is not an
additional correctness requirement.

Read and traced the complete EpisodeReturnRecords implementation, Infernal
return/results modules and numerical family views, and the affected execution
binding, runtime form validation/resolver/fact construction/admission consumers.
Read the original goal and required episode, estimation, practical execution,
task/steering and tool-grader directions; reread the original objective and full
sixteen-principle block after source examination and before handoff.

