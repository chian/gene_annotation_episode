# FBA host input witnesses and selected/realized launch boundary

Read-only implementation proposal, 690/002. This records interfaces for root to
adopt before assigning production edits. It does not amend the user goal,
authorize a run, or claim that these interfaces exist. Only this new verification
packet was written. Contract 011 now owns the parser extension proposed in
PRIOR_PROVENANCE_INTERFACE_001.md; its exact wording takes precedence there.

## 1. Existing authority to reuse

`ExecutionEpisodes.prepare_assignment`, `_match_request`, `_check_parent_inputs`
and `_versions` preserve a selected parent launch request and its
`immutable_input_versions`. Resource children must be commissioned by that
launch parent. `_match_request` permits the existing launch-instruction handling,
not a replacement job, model, allocation, resource or environment.

`expression_nmf_operands._received_context` authenticates the actual saved or
constructing BindingContext using `EpisodeReturnRecords`, then walks the existing
`EpisodeReceipts` inheritance chain. Each parent, scope and frozen `through_seq`
must match the episode's actual commission and knowledge-inheritance manifest.
The admitted reference set is that authenticated selection, not every current
Store reference. Reuse those primitives; do not create a generic source-authority
service or grant references merely to make an input pass.

Store source checks are specific: `state.py:768–783` requires declared source
artifact/text/request/stdout/stderr/auxiliary references to name actual artifacts
and parent_source_refs to name sources. It does not prove an arbitrary source is
a provider-authenticated acquisition. `Store.reference_subset` is a scope and
ownership filter; its artifact ownership projection is not episode receipt
inheritance. Both constraints matter. A selected source record is evidence of
that actual record and its relationships, not a blanket permission to every
artifact reachable from it.

`execution_input_versions.validate_execution_input_versions:59–99` preserves the
existing meaning of InputVersion:

```
{reference: str, version: str|null, content_sha256: hex64|null}
```

A nonnull version matches the original record revision. For an ordinary source,
content_sha256 hashes sequence_ref if present, otherwise artifact_ref. It does
not hash the source-record JSON and does not automatically pin text_ref or
request_ref. Do not reinterpret that established field to mean the requested
prior File. The separate witness below pins both the source record and the
specific selected File relationship. A source with a nonnull original input hash
still goes through the existing version check; any necessary primary-artifact
byte verification uses its existing mechanism, within the allowed execution
boundary, rather than host scientific decoding.

## 2. Exact proposed host binding

Use the function signatures and FBAInputBinding/FBAReceivedFile/FBAInputUse shapes
in PRIOR_PROVENANCE_INTERFACE_001.md:125–167, with these explicit refinements.
The initial implementation supports only the five scalar source fields already
listed there: artifact_ref, text_ref, request_ref, stdout_ref, stderr_ref. It must
reject an unsupported relationship explicitly, not search auxiliary fields or
parent sources for a substitute. A later supported source field needs an explicit
additive interface decision; no arbitrary JSON-pointer source authority is
introduced by this proposal.

```
FBAInputWitness = {
  reference: selected artifact/source ref,
  record_sha256: digest(exact Store.get(reference)),
  artifact_field: null|'artifact_ref'|'text_ref'|'request_ref'|'stdout_ref'|'stderr_ref',
  input_version: exact original selected InputVersion
}
FBAInputBinding = {
  version: 'flux_balance_input_binding_v1',
  run_id, episode_id,
  request_sha256: digest(context.request),
  assignment_sha256: digest(assignment),
  scope: exact validated receiving scope,
  inheritance_manifest: actual frozen EpisodeReceipts manifest,
  input_versions: exact original selected InputVersion array,
  model: FBAReceivedFile,
  prior_sources: [FBAReceivedFile]
}
```

Do not add a new source_ref to FBARequestedJob. The model and prior Files are
already its explicit operands. Bind each only through a witness from the
original input_versions array, in its order. For each selected source reference,
inspect only its declared scalar artifact fields and match equality against the
explicitly selected File.artifact_ref. Record each exact matching field rather
than selecting a convenient current source elsewhere in Store. Multiple matching
selected witnesses are retained, in original input order and declared field
order; duplicate identical witnesses collapse. Any conflict rejects the affected
binding rather than choosing one record. This deterministic join does not create
new scientific associations.

For a direct artifact witness, artifact_field is null and the reference equals
File.artifact_ref. For a source witness, record_type must be source and the named
field must equal File.artifact_ref exactly. Verify the original selected version
row without changing its meaning. Independently use `native_file_capture._metadata`
for the File's exact stored hash and length, and the existing protected-reference
resolver and scope/receipt checks for authority. Every selected file requires at
least one witness. Existing result-protected artifacts cannot be smuggled through
a new source alias; check both the selected witness and the File reference.

