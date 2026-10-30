# Protein resource registration: implementation and verification 408

The narrow registration increment approved in 380/020 is implemented and
verified. **66 tests passed in 126.72 seconds**, including 31 new registration
checks. This is registration/schema/reconstruction evidence. It does not
establish complete protein execution, numerical delivery, receipt authority,
scientific credit or episode-path integration. The completed-tool count remains
**112/308**; no inventory/tally row was edited.

## Exact ownership and changes

Only these four methods in `gene_annotation_episode/execution_episodes.py` were
changed by 408:

- `__init__`: validate the unchanged C390 `native_protein_structure` binding
  list; reject API/HPC mappings with
  `native_protein_structure_resource_execution_binding_unfinished:<kind>`;
  construct the actual 407 `NativeProteinStructureResults` then 397
  `NativeProteinStructureReturns` immediately after progress setup. The host
  uses the actual 406 `ProteinResultReceipts`. Their metadata-only constructors
  work with no configured protein resource and expose no unbound protein tool.
- `_request_schema`: append C390's exact per-resource `input_schema` alternatives
  beside existing alternatives. Internal JSON Schema resources and definitions
  remain intact. Inspect, extraction and both comparison modes retain the exact
  selected software and original requested-job shape.
- `assignment_schema`: when a protein resource is bound, add a separate
  `protein_structure_result_selector_v1` conditional using 399's detached schema.
  RNA conditions and unrelated generic/API selectors retain their existing
  behavior. Schema validation supplies no handoff or operand authorization.
- `resource_tool_contracts`: add C390's unchanged four-field information and
  invocation contracts through the existing name/resource-kind merge. Distinct
  local resource IDs retain their exact launch routes and schema alternatives.
  No API/HPC protein route or direct root tool is added.

The executed snapshot differs from the 402 baseline in exactly these four
methods. `as_record` is unchanged. See [owned_methods.diff](owned_methods.diff)
and [scope_audit.json](scope_audit.json). The402 guards in `_received`, `resolve`
and `episode_receipts.py` were preserved and their 23 focused cases passed.

The first attempted pre-edit copy used `python`, which is absent from PATH, and
did not run. The subsequent retained preimage was reconstructed immediately by
subtracting only the five exact patch insertions. Its SHA256 is the exact 402
baseline `616199a64000c10813cd9a482161ad3eda1119659baae67999d8a70462bff6cb`.
That provenance is recorded in [before/pin.json](before/pin.json); it is not
represented as an earlier successful copy.

The only other authored files are the new focused test module and this packet.
No prompt, library wording, calculator, literature, W05, continuation rule,
factory implementation or registry layer was changed.

## Inspected and executed consumer path

The complete four methods, `as_record`, `_validate_request` and `_launch` were
read, together with the actual local request validator and 405 configuration
ports. The selected job remains a caller operand; registration never discovers
software or a resource, changes allocation, starts a job or chooses a retry.
The production request-schema path and actual `LocalPracticalOperations`
validation were exercised with the same exact operation/mode/software values.
Smaller declared memory/scratch or a wall limit remain unchanged configuration
values and are rejected by the existing protein request validator.

The full `ExecutionServiceFactory` and its actual `__call__`, `as_record` and
`from_record` consumers were read, as were assembled-service setup,
`independent_execution._standard_bindings`, `_check_bindings`, descriptor
registry reconstruction and their existing tests. Real factory calls and
descriptor reconstruction preserve the exact original resource object. A
second test saves normal runtime settings through `run_workflow`, then uses
the actual `_standard_bindings`, `_check_bindings` and `assemble_workflow`
before model entry. It constructs the real 406/407/397 classes and verifies zero
runtime episodes, actions and provider jobs. Only model entry is intercepted
by a sentinel; no constructor, result host, factory or successful authority
port is replaced.

Communication remains the original requested typed form. This increment adds
the exact selector shape but no fact composition or model call. Credit and
continuation are untouched; these registration tests claim no scientific or
monitoring gain and exercise no new runtime observation or endpoint rule.
Root409 owns the remaining selected-action, durable result, received-form,
authority, credit and endpoint integrations.

## Bounded evidence

One bounded attempt ran. [check001/selected_request.json](check001/selected_request.json)
records the exact invocation; [stdout](check001/stdout.txt),
[stderr](check001/stderr.txt), [JUnit](check001/junit.xml) and
[receipt](check001/receipt.json) retain its outcome. There were **66 passes,
zero failures, zero errors and zero skips**. Stderr is empty. No failed pytest
attempt occurred; the harness refuses to overwrite attempts and retains their
outputs on failure.

