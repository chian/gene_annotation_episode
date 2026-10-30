"""Record actual integration evidence; never changes goal or historical records."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path.cwd()
PACKET = Path('verification/tool_graders_blast_masking_integration_2026-10-28_619')
RUNNER = Path('verification/tool_graders_hmmer_map_verification_2026-10-28_529')
now = datetime.now(timezone.utc).isoformat()

def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}

def save(path, value):
    path = Path(path)
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def check(name, qualification):
    directory = RUNNER/name
    receipt = json.loads((directory/'receipt.json').read_text())
    audit = json.loads((directory/'execution_audit.json').read_text())
    suites = list(ET.parse(directory/'junit.xml').getroot().iter('testsuite'))
    totals = {key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ('tests','errors','failures','skipped')}
    totals['passed'] = totals['tests']-totals['errors']-totals['failures']-totals['skipped']
    return {'attempt':name, 'result':totals, 'receipt':pin(directory/'receipt.json'),
        'execution':{k:receipt[k] for k in ('returncode','terminal','quiescent','source_unchanged','dependency_unchanged','stdlib_unchanged','binary_unchanged')},
        'audit':audit, 'case_reports':pin(directory/'case_reports.jsonl'), 'qualification':qualification}

checks = [
 check('check074_masking_workflow','Three actual native masking modes reached both requested parent returns. Six permission/accounting/replay checks passed. Three number checks expected nonexistent Components.operation; three counts fixture setup errors inserted fa_list although the compiler already fixes the single-FASTA flag. No production repair was needed for these test failures.'),
 check('check080_masking_workflow_counts_and_saved','Three corrected numerical assertions read the original074 retained artifacts without native work/calculation. One previously unlaunched tiny Window counts command passed all three full Workflow checks. Four original modes are covered across these two immutable attempts; no successful masking command was repeated.'),
 check('check082_masking_saved_status','Historical focused fixture failure forbade the saved custody validator as well as fresh capture. Production saved-status correction already present. This run is not final verification.'),
 check('check083_masking_saved_status_final','Corrected focused saved-status check forbids actual native observation, native-file capture, preparation and projection, while retaining original-custody validation. No native masking command. Saved status returns original observation, no acquisition grant, no duplicate credit and no false completion.'),
]
names = ['sequence_masking_contracts.py','sequence_masking_inputs.py','sequence_masking_calculations.py','windowmasker_statistics.py',
 'native_blast_masking_contracts.py','native_blast_masking_tool_info.py','native_blast_masking_driver.py','native_blast_masking_local.py','native_blast_masking_acquisition.py',
 'sequence_masking_result_views.py','native_blast_masking_result_worker.py','native_blast_masking_result_publication.py','native_blast_masking_results.py','native_blast_masking_returns.py',
 'execution_episodes.py','communication.py','episode_receipts.py','practical_execution_records.py','practical_execution_operations.py','execution_progress.py']
source_pins = [pin(Path('gene_annotation_episode')/name) for name in names]
snapshot_matches = {}
for attempt in ('check074_masking_workflow','check080_masking_workflow_counts_and_saved','check083_masking_saved_status_final'):
    snapshot_matches[attempt] = {r['path']:Path(r['path']).read_bytes()==(RUNNER/attempt/'source_snapshot'/r['path']).read_bytes() for r in source_pins}
worker_pin_checks=[]
for dirname, filename, key in (
 ('tool_graders_blast_masking_results_2026-10-28_616','HANDOFF_MANIFEST_005.json','owned_files'),
 ('tool_graders_blast_masking_host_returns_2026-10-28_617','HANDOFF_MANIFEST_004.json','files'),
 ('tool_graders_blast_masking_resource_wiring_2026-10-28_618','HANDOFF_MANIFEST_005.json','production_files')):
    manifest=Path('verification')/dirname/filename
    data=json.loads(manifest.read_text())
    worker_pin_checks.append({'manifest':pin(manifest),'checks':{r['path']:pin(r['path'])['sha256']==r['sha256'] for r in data[key]},
      'qualification':'The results host differs from617 final only by the root623 saved-status branch correction, verified083.' if '617' in dirname else 'Original owned source and contract pins checked.'})
verification={'record_type':'root_masking_workflow_integration_verification','recorded_at':now,
 'authority':pin('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt'),
 'checks':checks, 'source_pins':source_pins,'snapshot_matches':snapshot_matches,'worker_manifest_checks':worker_pin_checks,
 'new_native_commands':{'dustmasker_mask':1,'segmasker_mask':1,'windowmasker_mask':1,'windowmasker_create_counts':1},
 'verified_path':['scientific_process','launch','launch_local','results','scientific_process_return','annotation_return'],
 'verified_selected_mode_paths':4,'utilities_with_verified_selected_local_paths':3,
 'native_examples':{'dustmasker':[[80,80],[0,32],[72,72]],'segmasker':[[64,64],[0,20],[32,72]],'windowmasker':[[80,80],[0,32],[0,4]]},
 'credit':{'scientific':0,'annotation':0,'selected_local_launch_fixture_unit':7,'selected_handoff_fixture_unit':3,'first_acquisition_fixture_unit':2,'saved_status':0},
 'accounting':'One own observation per selected completed action; completing practical action retained and next expected gain exact zero without extra model/zero turn.',
 'permission_path':'Results returned selected measurements/artifacts/saved data to their scientific parent; narrower scientific return supplied only status/quantities/statistics to root. Root did not gain auxiliary artifacts. Native paths were removed before frozen replay; histories and receipts stayed unchanged.',
 'remaining':['Concrete result-decision and scientific-parent message rendering requires user feedback and implementation; current generic JSON/raw-field fallback is not settled.', 'No post-results scientific model decision was exercised: fixture scientific horizon was two; typed final forwarding was verified.', 'No API/HPC masking deployment or general remote binding is claimed.', 'Other ten R7 utilities remain unfinished;620 is defining their boundaries.'],
 'complete_inventory_increment':0,'all_R1_through_R7_remain_open':True}
save(PACKET/'ROOT_VERIFICATION_003.json',verification)

previous=Path('verification/tool_graders_shared_search_integration_2026-10-28_586/OPERATION_LINK_UPDATE_001.json')
old=json.loads(previous.read_text());rows=old['combined_rows']
new_rows=[
 {'key':'raw_sequence_masking','label':'Raw sequence masking extent','classification':'supporting_preparation_numerical_and_validation',
  'sheet_authority':'sequence_masking_sheet_v1','reader_authority':'sequence_masking_inputs.populate_sequence_masking_sheet',
  'calculator_authority':'sequence_masking_calculations.calculate_sequence_masking_components',
  'shared_components':['hmmer_search_grader._union','genomic_overlap_calculations._ratio'],
  'operation_names':['native.dustmasker.mask','native.segmasker.mask','native.windowmasker.mask'],
  'linked_name_count':3,'evidence_source':str(PACKET/'ROOT_VERIFICATION_003.json'),
  'meaning':'Input lengths, native/merged intervals, changed/masked/unmasked positions and masked fractions; not annotation confidence.'},
 {'key':'windowmasker_reference_statistics','label':'WindowMasker native reference statistics',
  'classification':'typed_extraction_and_validation_without_independent_calculator','sheet_authority':'windowmasker_statistics_v1',
  'reader_authority':'windowmasker_statistics.parse_windowmasker_statistics','validator_authority':'windowmasker_statistics.validate_windowmasker_statistics',
  'calculator_authority':[],'operation_names':['native.windowmasker.mask','native.windowmasker.create_counts'],
  'linked_name_count':2,'evidence_source':str(PACKET/'ROOT_VERIFICATION_003.json'),
  'meaning':'Native unit counts, percentile rows, reported thresholds and original reference associations; no invented scoring.'},
]
assert not {r['key'] for r in new_rows}&{r['key'] for r in rows}
rows=rows+new_rows
names_all=sorted({n for r in rows for n in r['operation_names']})
typed=[r for r in rows if r.get('classification')=='typed_extraction_and_validation_without_independent_calculator']
nums=[r for r in rows if r not in typed]
numerical_names=sorted({n for r in nums for n in r['operation_names']})
census={'record_type':'additive_shared_grader_operation_links','recorded_at':now,'previous_census':pin(previous),
 'added_groups':new_rows,'combined_rows':rows,'shared_groups':len(rows),'numerical_groups':len(nums),'typed_only_groups':len(typed),
 'linked_numerical_groups':sum(bool(r['operation_names']) for r in nums),'linked_typed_only_groups':sum(bool(r['operation_names']) for r in typed),
 'operation_name_links':sum(len(r['operation_names']) for r in rows),'distinct_operation_names':len(names_all),'operation_names':names_all,
 'distinct_numerically_linked_operation_names':len(numerical_names),'numerically_linked_operation_names':numerical_names,
 'unlinked_numerical_groups':[r['key'] for r in nums if not r['operation_names']],
 'source_pins':source_pins,'qualification':'Existing586 mapping inherited explicitly; only the newly integrated masking links are added and verified this turn. Counts are shared implementations and named operation/mode links, not wholly completed307inventory rows. Typed statistics are separate from numerical graders.',
 'new_completed_full_inventory_rows':0}
assert (census['shared_groups'],census['numerical_groups'],census['typed_only_groups'],census['operation_name_links'],census['distinct_operation_names'])==(47,45,2,138,125)
save(PACKET/'OPERATION_LINK_UPDATE_004.json',census)

status_packet=Path('verification/tool_graders_masking_saved_status_2026-10-28_623')
p=Path('gene_annotation_episode/native_blast_masking_results.py')
diff=''.join(difflib.unified_diff((status_packet/'native_blast_masking_results.py.before.txt').read_text().splitlines(True),p.read_text().splitlines(True),fromfile='before/'+p.name,tofile=str(p)))
(status_packet/'REPAIR_002.diff').write_text(diff)
save(status_packet/'VERIFICATION_003.json',{'recorded_at':now,'specific_repair':'Allow the advertised saved-recalculation status selection to find the original retained observation before validating its received sheet. Fresh native status and collect behavior retain existing ownership.',
 'source':pin(p),'test':pin('tests/test_native_blast_masking_saved_status_623.py'),'checks':checks[2:],'scientific_native_commands':0,'score_formula_changes':False,'prompt_changes':False})
print(json.dumps({k:census[k] for k in ('shared_groups','numerical_groups','typed_only_groups','linked_numerical_groups','linked_typed_only_groups','operation_name_links','distinct_operation_names','distinct_numerically_linked_operation_names','unlinked_numerical_groups')},indent=2))