`model_input.artifact_ref` must be a received Store artifact for the episode
binding. Its `file.path` must equal Store's canonical artifact path and its hash,
size and format must match the same bytes. The native producer preserves the
selected model artifact_ref; the parser's contract 011 additionally joins it to
the retained original_model File. A standalone legacy selection with null
artifact_ref remains valid where current native/parser contracts allow it, but
null does not establish an episode-authorized model input. Do not create a fake
source or mutate null to a Store reference to claim host admission.

Eligible priors are only the selected acquisition_receipt_file and each requested
constraint lower/upper SourceLocation.file. Preserve original_loader_selection,
repository_identifier, all source pointers and all original selected bytes.
Those identifiers cannot cause an acquisition in this boundary. A receipt File
with a source witness is still only the received record's bytes unless its
existing provider-specific validator establishes a more precise acquisition
meaning. Do not put a parser `trusted` flag on it.

The exact additional frozen control output is:

```
FBAInputBindingReceipt = {
  version: 'flux_balance_input_binding_receipt_v1',
  binding: FBAInputBinding,
  witness_records: [{reference, record: exact Store.get(reference)}]
}
```

Each distinct witness appears once, ordered by first use. Require digest(record)
to equal every matching witness.record_sha256 and record.id == reference. Freeze
this canonical control through the existing immutable control writer and
capture_control/store.artifact mechanism; the resulting File has format
`flux_balance_input_binding_receipt_v1`. It is internal transport outside the
eight native roles. It is not a new general-purpose authority record or receipt
grant. Do not forward these IDs/hashes/control contents into decision prompts.

Proposed extra functions, owned with flux_balance_operands.py:

```python
freeze_flux_balance_input_binding(store, *, binding: dict) -> dict
# returns FBAInputBindingReceipt; metadata/record checks only
validate_flux_balance_input_binding_receipt(store, value: dict, *,
    context, assignment: dict, input_versions: list[dict], reference_access) -> dict
# returns detached receipt; no new grants/acquisition
```

The selected launch/result action's existing immutable control helper writes and
captures the receipt; the operands helper does not choose an output directory or
publish a source record. This keeps one existing action owner for publication.

At launch admission, validate the real received context and freeze the binding.
At selected start, authenticate the same parent launch commission, compare exact
original input_versions, and validate the frozen control before reservation.
At results, obtain the original binding control through the original start and
handoff proof, not a current result selector. Historical replay validates frozen
records, original runtime/receipt witnesses and stored control identities; it
must not rebuild a different source selection from later Store rows. New byte
reads use retained File identities. A changed current source row cannot silently
rewrite the original binding. A new execution request needs its own selected
binding.

The worker receives only `prior_sources: [{file, path}]` derived from that valid
binding, plus the binding control File identity in its immutable plan. It checks
actual bytes and passes `{file, bytes}` to contract 011. Neither the worker nor
parser authorizes references. If authority fails before start, return the
structured input-selection failure without launching. If a previously admitted
prior file becomes unreadable at collection, keep native capture/independent
numerical work and record that precise missing input; do not replace the source.

## 3. Demonstrated environment integration gap

The current producer contract is exact and is not changed by this report:

- `native_flux_balance_contracts.validate_flux_balance_requested_job:89–93`
  derives the selected lifecycle from original environment.TMPDIR and requires
  equality to `flux_balance_environment`.
- `validate_flux_balance_run_plan:122–129` requires that same environment to use
  execution_id.parent, whose path contains digest(the later selected
  practical.job.start operation key).
- `native_flux_balance_driver:176–178` writes the exact original requested_job,
  then checks the runtime against the derived final environment before loading.
- Existing real producer fixtures choose the operation key before constructing
  that request. That proves the producer's selected invocation, not ordinary
  parent-to-resource-child integration where the child owns its later decision.

The existing NMF path separates those identities. `native_expression_nmf_local`
retains original requested_job/argv/environment in invoke.json, while `_request`
and `native.prepare_job` receive realized command/environment. NMF's driver
records expected realized environment in the native manifest. `_local_job_worker`
102–105 combines its process environment with the selected wrapper env and sets
TMPDIR/TMP/TEMP to the lifecycle cwd. It does not make the original selected
request equal to that realized environment. FBA must not pretend otherwise.

## 4. Exact proposed original/realized contract, requiring root adoption

