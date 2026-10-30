"""Read retained verification metadata with stdlib only; execute no application."""
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
RUNNER=ROOT/'verification/tool_graders_hmmer_map_verification_2026-10-28_529'
ATTEMPTS=('check197_selection734','check197b_selection734','check198_declarations733',
    'check198b_declarations733','check198c_declarations733')


def pin(path):
    path=Path(path)
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}


def save(name,value):
    (PACKET/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def record():
    runs=[]
    passed={}
    failures=[]
    for attempt in ATTEMPTS:
        path=RUNNER/attempt
        receipt=json.loads((path/'receipt.json').read_text())
        audit=json.loads((path/'execution_audit.json').read_text())
        assert receipt['terminal'] and receipt['quiescent']
        assert all(receipt[k] for k in ('source_unchanged','dependency_unchanged',
            'stdlib_unchanged','binary_unchanged','selected_stdlib_source_unchanged'))
        assert audit['outside_modules']==audit['unbound_mappings']==[]
        assert audit['native_unchanged'] and audit['original_retained_fixtures_unchanged']
        rows=[json.loads(line) for line in (path/'case_reports.jsonl').read_text().splitlines()]
        counts=Counter(row['outcome'] for row in rows)
        for row in rows:
            if row['outcome']=='passed':passed[row['nodeid']]=attempt
            elif row['outcome']=='failed':failures.append({'attempt':attempt,**row})
        request=json.loads((path/'selected_request.json').read_text())
        runs.append({'attempt':attempt,'case_counts':dict(counts),'receipt':pin(path/'receipt.json'),
            'audit':pin(path/'execution_audit.json'),'audit_values':audit,
            'handle':pin(path/'handle.json'),'case_reports':pin(path/'case_reports.jsonl'),
            'stdout':pin(path/'stdout.txt'),'junit':pin(path/'junit.xml'),
            'selected_request':pin(path/'selected_request.json'),
            'policy':receipt['metadata']['policy'],
            'swap_max':receipt['metadata']['verified_cgroup']['memory_swap_max'],
            'observed_scratch_bytes':receipt['metadata']['observed_scratch_bytes'],
            'terminal':True,'quiescent':True,'all_five_pin_classes_unchanged':True,
            'selected_python_source_pin':request['selected_python_source_pin'],
            'selected_stdlib_source':request['selected_stdlib_source']})
    new={key:value for key,value in passed.items() if any(name in key for name in
        ('test_restriction_mapping_selection_734.py','test_restriction_mapping_declarations_733.py'))}
    old={key:value for key,value in passed.items() if key not in new}
    assert len(new)==106 and len(old)==21 and len(passed)==127
    assert len([key for key in new if 'selection_734.py' in key])==78
    assert len([key for key in new if 'declarations_733.py' in key])==28
    assert all(row['nodeid'] in passed for row in failures)
    save('CASE_IDS_001.json',{'all_passing_cases':passed,'new_component_cases':new,
        'existing_regression_cases':old,'distinct_counts':{'selector734':78,'root733':28,
            'new_components':106,'regressions':21,'total':127},'preserved_failed_attempts':failures})
    sources=json.loads((PACKET/'SOURCE_PINS_001.json').read_text())
    for row in sources['pins']:
        assert pin(ROOT/row['path'])==row
    production=[row for row in sources['pins'] if row['path'].startswith('gene_annotation_episode/')]
    snapshots={}
    for attempt in ('check198b_declarations733','check198c_declarations733'):
        snapshots[attempt]={row['path']:hashlib.sha256((RUNNER/attempt/'source_snapshot'/row['path']).read_bytes()).hexdigest()==row['sha256']
            for row in production}
        assert all(snapshots[attempt].values())
    # Every host source check below parses source/bytes only.
    tree=ast.parse((ROOT/'gene_annotation_episode/scientific_process_episodes.py').read_text())
    names=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='_IMPLEMENTATION_FILES' for t in n.targets))
    assert {'restriction_mapping_selection.py','episode_contract_information.py',
        'episode_return_records.py','episode_journal.py'}<=set(names)
    value={'recorded_at':datetime.now(timezone.utc).isoformat(),
        'authority':pin(Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt')),
        'contracts':[pin(PACKET/'CONTRACT_001.md'),pin(PACKET/'CONTRACT_001_A.md')],
        'source_pins':pin(PACKET/'SOURCE_PINS_001.json'),'cases':pin(PACKET/'CASE_IDS_001.json'),
        'peer_evidence':pin(ROOT/'verification/tool_graders_restriction_selection_2026-10-29_734/EVIDENCE_001.json'),
        'runs':runs,'distinct_passing_new_component_checks':106,'existing_regressions':21,
        'all_distinct_passing_checks':127,'prior_restriction_component_union':386,
        'cumulative_restriction_component_union':492,'single_fresh492_case_suite':False,
        'root_source_matches_both_tested_snapshots':snapshots,
        'remaining_unrepaired_test_failures':0,'original_failures_retained':len(failures),
        'scientific_native_searches':0,'new_719_calculations':0,'external_model_network_calls':0,
        'verification_jobs':5,'original_scientific_stores_opened':False,
        'new_whole_tools_or_operation_links_or_numerical_groups':0,
        'limits':[
            'Pure saved numerical projection copies genuine728 values; it is not host authorization or a new scientific operation.',
            'Nonempty Workflow names are unavailable engineering rows without measurements.',
            'Generic contract-information profile is configured only in engineering tests; no new production ScientificProcessEpisodes profile/prompt was installed.',
            'Actual shared-loop compact empty-source closure and old scientific mechanics restoration use fixture providers/controllers, not configured-model scientific behavior.',
            'Production public ToolInfo/presentation, nonempty selected native scientific/credit/controller/resource execution, parent own-catalog initial cutoff proof and all R1-R7/FBA work remain open.']}
    save('VERIFICATION_001.json',value)
    save('ROOT_REVIEW_001.json',{'recorded_at':value['recorded_at'],
        'verification':pin(PACKET/'VERIFICATION_001.json'),
        'source_methods_and_unchanged_numerical_authorities':sources,
        'all_current_production_pins_match_tested_snapshots':True,
        'all_handles_terminal_collected_and_quiescent':True,
        'all_audits_clean_and_five_pin_classes_unchanged':True,
        'case_counts':{'new_components':106,'existing_regressions':21,'total':127},
        'failures':'Original compact compiler rejection; one734 positive reference fixture; eight733 EpisodeRequest serialization fixtures and one protocol frame/action fixture. All failed case IDs subsequently pass; production code stayed frozen during fixture repairs.',
        'new_prompt_or_catalog_or_credit_policy':False,'all_R1_R7_open':True})
    print(json.dumps({'new_components':len(new),'regressions':len(old),'total':len(passed),
        'failures_retained':len(failures),'current_source_matches_tested_snapshots':True}))


if __name__=='__main__':record()
