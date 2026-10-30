"""Seal only this new design directory; read-only preservation checks elsewhere."""
raise SystemExit("Historical note-governed artifact generator retired.")

from pathlib import Path
import hashlib
import importlib.metadata as md
import json
import platform
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=HERE.parent
sys.dont_write_bytecode=True

def fp(p):
 raw=p.read_bytes();return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
authorities=[
 '/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt',
 'AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md',
 'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
 'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
 'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
 'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
 'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md',
 'research/experimental_scoring_review_2026-10-23/AGENTS.md']
reads={str(Path(n) if n.startswith('/') else ROOT/n):dict(**fp(Path(n) if n.startswith('/') else ROOT/n),read_extent='complete',hash_timing='at_seal_not_a_read_time_snapshot') for n in authorities}
relative_reads=[
 'controlled_full_source_parent_review_069/V3_DESIGN_RELEASE_078_053.md',
 'controlled_full_source_parent_review_069/SOURCE_STAGE_IMPLEMENTATION_RELEASE_073.md',
 'controlled_full_source_parent_review_069/OWNER_SYNTHETIC_GRAPH_REPAIR_RELEASE_076.md',
 'a105_controlled_full_source_design_069/PROPOSAL_001.md','a105_controlled_full_source_design_069/API_001.json',
 'a105_controlled_full_source_design_069/V3_PARTIAL_RESULTS_ADDENDUM_002.md',
 'a105_controlled_full_source_design_069/V3_ORIGIN_AND_IDENTITY_LIMITS_003.md',
 'a105_controlled_full_source_design_069/PRESERVATION_SCOPE_ADDENDUM_004.md',
 'a105_controlled_full_source_design_069/build_declarations_001.py',
 'a105_controlled_full_source_design_069/IMPLEMENTATION_AND_NATIVE_HANDOFF_001.md',
 'a105_controlled_full_source_design_069/TASK_AND_EXTRACTION_TRACE_001.md',
 'a105_controlled_source_reader_073/HANDOFF_002.md',
 'a105_controlled_source_reader_073/run_pin_002.py','a105_controlled_source_reader_073/probe_actual_001.py',
 'a105_owner_synthetic_graph_repair_076/HANDOFF_001.md',
 'controlled_full_source_parent_review_069/verify_source_cases_052_002.py']
for n in relative_reads:reads[str(BASE/n)]=dict(**fp(BASE/n),read_extent='complete',hash_timing='at_seal_not_a_read_time_snapshot')
code_reads=['gene_annotation_episode/literature_controlled_response_inputs.py','gene_annotation_episode/literature_controlled_response_v2_inputs.py',
 'gene_annotation_episode/literature_controlled_response_figure_inputs.py','gene_annotation_episode/literature_controlled_response_owner_calculations.py',
 'gene_annotation_episode/literature_controlled_response_calculations.py','tests/test_literature_controlled_response_v2_inputs.py',
 'tests/test_literature_controlled_response_owner_calculations.py','gene_annotation_episode/literature_rate_storage.py',
 'gene_annotation_episode/literature_binding_interaction_render.py','gene_annotation_episode/literature_episodes.py']
for n in code_reads:reads[str(ROOT/n)]=dict(**fp(ROOT/n),read_extent='complete',hash_timing='at_seal_not_a_read_time_snapshot')
put('READ_PROVENANCE_006.json',dict(active_goal_read_first=authorities[0],release_read_second=str(BASE/relative_reads[0]),
 authorities_and_complete_paths=reads,
 exact_declaration_read='Complete compact069 constructor plus production v2/owner constructors; entire old expanded schemas parsed by actual new constructor and complete structural equality checks against production constructors',
 latest_root_steering_read='007ownership clarification and006shared/native source/schema requirements incorporated additively',
 paper_or_retained_paper_packet_read=False,post_packet_reset_triggered=False,
 actual_sources='Constructed069 bytes/pixels and new explicitly constructed coupled-source clauses only',
 limitation='Does not assert a complete fresh runtime.py/state.py/episode_services/composition/prompt-consumer read; future changed consumers must be read by their released owners'))
checks=[]
def check_map(directory,manifest):
 for name,v in manifest.items():
  actual=fp(directory/name)
  expected=v if isinstance(v,dict) else {'sha256':v}
  assert all(actual[k]==value for k,value in expected.items()),(directory,name)
 return len(manifest)
old069=BASE/'a105_controlled_full_source_design_069'
checks.append(dict(scope=str(old069),files=check_map(old069,json.loads((old069/'MANIFEST_001.json').read_text())['files']),matches_original_manifest=True))
p073=BASE/'a105_controlled_source_reader_073'
checks.append(dict(scope=str(p073/'pin_002'),files=check_map(p073/'pin_002',json.loads((p073/'PIN_MANIFEST_002.json').read_text())),matches_original_manifest=True))
p076=BASE/'a105_owner_synthetic_graph_repair_076'
checks.append(dict(scope=str(p076/'pin_001'),files=check_map(p076/'pin_001',json.loads((p076/'PIN_MANIFEST_001.json').read_text())),matches_original_manifest=True))
put('PROTECTED_READ_ONLY_CHECK_008.json',dict(checks=checks,asserts_other_owners_checkout_unchanged=False))
put('ENVIRONMENT_008.json',dict(python_executable=sys.executable,real_python_executable=str(Path(sys.executable).resolve()),
 executable_identity=fp(Path(sys.executable).resolve()),python_version=sys.version,platform=platform.platform(),
 distributions={n:md.version(n) for n in ['jsonschema','Pillow','pytest']},environment_vendored=False,
 bytecode_disabled=True,network_or_models=False))
# Seven schemas plus API, complete numeric proof and source data are already saved.
assert json.loads((HERE/'DESIGN_VERIFICATION_006.json').read_text())['schema_count']==7
manifest={str(p.relative_to(HERE)):fp(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['FINAL_MANIFEST_008.json','SHA256SUMS_008.txt']}
put('FINAL_MANIFEST_008.json',dict(status='design_only_no_production_release',file_count=len(manifest),files=manifest,
 final_schema_generation='006',final_schema_count=7,api_generation='006',latest_ownership_clarification='007',
 actual_v2_source_reads=20,actual_separate_existing_owner_sheets=20,actual_shared_scope_witness_authentications=2,
 local_API_implemented=False,v3_reader_implemented=False,production_writes=False))
lines=[f"{v['sha256']}  {n}\n" for n,v in manifest.items()]
lines.append(f"{fp(HERE/'FINAL_MANIFEST_008.json')['sha256']}  FINAL_MANIFEST_008.json\n")
with (HERE/'SHA256SUMS_008.txt').open('x') as f:f.writelines(lines)
print(json.dumps(dict(sealed_payload_files=len(manifest),checksum_lines=len(lines),final_schemas=7,protected=checks)))
