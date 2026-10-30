# Resource caller preparation packet001

This packet implements preparation only under the copied adopted scope
ADOPTED_SCOPE001.md (9224e495eeb891266ed5c7b212598f4b436c4e1d3cb376db4ffe30a187fd82ad).
The operator was not invoked by this author. Root owns its separate invocation and any
separate launch. The packet contains no scientific run, service result or new
scientific observation.

## Pinned invocation

The complete intended argv, cwd and explicit environment are in
INTENDED_INVOCATION001.json. The command is:

```sh
/home/chia/repos/gene_annotation_episode/.venv/bin/python /tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE/prepare_caller001.py --prepare --input-manifest-sha256 e398322011562a864f56a24ecc1bfa798854e83f78e96b07132ee04ed3db23f1
```

Use cwd `/tmp/gene-annotation-configured-caller-20261022-007` and explicit env
`PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=/tmp/gene-annotation-configured-caller-20261022-007`.
This is an intended command, not a transcript. No help, preparation or launch
invocation was performed while authoring the packet.

INPUTS001.json is the exact 14-member runtime input map. It pins the operator,
all static caller inputs, copied adopted authorities and the closed wrapper
output schema. The CLI's required expected manifest hash avoids a hash cycle.
MANIFEST_FINAL001.json is the outer seal of the packet, excluding itself.
Auxiliary documentation/static-check files are outer members, not additional
operator inputs.

## Exact adopted input changes

C_REQUEST001.json differs from BASELINE_C_REQUEST001.json only in
destination_workspace, now
`/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001/workspace`.
The original 198 reference list is retained exactly, canonical hash
05d35a200c33e1b4defb0859e0aea70699b49be48a4cc41e55b274ca8f59a860.

ADOPTED_INPUT_DELTAS001.json records the five configuration relocations
(history, workspace, minimap2 cache, native receipts, public access) and three
parameter changes (API history, API ledger, fresh public registry identity).
verify_static_inputs checks the entire parsed configuration and parameter
template against those baseline files and deltas. The policy stays unchanged;
its static template hash is
dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1.
focus.txt is the exact adopted focus b2f718a545a1829b8521f6cd437ff1c0688ad4068b5f739d033e9d8ce151c7bf.
The old focus and planning packet are unchanged.

Only actual verified outputs fill the two deferred fields:
policy.scientific_progress.initial_known_record_refs receives the actual C
result/receipt list (198 retained plus two fresh lineage records, 200 total);
policy.operational.registry_ref receives the actual prepare_case_run native
registry identity. The proposed fresh public registry is
execution_registry_1411c4378f584a40b65ed74178e1cb05; preparation does not submit
or choose public work.

The unchanged implementation is 137 runtime files at
3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842.
The unchanged C producer is 166d459b38295ab4003ebe39babd22184a96482dba5146b3b2479291ebd423ab;
the unchanged P factory is 4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f.

## Actual future operations and outputs

The operator exclusively reserves NEW
`/tmp/configured-resource-investigation-preparation-20261022-001`, validates
inputs and source bytes, creates the NEW run directory, then calls the existing
prepare_scientific_checkpoint_fork with the complete fixed C kwargs. C owns its
original-source readonly immutable SQLite access and fresh workspace custody;
the wrapper does not open original, active006 or active007 SQLite databases.

It validates actual C result and receipt against unchanged SCHEMAS004.json,
all manifest/artifact/authority hashes, 193 committed records, the four inherited
native receipts, 175 exact raw lineage rows, the 198-to-200 union and the
checkpoint/working independent inodes. It checks the working publication hash
before prepare_case_run. That hash is a historical C publication witness after
subsequent preparation, not a required later file inequality or equality.

It then calls existing prepare_case_run(case_dir, run_dir, configuration,
focus=focus), saves the returned object, checks equality with case-launch.json,
fills the two deferred parameters, and calls the existing pure P create_policy.
It does not call run_prepared_case, Workflow, a model, provider, native program,
job launch, controller or credit projector.

The wrapper's only own SQLite count reads are of the NEW inactive native jobs
database and NEW inactive prepared working database. Exact path allowlists,
empty/absent WAL, mode=ro&immutable=1, query_only, explicit BEGIN and finally-close
apply. Its evidence must show native orders/handoffs/samples=0 and the retained
old runtime counts 1 run, 1 episode, 179 actions, 175 observations and 180 model
calls. These retained counts are not new run progress. The independent checker
has a narrower SQL boundary: only the NEW immutable checkpoint and NEW inactive
native registry, never the NEW working DB.

Future run-owned caller-inputs files are:

- OPERATOR_INPUTS001.json: actual invocation and operator/input identities.
- C_REQUEST001.json, config.toml, focus.txt, PARAMETER_TEMPLATE001.json,
  EXPECTED_HANDOFF001.json, SCHEMAS004.json: exact copied input bytes.
- C_RESULT001.json: unchanged actual C result format; C_FAILURE001.json only if
  C raises its typed failure.
