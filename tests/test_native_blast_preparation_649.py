"""Bounded controlled native-producer tests, never scientific/native measurements.

The actual native matrix remains the sealed 644 packet. All subprocess.run calls
in this module are explicitly replaced; no database search or helper is run.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_blast_utility_contracts as contracts
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.native_blast_utility_materializations import (
    preparation_path_maps, realize_blast_utility_materializations,
)
from gene_annotation_episode.state import Store
from test_native_blast_utility_producer_628 import identity, job_fixture, plan_fixture, reserved_fixture


def output(key, role, path, fmt='text', *, population='file', database_key=None):
    return {'output_key': key, 'role': role, 'path_kind': 'file' if population == 'file' else 'prefix',
        'relative_path': path, 'format': fmt, 'population': population, 'database_key': database_key}


def supplied(tmp_path, key, role, fmt, raw):
    return {'input_key': key, 'role': role, 'format': fmt, **identity(tmp_path / 'inputs-original' / key, raw)}


def database(tmp_path, key):
    db = job_fixture(tmp_path / key, 'info')['databases'][0]
    db['database_key'] = db['manifest']['database_key'] = key
    db['manifest_file'] = identity(Path(db['manifest_file']['path']), json.dumps(db['manifest'], sort_keys=True).encode())
    return db


def copy_selection(db, relative):
    source = db['native_paths'][0]
    return {'database_key': db['database_key'], 'native_paths': [{'source_path': source, 'relative_path': relative}],
        'files': [{'source_path': row['path'], 'relative_path': relative + row['path'][len(source):]}
                  for row in db['manifest']['files']]}


def entry(ordinal, key, token, *, line=None, index=0):
    return {'ordinal': ordinal, 'database_key': key, 'native_path_index': index,
            'native_reference': token, 'line_number': line}


def preparation_job(tmp_path, mode, *, bound=False, old=False, profile_type='rps', binary=False):
    program = 'makembindex' if mode in {'create_megablast_index', 'show_filters'} else (
        'makeprofiledb' if mode == 'create_profile_database' else 'blastdb_aliastool')
    software = identity(tmp_path / 'fixture-executable', b'controlled executable, never run\n')
    Path(software['path']).chmod(0o755)
    job = {'version': contracts.JOB_VERSION_V2, 'operation': None,
        'software': {'executable': software['path'], 'sha256': software['sha256'], 'engine_version': 'fixture'},
        'environment': {'BLAST_USAGE_REPORT': 'false', 'NCBI_DONT_USE_NCBIRC': '1'},
        'inputs': [], 'databases': [], 'materializations': {'database_copies': [], 'list_files': []},
        'outputs': [output('stdout', 'stdout', 'logs/stdout',
            'blast_seqid_list_info_text' if mode == 'inspect_seqid_list' else 'text'),
                    output('stderr', 'stderr', 'logs/stderr')]}
    molecule, source = 'dna', None
    if mode in {'convert_gi_list', 'convert_seqid_list', 'inspect_seqid_list'}:
        fmt = 'seqid_list_binary' if mode == 'inspect_seqid_list' else 'text'
        job['inputs'] = [supplied(tmp_path, 'ids', 'identifier_list', fmt, b'# native input\n9\n3\n9\nnot-a-gi\n')]
        p = {'input_occurrence_id': 'ids'}
        molecule = 'unknown'
        if mode != 'inspect_seqid_list':
            p['output_path'] = 'result/ids.bgl' if mode == 'convert_gi_list' else 'result/ids.bsl'
            job['outputs'].append(output('list', 'identifier_list', p['output_path'],
                'gi_list_binary' if mode == 'convert_gi_list' else 'seqid_list_binary'))
        if mode == 'convert_seqid_list':
            p.update(title='native title', seqid_database_key='A' if bound else None)
            if bound:
                job['databases'] = [database(tmp_path, 'A')]; source, molecule = 'A', 'dna'
    elif mode == 'create_subset_alias':
        job['inputs'] = [supplied(tmp_path, 'ids', 'identifier_list', 'seqid_list_binary', b'opaque retained list')]
        job['databases'] = [database(tmp_path, 'A')]; source = 'A'
        p = {'output_prefix': 'result/subset', 'title': 'subset', 'source_database_key': source,
             'restriction': {'kind': 'seqid_list', 'occurrence_id': 'ids', 'format': 'seqid_list_binary'}}
    elif mode == 'aggregate_databases':
        job['databases'] = [database(tmp_path, 'A'), database(tmp_path, 'B')]
        job['inputs'] = [supplied(tmp_path, 'db-list', 'database_list', 'text', b' B \n\n\tA\t\nB\n')]
        entries = [entry(0,'B','B',line=1), entry(1,'A','A',line=3), entry(2,'B','B',line=4)]
        p = {'output_prefix': 'result/aggregate', 'title': 'aggregate',
             'classic_list': {'source': 'file', 'input_occurrence_id': 'db-list', 'entries': entries}, 'vdb_list': None}
        job['materializations']['list_files'] = [{'input_key': 'db-list', 'relative_path': 'selected/db.list',
            'grammar': 'blast_database_lines', 'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'],
                'token_ordinal': 0, 'original_token': e['native_reference'], 'target': {'kind': 'database',
                    'database_key': e['database_key'], 'native_path_index': 0}} for e in entries]}]
    elif mode == 'aggregate_volumes':
        job['databases'] = [database(tmp_path, 'A'), database(tmp_path, 'B')]; source = 'A'
        p = {'output_prefix': 'result/volumes', 'title': 'volumes', 'source_database_key': source,
             'num_volumes': 2, 'volume_entries': [entry(0,'A','volume_A'),entry(1,'B','volume_B')]}
        job['materializations']['database_copies'] = [copy_selection(db, 'result/volumes.' + str(i).zfill(2))
                                                     for i, db in enumerate(job['databases'])]
    elif mode == 'show_filters':
        job['databases'] = [database(tmp_path, 'A')]; source = 'A'
        p = {'source_database_key': source}
    elif mode == 'create_megablast_index':
        if old:
            job['inputs'] = [supplied(tmp_path, 'fasta', 'sequence_input', 'fasta', b'>one\nACGTACGT\n')]
        else:
            job['databases'] = [database(tmp_path, 'A')]; source = 'A'
            job['materializations']['database_copies'] = [copy_selection(job['databases'][0], 'copy/db')]
        p = {'input_format': 'fasta' if old else 'blastdb', 'input_occurrence_id': 'fasta' if old else None,
            'source_database_key': source, 'old_style_index': old, 'legacy': old,
            'output_prefix': 'result/old' if old else None, 'idmap': True, 'db_mask': None,
            'nmer': 8, 'ws_hint': 8, 'stride': 3, 'volume_size_mb': 1, 'verbosity': 'normal',
            'statistics_path': 'statistics/build.txt'}
        job['outputs'] += [output('index', 'index_family', 'result/old' if old else 'copy/db', 'blast_index_family',
            population='prefix_members' if old else 'staged_database_members', database_key=source),
            output('statistics', 'statistics', 'statistics/build.txt')]
    else:
        molecule = 'protein'
        fmt = 'pssm_asn1_binary' if binary else 'pssm_asn1_text'
        job['inputs'] = [supplied(tmp_path,'profiles','profile_list','text', b'model.asn\tmodel.asn\n'),
                         supplied(tmp_path,'pssm','profile_input',fmt,b'opaque complete profile bytes; never repair')]
        entries = [{'ordinal': i, 'input_occurrence_id': 'pssm', 'native_reference': 'model.asn',
                    'line_number': 1, 'token_ordinal': i} for i in range(2)]
        p = {'profile_list_occurrence_id': 'profiles', 'profile_entries': entries,
            'profile_type': profile_type, 'input_format': fmt, 'output_prefix': 'result/profile', 'title': 'profiles',
            'database_format_version': 5, 'max_smp_per_volume': 2500, 'create_sequence_indexes': True,
            'word_score_threshold': 9.82, 'force_threshold': True, 'gap_open': 11, 'gap_extend': 1,
            'scale': 1.0, 'matrix': 'BLOSUM62', 'observations_threshold': 6.0, 'exclude_invalid': True,
            'taxid': None, 'taxid_map_occurrence_id': None}
        job['materializations']['list_files'] = [{'input_key': 'profiles', 'relative_path': 'selected/profiles.list',
            'grammar': 'profile_whitespace_tokens', 'entries': [{'ordinal': i, 'line_number': 1,
                'token_ordinal': i, 'original_token': 'model.asn', 'target': {'kind': 'input', 'input_key': 'pssm'}}
                for i in range(2)]}]
    if mode in {'create_subset_alias','aggregate_databases','aggregate_volumes','create_profile_database'}:
        job['outputs'].append(output('family', 'database_family', p['output_prefix'], 'blastdb_family', population='prefix_members'))
    job['operation'] = {'version': 'blast_utility_operation_v2', 'program': program, 'mode': mode,
        'molecule': molecule, 'database_key': source, 'input_occurrence_ids': [r['input_key'] for r in job['inputs']],
        'parameters': p}
    return job


@pytest.mark.parametrize('mode', [mode for _,mode in contracts.PREPARATION_MODES])
def test_all_nine_selected_compilers_are_exactly_one_command(tmp_path, monkeypatch, mode):
    job = preparation_job(tmp_path, mode)
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('pure compile read bytes'))
    monkeypatch.setattr(driver.subprocess, 'run', lambda *a, **k: pytest.fail('pure compile invoked work'))
    request = contracts.requested_job_from_native_blast_utility(job)
    assert contracts.validate_native_blast_utility_requested_job(request) == request
    paths = preparation_path_maps(job, '/attempt')
    argv = contracts.compile_native_blast_utility_job(job, **paths, output_directory='/attempt')
    assert argv[0] == job['software']['executable']
    assert argv.count(job['software']['executable']) == 1
    if mode == 'convert_gi_list':
        assert argv[1:] == ['-gi_file_in', paths['input_paths']['ids'], '-gi_file_out', '/attempt/result/ids.bgl']
    if mode == 'inspect_seqid_list': assert argv[1:] == ['-seqid_file_info',paths['input_paths']['ids']]
    if mode == 'aggregate_databases': assert argv[-2:] == ['-dblist_file','/attempt/selected/db.list']
    if mode == 'aggregate_volumes': assert argv[-2:] == ['-num_volumes','2']
    if mode == 'create_megablast_index':
        assert argv[argv.index('-input')+1] == '/attempt/copy/db'
        assert '-output' not in argv
    if mode == 'show_filters': assert argv[-3:] == ['-iformat','blastdb','-show_filters']
    if mode == 'create_profile_database':
        assert argv[argv.index('-in')+1] == '/attempt/selected/profiles.list'
        assert argv[argv.index('-threshold')+1] == '9.82' and '-binary' not in argv


@pytest.mark.parametrize('profile_type', ['rps','delta','cobalt'])
@pytest.mark.parametrize('binary', [False,True])
def test_profile_declared_variants_preserve_exact_parameters(tmp_path, profile_type, binary):
    job = preparation_job(tmp_path,'create_profile_database',profile_type=profile_type,binary=binary)
    args = contracts.requested_job_from_native_blast_utility(job)['argv']
    assert args[args.index('-dbtype')+1] == profile_type
    assert ('-binary' in args) is binary
    assert args[args.index('-index')+1] == 'true'
    assert args[args.index('-max_smp_vol')+1] == '2500'


@pytest.mark.parametrize('kind,fmt,flag', [('gi_list','text','-gilist'),('gi_list','gi_list_binary','-gilist'),
    ('seqid_list','text','-seqidlist'),('seqid_list','seqid_list_binary','-seqidlist'),('taxid_list','text','-taxidlist'),
    ('oid_masks',None,'-oid_masks')])
def test_subset_variants_do_not_normalize_or_convert_inputs(tmp_path, kind, fmt, flag):
    job = preparation_job(tmp_path,'create_subset_alias')
    restriction = {'kind':kind,'value':1} if kind == 'oid_masks' else {'kind':kind,'occurrence_id':'ids','format':fmt}
    job['operation']['parameters']['restriction'] = restriction
    if kind == 'oid_masks':
        job['inputs'] = []; job['operation']['input_occurrence_ids'] = []
    else: job['inputs'][0]['format'] = fmt
    args = contracts.requested_job_from_native_blast_utility(job)['argv']
    assert args[-2:] == [flag,'1' if kind == 'oid_masks' else job['inputs'][0]['path']]


@pytest.mark.parametrize('mode', ['aggregate_databases','create_profile_database'])
def test_pure_realization_preserves_original_bytes_separators_repeats_and_exact_joins(tmp_path, mode):
    job = preparation_job(tmp_path,mode)
    contents = {r['input_key']:Path(r['path']).read_bytes() for r in job['inputs']}
    original = deepcopy(contents)
    value = realize_blast_utility_materializations(job,input_contents=contents,attempt_directory='/attempt')
    assert contents == original
    row = value['materialization_plan'][-1]
    if mode == 'aggregate_databases':
        a,b = [d['native_paths'][0] for d in job['databases']]
        expected = f' {b} \n\n\t{a}\t\n{b}\n'.encode()
    else:
        target = value['input_paths']['pssm']; expected = (target+'\t'+target+'\n').encode()
    assert value['list_bytes'][row['relative_path']] == expected
    assert row['sha256'] == hashlib.sha256(expected).hexdigest()
    assert [r['kind'] for r in value['materialization_plan'][:-1]] == ['input_copy'] * len(job['inputs'])
    with pytest.raises(ValueError):
        realize_blast_utility_materializations(job,input_contents={**contents,job['inputs'][0]['input_key']:b'changed'},attempt_directory='/attempt')
    job['materializations']['list_files'][0]['entries'][0]['original_token'] = 'other'
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_job(job)


@pytest.mark.parametrize('change', ['missing_copy','copy_bytes','copy_namespace','wrong_molecule','overlap','output_key','float_index'])
def test_selection_rejects_incomplete_and_conflicting_materializations(tmp_path, change):
    job = preparation_job(tmp_path,'create_megablast_index')
    if change == 'missing_copy': job['materializations']['database_copies'] = []
    elif change == 'copy_bytes': job['materializations']['database_copies'][0]['files'].pop()
    elif change == 'copy_namespace': job['materializations']['database_copies'][0]['files'][0]['relative_path'] = 'other/place.nhr'
    elif change == 'wrong_molecule': job['operation']['molecule'] = 'protein'
    elif change == 'overlap': job['outputs'][0]['relative_path'] = 'copy/db.stdout'
    elif change == 'output_key': job['outputs'][1]['output_key'] = 'stdout'
    else: job['operation']['parameters']['nmer'] = True
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_job(job)


def controlled(monkeypatch, job, *, rc=0, change=None, omit=False):
    calls = []
    def run(argv, **kw):
        calls.append(argv); root = Path(kw['cwd'])
        kw['stdout'].write(b'controlled stdout\n'); kw['stderr'].write(b'controlled failure\n' if rc else b'')
        for out in job['outputs']:
            if out['role'] in {'stdout','stderr'}: continue
            path = root / out['relative_path']; path.parent.mkdir(parents=True,exist_ok=True)
            if out['population'] == 'file': path.write_bytes(b'controlled bytes')
            elif not omit:
                suffixes = ('.00.idx','.shd','.unknown') if out['role'] == 'index_family' else (
                    ('.phr','.pin','.psq','.unknown') if job['operation']['program'] == 'makeprofiledb' else ('.nal','.unknown'))
                for suffix in suffixes: Path(str(path)+suffix).write_bytes(b'controlled output '+suffix.encode())
        if change: change(root)
        return SimpleNamespace(returncode=rc)
    monkeypatch.setattr(driver.subprocess,'run',run)
    return calls


@pytest.mark.parametrize('mode', ['convert_gi_list','create_subset_alias','aggregate_databases','aggregate_volumes',
                                   'create_megablast_index','create_profile_database'])
@pytest.mark.parametrize('rc', [0,2])
def test_one_process_seals_distinct_original_materialized_and_output_populations(tmp_path, monkeypatch, mode, rc):
    job = preparation_job(tmp_path,mode)
    before = {f['path']:Path(f['path']).read_bytes() for db in job['databases'] for f in db['manifest']['files']}
    before.update({r['path']:Path(r['path']).read_bytes() for r in job['inputs']})
    plan = plan_fixture(tmp_path,job)
    calls = controlled(monkeypatch,job,rc=rc)
    bundle = driver.run_native_blast_utility(plan)
    assert len(calls) == 1 and bundle['returncode'] == rc
    assert contracts.validate_native_blast_utility_bundle(bundle,plan) == bundle
    assert all(Path(p).read_bytes() == raw for p,raw in before.items())
    copies = {r['relative_path'] for r in bundle['materializations']}
    assert not copies & {r['relative_path'] for r in bundle['artifacts']}
    assert all(r['completeness'] == 'complete' for r in bundle['artifacts'])
    assert bundle['output_completeness_basis'] == 'captured_bytes'
    assert all('output_key' in r for r in bundle['artifacts'])
    if mode != 'convert_gi_list': assert any(r['format'] == 'unknown' for r in bundle['artifacts'])
    assert driver.run_native_blast_utility(plan) == bundle and len(calls) == 1


@pytest.mark.parametrize('what',['list','database'])
def test_changed_materializations_remain_specific_failure_and_never_original(tmp_path,monkeypatch,what):
    job = preparation_job(tmp_path,'aggregate_databases' if what == 'list' else 'create_megablast_index')
    relative = job['materializations']['list_files'][0]['relative_path'] if what == 'list' else job['materializations']['database_copies'][0]['files'][0]['relative_path']
    def alter(root):
        p=root/relative; p.chmod(0o644); p.write_bytes(b'changed')
    calls=controlled(monkeypatch,job,change=alter)
    plan=plan_fixture(tmp_path,job); bundle=driver.run_native_blast_utility(plan)
    assert len(calls)==1
    assert any(f['code']=='materialization_changed' and f['relative_path']==relative for f in bundle['failures'])
    selected=acquisition._selected_files(plan,bundle)
    row=next(r for r in selected if r['direction']=='materialization' and r['read_relative']==relative)
    assert not row['original']


def test_malformed_selected_list_prevents_execution_and_retains_other_inputs(tmp_path,monkeypatch):
    job=preparation_job(tmp_path,'create_profile_database')
    raw=b'not-the-selected-token\n'; selected=job['inputs'][0]
    selected.update(identity(Path(selected['path']),raw))
    calls=controlled(monkeypatch,job); plan=plan_fixture(tmp_path,job)
    bundle=driver.run_native_blast_utility(plan)
    assert not calls and not bundle['started']
    assert any(f['code']=='materialization_binding_invalid' for f in bundle['failures'])
    assert all(r['staged_sha256']==r['expected_sha256'] for r in bundle['inputs'])


def test_capture_saved_replay_preserves_original_staged_list_and_dependency_associations(tmp_path,monkeypatch):
    job=preparation_job(tmp_path,'aggregate_databases')
    state,handle,plan,target=reserved_fixture(tmp_path,monkeypatch,job=job)
    calls=controlled(monkeypatch,job); bundle=driver.run_native_blast_utility(plan)
    store=Store(tmp_path/'store'); directory=tmp_path/'capture'
    captured=acquisition.capture_local_utility_bundle(store,target=target,directory=directory)
    assert captured['bundle_validated'] and not captured['failures']
    selected=acquisition._selected_files(plan,bundle)
    assert len(captured['artifacts'])==len(selected)
    original=next(r for r in captured['artifacts'] if r['direction']=='input')
    staged=next(r for r in captured['artifacts'] if r['direction']=='materialization' and r['role']=='database_list')
    rewritten=next(r for r in captured['artifacts'] if r['role']=='materialized_list')
    assert original['artifact_ref']==staged['artifact_ref']!=rewritten['artifact_ref']
    assert original['original_path']!=staged['original_path']!=rewritten['original_path']
    assert {r['database_key'] for r in captured['artifacts'] if r['direction']=='database'}=={'A','B'}
    shutil.rmtree(Path(plan['attempt_directory']))
    for db in job['databases']: shutil.rmtree(Path(db['manifest_file']['path']).parent)
    monkeypatch.setattr(driver.subprocess,'run',lambda *a,**k:pytest.fail('replay invoked native'))
    assert acquisition.capture_local_utility_bundle(store,target=target,directory=directory)==captured
    assert len(calls)==1


def test_selected_vs_realized_maps_and_forged_bundle_members_reject(tmp_path,monkeypatch):
    job=preparation_job(tmp_path,'create_megablast_index')
    paths=preparation_path_maps(job,'/attempt'); paths['database_paths']['A']=job['databases'][0]['native_paths']
    with pytest.raises(ValueError): contracts.compile_native_blast_utility_job(job,**paths,output_directory='/attempt')
    plan=plan_fixture(tmp_path,job); controlled(monkeypatch,job)
    bundle=driver.run_native_blast_utility(plan)
    for edit in ('output_key','materialized_file','copy_digest'):
        wrong=deepcopy(bundle)
        if edit=='output_key': wrong['artifacts'][-1]['output_key']='unselected'
        elif edit=='materialized_file': wrong['artifacts'][-1]['relative_path']=wrong['materializations'][0]['relative_path']
        else: wrong['materializations'][0]['staged']['sha256']='0'*64
        with pytest.raises(ValueError): contracts.validate_native_blast_utility_bundle(wrong,plan)


def test_legacy_jobs_reject_v2_operation_without_changing_v1_shape(tmp_path):
    legacy=job_fixture(tmp_path/'legacy')
    old=contracts.requested_job_from_native_blast_utility(legacy)
    assert 'materializations' not in old['native_blast_utility']
    assert all('output_key' not in row for row in old['native_blast_utility']['outputs'])
    assert contracts.validate_native_blast_utility_requested_job(old)==old
    legacy['operation']=preparation_job(tmp_path/'new','convert_gi_list')['operation']
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_job(legacy)


def test_bound_seqid_and_inline_aggregate_use_exact_prepared_paths(tmp_path):
    bound=preparation_job(tmp_path/'bound','convert_seqid_list',bound=True)
    args=contracts.requested_job_from_native_blast_utility(bound)['argv']
    assert args[-4:]==['-seqid_db',bound['databases'][0]['native_paths'][0],'-seqid_dbtype','nucl']
    job=preparation_job(tmp_path/'aggregate','aggregate_databases')
    job['inputs']=[]; job['operation']['input_occurrence_ids']=[]
    job['materializations']['list_files']=[]
    job['operation']['parameters']['classic_list']={'source':'inline','entries':[
        entry(0,'B','B'),entry(1,'A','A'),entry(2,'B','B')]}
    args=contracts.requested_job_from_native_blast_utility(job)['argv']
    a,b=[r['native_paths'][0] for r in job['databases']]
    assert args[-2:]==['-dblist',f'{b} {a} {b}']


@pytest.mark.parametrize('legacy',[False,True])
def test_old_style_is_independent_from_legacy_and_keeps_selected_outputs(tmp_path,monkeypatch,legacy):
    job=preparation_job(tmp_path,'create_megablast_index',old=True)
    job['operation']['parameters']['legacy']=legacy
    args=contracts.requested_job_from_native_blast_utility(job)['argv']
    assert args[args.index('-old_style_index')+1]=='true'
    assert args[args.index('-legacy')+1]==str(legacy).lower()
    assert args[args.index('-output')+1]=='result/old'
    calls=controlled(monkeypatch,job); plan=plan_fixture(tmp_path,job)
    result=driver.run_native_blast_utility(plan)
    assert len(calls)==1 and result['returncode']==0


@pytest.mark.parametrize('mode',['create_megablast_index','convert_gi_list'])
def test_integer_copy_measurements_reject_float_and_boolean_values(tmp_path,monkeypatch,mode):
    job=preparation_job(tmp_path,mode)
    plan=plan_fixture(tmp_path,job); controlled(monkeypatch,job)
    result=driver.run_native_blast_utility(plan)
    for invalid in (True,float(result['materializations'][0]['expected']['size_bytes'])):
        wrong=deepcopy(result)
        wrong['materializations'][0]['expected']['size_bytes']=invalid
        wrong['materializations'][0]['staged']['size_bytes']=invalid
        wrong['materializations'][0]['final']['size_bytes']=invalid
        with pytest.raises(ValueError): contracts.validate_native_blast_utility_bundle(wrong,plan)


@pytest.mark.parametrize('changed',['original','staged_list'])
def test_changed_original_input_or_staged_source_retains_the_attempt(tmp_path,monkeypatch,changed):
    job=preparation_job(tmp_path,'create_profile_database')
    selected=job['inputs'][0]
    def alter(root):
        path=Path(selected['path']) if changed=='original' else root/contracts.staged_relative(selected)
        path.chmod(0o644);path.write_bytes(b'changed original')
    controlled(monkeypatch,job,change=alter)
    plan=plan_fixture(tmp_path,job); bundle=driver.run_native_blast_utility(plan)
    expected='original_input_changed' if changed=='original' else 'immutable_input_changed'
    assert any(r['code']==expected for r in bundle['failures'])
    assert bundle['started'] and bundle['writer_closed'] and bundle['artifacts']
    assert contracts.validate_native_blast_utility_bundle(bundle,plan)==bundle


def test_additional_vdb_manifest_is_validated_but_unconfigured_execution_is_not_attempted(tmp_path,monkeypatch):
    job=preparation_job(tmp_path,'aggregate_databases'); db=job['databases'][0]
    manifest=db['manifest']; manifest['version']='native_blast_prepared_database_manifest_v1'
    manifest['kind']=db['kind']='vdb'
    manifest['identity']['preparation_type']='unknown'
    manifest['preparation']['preparation_type']='vdb'
    manifest['native_paths']=db['native_paths']=[str(Path(manifest['files'][0]['path']).parent)]
    db['manifest_file']=identity(Path(db['manifest_file']['path']),json.dumps(manifest,sort_keys=True).encode())
    job['databases']=[db];job['inputs']=[];job['operation']['input_occurrence_ids']=[]
    job['materializations']['list_files']=[]
    job['operation']['parameters'].update(classic_list=None,vdb_list={'source':'inline','entries':[entry(0,'A','vdb')]})
    args=contracts.requested_job_from_native_blast_utility(job)['argv']
    assert args[-2:]==['-vdblist',db['native_paths'][0]]
    calls=controlled(monkeypatch,job);plan=plan_fixture(tmp_path,job)
    bundle=driver.run_native_blast_utility(plan)
    assert not calls and not bundle['started']
    assert any(r['code']=='database_unavailable' for r in bundle['failures'])
    job['databases'][0]['manifest']['access']['offline_configuration']=None
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_job(job)


@pytest.mark.parametrize('complete',[False,True])
def test_readonly_alias_dependencies_require_exact_selected_closure(tmp_path,monkeypatch,complete):
    job=preparation_job(tmp_path,'show_filters');db=job['databases'][0]
    prefix=Path(db['native_paths'][0]); alias=prefix.parent/'alias'
    data=b'DBLIST "tiny"\nNSEQ 3\nLENGTH 33\n' if complete else b'DBLIST "unselected"\n'
    file=identity(Path(str(alias)+'.nal'),data)
    db['native_paths']=db['manifest']['native_paths']=[str(alias)]
    db['manifest']['files'].append({k:v for k,v in file.items() if k!='artifact_ref'})
    db['manifest_file']=identity(Path(db['manifest_file']['path']),json.dumps(db['manifest'],sort_keys=True).encode())
    calls=controlled(monkeypatch,job);plan=plan_fixture(tmp_path,job)
    bundle=driver.run_native_blast_utility(plan)
    assert bool(calls) is complete
    assert bundle['started'] is complete
    if not complete: assert any(f['code']=='database_identity_mismatch' for f in bundle['failures'])


def test_one_manifest_can_explicitly_select_multiple_volume_prefixes(tmp_path,monkeypatch):
    job=preparation_job(tmp_path,'aggregate_volumes');a,b=job['databases']
    a['manifest']['files']+=b['manifest']['files']
    a['manifest']['native_paths']=a['native_paths']=[a['native_paths'][0],b['native_paths'][0]]
    a['manifest_file']=identity(Path(a['manifest_file']['path']),json.dumps(a['manifest'],sort_keys=True).encode())
    job['databases']=[a]
    job['operation']['parameters']['volume_entries']=[entry(0,'A','volume0',index=0),entry(1,'A','volume1',index=1)]
    acopy,bcopy=job['materializations']['database_copies']
    acopy['native_paths']+=bcopy['native_paths'];acopy['files']+=bcopy['files']
    job['materializations']['database_copies']=[acopy]
    calls=controlled(monkeypatch,job);plan=plan_fixture(tmp_path,job)
    bundle=driver.run_native_blast_utility(plan)
    assert len(calls)==1 and bundle['returncode']==0
    assert len([r for r in bundle['materializations'] if r['kind']=='database_copy'])==len(a['manifest']['files'])


def test_old_style_database_input_and_profile_taxid_map_stay_selected(tmp_path):
    job=preparation_job(tmp_path/'index','create_megablast_index')
    p=job['operation']['parameters'];p.update(old_style_index=True,output_prefix='result/old-db',db_mask='11')
    job['materializations']['database_copies']=[]
    job['outputs'][2]=output('index','index_family','result/old-db','blast_index_family',population='prefix_members')
    args=contracts.requested_job_from_native_blast_utility(job)['argv']
    assert args[args.index('-input')+1]==job['databases'][0]['native_paths'][0]
    assert args[args.index('-db_mask')+1]=='11'
    profile=preparation_job(tmp_path/'profile','create_profile_database')
    mapping=supplied(tmp_path/'profile','taxa','taxid_map','text',b'lcl|original 9606\n')
    profile['inputs'].append(mapping);profile['operation']['input_occurrence_ids'].append('taxa')
    profile['operation']['parameters'].update(taxid_map_occurrence_id='taxa',database_format_version=4,
        create_sequence_indexes=False,force_threshold=False,gap_open=None,gap_extend=None,exclude_invalid=False)
    args=contracts.requested_job_from_native_blast_utility(profile)['argv']
    assert args[-2:]==['-taxid_map',mapping['path']]
    assert args[args.index('-index')+1]=='false' and '-force' not in args and '-gapopen' not in args


@pytest.mark.parametrize('mode',['convert_seqid_list','create_subset_alias','aggregate_databases',
                                 'aggregate_volumes','create_profile_database'])
@pytest.mark.parametrize('title',[None,'','exact selected title'])
def test_v2_title_omission_empty_and_nonempty_are_distinct(tmp_path,monkeypatch,mode,title):
    job=preparation_job(tmp_path,mode)
    p=job['operation']['parameters']
    if title is None:
        p.pop('title')
        with pytest.raises(ValueError): contracts.requested_job_from_native_blast_utility(job)
        return
    p['title']=title
    request=contracts.requested_job_from_native_blast_utility(job)
    assert contracts.validate_native_blast_utility_requested_job(request)==request
    assert contracts.Draft202012Validator(contracts.NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA).is_valid(request)
    flag='-seqid_title' if mode=='convert_seqid_list' else '-title'
    assert request['argv'][request['argv'].index(flag)+1]==title
    wrong=deepcopy(request)
    del wrong['argv'][wrong['argv'].index(flag):wrong['argv'].index(flag)+2]
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_requested_job(wrong)
    calls=controlled(monkeypatch,job)
    plan=plan_fixture(tmp_path,job)
    bundle=driver.run_native_blast_utility(plan)
    assert len(calls)==1 and calls[0][calls[0].index(flag)+1]==title
    assert bundle['realized_argv']==calls[0]
    assert contracts.validate_native_blast_utility_bundle(bundle,plan)==bundle


def test_legacy_requested_job_keeps_the_nonempty_argument_rule(tmp_path):
    request=contracts.requested_job_from_native_blast_utility(job_fixture(tmp_path))
    assert contracts.validate_native_blast_utility_requested_job(request)==request
    wrong=deepcopy(request)
    wrong['argv'].append('')
    assert not contracts.Draft202012Validator(contracts.NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA).is_valid(wrong)
    with pytest.raises(ValueError): contracts.validate_native_blast_utility_requested_job(wrong)
