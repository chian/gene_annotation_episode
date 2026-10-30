"""Seal this bounded source implementation and its actual engineering proof."""
raise SystemExit("Historical note-governed artifact generator retired.")

from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE.parent

def fp(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
freeze=json.loads((HERE/'PRODUCTION_FREEZE_002.json').read_text())
assert all(fp(ROOT/name)==value for name,value in freeze['files'].items())
assert fp(ROOT/'gene_annotation_episode/literature_controlled_response_owner_calculations.py')==freeze['owner076']
assert freeze['owner076']['sha256']=='88399f65c495ca6800daf2a64237c7cfe0be481e349424ad1c03e1509969a546'
result=json.loads((HERE/'PIN_TEST_RESULT_002.json').read_text());assert result['exit_code']==0
receipt=json.loads((HERE/'PIN_EXECUTION_RECEIPT_002.json').read_text())
assert receipt['all_project_imports_in_pin'] and receipt['pin_bytes_unchanged'] and receipt['actual_full_source_cases']==14
put('FAILURE_AND_CORRECTION_HISTORY_002.json',[
 dict(stage='initial actual source graph',record='INITIAL_GRAPH_ORIGIN_FAILURE_001.txt',actual='old068 rejected synthetic origin plus actual graph interval',correction='Root separately released and accepted076; source keeps truthful origin and all actual063 bounds'),
 dict(stage='initial cleanup implementation',record='tool transcript only; no full retained stdout file',actual='56 old008 tests failed because cleanup treated _Inputs.sources dict as a _Sources instance',correction='Clear the actual dictionary; subsequent69 unchanged tests passed'),
 dict(stage='first broad source run',record='INITIAL_V2_TESTS_001.txt',actual='82 passed/3 failed: full-field CI selection, saved unsupported display and duplicate-label test reanchor',correction='Deterministic exact CI subspan adapter, original unsupported display semantics, exact structural label tokens'),
 dict(stage='first canonical persisted JSON probe',record='OBJECT_ORDER_FAILURE_002.txt',root_record='controlled_full_source_parent_review_069/OBJECT_ORDER_COUNTEREXAMPLE_052.json',actual='Original saved extraction passed; canonical object ordering failed at empty_condition0 diagnostic aggregation',correction='v2 aggregate diagnostic sets canonicalized; scientific arrays and exact063 records retained'),
 dict(stage='first reversed object correction',record='OBJECT_ORDER_CORRECTION_TEST_002.txt',actual='14 passed/5 failed because saved063 literal witness array was rebuilt by dictionary insertion order',correction='Rebuild in063 first/second/unit order; check complete graph source set while preserving original array'),
 dict(stage='unavailable scientific source canonical partial',record='PARTIAL_CANONICAL_TEST_004.txt',actual='3 passed/1 failed due reused unavailable span diagnostic fields',correction='Shared saved witness stage reconstructs each actual field as live reading does'),
 dict(stage='historical008 incidental bytecode cache',root_record='controlled_full_source_parent_review_069/IMMUTABLE008_CACHE_RESTORATION_052.json',actual='A single importlib-generated cache file was written; historical source SHA stayed816868d1c70f97f2b7c67e9206bedf902fca4e55ad33a609a6603da1af1ffb9e',correction='Root recorded and removed only that generated cache; tests now compile immutable baseline in memory; both pin runners disable bytecode'),
 dict(stage='pre-correction pin001',record='PIN_TEST_RUN_001.txt',actual='603 focused tests/14 actual full-source cases/14 detached cases/15 in-pin imports passed',qualification='Preserved pre-object-order generation; does not establish the later canonical persistence obligations'),
 dict(stage='final pin002',record='PIN_TEST_RUN_002.txt',actual='625 focused tests/14 actual full-source cases/14 detached cases PLUS14 canonical persisted JSON cases/15 in-pin imports passed',correction='Final coherent source generation; no source callback/decoder/count/population in saved validation')])
authorities=['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md',
 'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
 'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
 'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md','research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
 'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md','research/experimental_scoring_review_2026-10-23/AGENTS.md',
 'docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md']
contracts=['PROPOSAL_001.md','IMPLEMENTATION_AND_NATIVE_HANDOFF_001.md','TASK_AND_EXTRACTION_TRACE_001.md','FINAL_HANDOFF_001.md',
 'PRESERVATION_SCOPE_ADDENDUM_004.md','V3_ORIGIN_AND_IDENTITY_LIMITS_003.md','V3_PARTIAL_RESULTS_ADDENDUM_002.md',
 'API_001.json','SELECTION_SCHEMA_V2_001.json','EXTRACTION_SCHEMA_V2_001.json','build_declarations_001.py','build_constructed_examples_001.py']
put('READ_PROVENANCE_002.json',dict(first_read='/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt',
 second_read='controlled_full_source_parent_review_069/SOURCE_STAGE_IMPLEMENTATION_RELEASE_073.md',
 authorities={p:fp(ROOT/p) for p in authorities},contracts={p:fp(BASE/'a105_controlled_full_source_design_069'/p) for p in contracts},
 implementation_consumers='Complete original008 source/saved validator and tests; actual063 graph reader and tests; actual068/076 owner and006 arithmetic; source/unit/count/CI/visual helpers. Original graph/source/calculator production consumer search found no installed controlled-response native route.',
 reading_qualification='Some initial concatenated tool reads were truncated; later sequential complete sections filled omitted implementation/authority portions during this task. This records actual task inspection, not a claim that every helper was read before the first edit.',
 no_paper_or_retained_scientific_packet_opened=True,no_postpaper_reset_triggered=True,no_prompt_model_or_episode_change=True))
old_reader=BASE/'a105_controlled_response_design_056/implementation_stage_008/final_snapshot_008/gene_annotation_episode/literature_controlled_response_inputs.py'
assert fp(old_reader)['sha256']=='816868d1c70f97f2b7c67e9206bedf902fca4e55ad33a609a6603da1af1ffb9e'
assert not (old_reader.parent/'__pycache__').exists()
put('FINAL_PRESERVATION_CHECK_002.json',dict(owned_production_matches_final_pin=True,owned_files=freeze['files'],owner076=freeze['owner076'],
 original008_source=fp(old_reader),original008_generated_cache_absent=True,
 declared_v1_dependencies_unchanged=True,legacy_domain_drift_record='LEGACY_DEPENDENCY_COMPARISON_002.json',
 historical_payloads_rewritten=False,qualification='Root separately restored the one incidental generated historical cache; this task made no source/payload edits outside its three assigned code/test files. Existing untracked workspace drift is not a Git baseline.'))
text='''# Full controlled-response source reader073 — final002 handoff

Tranche S is implemented in the assigned shared source module, NEW v2 module and
NEW v2 test. No native catalog/storage/service/prompt/runtime/credit/controller,
paper, model/provider, HPC, workflow or live-run action was performed. This is
constructed source text/pixels and deterministic arithmetic. The full literature
objective remains incomplete.

The exact061 request and exact069 closed extraction are produced by compact
production constructors, with equality tests against the declarations. Six HOST
stages retain shared meaning, uncertainty, full original-N covariance and saved
science. V1 keeps its original four APIs, __all__, schema/results/dependencies,
legacy alias interpretation and saved-validation errors. Its legacy-specific
error/check order is deliberately retained rather than silently strengthened.
New-v2 reads real063 measurements before shared spread/unit/C assembly and emits
actual068 owner inputs. It never calls a sheet populator. No v1-null envelope,
post-hoc graph injection, dummy source values or independent meaning reparse was
introduced.

SourceContext prefetches every original closure pair once before geometry, with
cross-pair artifact alias rejection. All nominated witnesses are authenticated.
Unexpected/authorization/malformed callbacks propagate; declared availability
partials retain the original cached exception. EOF is translated to EIO only at
063's cache boundary. Context close releases frames/source caches on all exits.
No callback survives in a saved record.

The full original source-N lexer, exact symmetry/PSD and token/owner bindings
precede provided-owner projection. All original rows remain retained; duplicate
labels and normalized full-row aliases are checked. Missing canceled numbers,
mean units or bindings do not erase A/C support. Actual A/C-only C differs from
partial bindings of full valid C and from invalid full C. Unknown active owners
keep covariance incomplete even when all listed known IDs are covered. Both row
and column unit factors apply. Source and finite-matrix precision/range limits
remain distinct. Scientific owner/applicability conflict remains separate from
unused canceled numeric disagreement.

Graph units precede SD/CI arithmetic and printed-unit checks. The v2 CI adapter
uses only the explicitly nominated numbers and their exact enclosing bracket
span inside a selected full field; it preserves the original selection/witness.
SD1.2 nmol/min becomes.0012 umol/min; CI[8,12] becomes[.008,.012], with confidence,
count/repetition/fit meanings kept separate. Pixel domains are not sampling
uncertainty and create no covariance/model. Synthetic source origin takes
precedence in calculator operands while COMPLETE063 graph_details/measurement
remain byte-for-byte the actual graph output (including graph-derived method).
Root's separately accepted076 correction now permits these truthful synthetic
interval inputs without changing006/v1. HAND069 graph origins were illustrative,
not normative reader outputs.

Detached validation uses the shared saved-science entry and supplied text/graph
measurement checks. It verifies closure, source/image/locator/science/unit/spread,
original-N C, owner projection, model and exact actual input relationships. It
rebuilds063's original identity_record with exact sort_keys/ensure_ascii/allow_nan
serialization. It performs retained arithmetic without callbacks, native literal
readers, image decode/count, models, canonical reselection or sheet population.
It does not prove pixels from a digest or authenticate a replaced whole source
record; native original-outcome custody remains subsequent work.

JSON object order is not scientific meaning. Only v2 aggregate diagnostic SETS
use deterministic ordering; original063 records and scientific arrays retain
their actual order. Primitive-owner role grouping uses fixed PRIMITIVE_ORDER.
Original/canonical/reversed request and saved-object tests cover these boundaries,
including unavailable source-science partials. Original v1 diagnostic ordering
remains exact.

Final coherent pin002:625 tests passed in43.06s across the new125-case source suite
and unchanged/source-adjacent graph, owner and006 suites. Fifteen actual project
imports resolved inside the38-file pin, whose hashes remained unchanged. All14
constructed cases ran the ACTUAL full new source reader then the SEPARATE
076-corrected068 populator. All14 saved outputs also passed detached sentinel
checks in original form and canonical persisted JSON. Pin001's603 tests and
outputs are preserved as a pre-object-order generation; they are not the final
persistence proof. Tests overlap prior work and are not625 scientific observations.

Actual example: A10,C8 nmol/min with one known shared B represented as reported4
and graph4.05[3.95,4.15] gives e.002 umol/min,V3e-7(umol/min)^2,
S6.666666666666667,B.9974579674738373 under explicit synthetic known-normal
source premises. Both B numbers/units absent or B4-versus5 canceled numeric
conflict retain those values with qualifiers. Real scientific owner conflict
makes e/V unavailable. Active graphical A gives e.00205,V3e-7,reported SD.0012
or CI[.008,.012], while S/B remain unavailable. Invalid full C keeps e.002 and
leaves V unavailable. These are engineering measurements, not primary evidence.

Artifacts: ACTUAL_SOURCE_OUTPUTS_002.json contains complete actual extractions
and sheets; NUMERICAL_TABLE_002.json summarizes numerical cells, spread and owner
dependencies. PIN_EXECUTION_RECEIPT_002.json proves imports; PIN_TEST_RUN_002.txt,
DETACHED_SAVED_VALIDATION_002.json, ENVIRONMENT_002.json and PIN_MANIFEST_002.json
record execution. IMPLEMENTATION_002.patch is the exact three-file delta from
the retained shared before-file plus the two new paths. PRODUCTION_FREEZE_002.json
binds final code/test and076. MANIFEST_002.json and SHA256SUMS_002.txt seal all
owned payloads. No Git baseline is claimed.

Genuine failures and their corrections are preserved in
FAILURE_AND_CORRECTION_HISTORY_002.json and referenced logs, including root's
canonical-JSON counterexample. One initial importlib baseline load also wrote a
single bytecode cache into immutable008; root recorded/removes only that generated
cache in IMMUTABLE008_CACHE_RESTORATION_052.json. Historical source payload SHA
remained816868d1c70f97f2b7c67e9206bedf902fca4e55ad33a609a6603da1af1ffb9e.
The final baseline loader uses in-memory compile/exec; both pin runners disable
bytecode. Current domain.py differs from original008/063 (actualc76c6edd… versus
historicalccfacc70…); this is explicit outside-owner drift, not a hidden pin rewrite.
Every original declared008 helper dependency remains unchanged. New v2 dependencies
bind actual shared/new/graph/076 code plus declared existing helpers.

REQUIRED remaining work: v3 active companions, source-supported JOINT alternatives,
accepted active-reconciliation policy, authentic mixed-origin/group identities,
component-local native partial delivery when full068 projection is unsupported,
and corresponding declared source/native contracts. No unresolved primary-only
sheet is presented as a final reconciled result. Native selected storage/service/
catalog/binding, actual C1/C4 typed admission, requested subsets and parent use,
source-free runtime reconstruction, original outcome custody, primary-source and
configured-model scientific execution remain unimplemented/unverified here.
A101/target correspondence, W05 aggregation and all ten-axis completion remain
outside this bounded source tranche. No new episode/route/itinerary/controller
observation or scientific credit is introduced.
'''
with (HERE/'HANDOFF_002.md').open('x') as f:f.write(text)
files={str(p.relative_to(HERE)):fp(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ('MANIFEST_002.json','SHA256SUMS_002.txt')}
put('MANIFEST_002.json',dict(scope='Final073 source tranche; all owned payloads including historical failed/pre-correction generations; no native/scientific-completion claim',files=files))
checks={**{name:row['sha256'] for name,row in files.items()},'MANIFEST_002.json':fp(HERE/'MANIFEST_002.json')['sha256']}
with (HERE/'SHA256SUMS_002.txt').open('x') as f:
    f.writelines(digest+'  '+name+'\n' for name,digest in sorted(checks.items()))
print(json.dumps(dict(payloads=len(files),sha_lines=len(checks),manifest_sha256=checks['MANIFEST_002.json'],focused_tests=625,actual_source_cases=14)))
