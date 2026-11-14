"""Read-only compatibility of the actual closed 096 and 654 return trees.

Run only inside bounded529. Original SQLite files are opened immutable/read-only;
no Store is initialized, copied, or imported into a new annotation run. No native
invocation, acquisition, native-result parsing, prompt, or new episode selection
is permitted. Original-input list-realization validation is separately observed.
"""
from contextlib import contextmanager
from copy import deepcopy
import ast
import asyncio
import builtins
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_historical_fact_schemas import blast_utility_historical_fact_schemas, blast_utility_historical_schema_provenance
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import blast_utility_fact_sources
from gene_annotation_episode.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form,
)
from gene_annotation_episode.episodic_workflow.root.a101.native_blast_utility_returns import NativeBLASTUtilityReturns


PACKET_NAME = 'verification/tool_graders_hmmer_map_verification_2026-10-28_529'
CASES = {
    '096': 'check096_blast_utility_full_workflow/temporary/pytest/utility-workflow6340',
    '654': 'check113b_workflow654/temporary/pytest/preparation-workflow6540',
}
ADDED_SCHEMAS = {
    'execution.blast_utility_database_fields': 'c53cdb73800a6b44efc66d911f26e69247a866773280969e74791491cdcdbc95',
    'execution.blast_utility_missing': '790db139998ee7b96c79939c144b609d04859f93f8b3fbae50298f4d61e1a3a8',
    'execution.blast_utility_saved_data': '773ff91ad5a7bc1948530b5fa3e78d5fc3333a4df75043a1784f990517417fc1',
    'execution.blast_utility_artifacts': 'fc1af08156e6cd6c062567fe32508e045e4a0789e7e7dc3536e5545e9f11e9f8',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def pin(path):
    content = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest(),
            'size_bytes': len(content)}


def original_case(key):
    attempt = Path(os.environ['HMMER529_ATTEMPT'])
    request = json.loads((attempt / 'selected_request.json').read_text())
    assert request['policy'] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    assert request['swap_bytes'] == 0 and not request['native_executables']
    if key == '096':
        path = (Path(__file__).resolve().parent / 'fixtures/blast_utility_historical_forms/'
            'check096_blast_utility_full_workflow/temporary/pytest/utility-workflow6340')
    else:
        path = Path(request['repository_root']) / PACKET_NAME / CASES[key]
    assert path.is_absolute() and path.is_dir()
    return path


