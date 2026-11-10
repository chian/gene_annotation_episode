"""Nine selected native preparations through the ordinary shared Workflow.

Choices and scientific stopping are scripted engineering fixtures, as in634.
Native commands, custody, selected returns and practical terminal estimates are
real. Reuse sealed644 inputs; no database build, database search, profile repair,
automatic retry, model inference or remote execution belongs to this test.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.blast_preparation_result_assembly import assemble_blast_preparation_result
from gene_annotation_episode.blast_utility_result_views import project_blast_utility_result
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_blast_utility_contracts import BUNDLE_VERSION, requested_job_from_native_blast_utility
from gene_annotation_episode.native_blast_utility_local import local_blast_utility_plan
from gene_annotation_episode.native_blast_utility_result_worker import qualified_utility_context
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_blast_utility_result_views_629 import selector as result_selector
from test_native_blast_preparation_649 import copy_selection, entry, output
from test_native_blast_utility_producer_628 import POLICY
from test_native_blast_utility_workflow_634 import PUBLICATION, RESULT_FIELDS, child, form_for, selected
from test_native_hmmer_preparation_nested_workflow import provider_value, walk, history


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'verification/tool_graders_blast_preparation_native_2026-10-28_644'
ORIGINAL_RECEIPT = ROOT / ('verification/tool_graders_hmmer_map_verification_2026-10-28_529/'
    'check096_blast_utility_full_workflow/temporary/pytest/utility-workflow6340/state/artifacts/'
    'cd/cd03376e4f53255ec61e461dd529c127caba217f43ecedffca62567cae64df43')
RUN_ID = 'preparation-workflow654'
MODES = ('convert_gi_list', 'convert_seqid_list', 'inspect_seqid_list',
    'create_subset_alias', 'aggregate_databases', 'aggregate_volumes',
    'create_megablast_index', 'show_filters', 'create_profile_database')
SCIENCE_FIELDS = ('status', 'database_fields', 'preparation', 'failures', 'missing', 'saved_data')
EXECUTABLE_PINS = {
    'blastdb_aliastool': '71c9fa9760f4215b714e762a230486e7ae739c8a363396dd00a4bbb0329f2524',
    'makembindex': '97084c88ec845b38a1acf570b19f2edeb4f8bb87c1d551192886ce80400e29d3',
    'makeprofiledb': 'd81da87fc0260ebea804fb8a36769a7d7ce8ee404bfd2dfb87da0c95036eff0a',
}
VARIANTS = {
    'convert_gi_list': {}, 'convert_seqid_list': {'database_binding': 'unbound'},
    'inspect_seqid_list': {},
    'create_subset_alias': {'restriction_kind': 'seqid_list', 'input_format': 'seqid_list_binary'},
    'aggregate_databases': {'classic_source': 'file', 'vdb_source': None},
    'aggregate_volumes': {},
    'create_megablast_index': {'input_format': 'blastdb', 'old_style_index': False, 'legacy': False},
    'show_filters': {},
    'create_profile_database': {'profile_type': 'rps', 'input_format': 'pssm_asn1_text'},
}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def same_bytes(actual, expected):
    assert {k: actual[k] for k in ('sha256', 'size_bytes')} == {
        k: expected[k] for k in ('sha256', 'size_bytes')}


def copy_input(directory, relative, expected, relocations):
    original = PACKET / relative
    same_bytes(pin(original), expected)
    target = directory / 'supplied' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, target)
    relocations.append({'original': expected, 'retained': pin(original), 'selected': pin(target)})
    return target


def stage_inputs(directory):
    """Supply exact physical files through current caller custody in a fresh Store.

    The original manifest remains unchanged bytes. Current source pointers name
    that supplied document's /identity and /preparation objects. Native identity,
    software and original argv remain facts from that document. Prior Store state
    and its source IDs are neither copied nor admitted as received information.
    """
    store = Store(directory / 'state')
    store.create_problem(raw_sequence='TTGCAATTGCAA', molecule='dna')
    original_path = PACKET / 'retained_native/inputs/original096-manifest.json'
    original = json.loads(original_path.read_text())
    supplied_manifest = store.register_material(original_path, name='supplied original096 preparation manifest',
        use='evidence', format='auto', molecule='unspecified')
    source_ref = supplied_manifest['source_ref']
    source = store.get(source_ref)
    assert source['origin'] == source['provider'] == 'caller'
    assert store.get_artifact(source['artifact_ref']) == original_path.read_bytes()
    assert source_ref != original['identity']['source']['source_ref']
    captures = {name: json.loads((PACKET / name).read_text()) for name in (
        'retained_native/CAPTURE_001.json', 'retained_binary_alias/CAPTURE_002.json',
        'retained_profile28/CAPTURE_003.json')}
    primary = {row['id']: row for row in captures['retained_native/CAPTURE_001.json']['cases']}
    bound = captures['retained_binary_alias/CAPTURE_002.json']['cases'][0]
    profile = captures['retained_profile28/CAPTURE_003.json']['cases'][0]
    receipts = {}
    for name in ('runner_evidence', 'binary_alias_runner_evidence', 'profile28_runner_evidence'):
        receipt = json.loads((PACKET / name / 'receipt.json').read_text())
        assert receipt['returncode'] == 0 and receipt['terminal'] and receipt['quiescent']
        assert all(receipt[key + '_unchanged'] for key in ('source', 'dependency', 'stdlib', 'binary'))
        assert receipt['metadata']['policy'] == POLICY
        assert receipt['metadata']['verified_cgroup']['memory_swap_max'] == 0
        receipts[name] = receipt
    relocations = []

    def from_capture(case, relative, retained):
        expected, = [row for row in case['inventory_before'] if row['relative_path'] == relative]
        return copy_input(directory, retained, expected, relocations)

    paths = {
        'gi': from_capture(primary['01_gi_convert'], 'gi.txt', 'retained_native/cases/gi/gi.txt'),
        'seqid': from_capture(primary['02_seqid_unbound'], 'ids.txt', 'retained_native/cases/seqid_unbound/ids.txt'),
        'bound': from_capture(bound, 'bound.bsl', 'retained_binary_alias/bound.bsl'),
        'db_list': from_capture(primary['09_alias_file'], 'dblist.txt', 'retained_native/cases/aggregate_file/dblist.txt'),
        'profiles': from_capture(profile, 'profiles.list', 'retained_profile28/profiles.list'),
        'pssm': from_capture(profile, 'inputs/webpsi.2ndround.pssm.asn', 'retained_profile28/inputs/webpsi.2ndround.pssm.asn'),
    }
    assert pin(paths['bound'])['sha256'] == '83ba9e9aa335a18121b1cdf0727652e4ab8399f5c92deec9b0bc00716addc68e'
    assert pin(paths['pssm'])['sha256'] == 'a7ce96b9dae4e3a818c2dfb6e031606541791ba02840181fa1a9a83f9e30b85b'
    # An explicitly selected repeated dependency, not a modification of644.
    repeated = directory / 'supplied/selected-repeated-databases.list'
    repeated.write_bytes(paths['db_list'].read_bytes() + b'db_b/tiny\n')
    list_selection = {'original': pin(paths['db_list']), 'selected': pin(repeated),
        'selection': 'append one explicit repeated db_b/tiny entry; original bytes retained',
        'database_key_order': ['B', 'A', 'B'], 'independent_biological_populations': False}
    paths['repeated_db_list'] = repeated

    initial = {source_ref}
    databases = []
    for key in ('A', 'B'):
        manifest = deepcopy(original)
        manifest['database_key'] = key
        manifest['identity']['source'] = {'source_ref': source_ref, 'pointer': '/identity'}
        manifest['preparation']['source'] = {'source_ref': source_ref, 'pointer': '/preparation'}
        prefix = directory / 'supplied' / ('db_' + key.lower()) / 'tiny'
        prefix.parent.mkdir(parents=True)
        manifest['native_paths'] = [str(prefix)]
        for row in manifest['files']:
            original_file = deepcopy(row)
            retained = PACKET / 'retained_native/cases/seqid_bound/db' / Path(row['path']).name
            target = prefix.parent / retained.name
            same_bytes(pin(retained), row)
            shutil.copyfile(retained, target)
            row['path'] = str(target)
            relocations.append({'database_key': key, 'original': original_file,
                'retained': pin(retained), 'selected': pin(target)})
        for descriptor in [manifest['preparation']['receipt'], *manifest['metadata_manifests']]:
            retained = (ORIGINAL_RECEIPT if descriptor is manifest['preparation']['receipt'] else
                PACKET / 'retained_native/cases/seqid_bound/db' / Path(descriptor['path']).name)
            same_bytes(pin(retained), descriptor)
            raw = retained.read_bytes()
            target = prefix.parent / Path(descriptor['path']).name
            target.write_bytes(raw)
            same_bytes(pin(target), descriptor)
            relocations.append({'database_key': key, 'original': deepcopy(descriptor),
                'retained': pin(retained), 'selected': pin(target)})
            descriptor['path'] = str(target)
            descriptor['artifact_ref'] = None
        path = prefix.parent / 'selected-manifest.json'
        save(path, manifest)
        databases.append({'database_key': key, 'role': 'target',
            'kind': manifest['kind'], 'identity': deepcopy(manifest['identity']),
            'native_paths': manifest['native_paths'], 'manifest': manifest,
            'manifest_file': {**pin(path), 'artifact_ref': None}})
    assert databases[0]['identity'] == databases[1]['identity']
    assert {k: v for k, v in databases[0]['identity'].items() if k != 'source'} == {
        k: v for k, v in original['identity'].items() if k != 'source'}
    for ref in initial:
        registered = store.get(ref)
        assert registered['origin'] == 'caller' and registered['provider'] == 'caller'
        assert registered['version'] != BUNDLE_VERSION
    assert initial == {supplied_manifest['source_ref']}
    assert not initial & {original['identity']['source']['source_ref'], original['preparation']['source']['source_ref']}
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source' AND json_extract(data,'$.version')=?",
        (BUNDLE_VERSION,)).fetchone()[0] == 0
    protected = {str(p): pin(p) for p in (directory / 'supplied').rglob('*') if p.is_file()}
    selection = {'prior_store_copied': False, 'original_manifest': original,
        'supplied_manifest_custody': {'material': supplied_manifest, 'source': source,
            'original_file': pin(original_path), 'identity_pointer': '/identity', 'preparation_pointer': '/preparation'},
        'initial_received_references': sorted(initial), 'relocations': relocations,
        'repeated_database_selection': list_selection, 'sealed_runner_receipts': receipts,
        'profile_source_boundary': captures['retained_profile28/CAPTURE_003.json']['source_boundary'],
        'historical_failures_preserved': {key: primary[key]['returncode'] for key in (
            '06_subset_alias', '13_profile_rps', '14_profile_delta', '15_profile_cobalt')}}
    save(directory / 'INPUT_SELECTION_001.json', selection)
    return store, paths, databases, sorted(initial), protected


def selected_software():
    attempt = os.environ.get('HMMER529_ATTEMPT')
    if not attempt:
        pytest.skip('native Workflow verification requires bounded529')
    selected_binaries = json.loads((Path(attempt) / 'selected_native_executables.json').read_text())
    assert len(selected_binaries) == 3 and {Path(p).name for p in selected_binaries} == set(EXECUTABLE_PINS)
    result = {}
    for path in map(Path, selected_binaries):
        assert path.is_relative_to(ROOT) and pin(path)['sha256'] == EXECUTABLE_PINS[path.name]
        result[path.name] = {'executable': str(path), 'sha256': EXECUTABLE_PINS[path.name], 'engine_version': '2.17.0+'}
    return result


def original_job(mode, software, paths, databases):
    program = ('makembindex' if mode in {'create_megablast_index', 'show_filters'} else
        'makeprofiledb' if mode == 'create_profile_database' else 'blastdb_aliastool')
    job = {'version': 'native_blast_utility_job_v2', 'operation': None,
        'software': software[program],
        'environment': {'NCBI_DONT_USE_NCBIRC': '1', 'BLAST_USAGE_REPORT': 'false'},
        'inputs': [], 'databases': [], 'materializations': {'database_copies': [], 'list_files': []},
        'outputs': [output('stdout', 'stdout', 'logs/native.stdout',
            'blast_seqid_list_info_text' if mode == 'inspect_seqid_list' else 'text'),
            output('stderr', 'stderr', 'logs/native.stderr')]}

    def supplied(key, role, fmt, path):
        return {'input_key': key, 'role': role, 'format': fmt, **pin(path), 'artifact_ref': None}

    source, molecule = None, 'unknown'
    if mode in {'convert_gi_list', 'convert_seqid_list', 'inspect_seqid_list'}:
        path = paths[{'convert_gi_list': 'gi', 'convert_seqid_list': 'seqid', 'inspect_seqid_list': 'bound'}[mode]]
        job['inputs'] = [supplied('ids', 'identifier_list', 'seqid_list_binary' if mode == 'inspect_seqid_list' else 'text', path)]
        p = {'input_occurrence_id': 'ids'}
        if mode != 'inspect_seqid_list':
            p['output_path'] = 'result/ids.bgl' if mode == 'convert_gi_list' else 'result/ids.bsl'
            job['outputs'].append(output('list', 'identifier_list', p['output_path'],
                'gi_list_binary' if mode == 'convert_gi_list' else 'seqid_list_binary'))
        if mode == 'convert_seqid_list':
            p.update(title='654 original selected identifiers', seqid_database_key=None)
    elif mode == 'create_profile_database':
        molecule = 'protein'
        job['inputs'] = [supplied('profiles', 'profile_list', 'text', paths['profiles']),
            supplied('pssm', 'profile_input', 'pssm_asn1_text', paths['pssm'])]
        token = 'inputs/webpsi.2ndround.pssm.asn'
        entries = [{'ordinal': 0, 'input_occurrence_id': 'pssm', 'native_reference': token,
            'line_number': 1, 'token_ordinal': 0}]
        p = {'profile_list_occurrence_id': 'profiles', 'profile_entries': entries,
            'profile_type': 'rps', 'input_format': 'pssm_asn1_text', 'output_prefix': 'result/profiles',
            'title': '654 unchanged authentic 28-row profile', 'database_format_version': 5,
            'max_smp_per_volume': 2500, 'create_sequence_indexes': True, 'word_score_threshold': 9.82,
            'force_threshold': True, 'gap_open': None, 'gap_extend': None, 'scale': 1.0,
            'matrix': 'BLOSUM62', 'observations_threshold': 6.0, 'exclude_invalid': True,
            'taxid': None, 'taxid_map_occurrence_id': None}
        job['materializations']['list_files'] = [{'input_key': 'profiles', 'relative_path': 'selected/profiles.list',
            'grammar': 'profile_whitespace_tokens', 'entries': [{'ordinal': 0, 'line_number': 1,
                'token_ordinal': 0, 'original_token': token, 'target': {'kind': 'input', 'input_key': 'pssm'}}]}]
    else:
        molecule = 'dna'
        source = None if mode == 'aggregate_databases' else 'A'
        job['databases'] = deepcopy(databases if mode in {'aggregate_databases', 'aggregate_volumes'} else databases[:1])
        if mode == 'create_subset_alias':
            job['inputs'] = [supplied('ids', 'identifier_list', 'seqid_list_binary', paths['bound'])]
            p = {'output_prefix': 'result/subset', 'title': '654 retained binary subset',
                'source_database_key': 'A',
                'restriction': {'kind': 'seqid_list', 'occurrence_id': 'ids', 'format': 'seqid_list_binary'}}
        elif mode == 'aggregate_databases':
            job['inputs'] = [supplied('db-list', 'database_list', 'text', paths['repeated_db_list'])]
            entries = [entry(0, 'B', 'db_b/tiny', line=1), entry(1, 'A', 'db_a/tiny', line=3),
                entry(2, 'B', 'db_b/tiny', line=4)]
            p = {'output_prefix': 'result/aggregate', 'title': '654 repeated copies of original096',
                'classic_list': {'source': 'file', 'input_occurrence_id': 'db-list', 'entries': entries}, 'vdb_list': None}
            job['materializations']['list_files'] = [{'input_key': 'db-list', 'relative_path': 'selected/db.list',
                'grammar': 'blast_database_lines', 'entries': [{'ordinal': e['ordinal'], 'line_number': e['line_number'],
                    'token_ordinal': 0, 'original_token': e['native_reference'], 'target': {'kind': 'database',
                        'database_key': e['database_key'], 'native_path_index': 0}} for e in entries]}]
        elif mode == 'aggregate_volumes':
            p = {'output_prefix': 'result/volumes', 'title': '654 two explicitly selected copies',
                'source_database_key': 'A', 'num_volumes': 2,
                'volume_entries': [entry(0, 'A', 'volume_A'), entry(1, 'B', 'volume_B')]}
            job['materializations']['database_copies'] = [copy_selection(db, 'result/volumes.' + str(i).zfill(2))
                for i, db in enumerate(job['databases'])]
        elif mode == 'show_filters':
            p = {'source_database_key': 'A'}
        else:
            p = {'input_format': 'blastdb', 'input_occurrence_id': None, 'source_database_key': 'A',
                'old_style_index': False, 'legacy': False, 'output_prefix': None, 'idmap': False,
                'db_mask': None, 'nmer': 8, 'ws_hint': 8, 'stride': 3, 'volume_size_mb': 1,
                'verbosity': 'verbose', 'statistics_path': None}
            job['materializations']['database_copies'] = [copy_selection(job['databases'][0], 'copy/tiny')]
            job['outputs'].append(output('index', 'index_family', 'copy/tiny', 'blast_index_family',
                population='staged_database_members', database_key='A'))
    if mode in {'create_subset_alias', 'aggregate_databases', 'aggregate_volumes', 'create_profile_database'}:
        job['outputs'].append(output('family', 'database_family', p['output_prefix'], 'blastdb_family', population='prefix_members'))
    job['operation'] = {'version': 'blast_utility_operation_v2', 'program': program, 'mode': mode,
        'molecule': molecule, 'database_key': source, 'input_occurrence_ids': [r['input_key'] for r in job['inputs']],
        'parameters': p}
    return job


def selected_result(mode):
    fields = {'convert_gi_list': ['identifier_list_converted_count'],
        'inspect_seqid_list': ['identifier_list_count', 'identifier_list_database_length'],
        'create_subset_alias': ['database_sequence_count', 'database_residue_count'],
        'aggregate_databases': ['database_sequence_count', 'database_residue_count'],
        'aggregate_volumes': ['database_sequence_count', 'database_residue_count']}.get(mode, [])
    preparation = None if mode in {'inspect_seqid_list', 'show_filters'} else {
        'fields': ['kind', 'detail', 'dependencies', 'database_bindings', 'materializations']}
    artifact_roles = {'convert_gi_list': ['identifier_list'], 'convert_seqid_list': ['identifier_list'],
        'inspect_seqid_list': ['stdout'], 'create_subset_alias': ['alias_file'],
        'aggregate_databases': ['alias_file'], 'aggregate_volumes': ['alias_file'],
        'create_megablast_index': ['index_file', 'stderr'], 'show_filters': ['stdout'],
        'create_profile_database': ['profile_file', 'database_file']}[mode]
    return result_selector(database_fields=fields, preparation=preparation, saved_data=['result'], include_checks=True,
        artifacts=[{'direction': 'output', 'role': role, 'ordinal': None} for role in artifact_roles])


def retained_workflow_history(store, directory):
    """Snapshot completed rows and immutable files, not mutable run state."""
    selected_tables = {
        'runtime_actions': 'result IS NOT NULL', 'runtime_observations': '1',
        'runtime_model_calls': 'response IS NOT NULL', 'runtime_estimation_contexts': '1',
        'runtime_forms': 'form IS NOT NULL', 'runtime_report_attempts': 'form IS NOT NULL',
        'runtime_episodes': "state='yielded'", 'runtime_record_receipts': '1',
    }
    tables = []
    for table, condition in selected_tables.items():
        keys = [row['name'] for row in store.db.execute('PRAGMA table_info(' + table + ')') if row['pk']]
        assert keys
        rows = [dict(row) for row in store.db.execute('SELECT * FROM ' + table + ' WHERE run_id=? AND ' + condition, (RUN_ID,))]
        tables.append({'table': table, 'keys': keys, 'rows': rows})
    for table in ('problem', 'inputs', 'records', 'artifacts', 'record_roots'):
        keys = [row['name'] for row in store.db.execute('PRAGMA table_info(' + table + ')') if row['pk']]
        rows = [dict(row) for row in store.db.execute('SELECT * FROM ' + table)]
        tables.append({'table': table, 'keys': keys, 'rows': rows})
    pending = [dict(row) for row in store.db.execute(
        'SELECT * FROM runtime_model_calls WHERE run_id=? AND response IS NULL', (RUN_ID,))]
    assignments = [dict(row) for row in store.db.execute(
        'SELECT run_id,episode_id,path,request,initial_credit FROM runtime_episodes WHERE run_id=?', (RUN_ID,))]
    unfinished_actions = [dict(row) for row in store.db.execute(
        'SELECT run_id,episode_id,decision_index,action FROM runtime_actions WHERE run_id=? AND result IS NULL', (RUN_ID,))]
    files = {}
    for relative in ('workspace', 'run', 'supplied', 'state/artifacts'):
        for path in (directory / relative).rglob('*'):
            if path.is_file():
                files[str(path)] = pin(path)
    for name in ('INPUT_SELECTION_001.json', 'SELECTED_JOBS_001.json', 'NATIVE_ATTEMPTS_001.json', 'DECISION_CALLS_001.json'):
        files[str(directory / name)] = pin(directory / name)
    return {'tables': tables, 'files': files, 'pending_model_calls': pending,
        'episode_assignments': assignments, 'unfinished_actions': unfinished_actions}


def assert_retained_workflow_history(store, baseline):
    for table in baseline['tables']:
        query = 'SELECT * FROM ' + table['table'] + ' WHERE ' + ' AND '.join(key + '=?' for key in table['keys'])
        for original in table['rows']:
            actual = store.db.execute(query, [original[key] for key in table['keys']]).fetchone()
            assert actual is not None and dict(actual) == original, (table['table'], table['keys'])
    for original in baseline['pending_model_calls']:
        actual = store.db.execute('SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?',
            [original[key] for key in ('run_id', 'episode_id', 'call_index')]).fetchone()
        assert actual is not None
        for key in ('run_id', 'episode_id', 'call_index', 'purpose', 'request'):
            assert actual[key] == original[key], ('interrupted decision contract changed', key)
        old_intervals = json.loads(original['timing'])['intervals']
        assert json.loads(actual['timing'])['intervals'][:len(old_intervals)] == old_intervals
    for original in baseline['episode_assignments']:
        actual = store.db.execute('SELECT run_id,episode_id,path,request,initial_credit FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (original['run_id'], original['episode_id'])).fetchone()
        assert actual is not None and dict(actual) == original
    for original in baseline['unfinished_actions']:
        actual = store.db.execute('SELECT run_id,episode_id,decision_index,action FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? AND decision_index=?',
            (original['run_id'], original['episode_id'], original['decision_index'])).fetchone()
        assert actual is not None and dict(actual) == original
    for path, expected in baseline['files'].items():
        same_bytes(pin(Path(path)), expected)


def run_case(directory, *, continuation_output=None):
    continuing = continuation_output is not None
    output_directory = Path(continuation_output) if continuing else directory
    prior_native = None
    if continuing:
        # Reconstruct the same interrupted tree at its original paths. This is
        # not a fresh annotation run and imports no prior records into a new one.
        attempt = Path(os.environ['HMMER529_ATTEMPT'])
        runner_request = json.loads((attempt / 'selected_request.json').read_text())
        assert directory.is_absolute() and directory.is_relative_to(Path.cwd())
        assert Path.cwd() == Path(runner_request['working_root']) == directory.parents[2]
        assert attempt.parent == Path.cwd() and output_directory == attempt / 'original_tree_evidence'
        assert runner_request['policy'] == POLICY and runner_request['swap_bytes'] == 0
        assert runner_request['native_executables'] == []
        store = Store(directory / 'state')
        assert store.db.execute('SELECT count(*) FROM runtime_runs').fetchone()[0] == 0
        original_selection = json.loads((directory / 'INPUT_SELECTION_001.json').read_text())
        initial = original_selection['initial_received_references']
        for reference in initial:
            assert store.get(reference)['origin'] == 'caller'
        selected_jobs = json.loads((directory / 'SELECTED_JOBS_001.json').read_text())
        jobs = selected_jobs['jobs']
        prior_native = json.loads((directory / 'NATIVE_ATTEMPTS_001.json').read_text())
        assert prior_native['returncodes'] == [0] * 6
        assert [row['requested_job']['native_blast_utility']['operation']['mode']
            for row in prior_native['plans']] == list(MODES[:6])
        for job in jobs:
            executable = Path(job['software']['executable'])
            assert pin(executable)['sha256'] == job['software']['sha256'] == EXECUTABLE_PINS[executable.name]
        declared_executables = {row['path']: row for row in runner_request['existing_native_executables']}
        assert set(declared_executables) == {job['software']['executable'] for job in jobs}
        assert all(pin(Path(path)) == expected for path, expected in declared_executables.items())
        protected = {str(path): pin(path) for path in (directory / 'supplied').rglob('*') if path.is_file()}
        baseline = retained_workflow_history(store, directory)
        pending, = baseline['pending_model_calls']
        assert pending['purpose'] == 'decision' and pending['call_index'] == 1
        assert json.loads(pending['request'])['context']['execution_assignment']['handoff_ref'] == prior_native['handoffs'][5]
        save(output_directory / 'ORIGINAL_HISTORY_BEFORE_008.json', baseline)
    else:
        software = selected_software()
        store, paths, databases, initial, protected = stage_inputs(directory)
        jobs = [original_job(mode, software, paths, databases) for mode in MODES]
    scope = store.validate_scope()
    workspace = directory / 'workspace'
    if not continuing:
        workspace.mkdir()
    # Validate every exact selection before the first native command.
    requests = [requested_job_from_native_blast_utility(job) for job in jobs]
    bindings = [{'program': job['operation']['program'], 'mode': job['operation']['mode'],
        'software': job['software'], 'molecules': [job['operation']['molecule']],
        'variants': [VARIANTS[job['operation']['mode']]]} for job in jobs]
    if continuing:
        assert bindings == selected_jobs['bindings']
        assert all(requests[index] == row['requested_job'] for index, row in enumerate(prior_native['plans']))
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY, 'native_blast_utility': bindings}}
    handoff_form = {'type': 'object', 'additionalProperties': False, 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'}, 'x-source': 'execution_handoff_refs'}},
        'required': ['completed', 'references']}
    results_form, science_form = form_for(RESULT_FIELDS, True), form_for(SCIENCE_FIELDS)
    tools = ToolRegistry(store)
    application = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
    science_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': 'native.' + row['program'] + '.' + row['mode'], 'resources': 'local'} for row in bindings]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True, 'allocation': POLICY},
        'context': {'supplied_sequence': 'TTGCAATTGCAA', 'molecule': 'dna', 'candidate_annotation_required': False}}
    owner = ExecutionEpisodes(None, store=store, directory=directory / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial_value):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 2 * len(MODES)
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'scripted_scientific_test_horizon_not_production_stopping'})
        return YieldController(str(path), initial_value, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        def __init__(self):
            self.calls, self.plans, self.handoffs, self.native_outcomes = [], [], [], []
            self.science_calls, self.assignment = 0, None
            self.resource_calls, self.result_calls = set(), set()
            if continuing:
                self.plans = deepcopy(prior_native['plans'])
                self.handoffs = list(prior_native['handoffs'])
                self.native_outcomes = list(prior_native['returncodes'])
                roles = {row['episode_id']: json.loads(row['path'])[-1][0]
                    for row in store.db.execute('SELECT episode_id,path FROM runtime_episodes WHERE run_id=?', (RUN_ID,))}
                self.science_calls = sum(row['response'] is not None and roles[row['episode_id']] == 'scientific_process'
                    for row in store.db.execute('SELECT episode_id,response FROM runtime_model_calls WHERE run_id=?', (RUN_ID,)))
                assert self.science_calls == 12

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({'episode_id': episode_id, 'role': role})
            save(output_directory / 'DECISION_CALLS_001.json', self.calls)
            assert not current.get('feedback'), current.get('feedback')
            if 'practical_assignment' in current:
                assert episode_id not in self.resource_calls, 'no automatic native retry is permitted'
                self.resource_calls.add(episode_id)
                assert current['practical_assignment'] == self.assignment
                if continuing:
                    assert self.assignment['requested_job']['native_blast_utility']['operation']['mode'] in MODES[6:]
                answer = selected('practical.job.start')
            elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                answer = child('launch_local', self.assignment, scope, handoff_form)
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                assert episode_id not in self.result_calls, 'original selected result did not complete'
                self.result_calls.add(episode_id)
                answer = selected('execution.results.collect')
            elif 'scientific_process' not in current:
                answer = child('scientific_process', science_assignment, scope, science_form)
            else:
                self.science_calls += 1
                index = (self.science_calls - 1) // 2
                mode = MODES[index]
                if self.science_calls % 2:
                    self.assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'preparation654-' + mode,
                        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
                        'endpoint': 'usable_handoff', 'requested_job': requests[index],
                        'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
                        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
                        'inventory_snapshot': {}, 'constraints': {'allocation': POLICY}}
                    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': self.assignment},
                        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
                            'allowed_kinds': ['local'], 'allocation': POLICY}}
                    answer = child('launch', launch, scope, handoff_form)
                else:
                    handoff, = current['child_reports'][-1]['references']
                    target = flow.progress_provider.job_provider.targets.read_target(handoff, scope)
                    completed = await asyncio.to_thread(native.wait_job, native.NativeJobHandle(Path(target['execution_id'])))
                    self.native_outcomes.append(completed.returncode)
                    self.plans.append(local_blast_utility_plan(self.assignment, target['execution_id']))
                    self.handoffs.append(handoff)
                    save(output_directory / 'NATIVE_ATTEMPTS_001.json', {'plans': self.plans,
                        'returncodes': self.native_outcomes, 'handoffs': self.handoffs})
                    # Deliver any actual native failure through its selected result.
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': handoff,
                        'selector': selected_result(mode)}, scope, results_form)
            if answer['selection']['kind'] == 'episode_child':
                answer['selection']['goal'] = 'Complete the selected native BLAST preparation or inspection and retain its requested facts.'
                answer['selection']['purpose'] = 'Return only the selected native measurements, qualifications and saved result.'
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, directory / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=initial,
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build('annotation', 'root', 'Prepare and inspect the supplied molecular input artifacts.', scope)

    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record

    if not continuing:
        save(directory / 'SELECTED_JOBS_001.json', {'jobs': jobs, 'bindings': bindings, 'selectors': {m: selected_result(m) for m in MODES}})
    try:
        record = asyncio.run(execute())
    finally:
        if continuing:
            assert_retained_workflow_history(store, baseline)
            save(output_directory / 'ORIGINAL_HISTORY_AFTER_WORKFLOW_008.json', {'unchanged': True,
                'committed_rows': sum(len(table['rows']) for table in baseline['tables']),
                'immutable_files': len(baseline['files'])})
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {row['episode_id']: owner.native_blast_utility_returns.context(row['episode_id']) for row in records}
    results = []
    for row in records:
        context = contexts[row['episode_id']]
        if context.role == 'results':
            saved_actions = list(store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
                (RUN_ID, context.episode_id)))
            outcome = json.loads(saved_actions[-1]['result'])
            returned = json.loads(flow.journal.row('runtime_forms', context.episode_id)['form'])
            results.append({'context': context, 'record': row, 'outcome': outcome, 'returned': returned})
    results.sort(key=lambda item: MODES.index(item['outcome']['result']['target']['assignment']['requested_job']['native_blast_utility']['operation']['mode']))
    science_context, = [context for context in contexts.values() if context.role == 'scientific_process']
    forwarded = json.loads(flow.journal.row('runtime_forms', science_context.episode_id)['form'])
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root, record=record,
        records=records, contexts=contexts, root_context=contexts[record.episode_id], science_context=science_context,
        results=results, forwarded=forwarded, results_form=results_form, science_form=science_form,
        scope=scope, workspace=workspace, directory=directory, output_directory=output_directory,
        continuing=continuing, jobs=jobs, protected=protected,
        baseline=baseline if continuing else None)
    save(output_directory / 'CASE_001.json', {'scope': 'actual tiny native preparations; scripted shared episode choices',
        'native_returncodes': provider.native_outcomes,
        'results': [{key: row[key] for key in ('outcome', 'returned')} for row in results], 'forwarded': forwarded,
        'histories': {row['episode_id']: row['controller_state'] for row in records}})
    return case


@pytest.fixture(scope='module')
def native_case(tmp_path_factory):
    resumed = os.environ.get('HMMER_NATIVE_ORACLE_RESUME_CASE')
    case = (run_case(Path(resumed), continuation_output=Path(os.environ['HMMER_NATIVE_ORACLE_CONTINUATION_OUTPUT']))
        if resumed else run_case(tmp_path_factory.mktemp('preparation-workflow654')))
    try:
        yield case
    finally:
        if case.continuing:
            assert_retained_workflow_history(case.store, case.baseline)
            save(case.output_directory / 'ORIGINAL_HISTORY_AFTER_REPLAY_008.json', {'unchanged': True,
                'committed_rows': sum(len(table['rows']) for table in case.baseline['tables']),
                'immutable_files': len(case.baseline['files'])})
        case.store.close()


def test_fresh_supplied_inputs_and_all_nine_selections_without_native(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_utility_materializations import realize_blast_utility_materializations

    def forbidden(*args, **kwargs):
        raise AssertionError('input validation must not launch native work')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    software = selected_software()
    store, paths, databases, initial, protected = stage_inputs(tmp_path)
    try:
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_episodes'").fetchone()[0] == 0
        assert store.count('annotation') == store.count('observation') == 0
        for ref in initial:
            source = store.get(ref)
            assert source['origin'] == source['provider'] == 'caller'
            original = json.loads(store.get_artifact(source['artifact_ref']))
            assert source['version'] is None
            assert {original['identity']['source']['source_ref'], original['preparation']['source']['source_ref']}.isdisjoint(initial)
        selections = []
        for mode in MODES:
            job = original_job(mode, software, paths, databases)
            request = requested_job_from_native_blast_utility(job)
            realized = realize_blast_utility_materializations(job,
                input_contents={r['input_key']: Path(r['path']).read_bytes() for r in job['inputs']},
                attempt_directory=str(tmp_path / ('not-executed-' + mode)))
            assert request['native_blast_utility'] == job
            selections.append({'mode': mode, 'selected_argv': request['argv'],
                'materializations': realized['materialization_plan']})
        for path, expected in protected.items():
            same_bytes(pin(Path(path)), expected)
        save(tmp_path / 'FRESH_INPUT_VALIDATION_003.json', {'native_commands': 0,
            'prior_store_imported': False, 'initial_records': [store.get(ref) for ref in initial],
            'selected_modes': selections, 'protected_file_count': len(protected)})
    finally:
        store.close()


def test_retained_volume_materializations_keep_database_members_distinct_from_metadata(tmp_path, monkeypatch):
    """Recalculate the actual113b capture; do not repeat its six native commands."""
    evidence = ROOT / 'verification/tool_graders_blast_preparation_workflow_2026-10-28_654'
    retained = ROOT / ('verification/tool_graders_hmmer_map_verification_2026-10-28_529/'
        'check113b_workflow654/temporary/pytest/preparation-workflow6540')
    plan = json.loads((evidence / 'check113b_failed_volume_result/aggregate_volumes-plan.json').read_text())
    original_root = Path(plan['files'][0]['path']).parents[3]

    def forbidden(*args, **kwargs):
        raise AssertionError('retained capture verification must not start native or network work')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    context = qualified_utility_context(plan['capture'])
    assert context == plan['context']
    assert context['native_outcome']['returncode'] == 0
    contents = {}
    for descriptor in plan['files']:
        relative = Path(descriptor['path']).relative_to(original_root)
        assert relative.parts[:2] == ('state', 'artifacts')
        supplied = retained / relative
        same_bytes(pin(supplied), descriptor)
        contents[descriptor['occurrence_id']] = supplied.read_bytes()
    paired_paths = []
    for path in sorted({row['native_path'] for row in context['occurrences'] if row['direction'] == 'input'}):
        rows = [row for row in context['occurrences'] if row['direction'] == 'input' and row['native_path'] == path]
        if len(rows) > 1:
            assert {row['role'] for row in rows} == {'database_file', 'database_metadata'}
            assert len({(row['sha256'], row['size_bytes']) for row in rows}) == 1
            paired_paths.append(path)
    assert len(paired_paths) == 2
    result, prepared = assemble_blast_preparation_result(context=context, capture=plan['capture'], contents=contents)
    assert result['operation']['mode'] == 'aggregate_volumes'
    assert len([row for row in result['materializations'] if row['kind'] == 'database_copy']) == 20
    assert not any(row['code'] in {'semantic_validation_unavailable', 'dependency_unavailable'} for row in result['failures'])
    save(tmp_path / 'RETAINED_VOLUME_RECALCULATION_006.json', {'native_commands': 0,
        'original_capture': str(evidence / 'check113b_failed_volume_result/aggregate_volumes-plan.json'),
        'distinct_original_roles': paired_paths, 'result': result, 'prepared_database': prepared,
        'native_documents': [{'occurrence_id': row['occurrence_id'], 'role': row['role'],
            'sha256': row['sha256'], 'size_bytes': row['size_bytes'],
            'text': contents[row['occurrence_id']].decode('utf-8')}
            for row in context['occurrences'] if row['direction'] == 'output'
            and row['role'] in {'stdout', 'stderr', 'alias_file'}]})


def test_original_partial_workflow_journal_preserves_interrupted_decision_contract(tmp_path, monkeypatch):
    """Inspect a forensic SQLite/WAL copy; this does not create or resume a run."""
    import sqlite3

    def forbidden(*args, **kwargs):
        raise AssertionError('journal inspection must not start native or network work')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    retained = ROOT / ('verification/tool_graders_hmmer_map_verification_2026-10-28_529/'
        'check113b_workflow654/temporary/pytest/preparation-workflow6540/state')
    evidence = ROOT / 'verification/tool_graders_blast_preparation_workflow_2026-10-28_654'
    receipt = json.loads((evidence / 'check113b_failed_volume_result/aggregate_volumes-receipt.json').read_text())
    protected = {p: pin(p) for p in retained.glob('state.sqlite3*')}
    copied = tmp_path / 'forensic-journal'
    copied.mkdir()
    for path in protected:
        shutil.copyfile(path, copied / path.name)
    database = sqlite3.connect(str(copied / 'state.sqlite3'))
    database.row_factory = sqlite3.Row
    try:
        assert database.execute('SELECT count(*) FROM runtime_runs').fetchone()[0] == 0
        args = (receipt['run_id'], receipt['episode_id'])
        actions = list(database.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=?', args))
        observations = list(database.execute('SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=?', args))
        assert len(actions) == len(observations) == 1
        assert actions[0]['decision_index'] == observations[0]['unit_index'] == 0
        assert json.loads(actions[0]['result'])['result'] == receipt
        assert receipt['complete'] is False
        pending, = database.execute('SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND response IS NULL', args)
        assert pending['call_index'] == 1
        request = json.loads(pending['request'])

        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child_value in value.values():
                    yield from strings(child_value)
            elif isinstance(value, list):
                for child_value in value:
                    yield from strings(child_value)

        result_operations = sorted({value for value in strings(request['schema']) if value.startswith('execution.results.')})
        assert result_operations == ['execution.results.collect', 'execution.results.status']
        save(tmp_path / 'ORIGINAL_JOURNAL_BOUNDARY_007.json', {'native_commands': 0,
            'forensic_copy_only': True, 'annotation_run_created_or_resumed': False,
            'runtime_runs': 0, 'original_action': dict(actions[0]),
            'original_observation': dict(observations[0]), 'pending_call': dict(pending),
            'pending_result_operations': result_operations})
    finally:
        database.close()
    for path, expected in protected.items():
        same_bytes(pin(path), expected)


def test_selected_native_values_and_original_custody_reach_scientific_parent(native_case):
    case = native_case
    assert case.provider.native_outcomes == [0] * 9
    assert len(case.results) == len(case.jobs) == 9
    retained = {}
    for mode, selected in zip(MODES, case.results):
        body, returned = selected['outcome']['result'], selected['returned']
        assert body['complete'] and returned['completed'], body
        result = json.loads(case.store.get_artifact(body['prepared']['result_artifact_ref']))
        retained[mode] = result
        assert result['operation'] == case.jobs[MODES.index(mode)]['operation']
        assert returned['status'] == [body['status']] and body['status']['native_state'] == 'succeeded'
        fields = result.get('native_fields', result.get('native_metadata', []))
        assert all({k: v for k, v in row.items() if k not in {'source_ref', 'subject', 'database_key'}} in fields
            for row in returned['database_fields'])
        if returned['preparation']:
            assert returned['preparation'][0]['fields'] == {key: result[key] for key in selected_result(mode)['preparation']['fields']}
        case.owner.validate_report(selected['context'], returned, case.results_form)
    for field in SCIENCE_FIELDS:
        expected = []
        for selected in case.results:
            for row in selected['returned'][field]:
                if row not in expected:
                    expected.append(row)
        assert case.forwarded[field] == expected
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    assert {r['field_name']: r['value'] for r in retained['convert_gi_list']['native_metadata']}['identifier_list_converted_count'] == 3
    inspection = retained['inspect_seqid_list']
    assert inspection['subject'] == {'kind': 'identifier_list', 'occurrence_id': 'ids'}
    assert {r['field_name']: r['value'] for r in inspection['native_fields']}['identifier_list_count'] == 1
    assert {r['field_name']: r['value'] for r in inspection['native_fields']}['identifier_list_database_length'] == 33
    subset = retained['create_subset_alias']
    alias_fields = {r['field_name']: r['value'] for doc in subset['detail']['alias_documents'] for r in doc['native_fields']}
    assert alias_fields['database_sequence_count'] == 1 and alias_fields['database_residue_count'] == 13
    aggregate = retained['aggregate_databases']
    assert [r['database_key'] for r in aggregate['operation']['parameters']['classic_list']['entries']] == ['B', 'A', 'B']
    rewrite, = [r for r in aggregate['materializations'] if r['kind'] == 'list_rewrite']
    assert [r['target']['database_key'] for r in rewrite['entries']] == ['B', 'A', 'B']
    assert aggregate['database_bindings'][0]['identity'] == aggregate['database_bindings'][1]['identity']
    volumes = retained['aggregate_volumes']
    assert len([r for r in volumes['materializations'] if r['kind'] == 'database_copy']) == 20
    assert len(volumes['operation']['parameters']['volume_entries']) == 2
    volume_fields = {r['field_name']: r['value'] for doc in volumes['detail']['alias_documents'] for r in doc['native_fields']}
    assert volume_fields['database_sequence_count'] == volume_fields['database_residue_count'] == 0
    index = retained['create_megablast_index']
    assert index['operation']['parameters']['ws_hint'] == 8
    assert any(r['parameter'] == 'ws_hint' and r['effect'] == 'effective' and r['value'] == 10
        for r in index['detail']['parameter_observations'])
    filters = retained['show_filters']
    assert filters['native_fields'] == []
    assert case.store.get_artifact(filters['output_occurrence']['artifact_ref']) == b'\n'
    profile = retained['create_profile_database']
    assert all(r['disposition'] == 'unknown' for r in profile['detail']['profiles'])
    auxiliary_rows = [row for volume in profile['detail']['volumes']
        for document in volume['auxiliary_documents'] for row in document['rows']]
    assert len(auxiliary_rows) == 1
    assert auxiliary_rows[0]['sequence_length'] == 320 and auxiliary_rows[0]['karlin_k'] == 0.0375672
    aux, = [r for r in profile['outputs'] if r['native_format'] == 'blast_profile_aux_text']
    assert case.store.get_artifact(aux['artifact_ref']).splitlines()[-2:] == [b'320', b'3.756720e-02']
    assert {'.aux', '.rps', '.loo', '.freq'} <= {Path(r['native_path']).suffix for r in profile['outputs']}
    for path, expected in case.protected.items():
        same_bytes(pin(Path(path)), expected)
    assert case.store.count('annotation') == case.store.count('observation') == 0


def test_one_actual_action_observation_terminal_zero_and_explicit_artifact_grants(native_case):
    case = native_case
    assert len(case.provider.calls) == (16 if case.continuing else 46)
    if case.continuing:
        assert [row['requested_job']['native_blast_utility']['operation']['mode']
            for row in case.provider.plans[6:]] == list(MODES[6:])
        pending, = case.baseline['pending_model_calls']
        resumed = case.flow.journal.row('runtime_model_calls', pending['episode_id'], pending['call_index'])
        assert resumed['request'] == pending['request'] and resumed['response'] is not None
        assert case.provider.calls[0] == {'episode_id': pending['episode_id'], 'role': 'REASONING'}
        assert case.store.db.execute('SELECT count(*) FROM runtime_runs').fetchone()[0] == 0
    for row in case.records:
        role = case.contexts[row['episode_id']].role
        for table in ('runtime_actions', 'runtime_observations'):
            assert case.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=? AND episode_id=?',
                (RUN_ID, row['episode_id'])).fetchone()[0] == row['units_consumed']
        if role in {'launch_local', 'launch', 'results'}:
            repaired = (case.continuing and role == 'results' and
                case.contexts[row['episode_id']].assignment['handoff_ref'] == case.provider.handoffs[5])
            assert row['units_consumed'] == (2 if repaired else 1)
            assert row['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert history(row) == ([2, 0] if repaired else [{'launch_local': 7, 'launch': 3, 'results': 2}[role]])
    assert history(case.record.as_record()) == [0]
    root_known = set(case.flow.receipts.known(case.root_context.episode_id))
    science_known = set(case.flow.receipts.known(case.science_context.episode_id))
    resolver = case.flow.resolver(case.scope, context=case.root_context)
    for selected in case.results:
        body = selected['outcome']['result']
        assert body['source_ref'] in root_known
        assert all(r['artifact_ref'] in root_known for r in body['saved_data'])
        for row in body['artifacts']:
            assert row['artifact_ref'] in science_known
            assert row['artifact_ref'] not in root_known and not resolver(row['artifact_ref'], 'artifact')
        proof = case.owner.completion_for_action(selected['context'], body['operation_key'])
        assert proof and case.owner.verify_completion(selected['context'], proof)
    for plan in case.provider.plans:
        metadata = native.NativeJobHandle(Path(plan['identity']['execution_id'])).read()['metadata']
        assert metadata['policy'] == POLICY
        assert metadata['verified_cgroup']['memory_max'] == 20 * 1024**3
        assert metadata['verified_cgroup']['memory_swap_max'] == 0
        assert 'runtime_max' not in metadata['verified_cgroup']


def test_saved_only_recalculation_then_closed_replay_without_native_or_parsing(native_case, monkeypatch):
    case = native_case
    before_context = deepcopy(case.owner.native_blast_utility_returns.received_context(case.root_context))
    if case.continuing:
        # Preserve the original interrupted run while denying its native/input
        # paths to the saved-only calculation and replay.
        original_open = Path.open

        def retained_only(path, *args, **kwargs):
            actual = path.resolve()
            assert not any(actual.is_relative_to(root) for root in (case.workspace, case.directory / 'supplied'))
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, 'open', retained_only)
    else:
        shutil.rmtree(case.workspace)
        shutil.rmtree(case.directory / 'supplied')
    recalculated = []
    for selected in case.results:
        body = selected['outcome']['result']
        capture = body['capture']
        context = qualified_utility_context(capture)
        contents = {row['occurrence_id']: case.store.get_artifact(row['artifact_ref']) for row in context['occurrences']}
        result, prepared = assemble_blast_preparation_result(context=context, capture=capture, contents=contents)
        assert result == json.loads(case.store.get_artifact(body['prepared']['result_artifact_ref']))
        projection = project_blast_utility_result(source_ref=body['source_ref'], operation=context['operation'],
            native_outcome=context['native_outcome'], result=result, prepared_database=prepared,
            occurrences=context['occurrences'], selector=body['assignment']['selector'],
            failures=body['prepared']['failures'], saved_data=body['saved_data'])
        for field in RESULT_FIELDS:
            assert projection[field] == body[field]
        recalculated.append({'mode': result['operation']['mode'], 'result_equal': True, 'projection_equal': True})
    save(case.output_directory / 'SAVED_RECALCULATION_001.json', recalculated)

    def forbidden(*args, **kwargs):
        raise AssertionError('closed replay attempted acquisition, native execution or parsing')

    for module, name in (
        ('native_blast_utility_result_publication', 'run_local_job'),
        ('native_blast_utility_acquisition', '_capture_file'),
        ('native_blast_utility_acquisition', 'local_blast_utility_plan'),
        ('native_blast_utility_results', 'prepare_native_blast_utility_result'),
        ('native_blast_utility_results', 'publish_selected_utility_result'),
        ('blast_preparation_result_assembly', 'assemble_blast_preparation_result'),
        ('blast_database_preparation', 'populate_database_artifact_set'),
        ('blast_preparation_population', 'populate_blast_preparation_artifact_set')):
        monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
    before = list(case.store.db.iterdump())
    for selected in case.results:
        body = selected['outcome']['result']
        replay = asyncio.run(case.owner.execute(selected['context'], 'execution.results.collect', {}, body['operation_key']))
        assert replay == {key: value for key, value in selected['outcome'].items() if key != 'pending_work_after_action'}
    if case.continuing:
        volume = case.results[5]
        first = json.loads(case.flow.journal.row('runtime_actions', volume['context'].episode_id, 0)['result'])
        assert first['result']['complete'] is False and first['result']['prepared']['result_artifact_ref'] is None
        replay = asyncio.run(case.owner.execute(volume['context'], 'execution.results.collect', {}, first['result']['operation_key']))
        assert replay == {key: value for key, value in first.items() if key != 'pending_work_after_action'}
    case.flow.receive_form(case.root.source, case.forwarded, case.science_form, 0, redelivery=True)
    assert case.owner.native_blast_utility_returns.received_context(case.root_context) == before_context
    assert list(case.store.db.iterdump()) == before
    save(case.output_directory / 'CLOSED_REPLAY_001.json', {'result_actions': 10 if case.continuing else 9, 'native_commands': 0,
        'parsing': 0, 'state_unchanged': True, 'requested_root_redelivery': True,
        'original_failed_action_replayed_unchanged': case.continuing,
        'original_native_paths': 'read_denied_and_preserved' if case.continuing else 'copied_workspace_removed'})
