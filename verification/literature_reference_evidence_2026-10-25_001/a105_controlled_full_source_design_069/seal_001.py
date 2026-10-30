"""Seal only the owned069 design payload; all other paths are read-only."""
raise SystemExit("Historical note-governed artifact generator retired.")

import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE.parent

def entry(path):
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")

authorities=[
    'AGENTS.md','GOAL.md','research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md',
    'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md','docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md']
implementations=[
    'literature_controlled_response_inputs.py','literature_controlled_response_figure_inputs.py',
    'literature_controlled_response_owner_calculations.py','literature_controlled_response_calculations.py',
    'literature_experimental_contracts.py','literature_rate_native_inputs.py','literature_rate_storage.py',
    'literature_episodes.py','episode_services.py','literature_experimental_prompt.py',
    'literature_reference_parent_prompt.py','literature_binding_interaction_render.py',
    'episode_composition.py','independent_execution.py']
attachment=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
write('READ_PROVENANCE_001.json',dict(active_attachment_read_first=dict(path=str(attachment),**entry(attachment)),
    complete_authorities={p:entry(ROOT/p) for p in authorities},
    complete_relevant_implementations={p:entry(ROOT/'gene_annotation_episode'/p) for p in implementations},
    no_paper_or_retained_paper_packet_opened=True,no_post_paper_reset_triggered=True,
    limits='Additional declaration/proposal files were read as described in handoff. Large runtime.py/state.py and entire test suites were not inspected or executed. Hash records are current byte identities, not independent proof of reading.'))

checks=[]
for name,key in [('a105_controlled_response_design_056/implementation_stage_008/PIN_MANIFEST_008.json','pin_files'),
    ('a105_controlled_graph_reader_063/PIN_MANIFEST_003.json','files'),
    ('a105_controlled_owner_calculator_068/PIN_MANIFEST_002.json',None)]:
    document=json.loads((BASE/name).read_text()); records=document[key] if key else document
    if isinstance(records,list): records={v['path']:v for v in records}
    tested={}
    for rel,expected in records.items():
        path=ROOT/rel
        if not path.is_file():continue
        actual=entry(path)
        tested[rel]=dict(expected=expected['sha256'],actual=actual['sha256'],equal=expected['sha256']==actual['sha256'])
    checks.append(dict(manifest=name,checked_current_files=tested))
mismatches=[dict(manifest=check['manifest'],path=rel,**row) for check in checks for rel,row in check['checked_current_files'].items() if not row['equal']]
assert all(row['path']=='gene_annotation_episode/domain.py' for row in mismatches)
write('READ_ONLY_PIN_CHECK_001.json',dict(checks=checks,all_checked_files_match=not mismatches,
    controlled_source_graph_calculator_and_other_checked_pin_files_match=True,outside_owner_current_checkout_mismatches=mismatches,
    claim='All checked entries except current domain.py match recorded008/063/068 bytes. The domain mismatch is outside this owner and was not repaired; historical pins remain unchanged.'))
write('EXECUTION_RECEIPT_001.json',dict(
    successful_command='PYTHONDONTWRITEBYTECODE=1 .venv/bin/python verification/literature_reference_evidence_2026-10-25_001/a105_controlled_full_source_design_069/verify_declarations_001.py',
    check_result='DECLARATION_CHECK_001.json',retained_initial_reconstruction_failure='DECLARATION_RECONSTRUCTION_INITIAL_FAILURE_001.json',
    arithmetic='Fourteen HAND source projections plus active companion conditional/partial HAND inputs executed through actual accepted068. Reconstruction re-executes those same engineering constructions and compares13 generated payloads byte-for-byte; it creates no independent scientific evidence.',
    new_source_reader_executed=False,source_decoder_executed=False,new_production_tests_executed=False,
    workflow_executed=False,model_called=False,primary_source_evidence=False,native_or_typed_delivery_proved=False,
    source_or_test_mutations=False,full_goal_complete=False))
excluded={'MANIFEST_001.json','SHA256SUMS_001.txt'}
files={str(p.relative_to(HERE)):entry(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in excluded}
manifest=dict(status='sealed_design_only_not_implementation',file_count=len(files),files=files,
    authority_order=['PROPOSAL_001.md','V3_PARTIAL_RESULTS_ADDENDUM_002.md','V3_ORIGIN_AND_IDENTITY_LIMITS_003.md','PRESERVATION_SCOPE_ADDENDUM_004.md'],
    whole_goal_complete=False)
write('MANIFEST_001.json',manifest)
rows=[f"{v['sha256']}  {name}" for name,v in files.items()]
rows.append(f"{entry(HERE/'MANIFEST_001.json')['sha256']}  MANIFEST_001.json")
(HERE/'SHA256SUMS_001.txt').write_text('\n'.join(rows)+'\n')
print(json.dumps(dict(payload_files=len(files),sha_lines=len(rows),manifest_sha256=entry(HERE/'MANIFEST_001.json')['sha256'],
    controlled_source_graph_calculator_pins_match=True,outside_owner_domain_mismatches=len(mismatches))))