- C_VERIFICATION001.json: wrapper's concrete custody checks.
- PREPARE_RESULT001.json: actual ordinary case preparation return, equal to
  the run's case-launch.json; this is distinct from the outer result.
- parameters.json: actual final caller parameters.
- PREPARATION_RESULT001.json: outer closed resource preparation result.

The outer result version is
configured_resource_investigation_preparation_result_v1, status
prepared_not_started. Its exact closed shape is $defs.result in
OPERATOR_OUTPUT_SCHEMA001.json. It includes exact three-field file descriptors
{path,sha256,bytes}, actual registry identities, the retained counts, unchanged
source guards, zero new starts and zero model/HTTP/native calls. The operator's
RESULTS001.json is JSON-equal to caller-inputs/PREPARATION_RESULT001.json.

Operator-owned evidence files are OPERATOR_EXECUTION_STARTED001.json,
SOURCE_BEFORE001.json, SOURCE_AFTER_C001.json, SOURCE_AFTER_PREPARE001.json,
RESULTS001.json and OPERATOR_EXECUTION_FINISHED001.json. Source witnesses include
mode in addition to path/hash/bytes and record absent sidecars explicitly. The
original implementation 122-file manifest, authority/DB/sidecar files and
registered artifact files must be unchanged before/after; the executing 137-file
source is also rechecked. No original source DB is opened by the wrapper.

## External process receipt and failure preservation

The root-owned external receipt contract is already fixed separately. It uses
NEW `/tmp/configured-resource-investigation-root-preparation-20261022-001/`:
STARTED001.json, INVOCATION001.json, STDOUT001.log and STDERR001.log. The receipt
version is root_configured_resource_preparation_invocation_v1 with status
exited; it records actual argv/cwd/explicit env/start/end/exit, operator/INPUTS
and log descriptors, and 137-file source pins before/after. Root's separate
stdlib invoke_once001.py owns this evidence. This packet creates no second
external receipt, driver or invocation directory. Q consumes the root receipt
through --preparation-invocation.

The operator's internal STARTED fields are exactly argv, cwd,
explicit_environment{PYTHONDONTWRITEBYTECODE,PYTHONPATH}, started_at_utc,
operator{path,sha256,bytes}, scope_sha256. Its internal FINISHED fields are
started_at_utc, finished_at_utc, status, exit_code and last_phase. Successful
values are prepared_not_started, 0 and source_after_guard respectively. These
internal claims do not independently establish the external process exit.

Failures retain all partial files and raise to the root-owned caller; there is
no cleanup or retry. $defs.failure is closed, version
configured_resource_investigation_preparation_failure_v1, with the actual
phase/exception/message, nullable source_unchanged and source_guard_error_type,
preserve_partial=true, automatic_retry=false and zero model/HTTP/native calls.
If evidence reservation itself collides, the operator does not write into the
existing directory; external stderr/exit is the failure evidence. After owned
reservation, it attempts FAILURE001.json, internal FINISHED status
failed_preserve_partial/exit1 and SOURCE_AFTER_FAILURE001.json when an original
before guard exists. A diagnostic storage failure is printed to external
stderr. Files remain as actually created, including a late RESULTS followed by
FAILURE. Success therefore requires the external actual exit0, internal
successful FINISHED, no FAILURE, and exact outer result equality and validation.

## Static verification and limits

STATIC_COMMAND_START001.json and STATIC_COMMAND_RESULT001.json preserve the
only actual check invocation, which ran verify_static_packet001.py once and
exited0. It compiled/called seven selected pure static JSON/filesystem helpers
from the operator AST, never the operator module/main, C/P or SQLite. It checked
the 14 inputs, 286 published library inputs, original 198 list, sole focus
replacement, C request/schema, wrapper schema (one success-shape example,
ten failure-shape examples and three rejection examples), and frozen source.
SCHEMA_ONLY_EXAMPLES001.json contains explicit invented schema examples only;
none is an actual operation result, failure or file witness.

STATIC_CHECKS001.json reports 0 application imports, database connections,
operator main calls, C/P calls and model/service/native calls. No static check
opened an original DB or any active workspace. The separate final-metadata
command001 failed because its `python` executable was unavailable, before its
script body ran. Its exact shell command, script, exit127 and stderr are retained;
command002 used the required virtual-environment interpreter. This did not rerun
the static checker or preparation. Readset provenance and the complete old-to-new operator diff are
retained separately. The static checker outputs already exist and its own
exclusive output creation means it must not be rerun in this sealed packet.

This author executed no preparation. Root's separately timed actual invocation,
if performed while outer packet documentation is finalized, is proved only by
its external receipt and resulting files, never by these authoring records.
No raw actual scientific/provider input,
duration sample or active state is copied into this packet. The future empty API
history is not seeded: support0/null or real unavailable status remains useful
information. Preparation proves no selected job, informed selection, C1,
semantic handoff, child return, C4 admission or scientific use. Those require
separate future observed execution. Equivalent-job API/local/HPC comparison,
scoring adoption and the full goal remain unproved.
