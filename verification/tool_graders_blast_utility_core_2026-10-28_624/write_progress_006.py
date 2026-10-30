"""Additive verification/accounting; never changes the authoritative goal."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
RUNNER=ROOT/'verification/tool_graders_hmmer_map_verification_2026-10-28_529'

def pin(path):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}

def write_new(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write('\n')

checks={}
for name in ('check084_database_utility_native','check085_database_utility_diagnostic','check086_utility_components'):
    directory=RUNNER/name
    receipt=json.loads((directory/'receipt.json').read_text())
    audit=json.loads((directory/'execution_audit.json').read_text())
    reports=[json.loads(line) for line in (directory/'case_reports.jsonl').read_text().splitlines()]
    counts=collections.Counter((row['nodeid'].split('::')[0],row['outcome']) for row in reports if row['phase']=='call')
    checks[name]={'receipt':pin(directory/'receipt.json'),'audit':pin(directory/'execution_audit.json'),
        'case_reports':pin(directory/'case_reports.jsonl'),
        'execution':{k:receipt[k] for k in ('returncode','terminal','quiescent','source_unchanged',
                                            'dependency_unchanged','stdlib_unchanged','binary_unchanged')},
        'execution_audit':audit,
        'tests':[{'file':key[0],'outcome':key[1],'count':count} for key,count in sorted(counts.items())]}
    assert receipt['terminal'] and receipt['quiescent']
    assert all(receipt[k] for k in ('source_unchanged','dependency_unchanged','stdlib_unchanged','binary_unchanged'))
    assert not audit['outside_modules'] and not audit['unbound_mappings']
assert checks['check084_database_utility_native']['execution']['returncode']==1
assert checks['check085_database_utility_diagnostic']['execution']['returncode']==0
assert checks['check086_utility_components']['execution']['returncode']==0
assert sum(r['count'] for r in checks['check086_utility_components']['tests'] if r['outcome']=='passed')==361
names=('blast_utility_contracts.py','blast_database_extraction.py','blast_database_inspection.py',
       'blast_database_preparation.py','native_blast_standard_database_contracts.py',
       'native_blast_utility_contracts.py','native_blast_utility_tool_info.py')
source=[]
for name in names:
    relative=Path('gene_annotation_episode')/name
    current=ROOT/relative
    executed=RUNNER/'check086_utility_components/source_snapshot'/relative
    source.append({'source':pin(current),'executed_source':pin(executed),
                   'matches_executed_snapshot':current.read_bytes()==executed.read_bytes()})
original=RUNNER/'check084_database_utility_native/temporary/database_utility_native/CAPTURE_001.json'
probe=RUNNER/'check085_database_utility_diagnostic/temporary/database_utility_probe/PROBE_001.json'
a=json.loads(original.read_text());b=json.loads(probe.read_text())
evidence={'record_type':'root_database_utility_component_verification',
    'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'checks':checks,'source':source,
    'original_native_capture':pin(original),'diagnostic_capture':pin(probe),
    'native_commands_original':len(a['cases']),'native_commands_followup':len(b['cases']),
    'native_builds':3,'native_failed_duplicate_builds':1,
    'native_qualifications':[
        '084 capture test failed because both integrity commands were expected to succeed; actual metadata exceptions retained.',
        '085 capture test passed while retaining both actual integrity commands returncode1.',
        'Detailed native checks show missing Taxid9606 and three passing OID checks; no full integrity pass.',
        'Successful full/sample integrity parser cases are synthetic, explicitly labelled.',
        'No successful original build/search was repeated;085 uses original databases and diagnoses a failed check.',
        'No database BLAST, API, HPC, authentication or taxonomy download occurred.'],
    'numerical_examples':[
        {'population':'three tiny nucleotide sequences','sequence_count':3,'residue_count':31,'unit':'nt'},
        {'population':'two tiny protein sequences','sequence_count':2,'residue_count':35,'unit':'aa'},
        {'population':'seqB range2-7','native_full_length':12,'returned_symbols':6,
         'plus_sequence':'TGCAAT','minus_sequence':'ATTGCA'},
        {'population':'seqA range8-99','native_full_length':12,'returned_symbols':5}],
    'implementation':{
        'shared_records':'closed supporting utility types; no independent scientific score',
        'readers':'native extraction/info/metadata/integrity with partial records and original identities',
        'preparation':'original output families plus existing standard prepared-manifest projection',
        'compiler':'one explicit selected command; exact three original makeblastdb commands reproduced',
        'tool_information':'pure descriptors for configured software; not yet exposed through shared runtime'},
    'remaining':[
        'Native producer/reservation/capture now assigned fresh628 against005.',
        'Shared practical/resource binding, saved result publication and requested episode returns are unfinished.',
        'Actual full integrity success requires appropriate genuine taxonomy/reference data; none fabricated.',
        'Masking result/parent template renderers await required user feedback.',
        'Other R7 utilities and all R1-R7 obligations remain open.'],
    'accounting':{'new_completed_inventory_rows':0,'new_connected_operation_names':0,'new_numerical_graders':0}}
write_new(PACKET/'ROOT_VERIFICATION_006.json',evidence)
previous=ROOT/'research/tool_grader_progress_2026-10-27/PROGRESS_037.json'
progress=json.loads(previous.read_text())
progress['previous_progress_record']=str(previous.relative_to(ROOT))
progress['previous_progress_sha256']=pin(previous)['sha256']
progress['recorded_at']=evidence['recorded_at']
progress['previous_turn_classification']={'classification':'no_progress',
    'reason':'Previous user-response turn reconciled existing counts only; no implementation/state change.',
    'revalidation':'Reread original goal and current037; next safe work was fixed620/624 utility boundaries and implementation.'}
progress['current_turn_classification']={'classification':'progress',
    'reason':'New shared contracts/readers/preparation/compiler code;361passing component/regression tests; native observations change integrity and range handling.'}
progress['current_update_evidence']=str((PACKET/'ROOT_VERIFICATION_006.json').relative_to(ROOT))
progress['current_turn_verification']=evidence
progress['current_native_verification']={
    'original_attempt':'check084_database_utility_native','followup_attempt':'check085_database_utility_diagnostic',
    'native_commands':24,'completed_successful_builds':3,'full_episode_path_verified':False,
    'qualification':'Utility command/output observations only; integrity failures retained. Four previously verified masking Workflow modes remain in prior037 evidence.'}
progress['current_turn_accounting']={
    'new_complete_inventory_rows':0,'new_connected_operation_names':0,'new_numerical_groups':0,
    'linked_numerical_groups':44,'distinct_numerically_linked_operation_names':124,
    'numerical_groups':45,'typed_only_groups':2,'distinct_operation_names':125,'operation_name_links':138,
    'unlinked_numerical_groups':['rna_comparison'],'all_R1_through_R7_remain_open':True,
    'qualification':'Reuses619 mapping unchanged. New unconnected utility components are not counted as completed operations or new scientific graders.'}
progress['current_workloads']=[
    {'task':'blast_utility_contracts_625','status':'completed_pure_contract_workload','verification':'109of361passed'},
    {'task':'blast_database_readers_626','status':'completed_pure_reader_workload','verification':'60of361passed'},
    {'task':'blast_database_preparation_627','status':'completed_pure_preparation_workload','verification':'36newtestsand137existingcontractregressionspassed'},
    {'task':'root_native_utility_compiler','status':'compiler_and_descriptors_verified_unconnected','verification':'19of361passed'},
    {'task':'blast_utility_native_producer_628','status':'fresh_workload_assigned','contract':str((PACKET/'PRODUCER_CONTRACT_005.md').relative_to(ROOT))}]
progress['current_next_action']='Complete628producer/local reservation/capture, then connect typed result publication and requested episode returns. Pending masking templates require actual user feedback; continue independent utility work.'
progress['accounting_review']='44shared numerical graders linked to124distinctoperation/mode names remains unchanged. New supporting utility contracts/readers/compiler are implemented and component-tested but unconnected;0new completed inventory rows.'
for row in progress['deliverables']:
    assert row['status']=='open'
    if row['id']=='R7':
        row['qualification']='Three masking utilities retain four selected local Workflow modes verified; presentation remains pending. Three additional utilities now have common contracts/readers/preparation/compiler with361combined passing checks, but native execution/result-return integration is unfinished. All13whole-utility closures remain open.'
        row['current_database_utility_increment']={
            'programs':['makeblastdb','blastdbcmd','blastdbcheck'],
            'modes':['create_sequence_database','extract_sequences','info','metadata','integrity'],
            'contracts_readers_preparation_compiler_verified':True,
            'whole_episode_path_verified':False,'evidence':progress['current_update_evidence'],
            'next_native_producer_task':'/root/blast_utility_native_producer_628'}
progress['pending_message_feedback']={
    'masking_results_decision':'621fullTASK/STEERINGprintedthisturn;noanswerreceived;notimplemented',
    'masking_scientific_return':'622actualDUSTtableprintedthisturn;noanswerreceived;notimplemented',
    'rule':'docs/TASK_AND_STEERING.md requires user running feedback before template implementation'}
assert [r['id'] for r in progress['deliverables']]==['R1','R2','R3','R4','R5','R6','R7']
write_new(ROOT/'research/tool_grader_progress_2026-10-27/PROGRESS_038.json',progress)
print(json.dumps({'progress':'PROGRESS_038.json','evidence':'ROOT_VERIFICATION_006.json',
    'tests_passed':361,'connected_operation_increment':0,'completed_inventory_increment':0,
    'all_R1_through_R7_open':True}))
