# Existing-episode integration for the VDB utility

This is an implementation port for unfinished R7, not a goal or scope amendment.
The immutable user attachment remains authoritative. No formatter, new episode,
new scientific score or alternate numerical authority is introduced.

## Already-owned dependencies

667 owns the complete pure selector/projection/fact contract from665. It exposes
NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA, ..._V2_SCHEMA, their closed union,
validate_blast_utility_result_selector(selector, *, operation), full-context
projection/validation, fourteen FACT_SOURCES and four logical namespaces.
668 owns job-v3/compiler/capture/offline execution and the whole result worker.
Its exact job and context/proof types are664; reuse public JOB_VERSION_V3,
VDB_MODES, native_blast_utility_job_schema(program,mode), the requested-job
validator and vdb_utility_database_operands(job). The original proof remains in
worker receipt/manifest, not another artifact.669 owns original publication,
acquired-body version dispatch and returns. Outer prepared/retained/bundle
versions remain unchanged. Their implementations/tests are still being finished.

## Root: actual resource tool information

Root exclusively owns native_blast_utility_tool_info.py and new tests670.
Preserve every legacy/preparation description, instruction and schema behavior.
For the four VDB pairs (blast_vdb_cmd with extract_sequences/info/paths/paths_all),
require the same binding fields plus an explicit nonempty unique variants list:

{program, mode, software, molecules:[dna], variants:[{
 database_source: db|dbs_file,
 database_input_kind: path,
 selection_kind: entries|all_native_sequences|all_references|null,
 entry_source: entry|entry_batch|null,
 include_filtered_reads: boolean
}]}

Each variant is closed. Extraction permits entries with either source;
all-native/all-reference require null entry_source. Inspection modes require
null selection_kind and entry_source and false include_filtered_reads.
All-reference also requires false include_filtered_reads. The first actual
resource binding exposes absolute path operands; alias/accession mappings stay
an explicit unfinished resource-verification item, not an implied resolution.
Common core/compiler support for those tokens is preserved.

Implement pure VDB variant-schema and operation-constraint helpers in that file.
Reuse the same constraint in _bound_job_schema and runtime binding acceptance.
It fixes exact job-v3/software/program/mode/dna, database source and every input
kind, selection kind/source and filtered-read flag. Native schema validates
remaining required fields; don't copy its database/context/offline definitions.
Expose existing operation names native.blast_vdb_cmd.<mode> through the existing
commission route launch -> selected local resource, never a direct root tool.

Information fields retain name, description, resources, substantive instructions.
These are tool-library facts about this selected operation, not a new TASK or
STEERING template. Describe original prepared operands/config, fixed native
formats and selection semantics, retained native versus normalized values,
explicit requested artifacts and no inferred sample/member identities. Keep
resource instructions consistent with the exact offline producer, actual caller
allocation and unverified remote/alias limits. No monitoring-specific LLM judge.

## Fresh coding owner671: existing generic execution consumers

Own execution_episodes.py, practical_execution_operations.py and
execution_progress.py; new tests671 and its evidence directory. Do not edit
root's tool-info file,668 producer/context/worker,667 views,669 publication/
results/returns, communication.py, historical schema literals or prompts.
Read complete affected methods and their consumers, not just search snippets.

ExecutionEpisodes assignment_schema('results') must explicitly admit the v1/v2
selector union under the exact two version tags; _utility_selector must agree.
Use shared validate_blast_utility_result_selector with the exact original
operation. Existing catalog/execute/fact/reference/return/credit/completion
routes must reach669 for v2 just as v1. Keep explicit artifact grants, new logical
namespaces and original target/commission checks; no generic-source fallback
may widen delivery. Use existing fourteen fact-source registration and versioned
facts, preserving empty new fields on old bodies. Do not add keys to old bodies.

Practical execution uses the common job-v3 validator and root's exact bound
variant acceptance, with unchanged local policy/allocation identity. Trace its
plan/handle/output/observe/read/execute methods. V3 uses simple two-stream output
specs, not v2 materializations or prepared-database projection. Inspect code for
v1/v2-only predicates and change only conditions required by the new contract.
Keep raw utility bytes behind result collection, one original native attempt and
shared local lifecycle. No resource substitution, extra polling, scoring,
retries, observations or synthetic completion. Existing closed-writer capture
success/failure distinctions and immediate exact future zero remain unchanged.

Execution progress exposes the actually supported result selector schema and
formats for the original program/mode/job version. Update only deterministic
capability/descriptor fields where needed; preserve existing generic resource
TASK/STEERING text and monitoring credit. Report any necessary prompt wording
as a separate draft, not a production edit. Existing v1/v2 output/info semantics
remain exact. Information does not establish successful native execution.

Tests use real configured ExecutionEpisodes, practical assignment validation,
actual selector dispatch, requested-input checks and original source/artifact
scope. Valid v3 assignments route; wrong resource, software, variants, allocation,
operation-selector version, original-input identities and handoff must reject
before execution. Preserve old configured mode tests. Controlled worker fixtures
must be labeled; no fabricated native scientific evidence or actual VDB run.
Root separately owns the real tiny-fixture native/Workflow test and historical
actual652/654 replay after integration. No operation-count increment from these
controlled tests alone.

## Verification and preservation

All application imports/tests/native/data-content work stays in bounded529,
20 GiB RAM/4 GiB scratch/zero swap/no wall cap, explicit check005 dependencies.
671 uses check128_vdb_episode671 (suffix each failed/changed attempt); root670
uses check129_vdb_tool_info670. Collect authoritative handles; never resubmit
because observation expired. Keep all failed attempts and frozen source pins.
No local database BLAST. No SSH/HPC/authentication guess and no new download.

Reread the original attachment objective and full OPERATING PRINCIPLES after
each bioinformatics tool/substantial native or external reading. Reread this
port and664/665 before declaring completion. Report actual paths, cases, native
scope, missing variants/resources and numerical authority precisely. This port
is not a runtime reviewer, permission mechanism or completion gate.
