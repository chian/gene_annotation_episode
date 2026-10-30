"""Retained735/736 metadata only; no application import or scientific work."""
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
RUNNER=ROOT/'verification/tool_graders_hmmer_map_verification_2026-10-28_529'


def pin(path):
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}


def save(name,value):
    (PACKET/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def record():
    runs=[];passed={};failures=[]
    for name in ('check199_catalog735','check200_initial736','check200b_initial736','check200c_initial736'):
        path=RUNNER/name
        receipt=json.loads((path/'receipt.json').read_text())
        audit=json.loads((path/'execution_audit.json').read_text())
        request=json.loads((path/'selected_request.json').read_text())
        assert receipt['terminal'] and receipt['quiescent']
        assert all(receipt[k] for k in ('source_unchanged','dependency_unchanged','stdlib_unchanged',
            'binary_unchanged','selected_stdlib_source_unchanged'))
        assert audit['outside_modules']==audit['unbound_mappings']==[]
        assert audit['native_unchanged'] and audit['original_retained_fixtures_unchanged']
        rows=[json.loads(x) for x in (path/'case_reports.jsonl').read_text().splitlines()]
        for row in rows:
            if row['outcome']=='passed':passed[row['nodeid']]=name
            elif row['outcome']=='failed':failures.append({'attempt':name,**row})
        runs.append({'attempt':name,'case_counts':dict(Counter(x['outcome'] for x in rows)),
            'receipt':pin(path/'receipt.json'),'audit':pin(path/'execution_audit.json'),
            'audit_values':audit,'handle':pin(path/'handle.json'),'cases':pin(path/'case_reports.jsonl'),
            'junit':pin(path/'junit.xml'),'stdout':pin(path/'stdout.txt'),
            'request':pin(path/'selected_request.json'),'policy':receipt['metadata']['policy'],
            'verified_cgroup':receipt['metadata']['verified_cgroup'],
            'observed_scratch_bytes':receipt['metadata']['observed_scratch_bytes'],
            'selected_python_source_pin':request['selected_python_source_pin'],
            'selected_stdlib_source':request['selected_stdlib_source'],
            'terminal':True,'quiescent':True,'all_five_pin_classes_unchanged':True})
    new={k:v for k,v in passed.items() if 'catalog_cutoff_735.py' in k or 'initial_catalog_736.py' in k}
    old={k:v for k,v in passed.items() if k not in new}
    assert len(new)==84 and len(old)==12 and len(passed)==96
    assert sum('catalog_cutoff_735.py' in k for k in new)==56
    assert sum('initial_catalog_736.py' in k for k in new)==28
    assert len(failures)==1 and failures[0]['nodeid'] in passed
    save('CASE_IDS_001.json',{'all_passing_cases':passed,'new_component_cases':new,
        'existing_regression_cases':old,'preserved_failures':failures,
        'distinct_counts':{'cutoff735':56,'receiver736':28,'new_components':84,'regressions':12,'total':96}})
    source=json.loads((PACKET/'SOURCE_PINS_001.json').read_text())
    for row in source['pins']:assert pin(ROOT/row['path'])==row
    snapshot=RUNNER/'check200c_initial736/source_snapshot'
    for row in source['pins']:
        if row['path'].startswith(('gene_annotation_episode/','tests/')):
            assert hashlib.sha256((snapshot/row['path']).read_bytes()).hexdigest()==row['sha256']
    # Only the documented parent-manifest check changed after the first green
    # root scope. Verify that exact AST delta instead of claiming byte equality.
    file=Path('gene_annotation_episode/restriction_mapping_references.py')
    old_tree=ast.parse((RUNNER/'check200b_initial736/source_snapshot'/file).read_text())
    new_tree=ast.parse((ROOT/file).read_text())
    removed=[]
    for node in ast.walk(new_tree):
        if isinstance(node,ast.FunctionDef) and node.name=='_initial_catalog_reference':
            for child in ast.walk(node):
                if isinstance(child,ast.If):
                    keep=[]
                    for item in child.body:
                        if (isinstance(item,ast.Expr) and isinstance(item.value,ast.Call)
                                and isinstance(item.value.func,ast.Attribute) and item.value.func.attr=='_manifest'
                                and len(item.value.args)==1 and isinstance(item.value.args[0],ast.Name)
                                and item.value.args[0].id=='parent'):
                            removed.append(ast.dump(item,include_attributes=False))
                        else:keep.append(item)
                    child.body=keep
    assert len(removed)==1 and ast.dump(old_tree,include_attributes=False)==ast.dump(new_tree,include_attributes=False)
    value={'recorded_at':datetime.now(timezone.utc).isoformat(),
        'authority':pin(Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt')),
        'contracts':[pin(PACKET/'CONTRACT_001.md'),pin(PACKET/'CONTRACT_001_A.md')],
        'source_pins':pin(PACKET/'SOURCE_PINS_001.json'),'cases':pin(PACKET/'CASE_IDS_001.json'),
        'peer_evidence':pin(ROOT/'verification/tool_graders_restriction_catalog_cutoff_2026-10-29_735/EVIDENCE_001.json'),
        'runs':runs,'new_component_checks':84,'existing_regressions':12,'total_distinct_checks':96,
        'prior_restriction_component_union':492,'cumulative_restriction_component_union':576,
        'single_fresh576_case_suite':False,'root_final_source_matches_latest_test_snapshot':True,
        'root_first_green_scope_exact_followup_AST_delta':removed,
        'remaining_unrepaired_case_failures':0,'original_failure_retained':True,
        'new_native_searches':0,'new_719_calculations':0,'external_model_network_calls':0,
        'original_scientific_stores_opened':False,'verification_jobs':4,
        'new_whole_tools_or_operation_links_or_numerical_groups':0,
        'actual_engineering_example':{'catalog_action_decision_index':3,'allowed_commission_index':4,
            'same_index_commission_allowed':False,'receipt_after_frozen_cutoff_allowed':False,
            'biological_measurement':False},
        'scope_limits':['Namespace/custody tests use an explicitly labelled publication/job authority seam, without native measurements or fake selectable ToolInfo.',
            'Actual Workflow selection, typed initial admission, multigeneration explicit handoff, receipt cutoff, transaction rollback and reconstruction are verified as engineering paths.',
            'Production public ToolInfo/presentation, authentic nonempty selected native scientific/credit/controller/resource execution and all R1-R7/FBA obligations remain open.']}
    save('VERIFICATION_001.json',value)
    save('ROOT_REVIEW_001.json',{'recorded_at':value['recorded_at'],'verification':pin(PACKET/'VERIFICATION_001.json'),
        'source_review':source,'all_handles_collected_terminal_quiescent':True,
        'all_audits_clean_and_five_pin_classes_unchanged':True,
        'all_source_pins_match_current_and_final_root_snapshot':True,
        'first_green_scope_followup_delta':removed,'new_component_cases':84,
        'existing_regressions':12,'total_distinct_passing_cases':96,
        'original_failure':'check200 initial named reference was rejected during actual nested Workflow construction; that original case now passes.',
        'new_prompt_catalog_scientific_calculation_or_credit_policy':False,'all_R1_R7_open':True})
    print(json.dumps({'new_components':len(new),'regressions':len(old),'total':len(passed),
        'original_failure_retained':True,'final_source_verified':True}))


if __name__=='__main__':record()
