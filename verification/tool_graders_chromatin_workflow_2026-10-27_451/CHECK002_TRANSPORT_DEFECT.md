# 451 check002: composed assignment transport rejects the bound Cooler job

check002 is retained and collected: **0passed,2failed,5setup errors** in104.45s,
returncode1, terminal/quiescent, unchanged frozen source and interpreter pins.
No practical.job.start or native chromatin execution occurred. The shared
complete fixture and the independent partial/empty fixtures all stop at the
same launch→launch_local provider boundary. This does not overwrite check001's
six passes on its earlier immutable source snapshot.

## Exact first failure

`jsonschema.exceptions.ValidationError`: selected launch_local commission
“is not valid under any of the given schemas”. Validator:anyOf,
instance.selection, schema.properties.selection.

Retained first-project trace locations are test153 → fixture_helpers325 →
run_root170 → shared method_loop/episode.py1551 → runtime.py1362 →
runtime.py954 → fixture_helpers.py315 (`Draft202012Validator(schema).validate`).
The complete trace is in `check002/stdout.txt` (large because pytest printed
the selected software literal and complete schema). Compact leaf errors are
in [probe002/LEAF_ERRORS.json](probe002/LEAF_ERRORS.json).

The relevant error is `'native_runtime' is a required property` at
`assignment.requested_job.native_chromatin_interactions.software`.
The instance is the actual caller-bound Cooler software, which correctly omits
this optional HIC-only member. No field or software literal was modified in
the failed Workflow.

## Bounded diagnostic evidence

Three explicit read-only probes used check002's immutable production snapshot
and original Store with SQLite mode=ro. Each had20GiB RAM,4GiB scratch,zero swap,
no wall budget and a separately followed original handle. All three probes
closed returncode0 with unchanged probe/source/interpreter pins. They performed
no native acquisition or new Workflow commission.

```sh
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py launch probe001
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py collect probe001
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py launch probe002
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py collect probe002
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py launch probe003
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_probe.py collect probe003
```

1. probe001 validates the selected commission against the retained original
   domain schema: valid, zero errors. Its purpose/result is the domain side of
   the boundary; it did not apply the provider transformation.
2. probe002 applies the actual `_action_generation_schema` first and reproduces
   the provider failure. The selected launch_local branch is index12.
3. probe003 tries explicit strict nulls for native_runtime and launch_instructions,
   then runs the actual `_decode_action_response`. Original domain valid=true;
   strict provider valid=false; decoded domain valid=false; native_runtime:null
   survives decoding. The relevant decoded leaf is `None is not of type 'object'`.

There is **no provider-valid null representation for this exact software**:

* `requested_job.anyOf[1].allOf[0].$defs.SoftwareBinding.required` now contains
  native_runtime, whose provider field is anyOf(HicNativeRuntime,null).
* The other conjunct,
  `requested_job.anyOf[1].allOf[1].anyOf[0].properties.native_chromatin_interactions.properties.software.enum[0]`,
  is the exact bound software literal and has no native_runtime member.
* Omitting the member fails required. Adding any value, including null, fails
  equality to that immutable literal. The literal was deliberately not weakened
  to manufacture a provider-valid sample.

This establishes a production transport contradiction. The fixture's limited
provider adapter also does not adapt allOf/ref bodies, but adapting it cannot
satisfy these contradictory constraints while preserving the exact software.

## Exact function behavior and consumers

`runtime._json_episode_assignment` (279) accepts kind.const=episode_child only
when assignment.type=object. Its actual input here has assignment.anyOf with
one complete practical object branch and no top-level type, so it returnsfalse.
Consequently `_action_generation_schema` (210) leaves that assignment expanded,
changes every optional object property to required nullable, and deliberately
preserves literal const/enum values. This creates the contradiction above.

`runtime._decode_action_response` (314) traverses anyOf, explicit objects and
arrays, and JSON-decodes recognized encoded assignments/tool arguments. It
does not traverse the nested allOf/ref request schema, so the added strict null
survives. `EpisodeSource.apply_response` (1406) calls this decoder, then validates
the original selection schema (1427) before `workflow.selected`; it cannot
admit that null into the original domain contract.

Production construction and affected consumers:

* `ExecutionEpisodes._request_schema` (263) embeds actual operation contracts
  under requested_job.anyOf. `assignment_schema` (336) wraps resource-specific
  launch_local/API/HPC alternatives in assignment.anyOf.
* `native_chromatin_interaction_contracts.chromatin_interaction_execution_schema`
  (116) combines the complete RequestedJob schema with the exact selected
  software literal using allOf. The actual tool-info compiler calls this port.
* `ExecutionEpisodes._match_request` (552) separately preserves the exact
  original parent request, allocation and resource. Adding an invented
  native_runtime:null is not an allowed substitution.
* `EpisodeSource.call` (818,954) saves the original domain schema and supplies
  the generated schema to the provider. Its saved-response branch returns the
  original response/schema for interrupted decisions; resumed decoding remains
  a compatibility consumer of any repair.
* `validate_contract_exchange_request` (1044) compares saved output_schema to
  generated exchange schema. `exchange_decision` (1154) creates it for new
  exchanges but retains the original output schema for existing exchanges.
  A shared fix must account for these durable, previously recorded contracts.
* `_decode_action_response` is used by `apply_response` (1409) before original
  domain validation and action admission, not after execution or credit.

No production file, validator, exact binding or field meaning was changed by451.
Root owns the narrow shared repair. In particular, the fix must not make native
runtime fields mandatory for Cooler, drop HIC functionality, relax literal
software identity, or make the fixture bypass production validation.

## Reproduction identities and remaining work

check002 handle: `check002/handle.json`; unit
`gene-local-job-97e7c33db456440f88744c8e78587db7.service`.
Terminal receipt SHA256:
`e61f80061e41bdb7c8007538462ab5f79c052d29520273c12f61bf46fa35fc8f`.

Relevant executed source SHA256:

| File | SHA256 |
| --- | --- |
| runtime.py | `57f3fff849bc6703fe14f9a2382ea958b0f1f6697394cef9a8dfdff3a10b15ba` |
| execution_episodes.py | `f0face3937cef3122097aec41e94d8238e2feb3221429dc328ccd6d931e7181f` |
| native_chromatin_interaction_contracts.py | `1f1081d9acc2cb0bc27388cf075480c8763341ed2773f093895d228440eb07d5` |
| chromatin_interaction_contracts.py | `8615d46130306a8c7c774f88d75f655ccf35e69afae1252839bd70b1ba621a49` |
| Test | `45171a96f10fc42f3e40109b771f308c339555c3b831e3587375e0e1cc3de73c` |
| Fixture helper | `66d52415fd3832042c99c7104a5749c2daa503b4498473b87b65417caeb24783` |

The all-empty sparse case and new composite-resolver checks remain unverified.
All seven current Workflow cases need a new explicitly frozen attempt after
the shared repair. The later HIC-only mmap runtime pin fix was not in check002
and is unrelated to this pre-native failure. No inventory count is changed.
