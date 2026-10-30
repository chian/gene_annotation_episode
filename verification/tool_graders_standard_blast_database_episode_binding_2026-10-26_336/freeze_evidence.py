"""Retain exact source identities and existing verification receipts; no science."""
from pathlib import Path
import hashlib
import json
import sys

root=Path(__file__).resolve().parents[2]
directory=Path(__file__).parent
def descriptor(path):
    path=Path(path)
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
shared='practical_execution_records practical_execution_operations practical_pbs_operations execution_progress execution_episodes communication domain state evidence_geometry evidence_axis_contracts alignment_site_native blast_result_views infernal_result_presentation'.split()
new=['native_blast_standard_database_'+name for name in ('acquisition','result_publication','results','returns')]
tests=['test_native_blast_standard_database_'+name for name in ('acquisition','results','returns','episode_binding')]
regressions=['test_native_blast_database_'+name for name in ('acquisition','results','returns','episode_binding')]+[
    'test_blast_pairwise_results','test_blast_typed_return_integration','test_blast_native_return_admission',
    'test_execution_episodes_family','test_execution_progress','test_practical_pbs_operations',
    'test_communication','test_tool_knowledge']
dependencies=['native_blast_standard_database_'+name for name in ('contracts','driver','tool_info','metadata','calculators','result_views','result_worker')]+[
    'native_blast_database_metadata','blast_database_grader','blast_sequence_database','blast_report_collection',
    'blast_graders','blast_pairwise_grader','blast_pssm_calculators','acquisition','local_jobs','native_lifecycle','_local_job_worker']
value=dict(version='standard_blast_database_E_source_and_receipt_evidence_v1',
    source_new=[descriptor(root/'gene_annotation_episode'/(name+'.py')) for name in new],
    source_shared=[descriptor(root/'gene_annotation_episode'/(name+'.py')) for name in shared],
    source_dependencies=[descriptor(root/'gene_annotation_episode'/(name+'.py')) for name in dependencies],
    source_tests=[descriptor(root/'tests'/(name+'.py')) for name in tests],
    source_regression_tests=[descriptor(root/'tests'/(name+'.py')) for name in regressions],
    knowledge=[descriptor(root/'gene_annotation_episode/knowledge'/name) for name in ('index.json','native-blast-standard-database-results.md')],
    shared_before=json.loads((directory/'SHARED_BEFORE_001.json').read_text()),
    test_runs=[], original_attempt_files=[], action_receipts=[], worker_generation_files=[], numerical_examples=[])
seen=set()
for check in sorted(directory.glob('check_*')):
    if (check/'receipt.json').exists():
        row=dict(receipt=descriptor(check/'receipt.json'), result=json.loads((check/'receipt.json').read_text()))
        for name in ('source_snapshot.json','stdout.txt','stderr.txt'):
            if (check/name).exists():row[name]=descriptor(check/name)
        value['test_runs'].append(row)
    for path in sorted(check.rglob('*')):
        if not path.is_file() or path.resolve() in seen:continue
        seen.add(path.resolve())
        if path.name in {'submission.json','job-request.json','native-blast-standard-database-plan.json','bundle.json','exit.json'}:
            value['original_attempt_files'].append(descriptor(path))
        if path.name in {'receipt.json','capture.json','authenticated-attempt.json','preparation.json','publication.json'} and 'native-blast-standard-database' in str(path):
            value['action_receipts'].append(descriptor(path))
        if path.name in {'worker-manifest.json','request.json','retained.json','worker.stdout','worker.stderr','implementation.json','implementation-receipt.json',
                'inputs.json','collection.json','sheets.json','calculations.json','rows.ndjson','row-index.json','metric-definitions.json','diagnostics.json'} and 'native-blast-standard-database' in str(path):
            value['worker_generation_files'].append(descriptor(path))
        if path.name in {'range-evidence.json','failed-attempt-return.json','projection-return-union.json','distinct-calculations.json','zero-hits-return.json','lifecycle-failure-evidence.json'}:
            value['numerical_examples'].append(descriptor(path))
name=sys.argv[1]
frozen=directory/(Path(name).stem+'.sources')
frozen.mkdir()
value['frozen_source_copies']=[]
for key in ('source_new','source_shared','source_dependencies','source_tests','source_regression_tests','knowledge'):
    for row in value[key]:
        source=root/row['path']
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('source_changed_during_freeze:'+row['path'])
        copy=frozen/row['path'];copy.parent.mkdir(parents=True,exist_ok=True)
        with copy.open('xb') as stream:stream.write(raw)
        value['frozen_source_copies'].append(dict(original_path=row['path'],**descriptor(copy)))
with (directory/name).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(evidence=str(directory/name), **{k:len(value[k]) for k in ('test_runs','original_attempt_files','worker_generation_files','numerical_examples')}),sort_keys=True))