Keep producer v1 semantics and existing verified fixtures intact. Ordinary new
launch selections need an explicit versioned execution interpretation before
registration can claim support. Do not assign a future child operation key in
advance and do not rewrite the parent's requested_job after child selection.

The minimal explicit selection extension proposed for NEW practical FBA
assignments is an optional closed top-level member, outside requested_job:

```
native_flux_balance_execution: {
  version: 'flux_balance_execution_selection_v1',
  environment_realization: 'operation_scoped_tmp_and_cache_v1'
}
```

Absence retains existing literal environment semantics: reservation succeeds
only if requested environment already equals the actual attempt environment.
Presence authorizes exactly the path realization below and is included in the
original parent assignment/commission digest and frozen selected tool contract.
It must be part of a newly selected assignment; never add it retroactively to a
saved original request. Root may choose another explicit selection carrier, but
must freeze its exact shape and original commission relationship before coding.
The report does not assume that a deployment default authorizes literal parent
environment changes. Existing arbitrary constraints/allocations remain exact.

A versioned v2 run plan preserves every v1 field unchanged and adds:

```
environment_binding: {
  version: 'flux_balance_environment_binding_v1',
  selection: exact native_flux_balance_execution selection,
  requested_job_sha256: digest(untouched requested_job),
  requested_environment: exact requested_job.environment,
  realized_environment: exact flux_balance_environment(software,
      attempt_directory=attempt, lifecycle_directory=execution_id.parent),
  relocations: [
    {name: 'TMPDIR', selected: str, realized: str},
    {name: 'TMP', selected: str, realized: str},
    {name: 'TEMP', selected: str, realized: str},
    {name: 'XDG_CACHE_HOME', selected: str, realized: str},
    {name: 'PIP_CACHE_DIR', selected: str, realized: str}
  ]
}
```

Always five rows, in that exact order, including unchanged values. The first
three realized values equal execution_id.parent. The last two equal
attempt/cache and attempt/cache/pip. Every other key/value equals the original
selected environment, including software roots, interpreter settings and thread
limits. No extra env key, dependency root, command argument, resource, input,
constraint or allocation is substituted. The selected environment is itself
valid under the existing requested-job validator. The attempt root remains the
one existing operation-scoped root; paths cannot overlap model/software inputs.

Proposed pure interface owned by the future launch contract owner:

```python
bind_flux_balance_environment(requested_job: dict, *, execution_id: str,
    attempt_directory: str, selection: dict | None) -> dict
validate_flux_balance_environment_binding(value: dict, *, requested_job: dict,
    execution_id: str, attempt_directory: str, selection: dict | None) -> dict
```

The output is the binding above; a missing selection with unequal environments
fails. `identity.requested_job_sha256` always hashes the untouched requested_job,
not an environment-rewritten derivative. `identity.assignment_sha256` covers the
original selection carrier. The wrapper's request env uses realized_environment;
its command uses the selected driver argv with the original plan filename
resolved to that selected lifecycle root. Keep both original invoke.json and
actual wrapper request_raw/hash; neither stands in for the other.

A producer extension would need a v2 run-plan validator and driver acceptance of
this binding, plus exact evidence in the retained manifest/native control
snapshot. It must preserve the v1 sealed replay route. A clean minimum retained
evidence addition is an optional `environment_binding` in the native manifest
for v2, equal to the plan value; the selected-request artifact remains its exact
original job. Parser/host validators must not infer a missing environment
observation. Root/producer owners must adopt that precise addition together;
690 did not edit their files. Until then the current v1 integration gap remains.

## 5. Verification required at these interfaces

Use source-only/synthetic contract cases and existing retained native artifacts;
no new solve is required to prove these joins. Future bounded checks should cover:

- Actual original launch inheritance, direct artifact and explicit source-field
  witnesses; multiple uses/witnesses; canonical Store paths and model File join.
- Unreceived, wrong-parent, later-than-frozen-prefix, protected, wrong-scope,
  conflicting source, unsupported field and forged record controls. No new grant.
- Source input_version hashes its primary artifact while selected prior File is
  request_ref: both independent identities must pass; swapping them must fail.
- Changed model/prior bytes, mismatched original request/assignment/version array,
  replay after unrelated later receipts, original source metadata retained.
- v1 exact environment unchanged; v1 future-key mismatch rejected; new selected
  v2 policy only; all five permitted path realizations; every other key exact.
- No future child decision preassignment, no hidden request rewrite, no fallback
  resource/allocation, no automatic retry, no new optimize call on any replay.
- Source-only control replay cannot establish productive native progress or
  successful scientific results. A frozen binding is necessary custody evidence,
  not an executed capability.
