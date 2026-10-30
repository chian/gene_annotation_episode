# One selected Infernal native attempt

Read the entire authoritative goal attachment before work:
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
(SHA256 11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7),
AGENTS.md, GOAL.md, docs/EPISODE_STRUCTURE.md, docs/TIME_AWARE_ESTIMATION.md,
docs/PRACTICAL_EXECUTION.md and its original additive contract. Reread the
original objective and all16 principles verbatim after substantial native/source
examination and before moving to another tool or declaring a tool complete.

This is a fresh implementation workload, not a new episode. Read root221's
CONTRACT_001.md and NATIVE_CONTRACT_CORRECTIONS_001.md first. Workloads219/220
own pure graders; this workload does not depend on their completion. Root owns
all existing shared runtime files and the results acquisition/publication path.

## Exclusive writes

- gene_annotation_episode/native_infernal_driver.py
- gene_annotation_episode/native_infernal_local.py
- tests/test_native_infernal_execution.py
- tests/fixtures/native_infernal_execution/*
- all new files under this verification directory

All existing shared files, contracts, graders and other verification directories
are read-only. No changes to method_loop, credit, inventories, prompts, literature
or W05. Root's native_infernal_contracts.py and native_infernal_tool_info.py are
available now; consume their actual signatures. Report needed contract changes
to root rather than editing them yourself.

## Inputs and outputs

Implement `run_native_infernal(plan) -> dict`, a CLI taking exactly one plan JSON
path, and `validate_native_infernal_bundle_files(bundle, directory) -> dict`.
Plan has exactly version native_infernal_run_plan_v1, identity, requested_job,
attempt_directory (absolute), policy (actual LocalJobPolicy dict).
Identity has run_id, episode_id, resource_id, execution_id, attempt_id,
operation_key, requested_job_sha256; validate all against the original selected
request using native_infernal_digest. Do not invent default limits or timers.

Bundle mirrors the existing native producer separation: version
native_infernal_bundle_v1, identity, requested_job, program, table_format,
software {executable, expected_sha256, actual_sha256, declared_engine_version},
realized_argv, environment, inputs, operand_bindings, returncode, artifacts,
failures, started_at, finished_at. Preserve original job exactly; realized paths
are separate staged paths. Input rows carry role/format/original_path,
relative_path, artifact_ref, expected/actual hashes and expected/actual sizes.
Artifact rows carry role, format, relative_path, size_bytes, sha256. Failure
rows have stage, code, role|null and typed detail dict; preserve partial files.
Do not manufacture a measured native version from a caller declaration.

The driver runs exactly the selected executable once after validating/staging
the exact selected inputs and executable hash. It makes no model calls, network
requests, polling, automatic repair, resource substitution, index building or
scientific judgment. Native nonzero exit is retained with stdout/stderr and any
partial artifacts. All command/output/temp/cache paths stay in the one attempt
directory; copy inputs before any native adjacent-file access. Cmscan's four
explicit pressed companions keep the prefix relationship. Native CM framing
must allow multiple models for search and exactly one for cmalign. Keep caller
allocation; native compatibility errors do not justify silently changing options.

Use existing native_lifecycle/local_jobs for actual process lifetime and limits.
Immutable ownership and sealed manifest support replay: the same completed plan
reopens/validates its original bytes without rerunning; same plan with an unsealed
attempt is uncertain, not permission to rerun; conflicting identities reject.
Validate path confinement, symlink/regular-file relationships and saved file
hashes without replacing or recapturing corrupted files. Every retained input
needed for later result calculations must be checked as well as output artifacts.

## Existing lifecycle bridge

Implement `prepare_local_infernal(state, operation_key, *, root, policy)` returning
the existing NativeJobHandle and `local_infernal_plan(assignment, execution_id)`
returning the validated original plan. The attempt subdirectory is
infernal-attempt; immutable plan is infernal-plan.json; the driver CLI command is
the actual Python interpreter -m gene_annotation_episode.native_infernal_driver
plus that plan file. Preserve original selected argv/environment in invoke.json,
with native_infernal_plan='infernal-plan.json'. Native handle prepare is separate
from start; helper construction must not start work. The plan reader validates
original job, resource, attempt/operation identity, original driver command,
directory and policy. Do not add a new background loop or modify parent ownership.

Read the COMPLETE existing native_hmmer_driver.py/native_hmmer_local.py and actual
native_lifecycle/local_jobs consumers as implementation examples. Reuse matching
primitive semantics; do not import HMMER grading or masquerade as a HMMER job.

## Verification and handoff

Use actual tiny native cmsearch, cmscan and cmalign runs using the installed
resources/software/infernal-1.1.5-install/bin executables and tutorial data.
These can consume copies of existing tiny models/indexes; do not alter tutorial
files. Verify compiled invocation arguments against actual native outcomes.
20 GiB RAM / 4 GiB scratch, no wall cap. Test correct replay without subprocess,
missing/changed inputs, wrong software hash, bad framing, incomplete/unsealed
attempts, corrupted saved input/output, path escape and a real native nonzero
result with retained diagnostics. Separate synthetic failure fixtures from real
native examples. Do not repeat passed native jobs merely for another assertion;
use saved artifacts where applicable.

Deliver exact native commands, numerical artifact examples (not annotation
scores), test results, file hashes, frozen bundle examples and source/reset
receipts. State plainly that shared production launch/results wiring and full
episode communication remain root-owned verification, not proved by this module.
