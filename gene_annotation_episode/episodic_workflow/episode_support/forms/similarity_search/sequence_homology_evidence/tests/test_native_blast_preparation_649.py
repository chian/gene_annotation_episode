"""Bounded controlled native-producer tests, never scientific/native measurements.

The actual native matrix remains the sealed 644 packet. All subprocess.run calls
in this module are explicitly replaced; no database search or helper is run.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence import native_blast_utility_contracts as contracts
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import native_blast_utility_driver as driver
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.sequence_homology_evidence import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.native_blast_utility_materializations import preparation_path_maps, realize_blast_utility_materializations
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_native_blast_utility_producer_628 import identity, job_fixture, plan_fixture
import gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_utility_capture_contracts as _scientific_native_blast_utility_acquisition


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


