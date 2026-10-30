# B-L130 finite native producer ports, revision 1

This implements only the native/local producer of the original authoritative
goal. Packet491 owns numerical readers/sheets/calculators. Root owns all shared
integration. No complete Workflow claim follows from these ports.

`native_barcode_contracts.py` exports `POLICY` (20 GiB RAM, 4 GiB scratch,
wall_seconds null), `NATIVE_BARCODE_REQUESTED_JOB_SCHEMA`, `validate_barcode_job`,
`validate_barcode_requested_job`, `validate_barcode_bindings`,
`validate_barcode_software`, `validate_barcode_run_plan`,
`requested_job_from_barcode(job, *, environment)`,
`barcode_environment(software, *, attempt_directory)`,
`barcode_output_files(job)`, `barcode_driver_argv(plan)`.

Native job exact fields: `version='native_barcode_job_v1'`,
`operation='analyze_barcode_sequencing_data'`, `request=BarcodeRequestV1`,
`inputs={reads,original_request,target_map}`, `software`, `output_prefix`.
Each input is `{path: absolute non-symlink file, file: ArtifactFile}`;
target_map is null iff request.barcode_target_file is null. Original request
file is mandatory: preserve its original JSON bytes and verify parsed semantic
identity against request. Reads and target file identities equal their exact
request identities. Missing/changed files are executed structured failures,
not permission to analyze alternative data. Invalid target content preserves
independent read/count/distance work.

Software exact fields: `version='barcode_software_v1'`, `python` (path/size/SHA),
`python_version`, `python_home`, `module_root`, `implementation_files`
(path/size/SHA list), `dependency_roots`, `distributions` (name/version/requires),
`runtime_files` (path/size/SHA list). Required distribution identities include
biopython, numpy, scipy and jsonschema plus its runtime dependencies. All actual
driver source, interpreter, stdlib, dependency and native library files are
pinned. The native process verifies pins and loaded module association.

Requested job exact fields: `argv`, `environment`, `native_barcode` (job above).
Argv is `[python,'-B','-S','-m','gene_annotation_episode.native_barcode_driver',
'barcode-plan.json']`. Caller environment follows barcode_environment; original
values remain recorded, while the established local lifecycle explicitly owns
the actual attempt temporary paths. No shell dispatch.

Plan exact fields: `version='barcode_run_plan_v1'`, `identity`, `requested_job`,
`attempt_directory`, `policy`, `outputs`. Identity has run_id, episode_id,
resource_id, execution_id, attempt_id, operation_key, requested_job_sha256,
assignment_sha256. The native handle is original
`.episode-operations/digest(run,episode)/digest(operation_key)/native.json`;
attempt_directory is its sibling `barcode-attempt`. Outputs have role,
relative_path and format: nine packet491 roles plus manifest=bundle.json.
They are rooted beneath the selected output_prefix. Plan/owner/start markers
are immutable. An existing output directory is rejected, never reused.

`native_barcode_local.py` exports
`prepare_local_barcode(state, operation_key, *, root, policy) -> NativeJobHandle`
(reserve only), and `local_barcode_plan(assignment, execution_id) -> dict`
(authenticate only). Existing local operations own dispatch/status/collection.

`native_barcode_driver.py` exports `run_barcode_job(plan) -> BarcodeNativeManifestV1`
(the exact packet491 bundle manifest) and `execute_barcode_plan(plan) -> int`.
The latter maps a returned manifest to native success/nonzero exit. Original
request/reads/mapping bytes retain exact identities; extracted records stream
to ledger, all counts remain, direct condensed distances feed SciPy average
linkage and distance-threshold fcluster. No square-row Euclidean transform.
Prefix errors retain their complete parsed prefix with explicit extent. K<2
declares not_enough_barcodes. Strict unequal lengths retain invalid pair rows
and counts. Complete selected pair capacity is checked before allocating;
insufficient memory/scratch yields resource_limit_exceeded without sampling.

`native_barcode_observations.py` exports
`barcode_observed_files(plan, observation, *, log_window_bytes, log_roles)`
returning `(outputs, logs, manifest_available)` matching existing local ports,
and `read_barcode_output(plan, *, path, offset, limit)`. Logs contain actual
stage/count measurements and dependency versions, no percent or scientific
score. Closed-file indication requires terminal and quiescent observation.

`native_barcode_tool_information.py` exports
`barcode_tool_contracts(bindings, *, resource_kind, resource_id)` and
`barcode_tool_information(...)`. Binding rows are `{operation,software}`.
The only route is existing launch -> launch_local; no HPC deployment is claimed.

Verification uses new packet-local immutable snapshots and original lifecycle
handles copied mechanically from packet488. No application imports/tests/native
work run directly on the host. Tests cover the 12/10/4-3-2-1 example, true heights
1 and 3.5, two-barcode distance 3, FASTA/FASTQ/gzip, prefix/failure and custody cases,
strict/overhang/extraction alternatives, native numerical reader compatibility,
local reservation/replay, and stale/changed inputs. Root remains responsible
for selected tool, communication, capture/publication and credit integration.

## Additive implementation clarification

The executable producer imports packet491's `barcode_formats.BarcodeTextLines` for
strict linewise decoding; its source therefore belongs in implementation_files.
This avoids losing already emitted SeqIO records when a later byte line cannot
decode. Native stage declarations follow packet491's stage-specific validators.

The executable checks individual pins for all imported files and executable
native-library mappings. Direct bounded calls additionally validate all actual
stdlib/dependency and barcode sources without asserting ownership of unrelated
caller modules. The verification harness pins every source/dependency/stdlib
file, interpreter and resolved native library before work and checks them after.

Staging writes `.unverified-<filename>` first. Only complete expected bytes are
published under an authoritative role filename. Missing or same-size tampered
reads prevent analysis; a missing/tampered target map leaves its authoritative
filename absent while retaining independent counts. Unverified bytes are not
scientific artifacts and never receive fabricated expected identities.

Count-table/population space is reserved as unique barcodes are admitted so
resource failure while streaming does not deliberately discard completed counts.
The full selected distance population is checked against conservative memory
and output-size requirements before its array is allocated. Actual cgroup and
scratch enforcement remain the existing native lifecycle's responsibility.
