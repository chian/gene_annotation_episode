# Infernal library and selected-resource boundary verification

Read the original complete tool-grader goal at
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
AGENTS.md and required design documents before work. Reread its objective and
all sixteen design principles verbatim after substantial examination and before
handoff. Preserve all original scientific and resource constraints.

Own only new `tests/test_native_infernal_local_binding.py` and this verification
directory. Do not edit production, existing tests, immutable records or other
subagents' files. Report concrete production failures to root. Agent 226 owns
live native Workflow tests; do not duplicate its native runs.

Verify these actual consuming interfaces together:
- native_infernal_tool_contracts(bindings, resource_kind='local', resource_id)
  produces name/description/resources/instructions and an exact requested-job
  input_schema with invocation_route to launch -> launch_local.
- ExecutionEpisodes.resource_tool_contracts() exposes these only for explicitly
  configured bindings, preserving different deployments of the same program.
- ExecutionEpisodes.assignment_schema(), prepare_assignment(), initialize(),
  and LocalPracticalOperations.validate_assignment() qualify the original
  resource/job rather than merely accepting a standalone schema.
- Shared configuration may contain both native_hmmer and native_infernal. Their
  callable job alternatives and information must coexist without overwriting,
  dropping, or substituting another program/software/resource.
- Infernal result selectors and all five family report schemas remain closed,
  with exact named metrics and the separate sequence/model associations.

Inputs: exact local program/software binding rows; real frozen cmsearch/cmscan/
cmalign request contracts and fixtures already in tests/verification. Pure
selection tests may use declared executable identities without executing them;
state honestly that these tests verify selection, not deployment. Use actual
existing ExecutionEpisodes and PracticalResourceEpisodes composition, not a
standalone substitute registry. Read affected complete functions first.

Cases: all three configured programs; no Infernal configuration; Infernal plus
HMMER on one resource; same Infernal program on two explicit local resources with
different software identity; changed program/executable/hash/version/resource/
compiled argv/original options; parent-constrained original job and scope;
unsupported API/HPC native_infernal configuration rejects explicitly and never
claims a deployed binding. Verify that capability information itself performs
no acquisition, native job, parser or scientific calculation.

The existing selector contracts permit search_hit/search_sequence for searches
and alignment_sequence/alignment_column/alignment_pair for cmalign, with explicit
row offset/limit or record_keys and metrics. Invalid mode/family/metric choices
must not become an implicit default selection. Don't invent extra restrictions
or acceptance gates merely to make a test pass.

Use existing run_local_job with LocalJobPolicy(20*1024**3, 4*1024**3, None), retain
command/environment/source hashes and actual results. Do not use fake scientific
outputs to claim live behavior. Report precise coverage and missing paths.
