# Native-six lifecycle failure source review

This packet implements IMPLEMENTATION_CONTRACT_001.md. The immutable goal was
read in full and its purpose and all sixteen principles were reread before
implementation. Its SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
AGENTS.md, GOAL.md, EPISODE_STRUCTURE.md, TIME_AWARE_ESTIMATION.md,
PRACTICAL_EXECUTION.md, the original practical execution contract, the tool-grader
goal/principles, and the six relevant WORK_STATUS rows were read. No permanent
direction or accounting file was edited.

The two owned production modules and existing owned test file were read in full.
Their original bytes are under `before/`; BEFORE_SHA256_001.json records the
pre-edit hashes and sizes. The complete local_jobs and native_lifecycle modules,
AcquisitionError definition, result-owner return module, SyntheticHost fixture,
publication and frozen-validation path, and complete numerical worker entry
function were inspected. Source inspection also covered the actual execution
dispatch, selected-action authentication, results facts, credit projection,
completion proof, form validation, parent admission and received-facts consumers.
The standard336 helpers/tests and handoff were read as a reference, not used as
evidence that native-six was already corrected.

## Established defects and correction

- A negative LocalJobResult return code previously selected resource_limit.
  Native lifecycle only proves that classification through an AcquisitionError
  whose exact code is local_job_resource_limit. An unqualified nonzero result
  now retains the existing worker_failed / implementation_failure meaning.
- AcquisitionError derives from RuntimeError and escaped both existing handler
  lists. Explicit typed handlers now retain code, phase and a deep copy of
  operational facts. No generic RuntimeError or BaseException handler was added.
- Inventory failure writes implementation-receipt.json and re-raises the same
  exception. The outer owner retains this receipt and the exception diagnostic,
  then records the originally selected failed action through its existing path.
- The worker boundary retains its failure receipt, caller diagnostics, existing
  log bytes and atomic output siblings. Without a valid manifest those siblings
  remain diagnostic artifacts and cannot populate numerical rows. Caller
  diagnostics are now retained even when the worker already sealed a valid
  manifest. Frozen validation reads their retained bytes without rerunning work.

The private failure receipt is
`{version:native_blast_database_local_job_failure_v1,code,phase,operational}`.
Diagnostics retain failure_index, exception_type and message, adding the typed
code/phase/operational facts. These are diagnostic custody records, not new
scientific or parent-return schemas.

## Complete receiving path and unchanged owners

ExecutionEpisodes.execute dispatches the selected native-six results action to
NativeBLASTDatabaseResults.execute. The latter authenticates the original action
and freezes intent. It acquires the selected original bundle, inventories the
implementation, and runs the numerical worker under the caller's original
local-job policy. The correction changes failure recording at those two selected
local-job boundaries. It neither chooses another action nor repeats a job.

For a worker failure, preparation stores the original caller failure beside any
sealed rows. Publication projects only manifest-authorized rows; failures keep
projection_complete and complete false. An inventory failure preserves the
acquired original source and returns no prepared numerical publication. The
owner writes its existing immutable action receipt before returning status
completed. Its frozen receipt/publication validators remain authoritative.

The existing facts and NativeBLASTDatabaseReturns validation/admission paths copy
the requested closed failures, rows and acquisition flags to the original parent.
No model composes this return. Replaying the same selected action reads the
original receipt. No worker, inventory, remote observation or new selected action
is invoked on that replay. No practical completion proof is produced for these
failed actions. The existing credit and controller paths are unchanged.

## Scope and verification limits

Only native_blast_database_result_publication.py,
native_blast_database_results.py and tests/test_native_blast_database_results.py
were changed outside this evidence packet. No worker, metadata, standard336,
public339, shared lifecycle, schema, formula, prompt, credit or estimator change
is part of this work. No incompatible interface required expanded ownership.

The tests use explicitly synthetic native reports, a controlled local PBS
fixture, actual result owners/Store/action journal/parent forms, actual bounded
local numerical workers, and actual native_lifecycle.collect classification
against injected status values. Injected oom-kill is not physical exhaustion;
the fixture is not a live HPC or database-BLAST run. No scientific API request,
installation, download or configured-model investigation is claimed.

The verification runner uses the existing .venv/bin/python -B and run_local_job,
20 GiB RAM, 4 GiB scratch and no wall cap. Each invocation retains command,
before/after source hashes, stdout/stderr and the actual lifecycle receipt. Test
counts and retained concrete values are reported separately in the final
verification record after execution.
