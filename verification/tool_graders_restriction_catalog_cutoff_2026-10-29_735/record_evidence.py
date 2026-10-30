"""Read original bounded verification metadata; stdlib only, no application."""
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
ATTEMPT=ROOT/'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check199_catalog735'
SOURCE=ROOT/'gene_annotation_episode/restriction_mapping_action_records.py'
TEST=ROOT/'tests/test_restriction_mapping_catalog_cutoff_735.py'
CONTRACT=ROOT/'verification/tool_graders_restriction_initial_catalog_2026-10-29_736/CONTRACT_001.md'


def pin(path):
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}


def write(name,value):
    (PACKET/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def methods(path):
    tree=ast.parse(path.read_text())
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef)
        and node.name=='RestrictionMappingActionRecords')
    return {node.name:ast.dump(node,include_attributes=False) for node in cls.body
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}


def record():
    receipt=json.loads((ATTEMPT/'receipt.json').read_text())
    audit=json.loads((ATTEMPT/'execution_audit.json').read_text())
    request=json.loads((ATTEMPT/'selected_request.json').read_text())
    rows=[json.loads(line) for line in (ATTEMPT/'case_reports.jsonl').read_text().splitlines()]
    counts=Counter(row['outcome'] for row in rows)
    assert receipt['terminal'] and receipt['quiescent'] and receipt['returncode']==0
    assert all(receipt[key] for key in ('source_unchanged','dependency_unchanged',
        'stdlib_unchanged','binary_unchanged','selected_stdlib_source_unchanged'))
    assert audit['outside_modules']==audit['unbound_mappings']==[]
    assert audit['native_unchanged'] and audit['original_retained_fixtures_unchanged']
    assert set(counts)=={'passed'}
    assert pin(SOURCE)['sha256']=='91e49c5b8a6284c7f372fc2240899698a11d00ddd4d887523ccbff380a2207d4'
    assert pin(SOURCE)['sha256']==pin(ATTEMPT/'source_snapshot'/SOURCE.relative_to(ROOT))['sha256']
    assert pin(TEST)['sha256']==pin(ATTEMPT/'source_snapshot'/TEST.relative_to(ROOT))['sha256']
    new=[row['nodeid'] for row in rows if 'test_restriction_mapping_catalog_cutoff_735.py' in row['nodeid']]
    old=[row['nodeid'] for row in rows if row['nodeid'] not in new]
    assert len(old)==2
    baseline=ROOT/'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check198c_declarations733/source_snapshot'
    earlier,current=methods(baseline/SOURCE.relative_to(ROOT)),methods(SOURCE)
    changes=sorted(key for key in earlier.keys()|current.keys() if earlier.get(key)!=current.get(key))
    assert changes==['_query','own_enzyme_reference']
    untouched=[]
    for name in ('restriction_mapping_contracts.py','restriction_mapping_readers.py',
        'restriction_mapping_returns.py','restriction_mapping_publication.py','restriction_mapping_jobs.py'):
        file=ROOT/'gene_annotation_episode'/name
        assert file.read_bytes()==(baseline/'gene_annotation_episode'/name).read_bytes()
        untouched.append(pin(file))
    value={'version':'restriction_catalog_cutoff_verification735_v1',
        'recorded_at':datetime.now(timezone.utc).isoformat(),
        'authority':pin(Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt')),
        'contract':pin(CONTRACT),'api':'own_enzyme_reference(context, reference, *, before_decision_index=None, through_receipt_index=None) -> bool',
        'source':pin(SOURCE),'test':pin(TEST),'trace':pin(PACKET/'TRACE_001.md'),
        'original_handle':pin(ATTEMPT/'handle.json'),'unit':receipt['unit'],
        'receipt':pin(ATTEMPT/'receipt.json'),'audit':pin(ATTEMPT/'execution_audit.json'),
        'audit_values':audit,'junit':pin(ATTEMPT/'junit.xml'),'stdout':pin(ATTEMPT/'stdout.txt'),
        'stderr':pin(ATTEMPT/'stderr.txt'),'selected_request':pin(ATTEMPT/'selected_request.json'),
        'case_reports':pin(ATTEMPT/'case_reports.jsonl'),
        'terminal':True,'quiescent':True,'all_five_pin_classes_unchanged':True,
        'case_counts':dict(counts),'new_component_case_count':len(new),
        'existing_regression_case_count':len(old),'new_component_cases':new,'existing_regression_cases':old,
        'policy':receipt['metadata']['policy'],'verified_cgroup':receipt['metadata']['verified_cgroup'],
        'selected_python_source_pin':request['selected_python_source_pin'],
        'selected_stdlib_source':request['selected_stdlib_source'],
        'changed_methods':changes,'unchanged_numerical_publication_and_job_authorities':untouched,
        'new_native_scientific_searches':0,'new_719_calculations':0,'external_model_network_calls':0,
        'original_scientific_stores_opened':False,'new_public_tool_info_or_prompt_or_credit_policy':False,
        'scope_limits':[
            'Original729 engineering authority seam only, no authentic native output or scientific measurement is fabricated.',
            'SQL/context/custody checks establish this bounded ActionRecords component; root736 owns original initial-form and complete Workflow receiving proof.',
            'No new ToolInfo/catalog installation, real public scientific path, configured model or resource deployment is established.',
            'No whole-tool/name/group coverage increment; all R1-R7 and FBA remain open.']}
    write('EVIDENCE_001.json',value)
    write('CASE_IDS_001.json',{'new_component_cases':new,'existing_regression_cases':old,
        'passed':len(rows),'failed':0})
    print(json.dumps({'new_component_cases':len(new),'existing_regressions':len(old),
        'total_passed':len(rows),'source_sha256':value['source']['sha256']}))


if __name__=='__main__':record()