| Executed checks | Count | Scope |
| --- | ---: | --- |
| New registration/schema/reconstruction cases | 31 | All four operation/mode tuples; narrow software and resource identity; malformed/unknown bindings; explicit API/HPC rejection; unchanged policy and actual rejection; real inert helpers; absent protein capability when unbound; two local route IDs and software alternatives; RNA/generic selector coexistence; detached schemas; factory and saved-standard reconstruction. |
| Existing execution-family configuration consumers | 3 | Original descriptor, multiple HPC selection, API selected-resource identity. |
| Existing operation declarations | 8 | API declarations and native HMMER mode/resource schemas and unchanged information text. |
| Existing saved three-resource reconstruction | 1 | Local/API/HPC reconstruction before model entry, without work. |
| Existing 402 source exclusions | 23 | Protein and preexisting native source families, explicit artifact handling, frozen inheritance/reopen and generic-result denial. |

All executed project and helper files came from the read-only
`check001/source_snapshot/`. All **2,151 source pins were unchanged** after the
run. The enclosing `local_jobs` receipt verifies 20 GiB memory, 4 GiB scratch,
`memory_swap_max=0` and `runtime_max=infinity`. Its measured service-wall
duration is 127.564401815 seconds; observed scratch is 67,457,024 bytes. Scratch
uses the existing monitored enforcement with possible overshoot and a hard
per-file bound; it is not a filesystem sandbox.

The harness recorded two concurrent checkout changes separately: root's
`execution_episodes.py` changed from executed
`b9c56c0ec1041ddb5a9afaab0207a482bb63ed5564da22987e1c7ac3d39eac6a`
to observed post-run
`b81ee6c6b51d52a3cacc6d45d38bedb0c00b8a9bc8b55bdbb7d9618816a504cb`;
407's `native_protein_structure_results.py` changed from executed
`570569324173f5f993253d7597c74269a47b5311eb60edfeaf5964809dd649b6`
to observed post-run
`f39660fd460b1c147a9d313271ad5a77f27ce94accc5241fa3f21e2a9101b890`.
Those later bytes were not executed by this attempt. The four 408 methods remain
byte-identical to their executed snapshot; [handoff_scope_check.json](handoff_scope_check.json)
records the separate current-file check. Root owns verification of the combined
later source. 408 released its four methods after the successful focused run.

| Executed source | SHA256 |
| --- | --- |
| execution_episodes.py | `b9c56c0ec1041ddb5a9afaab0207a482bb63ed5564da22987e1c7ac3d39eac6a` |
| native_protein_structure_results.py (407) | `570569324173f5f993253d7597c74269a47b5311eb60edfeaf5964809dd649b6` |
| protein_structure_result_receipts.py (406) | `cacd8f85a79b82a502093231f18c0659aeee210140e49111bc4309e43e2b7f56` |
| native_protein_structure_returns.py (397) | `355dd928ef65269788b3af8f2d93aebf7c6510197a5d779140e7f64cae84611e` |
| native_protein_structure_contracts.py (390) | `13e1f7c4e9e60fed6283ab66aea03dd3b54de4767941d6509f496c2188cdaea0` |
| native_protein_structure_tool_info.py (390) | `fa358a9c27fe80fcb4c23ac6d73b80c823f85d7d7ee29f7457740fe79c344993` |
| protein_structure_selection.py (399) | `d8bea30cbbeb788efeea80dcf180bb281f13ef0ec42a0e5bf78966754051a828` |
| execution_service_setup.py, unchanged | `539b821bdbc2698d607dac421a5ea94895bec5a05a6935a06580658888ac82a0` |
| independent_execution.py, unchanged | `75968560eca9051a0a71c554e6fd636b189144bd48d8d25514297b8dc94a1bce` |
| episode_receipts.py, unchanged 402 guard | `523e29fc44d9ecbe074e57d650425dd8ac90311d96de280a3411e205427caeba` |
| test_protein_structure_resource_registration.py | `431ff39d1d2ce173ee3b086367fcd5a8534c433fd66405f8621e93209314a8a7` |
| run_bounded.py | `78b25a5b44a092cfb3d31ac4ef2357e6dc0e6ec3d5442af77780eb6cb4f8deb0` |

## Limits and authority reset

The test inputs are explicit synthetic structure/schema operands. The actual
small input parsers used by fixture construction ran inside the bounded worker;
no native protein job, network call, HPC deployment, model call, saved-sheet
recalculation or protein numerical publication was executed by 408. Retained
HMMER plans were read only for existing declaration tests. An altered second
software hash tests exact configured alternatives and makes no claim that the
second deployment exists. The real 406/407 modules satisfy the constructor
dependency at the recorded pins; their broader result/proof correctness remains
their lanes' and root's verification responsibility.

The complete immutable objective and all sixteen principles were read initially
and reread verbatim after the passing run, followed by contract 380/020. The
original attachment remains authoritative, SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The complete relevant AGENTS/design/practical/task-steering records and the
existing `compare_protein_structures` inventory row were inspected. No GOAL.md
was created or inferred. This packet changes no definition of full-tool
completion and makes no 112/308 increment.