def save(name, value):
    output = Path(os.environ['HMMER529_ATTEMPT']) / 'original_tree_evidence'
    output.mkdir(exist_ok=True)
    (output / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


@contextmanager
def original_database(key):
    path = original_case(key) / 'state/state.sqlite3'
    # An immutable connection cannot safely ignore uncheckpointed WAL state.
    assert not Path(str(path) + '-wal').exists()
    before = pin(path)
    database = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    database.row_factory = sqlite3.Row
    database.execute('PRAGMA query_only=ON')
    try:
        yield database
    finally:
        database.close()
        assert pin(path) == before


def actual_deliveries(database):
    found = []
    for row in database.execute('SELECT * FROM runtime_report_attempts '
            'WHERE form IS NOT NULL AND failure IS NULL ORDER BY run_id,parent_episode_id,decision_index'):
        contract = json.loads(row['contract'])
        schema = contract['measurements']['schema']
        if any(str(node.get('x-source', '')).startswith('execution.blast_utility_')
               for node in schema['properties'].values()):
            found.append({**dict(row), 'schema': schema, 'values': json.loads(row['form'])})
    return found


def schema_for(node):
    return {'type': 'object', 'additionalProperties': False,
        'properties': {'rows': deepcopy(node)}, 'required': ['rows']}


def value_reader(database=None, run_id='registered-schema672'):
    return NativeBLASTUtilityReturns(SimpleNamespace(store=SimpleNamespace(db=database),
        run_id=run_id, native_blast_utility_results=None))


@pytest.mark.parametrize('source', tuple(blast_utility_fact_sources()))
def test_exact_current_and_retained_schemas_have_closed_values_reader(source):
    current = blast_utility_fact_sources()
    assert len(current) == 14
    for node in [current[source]['report_schema'],
                 *blast_utility_historical_fact_schemas().get(source, ())]:
        schema = schema_for(node)
        assert validate_closed_schema(schema) == schema
        assert value_reader()._values({'rows': []}, schema) == {source: []}




@pytest.mark.parametrize('source', tuple(ADDED_SCHEMAS))
@pytest.mark.parametrize('mutation', ('narrowed', 'open', 'wrong_source', 'nested'))
def test_added_registration_never_accepts_caller_schema_mutations(source, mutation):
    node = deepcopy(blast_utility_historical_fact_schemas()[source][-1])
    if mutation == 'narrowed':
        node['maxItems'] = 0
    elif mutation == 'open':
        node['items']['additionalProperties'] = True
    elif mutation == 'wrong_source':
        node['x-source'] = 'execution.blast_utility_status'
    schema = schema_for(node)
    if mutation == 'nested':
        schema = schema_for(schema)
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


def test_registered_context_provenance_does_not_become_reference_annotation():
    sources = blast_utility_fact_sources()
    context = sources['execution.blast_utility_vdb_context']['report_schema']
    paths = []
    def walk(node, location):
        if isinstance(node, dict):
            if node.get('format') in {'reference', 'identifier', 'accession'}:
                paths.append(location)
            for key, child in node.items():
                walk(child, (*location, key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, (*location, index))
    walk(context, ())
    assert paths == [('items', 'properties', 'source_ref')]
    # These ordinary nested strings are provenance, never selected byte grants.
    fake = {'execution.blast_utility_vdb_context': [{
        'source_ref': 'source_actual_top_level',
        'context': {'source_ref': 'artifact_unselected_metadata',
                    'artifact_ref': 'artifact_unselected_native'}}]}
    assert list(NativeBLASTUtilityReturns._reference_pairs(fake)) == [('source_actual_top_level', 'source')]


def test_registry_registration_is_pure_and_generic_free_text_stays_closed(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('runtime historical registration attempted file access')
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    for source, schemas in blast_utility_historical_fact_schemas().items():
        for node in schemas:
            assert value_reader()._values({'rows': []}, schema_for(node)) == {source: []}
    with pytest.raises(ReportBoundaryError, match='declared semantic type'):
        validate_closed_schema(schema_for({'type': 'string'}))




def selected_result_actions(database):
    found = []
    for row in database.execute('SELECT * FROM runtime_actions WHERE result IS NOT NULL '
            'ORDER BY episode_id,decision_index'):
        outcome = json.loads(row['result'])
        body = outcome.get('result')
        if isinstance(body, dict) and body.get('version') == 'native_blast_utility_acquired_result_v1':
            found.append({**dict(row), 'selected': json.loads(row['action']),
                          'outcome': outcome, 'body': body})
    return found


def original_owner(key, database, monkeypatch):
    """Read-only constructor shells; all actual validation dependencies remain."""
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.execution_progress import ExecutionProgressProvider, ExecutionTargetReader
    from gene_annotation_episode.state import Store

    directory = original_case(key)
    store = Store.__new__(Store)
    store.path, store.db, store._savepoint = directory / 'state', database, 0
    database.create_function('library_scope_record', 2, store._scope_filter_record)
    actions = selected_result_actions(database)
    run_id, = {row['run_id'] for row in actions}
    if key == '654':
        selection = json.loads((directory / 'SELECTED_JOBS_001.json').read_text())
        bindings = selection['bindings']
        assert len(bindings) == len(selection['jobs']) == 9
    else:
        bindings = []
        for row in actions:
            job = row['body']['target']['assignment']['requested_job']['native_blast_utility']
            bindings.append({'program': job['operation']['program'], 'mode': job['operation']['mode'],
                'software': job['software'], 'molecules': ['dna']})
        # The original five bindings are copied from the original requests.
        order = ('create_sequence_database', 'extract_sequences', 'info', 'metadata', 'integrity')
        bindings.sort(key=lambda row: order.index(row['mode']))
    policy = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    resources = {'here': {'kind': 'local', 'workspace': str(directory / 'workspace'),
        'policy': policy, 'native_blast_utility': bindings}}

    def retained_progress(self, store, *, run_id, directory, resources, api_execution,
                          log_window_bytes, log_roles):
        # The normal constructor's only omitted behavior is CREATE TABLE.
        required = {'runtime_execution_progress_' + name for name in
            ('operations', 'custody', 'snapshots', 'dependencies')}
        tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert required <= tables
        self.store, self.run_id, self.directory = store, run_id, Path(directory)
        self.resources = deepcopy(resources)
        self.log_window_bytes, self.log_roles = log_window_bytes, tuple(log_roles)
        self.targets = ExecutionTargetReader(store, run_id=run_id, directory=directory,
            resources=resources, api_execution=api_execution)
        self.targets.log_window_bytes, self.targets.log_roles = log_window_bytes, tuple(log_roles)

    monkeypatch.setattr(ExecutionProgressProvider, '__init__', retained_progress)
    owner = ExecutionEpisodes(None, store=store, directory=directory / 'run', run_id=run_id,
        resources=resources, initial_information={}, tool_registry=None, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    assert all(row['body']['target']['resource_id'] == 'here' for row in actions)
    return owner, actions


def database_digest(database):
    result = hashlib.sha256()
    for line in database.iterdump():
        result.update(line.encode())
        result.update(b'\n')
    return result.hexdigest()


def original_files(directory):
    return {str(path): pin(path) for path in sorted(directory.rglob('*')) if path.is_file()}


@contextmanager
def retained_only(monkeypatch, owner, key):
    """Suppress writes only after validating each exact existing immutable byte."""
    original = original_case(key)
    comparisons = []
    lexical_calls = []
    # Preserve the original custody validator. Allow its selected input-list
    # syntax validation only, with exact original request/byte identities.
    from gene_annotation_episode.episodic_workflow.root.a101.library import blast_preparation_inputs
    original_list_parser = blast_preparation_inputs.parse_blast_preparation_list
    allowed_lists = {}
    for action in selected_result_actions(owner.store.db):
        body = action['body']
        capture = body['capture']
        job = capture['plan']['requested_job']['native_blast_utility']
        if job['version'] != 'native_blast_utility_job_v2':
            continue
        inputs = {row['input_key']: row for row in job['inputs']}
        for selected in job['materializations']['list_files']:
            operand = inputs[selected['input_key']]
            occurrence = {'occurrence_id': selected['input_key'], 'direction': 'input',
                'role': operand['role'], 'ordinal': 0,
                'artifact_ref': operand['artifact_ref'] or 'artifact_' + operand['sha256'],
                'native_path': operand['path'], 'native_format': 'text',
                'completeness': 'complete', 'sha256': operand['sha256'],
                'size_bytes': operand['size_bytes']}
            receipt, = [row for row in capture['original_bundle']['materializations']
                if row['kind'] == 'list_rewrite' and row['input_key'] == selected['input_key']]
            identity = canonical([selected['grammar'], occurrence])
            allowed_lists.setdefault(identity, []).append({'operation_key': body['operation_key'],
                'original_list_selection': selected, 'original_materialization_receipt': receipt,
                'original_capture_sha256': hashlib.sha256(canonical(capture).encode()).hexdigest()})

    def retained_list_parser(contents, *, grammar, occurrence):
        frame = inspect.currentframe().f_back
        assert frame.f_code.co_name == 'realize_selected_list'
        assert Path(frame.f_code.co_filename).name == 'native_blast_utility_materializations.py'
        assert frame.f_back.f_code.co_name == '_validate_saved_realizations'
        assert Path(frame.f_back.f_code.co_filename).name == 'native_blast_utility_acquisition.py'
        identity = canonical([grammar, occurrence])
        assert identity in allowed_lists
        assert len(contents) == occurrence['size_bytes']
        assert hashlib.sha256(contents).hexdigest() == occurrence['sha256']
        document = original_list_parser(contents, grammar=grammar, occurrence=occurrence)
        lexical_calls.append({'grammar': grammar, 'occurrence': deepcopy(occurrence),
            'original_selections': deepcopy(allowed_lists[identity]),
            'validated_document_sha256': hashlib.sha256(canonical(document).encode()).hexdigest(),
            'call_path': ['_validate_saved_realizations', 'realize_selected_list',
                          'parse_blast_preparation_list']})
        return document
    def forbidden(*args, **kwargs):
        raise AssertionError('historical672 denied native/acquisition/parser/write operation')
    def immutable(path, value):
        path = Path(path)
        assert path.is_relative_to(original) and path.is_file() and not path.is_symlink(), path
        expected = (canonical(value) + '\n').encode()
        actual = path.read_bytes()
        assert actual == expected, path
        comparisons.append({'path': str(path), 'sha256': hashlib.sha256(actual).hexdigest(),
                            'size_bytes': len(actual)})
    native_roots = [original / 'workspace', original / 'supplied', original / 'supplied.fa']
    for resource in owner.resources.values():
        native_roots.extend(Path(row['software']['executable']) for row in resource['native_blast_utility'])
    def allowed(path, mode='r'):
        if isinstance(path, int):
            return
        path = Path(path).resolve()
        assert not any(path == root or path.is_relative_to(root) for root in native_roots), path
        if isinstance(mode, str):
            assert not any(letter in mode for letter in 'wax+'), (path, mode)
        else:
            assert not mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), (path, mode)
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open
    def checked_open(path, mode='r', *args, **kwargs):
        allowed(path, mode)
        return original_open(path, mode, *args, **kwargs)
    def checked_io_open(path, mode='r', *args, **kwargs):
        allowed(path, mode)
        return original_io_open(path, mode, *args, **kwargs)
    def checked_os_open(path, flags, *args, **kwargs):
        allowed(path, flags)
        return original_os_open(path, flags, *args, **kwargs)
    def existing_directory(path, *args, **kwargs):
        assert Path(path).is_dir(), path
    with monkeypatch.context() as guard:
        for module in ('execution_episodes', 'native_blast_utility_results',
                       'native_blast_utility_acquisition', 'native_blast_utility_result_publication'):
            guard.setattr('gene_annotation_episode.' + module + '._immutable', immutable)
        for module, name in (
            ('native_blast_utility_result_publication', 'run_local_job'),
            ('native_blast_utility_acquisition', '_capture_file'),
            ('native_blast_utility_acquisition', 'local_blast_utility_plan'),
            ('native_blast_utility_results', 'prepare_native_blast_utility_result'),
            ('native_blast_utility_results', 'publish_selected_utility_result'),
            ('native_blast_utility_result_worker', '_parse_original'),
            ('native_blast_utility_result_worker', '_project_saved'),
            ('blast_preparation_result_assembly', 'assemble_blast_preparation_result'),
            ('blast_database_preparation', 'populate_database_artifact_set'),
            ('blast_preparation_population', 'populate_blast_preparation_artifact_set')):
            guard.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)
        for name in ('blast_database_extraction', 'blast_database_inspection',
                     'blast_preparation_inputs', 'blast_vdb_utility_inputs'):
            module = importlib.import_module('gene_annotation_episode.' + name)
            for function, value in vars(module).items():
                if function.startswith('parse_') and callable(value):
                    guard.setattr(module, function, forbidden)
        guard.setattr(blast_preparation_inputs, 'parse_blast_preparation_list', retained_list_parser)
        guard.setattr(subprocess, 'Popen', forbidden)
        guard.setattr(socket, 'create_connection', forbidden)
        guard.setattr(owner.job_progress_provider.targets, 'observe_target', forbidden)
        guard.setattr(owner.store, 'artifact', forbidden)
        guard.setattr(builtins, 'open', checked_open)
        guard.setattr(io, 'open', checked_io_open)
        guard.setattr(os, 'open', checked_os_open)
        guard.setattr(Path, 'mkdir', existing_directory)
        for name in ('unlink', 'remove', 'rename', 'replace', 'mkdir', 'rmdir'):
            guard.setattr(os, name, forbidden)
        yield comparisons, lexical_calls


def validate_original_prefix(database, directory):
    baseline_path = directory.parents[2] / 'check117c_continuation654/original_tree_evidence/ORIGINAL_HISTORY_BEFORE_008.json'
    baseline = json.loads(baseline_path.read_text())
    for table in baseline['tables']:
        query = 'SELECT * FROM ' + table['table'] + ' WHERE ' + ' AND '.join(key + '=?' for key in table['keys'])
        for original in table['rows']:
            row = database.execute(query, [original[key] for key in table['keys']]).fetchone()
            assert row is not None and dict(row) == original
    for original in baseline['episode_assignments']:
        row = database.execute('SELECT run_id,episode_id,path,request,initial_credit FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (original['run_id'], original['episode_id'])).fetchone()
        assert dict(row) == original
    for original in baseline['pending_model_calls']:
        row = database.execute('SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?',
            tuple(original[key] for key in ('run_id', 'episode_id', 'call_index'))).fetchone()
        assert all(row[key] == original[key] for key in ('run_id', 'episode_id', 'call_index', 'purpose', 'request'))
        intervals = json.loads(original['timing'])['intervals']
        assert json.loads(row['timing'])['intervals'][:len(intervals)] == intervals
    for path, expected in baseline['files'].items():
        assert pin(Path(path)) == expected
    return {'baseline': pin(baseline_path), 'committed_rows': sum(len(row['rows']) for row in baseline['tables']),
            'immutable_files': len(baseline['files']), 'pending_requests_preserved': len(baseline['pending_model_calls'])}






