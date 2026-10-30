"""Custody and failure oracles using only a synthetic file-writing subprocess.

No BLAST program, API, scheduler or real database is invoked by these fixtures.
Each retained report explicitly says it contains no native measurements.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_standard_database_contracts as c
from gene_annotation_episode import native_blast_standard_database_driver as driver
from test_native_blast_standard_database_contracts import job_for, forbid_io

ROOT = Path(__file__).resolve().parents[1]
PSSM = b'''PssmWithParameters ::= { pssm { isProtein TRUE, numRows 2, numColumns 2,
 query seq { inst { repr raw, mol aa, length 2, seq-data iupacaa "AC" } },
 finalData { scores { 1, 2, 3, 4 }, lambda 1.0, kappa 1.0, h 1.0 } } }
'''


def file_identity(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw), 'artifact_ref': None}


def write(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return file_identity(path)


def save_json(path, value):
    return write(path, (json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


def fixture(base, program='blastp', query='sequence', behavior='complete', fmt='json15', pssm_parser=True):
    base.mkdir(parents=True, exist_ok=True)
    deploy = base/'deployment'
    names = ['__init__.py', 'native_blast_standard_database_contracts.py',
             'native_blast_standard_database_driver.py', 'blast_program_context.py']
    if pssm_parser: names.append('blast_pssm_inputs.py')
    for name in names:
        write(deploy/'gene_annotation_episode'/name, (ROOT/'gene_annotation_episode'/name).read_bytes())
    runtime = write(base/'runtime-file', b'explicit synthetic additional runtime identity\n')
    python = file_identity(Path(sys.executable).resolve())
    manifest = {'version': 'native_blast_standard_database_producer_manifest_v1', 'module_root': str(deploy),
        'entry_module': 'gene_annotation_episode.native_blast_standard_database_driver',
        'python': {k: python[k] for k in ['path', 'sha256', 'size_bytes']},
        'package_files': [{'relative_path': str(p.relative_to(deploy)),
            **{k: file_identity(p)[k] for k in ['sha256', 'size_bytes']}}
            for p in sorted(deploy.rglob('*')) if p.is_file()],
        'runtime_files': [{k: runtime[k] for k in ['path', 'sha256', 'size_bytes']}]}
    producer_manifest = save_json(base/'producer-manifest.json', manifest)
    script = ('#!'+sys.executable+'\n'+'''import json, os, pathlib, sys
argv = sys.argv[1:]
with open("synthetic-invocations.log", "a") as stream:
    stream.write(json.dumps({"argv": argv, "cwd": os.getcwd(), "environment": dict(os.environ)}) + "\\n")
assert sys.stdin.read() == ""
print("synthetic stdout:" + "x" * 1048583)
sys.stderr.write("synthetic stderr\\n")
behavior = os.environ["SYNTHETIC_BEHAVIOR"]
report = pathlib.Path(argv[argv.index("-out") + 1])
if behavior != "missing":
    if behavior == "symlink":
        report.symlink_to(pathlib.Path(os.environ["OUTSIDE_FILE"]))
    else:
        report.write_bytes(b'{"synthetic":true,"not_native_measurements":true}\\n' if behavior != "nonzero" else b'{"synthetic_partial":')
        if behavior == "empty": report.write_bytes(b"")
raise SystemExit(7 if behavior == "nonzero" else 0)
''').encode()
    executable = base/'synthetic-file-writer'
    software = write(executable, script); executable.chmod(0o700)
    job = job_for(program, query, fmt)
    job['software'] = {'executable': software['path'], 'sha256': software['sha256'], 'engine_version': None}
    outside = base/'outside-file'; write(outside, b'outside original bytes must not be captured\n')
    job['environment'] = {'SYNTHETIC_BEHAVIOR': behavior, 'OUTSIDE_FILE': str(outside)}
    query_bytes = PSSM if query == 'pssm' else (b'>same\nAcDEK\n>same other title\nMKL\n'
        if program in {'blastp', 'tblastn'} else b'>same\nAcGTURYSWKMBDHVN\n>same other title\nACGT\n')
    job['inputs'][0].update(write(base/'selected-query', query_bytes))
    job['inputs'].append({'input_key': 'metadata', 'role': 'metadata', 'format': 'json',
        **write(base/'metadata.json', b'declared JSON deliberately opaque to producer\x00\xff')})
    job['metadata_inputs'] = [{'input_key': 'metadata', 'consumer': 'sequence_database',
        'schema_id': 'native_blast_database_sequence_metadata_v1'}]
    db = job['databases'][0]; m = db['manifest']; prefix = base/'selected-db'
    db['native_paths'] = m['native_paths'] = [str(prefix)]
    letter = 'p' if db['kind'] == 'blast_protein_sequence' else 'n'
    m['files'] = []
    for suffix in [letter+'hr', letter+'in', letter+'sq', letter+'al']:
        data = write(base/('selected-db.'+suffix), ('synthetic selected database dependency '+suffix+'\n').encode())
        m['files'].append({k: data[k] for k in ['path', 'sha256', 'size_bytes']})
    m['preparation']['receipt'] = write(base/'preparation.receipt', b'opaque synthetic preparation record\x00\xff')
    m['preparation']['input_manifest'] = write(base/'preparation.inputs', b'opaque synthetic preparation inputs\xff')
    m['metadata_manifests'] = [write(base/'database.metadata', b'opaque supplied metadata\x00')]
    m['access']['offline_configuration'] = write(base/'database.config', b'explicit supplied synthetic config\xff')
    db['manifest_file'] = save_json(base/'database.manifest.json', m)
    request = c.requested_job_from_standard_blast_database(job)
    owner = {'run_id': 'synthetic-331', 'episode_id': 'synthetic-hpc-child', 'resource_id': 'synthetic-declared-hpc',
        'operation_key': 'explicit-selected-operation', 'assignment_sha256': 'd'*64,
        'requested_job_sha256': c._digest(request), 'execution_id': None}
    owner['attempt_id'] = c._digest(owner['operation_key'])
    owner['submission_token'] = c._digest({k: owner[k] for k in ['run_id', 'episode_id', 'assignment_sha256', 'operation_key']})
    attempt = base/'attempt'; attempt.mkdir()
    plan = {'version': 'native_blast_standard_database_run_plan_v1', 'identity': owner,
        'requested_job': request, 'attempt_directory': str(attempt),
        'input_paths': {r['input_key']: str(attempt/'inputs'/r['input_key']) for r in job['inputs']},
        'database_paths': {db['database_key']: db['native_paths']}, 'output_directory': str(attempt/'outputs'),
        'resource_environment': {'RESOURCE_SETTING': 'explicit'}, 'producer_manifest': producer_manifest}
    path = attempt/driver.PLAN_NAME; save_json(path, plan)
    return path, plan, manifest


def refresh_plan(path, plan):
    job = plan['requested_job']['native_blast_standard_database']
    plan['requested_job'] = c.requested_job_from_standard_blast_database(job)
    plan['identity']['requested_job_sha256'] = c._digest(plan['requested_job'])
    save_json(path, plan)


def run_fixture(path, plan, *, pbs_jobid='331.synthetic', shadow=None):
    # The test caller's deployment binding stays independent of manifest bytes;
    # a tampered manifest must reach the producer's own preflight validator.
    deployment = str(path.parent.parent/'deployment') if shadow is None else str(shadow)
    env = {'PYTHONPATH': deployment, 'PYTHONDONTWRITEBYTECODE': '1'}
    if pbs_jobid is not None: env['PBS_JOBID'] = pbs_jobid
    result = subprocess.run([sys.executable, '-B', '-m', 'gene_annotation_episode.native_blast_standard_database_driver', str(path)],
        cwd=path.parent, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    # Every wrapper receipt is retained separately, including replay failures.
    ordinal = len(list(path.parent.glob('wrapper-*.stdout')))
    (path.parent/f'wrapper-{ordinal:03d}.stdout').write_bytes(result.stdout)
    (path.parent/f'wrapper-{ordinal:03d}.stderr').write_bytes(result.stderr)
    bundle_path = path.parent/'bundle.json'
    return result, json.loads(bundle_path.read_bytes()) if bundle_path.exists() else None


def envelope(plan):
    return {'identity': {**plan['identity'], 'execution_id': '331.synthetic'},
        'attempt_directory': plan['attempt_directory'], 'plan_sha256': c._digest(plan)}


def validate_bundle(bundle, plan):
    return c.validate_standard_blast_database_bundle(bundle,
        original_job=plan['requested_job']['native_blast_standard_database'], attempt_identity=envelope(plan))


@pytest.mark.parametrize('program,query', [(p,q) for p in c.PROGRAMS for q in
    (['sequence','pssm'] if p == 'tblastn' else ['sequence'])])
def test_one_synthetic_process_all_modes_exact_retention_and_immutable_replay(tmp_path, program, query):
    path, plan, manifest = fixture(tmp_path, program, query)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 0, result.stderr.decode()
    assert not bundle['failures'] and validate_bundle(bundle, plan) == bundle
    assert bundle['producer_verification']['manifest'] == manifest
    assert bundle['producer_verification']['status'] == 'verified'
    assert bundle['process']['started'] and bundle['process']['returncode'] == 0
    assert bundle['process']['native_elapsed_seconds'] >= 0
    invocations = (path.parent/'synthetic-invocations.log').read_text().splitlines()
    assert len(invocations) == 1
    invocation = json.loads(invocations[0])
    assert invocation['argv'] == bundle['realized_argv'][1:]
    assert invocation['cwd'] == str(path.parent)
    for key, value in bundle['environment'].items(): assert invocation['environment'][key] == value
    assert bundle['environment']['RESOURCE_SETTING'] == 'explicit'
    assert 'PBS_JOBID' not in bundle['environment'] and 'HOME' not in bundle['environment']
    assert bundle['environment']['TMPDIR'] == str(path.parent/'tmp')
    assert set(bundle['associations']) == {'query_input_key', 'selected_options', 'external_manifest_keys'}
    for a in bundle['artifacts']:
        actual = file_identity(path.parent/a['relative_path'])
        assert (actual['sha256'],actual['size_bytes']) == (a['sha256'],a['size_bytes'])
        assert a['content_assessment'] == 'not_parsed'
    query_artifact = next(a for a in bundle['artifacts'] if a['input_key'] == 'query')
    assert (path.parent/query_artifact['relative_path']).read_bytes() == Path(plan['requested_job']['native_blast_standard_database']['inputs'][0]['path']).read_bytes()
    stdout = next(a for a in bundle['artifacts'] if a['role'] == 'stdout')
    assert stdout['size_bytes'] > 1024**2
    assert len(bundle['database_manifest'][0]['checks']) == 4
    assert all(r['status'] == 'verified' for r in bundle['database_manifest'][0]['checks'])
    replay, saved = run_fixture(path, plan)
    assert replay.returncode == 0 and saved == bundle
    assert len((path.parent/'synthetic-invocations.log').read_text().splitlines()) == 1


@pytest.mark.parametrize('behavior,code,rc', [('nonzero','native_nonzero_exit',7), ('missing','required_output_missing',0),
    ('symlink','output_path_escape',0)])
def test_partial_missing_escape_preserve_distinct_outcomes(tmp_path, behavior, code, rc):
    path, plan, _ = fixture(tmp_path, behavior=behavior)
    result, bundle = run_fixture(path, plan)
    assert result.returncode == 1, result.stderr.decode()
    assert validate_bundle(bundle, plan) == bundle
    assert bundle['process']['returncode'] == rc
    assert code in {r['code'] for r in bundle['failures']}
    assert any(a['role'] == 'stdout' for a in bundle['artifacts'])
    if behavior == 'nonzero':
        report = next(a for a in bundle['artifacts'] if a['role'] == 'primary_report')
        assert (path.parent/report['relative_path']).read_bytes() == b'{"synthetic_partial":'
    assert len((path.parent/'synthetic-invocations.log').read_text().splitlines()) == 1


def test_empty_captured_report_is_unparsed_bytes_not_a_zero_hit_claim(tmp_path):
    path,plan,_=fixture(tmp_path,behavior='empty')
    result,bundle=run_fixture(path,plan)
    assert result.returncode==0,result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    report=next(a for a in bundle['artifacts'] if a['role']=='primary_report')
    assert report['size_bytes']==0 and report['content_assessment']=='not_parsed'
    assert 'hit_count' not in report
    assert next(r for r in bundle['output_manifest'] if r['output_key']=='report')['presence']=='present'


def test_native_start_failure_has_no_invented_exit_or_elapsed_measurement(tmp_path):
    path,plan,_=fixture(tmp_path)
    Path(plan['requested_job']['native_blast_standard_database']['software']['executable']).chmod(0o600)
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1,result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert bundle['process']=={'started':False,'returncode':None,'started_at':None,'finished_at':None,'native_elapsed_seconds':None}
    assert 'native_start_failed' in {r['code'] for r in bundle['failures']}
    assert not (path.parent/'synthetic-invocations.log').exists()


@pytest.mark.parametrize('change,code', [('software','software_identity_mismatch'), ('input','input_identity_mismatch'),
    ('missing_volume','database_file_missing'), ('alias','database_identity_mismatch'),
    ('manifest','database_identity_mismatch'), ('metadata','database_identity_mismatch'),
    ('input_manifest','database_identity_mismatch'), ('config','database_identity_mismatch')])
def test_changed_or_missing_selected_bytes_prevent_execution_keep_custody(tmp_path, change, code):
    path, plan, _ = fixture(tmp_path)
    job = plan['requested_job']['native_blast_standard_database']; db=job['databases'][0]
    target = {'software': job['software']['executable'], 'input': job['inputs'][0]['path'],
        'missing_volume': db['manifest']['files'][1]['path'], 'alias': db['manifest']['files'][-1]['path'],
        'manifest': db['manifest_file']['path'], 'metadata': db['manifest']['metadata_manifests'][0]['path'],
        'input_manifest': db['manifest']['preparation']['input_manifest']['path'],
        'config': db['manifest']['access']['offline_configuration']['path']}[change]
    if change == 'missing_volume': Path(target).unlink()
    else: Path(target).write_bytes(Path(target).read_bytes()+b'changed\n')
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1, result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert not bundle['process']['started'] and bundle['process']['returncode'] is None
    assert code in {r['code'] for r in bundle['failures']}
    assert not (path.parent/'synthetic-invocations.log').exists()
    assert bundle['input_manifest'] and bundle['database_manifest']


@pytest.mark.parametrize('change,code', [('package','producer_file_identity_mismatch'), ('runtime','producer_file_identity_mismatch'),
    ('extra','producer_package_inventory_mismatch'), ('manifest','producer_manifest_invalid'),
    ('missing','producer_file_missing'), ('symlink','producer_package_inventory_mismatch')])
def test_selected_manifest_alone_does_not_verify_actual_runtime(tmp_path, change, code):
    path,plan,manifest=fixture(tmp_path); deploy=Path(manifest['module_root'])
    if change=='package':
        p=deploy/'gene_annotation_episode/__init__.py'; p.write_bytes(p.read_bytes()+b'\n# changed\n')
    elif change=='runtime': Path(manifest['runtime_files'][0]['path']).write_bytes(b'changed')
    elif change=='extra': write(deploy/'extra',b'unselected')
    elif change=='manifest': Path(plan['producer_manifest']['path']).write_bytes(b'changed')
    elif change=='missing': (deploy/'gene_annotation_episode/blast_pssm_inputs.py').unlink()
    else: (deploy/'link').symlink_to(tmp_path/'outside-file')
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1, result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert code in {r['code'] for r in bundle['failures']}
    assert not bundle['process']['started']
    assert not (path.parent/'synthetic-invocations.log').exists()


@pytest.mark.parametrize('program,raw,options', [('blastn',b'>q\nACGTZ\n',[]), ('blastx',b'>q\nMKE\n',[]),
    ('tblastx',b'>q\nACG-\n',[]), ('blastp',b'>q\nACG1\n',[]), ('blastp',b'>q\n',[]),
    ('blastp',b'ACGT\n',[]), ('blastn',b'>q\nACGT\n',['-query_loc','1-5']),
    ('blastp',b'>q\nACGT\n>q2\nAC\n',['-query_loc','1-4'])])
def test_fasta_syntax_molecule_and_all_record_ranges_are_preflight_facts(tmp_path, program, raw, options):
    path,plan,_=fixture(tmp_path,program)
    job=plan['requested_job']['native_blast_standard_database']; job['inputs'][0].update(write(tmp_path/'selected-query',raw))
    job['options']=options; refresh_plan(path,plan)
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1, result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert 'input_native_incompatible' in {r['code'] for r in bundle['failures']}
    assert not bundle['process']['started']


@pytest.mark.parametrize('raw', [b'not ASN', PSSM[:-5], PSSM+PSSM,
    PSSM.replace(b'isProtein TRUE', b'isProtein FALSE')])
def test_pssm_unusable_syntax_is_retained_without_consensus(tmp_path,raw):
    path,plan,_=fixture(tmp_path,'tblastn','pssm')
    job=plan['requested_job']['native_blast_standard_database']; job['inputs'][0].update(write(tmp_path/'selected-query',raw)); refresh_plan(path,plan)
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1, result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert 'input_native_incompatible' in {r['code'] for r in bundle['failures']}
    captured=next(a for a in bundle['artifacts'] if a['input_key']=='query')
    assert (path.parent/captured['relative_path']).read_bytes()==raw
    assert not bundle['process']['started']


def test_missing_pssm_parser_is_specific_unavailable_dependency(tmp_path):
    path,plan,_=fixture(tmp_path,'tblastn','pssm',pssm_parser=False)
    result,bundle=run_fixture(path,plan)
    assert result.returncode==1, result.stderr.decode()
    assert validate_bundle(bundle,plan)==bundle
    assert 'producer_input_parser_unavailable' in {r['code'] for r in bundle['failures']}
    assert not bundle['process']['started']


def test_unsealed_attempt_and_missing_actual_pbs_identity_never_rerun(tmp_path):
    path,plan,_=fixture(tmp_path)
    result,bundle=run_fixture(path,plan,pbs_jobid=None)
    assert result.returncode!=0 and bundle is None
    assert b'actual_pbs_execution_id_required' in result.stderr
    save_json(path.parent/driver.OWNER_NAME,plan)
    result,bundle=run_fixture(path,plan)
    assert result.returncode!=0 and bundle is None
    assert b'unsealed_attempt_execution_uncertain' in result.stderr
    assert not (path.parent/'synthetic-invocations.log').exists()


def test_replay_changed_sealed_bytes_rejects_without_command(tmp_path):
    path,plan,_=fixture(tmp_path); result,bundle=run_fixture(path,plan)
    assert result.returncode==0,result.stderr.decode()
    report=next(a for a in bundle['artifacts'] if a['role']=='primary_report')
    Path(path.parent/report['relative_path']).write_bytes(b'changed sealed bytes')
    result,saved=run_fixture(path,plan)
    assert result.returncode!=0 and saved==bundle
    assert b'sealed_artifact_identity_mismatch' in result.stderr
    assert len((path.parent/'synthetic-invocations.log').read_text().splitlines())==1


@pytest.mark.parametrize('change', [lambda b:b['identity'].update(execution_id='other'),
    lambda b:b['plan']['identity'].update(operation_key='other'), lambda b:b['realized_argv'].append('-remote'),
    lambda b:b['environment'].update(HOME='/elsewhere'), lambda b:b['associations'].update(query_input_key='other'),
    lambda b:b['artifacts'][0].update(relative_path='../escape'),
    lambda b:b['database_manifest'][0]['checks'].pop(),
    lambda b:b['process'].update(returncode=None), lambda b:b['producer_verification'].update(status='failed')])
def test_bundle_validation_rejects_forged_relationships_pure(tmp_path,monkeypatch,change):
    path,plan,_=fixture(tmp_path); result,bundle=run_fixture(path,plan)
    assert result.returncode==0,result.stderr.decode()
    altered=deepcopy(bundle); change(altered)
    forbid_io(monkeypatch)
    assert validate_bundle(bundle,plan)==bundle
    with pytest.raises(ValueError): validate_bundle(altered,plan)


@pytest.mark.parametrize('change', [lambda p:p['identity'].update(attempt_id='0'*64),
    lambda p:p['identity'].update(execution_id='premature'), lambda p:p['identity'].update(submission_token='0'*64),
    lambda p:p.update(output_directory='/unselected/output'),
    lambda p:p['input_paths'].update(query='/outside/query'),
    lambda p:p['input_paths'].update(query=p['attempt_directory']+'/bundle.json'),
    lambda p:p['database_paths'].update(target=['/unselected/db'])])
def test_plan_and_control_relationship_rejections_are_pure(tmp_path,monkeypatch,change):
    _,plan,_=fixture(tmp_path); bad=deepcopy(plan);change(bad)
    forbid_io(monkeypatch)
    assert c.validate_standard_blast_database_plan(plan)==plan
    with pytest.raises(ValueError): c.validate_standard_blast_database_plan(bad)
