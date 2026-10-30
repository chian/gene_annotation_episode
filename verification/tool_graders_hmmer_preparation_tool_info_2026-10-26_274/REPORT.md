# HMMER preparation tool information — 274 / I1

Implemented the three I1 information-construction ports in
`gene_annotation_episode/native_hmmer_preparation_tool_info.py` for the fixed ten
programs and 26 modes. Each explicitly supplied binding produces the exact P1
request schema with its executable, SHA-256 and HMMER 3.4 version pinned, the
specified local launch commission route, and corresponding four-field tool
information. Construction validates data without file access, probing,
installation inference, native execution, parsing or grading.

This workload edited only its new information module, its test module and this
verification directory. Shared resource/episode integration belongs to the root
workload. No completion inventory or full-tool tally was changed.

## Verification

`check001` ran `.venv/bin/python -m pytest` through the existing `local_jobs`
runner: **254 passed in 1.05 seconds**, return code 0. The receipt records a
1.491246711-second service duration and 679,936 observed scratch bytes. Its
enforced policy was 20 GiB RAM, zero swap, 4 GiB monitored scratch with the
documented possible overshoot, and no wall-time cap. The cgroup verification
record reports `memory_max=21474836480`, `memory_swap_max=0`, and
`runtime_max=infinity`.

The tests consumed the retained successful P1 requests for all 26 modes from
producer267/check005, checking the immutable native-case manifest and each
bundle hash. They did not launch any native program. They verified:

- Exact ten-program/26-mode enumeration, unique mode-specific information, all
  required and optional operand/output roles and declared native formats.
- Exact six-field callable entries, four-field information entries, original
  ordering, exact `commission -> launch -> launch_local` routes, and exact P1
  schemas with pinned supplied software. All 26 actual saved requests passed
  JSON Schema and the existing P1 relational validator.
- Rejection of changed software identities, malformed binding shapes, unknown
  modes, duplicate program/mode bindings, invalid paths/digests/versions,
  malformed resource identifiers and unfinished nonlocal resources.
- Independent copies across input, validation output, schema trees, routes,
  information entries and later constructor calls.
- All 26 constructors while common filesystem, network, environment-discovery
  and subprocess entry points were replaced by failing sentinels. An unprobed
  absolute executable path remained acceptable as explicit binding data.
- Native semantic caveats and the named numerical fields against V1's actual
  separate projection catalogue. This checks field availability and its declared
  meaning/source/unit, not the correctness of the separate calculators.

`check001/intent.json` records the exact command, policy and SHA-256 values for
the implementation, test, harness, P1 producer paths, Infernal reference paths,
V1 catalogue, local job runner, governing documents, all259 native contracts,
all261 component/handoff documents, and all 26 consumed P1 bundles/receipts.
`check001/source_stability.json` records no changes during the test run.
`check001/junit.xml`, `stdout.log`, `stderr.log` and `receipt.json` retain the
actual outcome. Full reviewable contract and information arrays are in
`check001/temporary/test_retain_reviewable_catalog0/tool_contracts.json` and
`tool_information.json`; the information array is the exact four-field projection
of those contracts.

## Concrete instruction examples

Each example below is actual instruction text, not a new prompt or grading
procedure. The retained arrays contain the complete selected-mode instructions,
including its input/output roles and formats.

- `native.hmmstat.summary`: “Independent calculations require explicitly
  supplied background and length_probability (p1); the versioned HMMER 3.4 helper
  is available only for an explicit caller selection. Absence remains unknown
  and is never filled automatically.” Its result information names
  `parse_hmmstat_summary`, `populate_hmmstat_sheet` and
  `calculate_hmmstat_components`, and fields including
  `components.mean_match_information` and `components.position_relative_entropy`.
- `native.hmmconvert.binary`: “stdout is binary model data and must never be
  decoded or monitored as an ordinary text log.” Shared conversion information
  says `stdout` and `converted_models` alias one path with two retained role
  occurrences but one model population. Binary/HMMER2 decoding limitations stay
  explicit despite native execution support.
- `native.hmmerfm-exactmatch.locations`: “Coordinates are one-based inclusive: f
  is a left endpoint and r a right endpoint; r means string reversal, not reverse
  complement or a biological minus strand.” Instructions preserve native
  boundary defects and independently valid/invalid/unresolved counts; imported
  FM ABI and original source associations must be explicit.
- Every `hmmsim` mode: “The producer explicitly records --fast=false and
  --tlinear=false when unselected; historical omissions remain unknown.” Full
  native score vectors require their original recorded ABI; rounded verbose
  output cannot replace them. Native and independently fitted rows stay separate.
- `native.alimask.alignment_to_model`: “The producer rejects intervals wholly
  after the last match column.” Its established preflight and unsupported
  weighting/subsampling cases are described without substituting another map.
- All modes: “Monitoring uses the existing generic local-resource task
  instructions: observe the same execution identity, native state, available
  outputs and selected stdout/stderr windows, subject to the tool's binary-output
  restriction.” Results information refers to the original captured bundle,
  separate deterministic parsers/calculators and explicit V1 numerical/artifact
  selections; it supplies no LLM monitoring or scientific-support judgment task.

## Scope limits and root handoff

The ports are `validate_native_hmmer_preparation_bindings`,
`native_hmmer_preparation_tool_contracts` and
`native_hmmer_preparation_tool_information`. Bindings contain exactly
`program`, `mode`, and `software={executable,sha256,engine_version}`.

Root still owns registration of these ports in shared resource information and
callable construction, preservation of selected child information across the
episode boundary, actual local dispatch/monitoring/result collection, and
verification through the complete episode path. This isolated workload does not
establish that integration or perform live native execution. API/HPC bindings
raise the explicit unfinished-resource-binding error; no API/HPC deployment is
claimed. Native format acceptance does not imply a complete numerical decoder.
The separate D1/V1 workers retain ownership of grading and result projection.
No new episode, root execution tool, TASK template, LLM grader, scoring language,
retry/resource decision, automatic poll, continuation rule, observation or
credit was added here.

The immutable original objective, all16 design principles and I1 contract were
reread during implementation and again before handoff. They remain design
authority, not runtime gates or executable actions.

## Exact SHA-256 identities

| File | SHA-256 |
| --- | --- |
| `gene_annotation_episode/native_hmmer_preparation_tool_info.py` | `c149a0bd02723ed02fb3baf9877a8d7d78b1657b13187772783b79a83c19401f` |
| `tests/test_native_hmmer_preparation_tool_info.py` | `d9b10303549a92d8b331f1b7fca6ca5782cd408b32ad923ce3e744b890c6be0b` |
| `run_tests.py` | `5821435d9ec961bf24f509b428a48decb680c5d2762ae1d6effcacbbd90a75fc` |
| `check001/intent.json` | `61f83bea486f9188d5966c5bf6ccc998db5bedf9ac4c347902d4cdd1928c15e2` |
| `check001/receipt.json` | `05d28edf1fc6c846aac5d8c755e4a2f50fdff245e89473e941309cae288d1a72` |
| `check001/junit.xml` | `ecfa53af1de28b2397e7c20f6f46488a3a2c182a5f5c623ac0bf362b6e86f032` |
| producer267 `check005_native_cases.json` | `1ac655502d673ce9d61c8eada0d7d95c17a812222568a07b8d3dde1dd5cc5bae` |
| 261 `TOOL_INFORMATION_CONTRACT_001.md` | `739a35cc13252b732d27faf92eb6664c269bd8def2be0fe9bfefb6509b889fa2` |
| Original attachment `e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt` | `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7` |
