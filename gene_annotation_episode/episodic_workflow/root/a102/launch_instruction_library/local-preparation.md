# Local assignment, setup and reuse

The parent supplies the requested job, workspace, constraints, validated
endpoint and typed return form. The child chooses useful preparation, reuse,
diagnosis and execution actions within that assignment. These instructions are
supporting information; they are not a fixed action order or a complete episode.

The opt-in local practical binding requires an explicit configuration with
`kind=local`, an absolute `workspace` and a caller-owned resource `policy`.
The policy supplies `memory_bytes` and `scratch_bytes`. It has no elapsed-time setting.
Use that actual policy and the assignment's `constraints`; this manual supplies
no allocation values or timeout and cannot change the selected limits.

The supplied inventory snapshot describes known preparations before the first
choice. Its canonical content hash and local/remote comparison identify catalog
bytes, not present runtime usability. Decide from the assigned software and
input requirements whether an existing executable, environment, database or
prepared wrapper needs checking. Reuse a valid setup. If something is missing
or incompatible, choose a scoped preparation/repair action and retain its
actual result. Do not silently substitute another database or algorithm.

Record executable/source/package and database identities at the specificity the
job needs. A file existing at an old path is weaker than a checked release/hash
or a successful relevant operation. Changes in load/free space/throughput are
current observations, separate from the reusable setup. Repairing one run's
conditions does not require rebuilding that setup or rewriting old records.

Native execution requires `systemd-run`, `systemctl`, a usable user systemd
manager and verified cgroup limits. Failure to establish that boundary returns
an operational failure; no unprotected fallback is installed. The native
lifecycle controls the process tree independently of the episode. Memory and
swap have cgroup limits; scratch is monitored with possible overshoot and a
per-file limit. This does not constitute a filesystem sandbox. Keep selected
files and generated control/output paths in the supplied workspace.

## Native scientific manifests

An assignment's `requested_job.native_*` operand identifies the scientific
format and pinned software being requested. Its existing driver, manifest and
result reader retain their original scientific requirements. Use the supplied
native contract module when authoring a run manifest; a successful unrelated
shell command is not evidence that this scientific program ran.

`EPISODE_COMMAND_INTENT` is the actual selected command's immutable JSON input.
It supplies the original assignment, run, episode and operation identity to
scripts directly. A scientific preparation manifest can retain that preparation
command's identity. Its later actual driver invocation has its own command
receipt, linked by the manifest's captured unchanged bytes; do not invent a
systemd job handle or maintain a second receipt ledger.

The existing contract modules are `native_expression_nmf_contracts`,
`native_fluorescence_contracts`, `native_genomic_overlap_contracts`,
`native_chromatin_interaction_contracts`, `native_atac_differential_contracts`,
`native_protein_structure_contracts` and `native_flux_balance_contracts` under
`gene_annotation_episode`. Each defines its purpose-specific run-plan validator,
`RUN_PLAN_FILENAME` and driver-argument function. The manifest belongs at that
filename beside its preparation intent, and its attempt directory belongs
beneath that same command directory. Pass the actual native driver argument
array to the general terminal so its invocation and input/output versions can
be recorded exactly. Choose the required environment from that scientific
contract; explicitly selected temporary/cache paths are preserved when confined
to the original assigned workspace. The executor supplies confined defaults
for omitted paths. The purpose-specific result reader still checks the original
scientific manifests and outputs; operational handoff credit is separate.
