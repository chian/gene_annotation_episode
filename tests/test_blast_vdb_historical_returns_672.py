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

from gene_annotation_episode.blast_utility_historical_fact_schemas import (
    blast_utility_historical_fact_schemas, blast_utility_historical_schema_provenance,
)
from gene_annotation_episode.blast_utility_result_views import blast_utility_fact_sources
from gene_annotation_episode.communication import (
    ReportBoundaryError, validate_closed_schema, validate_form,
)
from gene_annotation_episode.native_blast_utility_returns import NativeBLASTUtilityReturns


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


def test_old_literals_remain_independent_and_added_documents_are_exact_retained_fields():
    root = Path(__file__).resolve().parents[1]
    baseline = root / PACKET_NAME / ('check113b_workflow654/check130_vdb_historical672/'
        'source_snapshot/gene_annotation_episode/blast_utility_historical_fact_schemas.py')
    tree = ast.parse(baseline.read_text())
    literals = {row.targets[0].id: ast.literal_eval(row.value) for row in tree.body
        if isinstance(row, ast.Assign)}
    old = json.loads(literals['_HISTORICAL_REGISTRY_JSON'])
    old_provenance = json.loads(literals['_SOURCE_PROVENANCE_JSON'])
    import gene_annotation_episode.blast_utility_historical_fact_schemas as module
    assert module._HISTORICAL_REGISTRY_JSON == literals['_HISTORICAL_REGISTRY_JSON']
    assert module._SOURCE_PROVENANCE_JSON == literals['_SOURCE_PROVENANCE_JSON']
    current, provenance = blast_utility_historical_fact_schemas(), blast_utility_historical_schema_provenance()
    assert set(current) == set(old) and sum(map(len, current.values())) == 18
    for source, schemas in old.items():
        assert list(current[source][:len(schemas)]) == schemas
        assert len(current[source]) == len(schemas) + (source in ADDED_SCHEMAS)
    for name, document in old_provenance.items():
        assert provenance[name] == document
    assert set(provenance) == {*old_provenance, 'check113b_workflow654'}
    with original_database('654') as database:
        actual = actual_deliveries(database)
        for source, expected_hash in ADDED_SCHEMAS.items():
            original = [node for delivery in actual for node in delivery['schema']['properties'].values()
                if node.get('x-source') == source]
            assert original and all(node == original[0] for node in original)
            assert current[source][-1] == original[0]
            assert hashlib.sha256(canonical(original[0]).encode()).hexdigest() == expected_hash
            assert provenance['check113b_workflow654']['schema_documents_sha256'][source] == [expected_hash]
    assert provenance['check113b_workflow654']['original_sqlite'] == pin(original_case('654') / 'state/state.sqlite3')


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


def test_exact_original_schema_audit():
    current = blast_utility_fact_sources()
    historical = blast_utility_historical_fact_schemas()
    evidence, missing = {}, {}
    for key in CASES:
        with original_database(key) as database:
            deliveries = actual_deliveries(database)
            assert len(deliveries) == (6 if key == '096' else 10)
            schemas, uses = {}, []
            for delivery in deliveries:
                for name, node in delivery['schema']['properties'].items():
                    source = node.get('x-source')
                    if source not in current:
                        continue
                    document = canonical(node)
                    identity = hashlib.sha256(document.encode()).hexdigest()
                    schemas[identity] = node
                    registered = [current[source]['report_schema'], *historical.get(source, ())]
                    accepted = document in map(canonical, registered)
                    uses.append({'run_id': delivery['run_id'],
                        'parent_episode_id': delivery['parent_episode_id'],
                        'child_episode_id': delivery['child_episode_id'],
                        'decision_index': delivery['decision_index'], 'field': name,
                        'source': source, 'schema_sha256': identity,
                        'registered': accepted})
                    if not accepted:
                        missing.setdefault(source, {})[identity] = node
                    wrapper = {'type': 'object', 'additionalProperties': False,
                        'properties': {'rows': node}, 'required': ['rows']}
                    try:
                        validate_closed_schema(wrapper)
                    except ReportBoundaryError:
                        assert not accepted
                    else:
                        assert accepted
            evidence[key] = {'sqlite': pin(original_case(key) / 'state/state.sqlite3'),
                'deliveries': len(deliveries), 'schemas': schemas, 'uses': uses}
    save('SCHEMA_AUDIT_001.json', {'cases': evidence, 'missing': missing})
    assert not missing, {source: list(nodes) for source, nodes in missing.items()}


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
    from gene_annotation_episode import blast_preparation_inputs
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


@pytest.mark.parametrize('key', ('096', '654'))
def test_actual_original_returns_grants_and_closed_action_replay(key, monkeypatch):
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.form_reference_validation import form_reference_validation

    directory = original_case(key)
    before_files = original_files(directory)
    with original_database(key) as database:
        before_dump = database_digest(database)
        owner, actions = original_owner(key, database, monkeypatch)
        reader = owner.native_blast_utility_returns
        deliveries = actual_deliveries(database)
        assert len(actions) == (5 if key == '096' else 10)
        assert len(deliveries) == (6 if key == '096' else 10)
        prefix = validate_original_prefix(database, directory) if key == '654' else None
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = owner.store, database, owner.run_id
        boundary_evidence, replay_evidence = [], []
        with retained_only(monkeypatch, owner, key) as (comparisons, lexical_calls):
            for delivery in deliveries:
                parent = reader.context(delivery['parent_episode_id'])
                child = reader.context(delivery['child_episode_id'])
                operation_key = f'{owner.run_id}:{parent.episode_id}:{delivery["decision_index"]}:typed_form'
                with form_reference_validation():
                    admitted = reader.record_admission(parent, delivery['values'], delivery['schema'], operation_key)
                    values = reader._values(delivery['values'], delivery['schema'], generic=child.role == 'results')
                    assert admitted == reader._references(values)
                    reader.validate_received_report(child, delivery['values'], delivery['schema'])
                    if child.role == 'results':
                        owner.validate_report(child, delivery['values'], delivery['schema'])
                    else:
                        owner.validate_received_report(child, delivery['values'], delivery['schema'])
                    known = set(receipts.known(parent.episode_id))
                    assert set(admitted) <= known
                    for reference, namespace in dict.fromkeys(reader._reference_pairs(values)):
                        assert reader.resolve_received_reference_metadata(parent, reference, namespace) is True
                        assert owner._utility_reference_access(parent, reference, namespace) is True
                    denied = []
                    for source in {row['source_ref'] for rows in values.values() for row in rows if isinstance(row, dict)}:
                        record = owner.store.get(source)
                        for reference in [record['artifact_ref'], *record['auxiliary_artifact_refs']]:
                            if reference not in known:
                                assert reader.resolve_received_reference_metadata(parent, reference, 'artifact') is None
                                assert owner._utility_reference_access(parent, reference, 'artifact') is False
                                denied.append(reference)
                    if key == '096' and parent.role == 'annotation':
                        assert not any(owner.store.get(ref)['record_type'] == 'artifact' for ref in admitted)
                    boundary_evidence.append({'parent_episode_id': parent.episode_id,
                        'child_episode_id': child.episode_id, 'decision_index': delivery['decision_index'],
                        'original_contract_sha256': hashlib.sha256(delivery['contract'].encode()).hexdigest(),
                        'original_form_sha256': hashlib.sha256(delivery['form'].encode()).hexdigest(),
                        'values': values, 'admitted': admitted, 'denied_unrequested_artifacts': sorted(set(denied))})
            for action in actions:
                body, selected = action['body'], action['selected']
                context = reader.context(action['episode_id'])
                replay = asyncio.run(owner.execute(context, selected['tool'], selected['arguments'], body['operation_key']))
                assert replay == {name: value for name, value in action['outcome'].items()
                                  if name != 'pending_work_after_action'}
                with form_reference_validation():
                    facts = owner.native_blast_utility_results.facts(context)
                    assert all(facts[source] == [] for source in (
                        'execution.blast_utility_vdb_context', 'execution.blast_utility_paths',
                        'execution.blast_utility_path_sections'))
                    assert not {'vdb_context', 'paths', 'path_sections'} & body.keys()
                    if body['complete']:
                        proof = owner.completion_for_action(context, body['operation_key'])
                        assert proof and owner.verify_completion(context, proof)
                replay_evidence.append({'episode_id': context.episode_id, 'operation_key': body['operation_key'],
                    'mode': body['target']['assignment']['requested_job']['native_blast_utility']['operation']['mode'],
                    'complete': body['complete'], 'credit': action['credit'], 'reused_from': body['reused_from'],
                    'original_receipt': pin(owner.native_blast_utility_results._saved_directory(
                        context.episode_id, body['operation_key']) / 'receipt.json')})
        assert comparisons
        if key == '654':
            assert lexical_calls
            assert len({row['mode'] for row in replay_evidence}) == 9
            failed, repaired = [row for row in replay_evidence if row['mode'] == 'aggregate_volumes']
            assert failed['complete'] is False and repaired['complete'] is True
            assert repaired['reused_from']['operation_key'] == failed['operation_key']
            assert failed['credit'] == repaired['credit'] == 2
            original_failed, original_repaired = [row['body'] for row in actions
                if row['body']['operation_key'] in {failed['operation_key'], repaired['operation_key']}]
            assert original_failed['prepared']['result_artifact_ref'] is None
            assert original_repaired['prepared']['result_artifact_ref'] is not None
            assert original_failed['capture'] == original_repaired['capture']
            assert original_failed['observation'] == original_repaired['observation']
        else:
            assert lexical_calls == []
        assert database_digest(database) == before_dump
        after_prefix = validate_original_prefix(database, directory) if key == '654' else None
        assert after_prefix == prefix
    assert original_files(directory) == before_files
    save('ORIGINAL_' + key + '_COMPATIBILITY_001.json', {'original_tree': str(directory),
        'database_sha256': before_files[str(directory / 'state/state.sqlite3')]['sha256'],
        'database_dump_sha256': before_dump, 'original_file_pins': before_files,
        'all_original_files_unchanged': True, 'database_unchanged': True,
        'deliveries': boundary_evidence, 'result_actions': replay_evidence,
        'immutable_exact_byte_comparisons': comparisons, 'original_prefix': prefix,
        'original_input_list_validation_calls': lexical_calls,
        'qualification': 'replay with write suppression after exact-byte validation',
        'new_store': False, 'native_commands': 0, 'acquisition': 0, 'native_result_parsing': 0,
        'new_selections_or_observations': 0})


def test_original_numerical_facts_and_closed_histories(monkeypatch):
    """Read retained values and observed histories; perform no recalculation."""
    from gene_annotation_episode.numerical import NumericBand
    from gene_annotation_episode.state import Store
    def forbidden(*args, **kwargs):
        raise AssertionError('historical numeric audit denied native/acquisition/parser/new Store')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(Store, '__init__', forbidden)
    monkeypatch.setattr(Store, 'artifact', forbidden)
    for module, name in (
        ('native_blast_utility_result_publication', 'run_local_job'),
        ('native_blast_utility_acquisition', '_capture_file'),
        ('native_blast_utility_acquisition', 'local_blast_utility_plan'),
        ('native_blast_utility_results', 'prepare_native_blast_utility_result'),
        ('native_blast_utility_results', 'publish_selected_utility_result'),
        ('blast_preparation_result_assembly', 'assemble_blast_preparation_result'),
        ('blast_preparation_inputs', 'parse_blast_preparation_list'),
        ('blast_database_preparation', 'populate_database_artifact_set'),
        ('blast_preparation_population', 'populate_blast_preparation_artifact_set')):
        monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)
    prior_pins_path = original_case('654').parents[2] / 'check130b_vdb_historical672/original_retained_fixture_pins_before.json'
    prior_pins = json.loads(prior_pins_path.read_text())
    assert all(pin(Path(row['path'])) == row for row in prior_pins)
    examples = {}
    for key in CASES:
        directory = original_case(key)
        case_path = (directory / 'CASE.json' if key == '096' else directory.parents[2]
            / 'check117c_continuation654/original_tree_evidence/CASE_001.json')
        case = json.loads(case_path.read_text())
        with original_database(key) as database:
            actions = selected_result_actions(database)
            modes = {}
            for row in actions:
                body = row['body']
                modes.setdefault(body['target']['assignment']['requested_job']['native_blast_utility']['operation']['mode'], []).append(body)
            histories = []
            for episode_id, controller in case['histories'].items():
                row = database.execute('SELECT path,state FROM runtime_episodes WHERE episode_id=?', (episode_id,)).fetchone()
                role = json.loads(row['path'])[-1][0]
                observations = [dict(item) for item in database.execute('SELECT * FROM runtime_observations '
                    'WHERE episode_id=? ORDER BY unit_index', (episode_id,))]
                completed = [dict(item) for item in database.execute('SELECT * FROM runtime_actions '
                    'WHERE episode_id=? AND result IS NOT NULL ORDER BY decision_index', (episode_id,))]
                assert len(observations) == len(completed) == len(controller['scores'])
                if role in {'launch_local', 'launch', 'results'}:
                    assert controller['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    expected = {'launch_local': [7], 'launch': [3], 'results': [2]}[role]
                    if key == '654' and role == 'results' and episode_id == modes['aggregate_volumes'][0]['episode_id']:
                        expected = [2, 0]
                    assert controller['scores'] == expected
                histories.append({'episode_id': episode_id, 'role': role, 'scores': controller['scores'],
                    'expected_next_gain': controller['estimate']['expected_next_gain'],
                    'original_observations': observations})
            if key == '096':
                fields = {row['field_name']: row['value'] for row in modes['create_sequence_database'][0]['database_fields']}
                assert fields == {'database_sequence_count': 3, 'database_residue_count': 33}
                extracted = modes['extract_sequences'][0]['sequences']
                assert len(extracted) == 2
                assert all(row['native_reported_length'] == 12 and row['returned_symbol_count'] == 6
                    and row['sequences'] == {'normalized_sequence': 'ATTGCA'} for row in extracted)
                facts = {'created_database': fields, 'extracted': extracted}
            else:
                get_fields = lambda mode: {row['field_name']: row['value'] for row in modes[mode][-1]['database_fields']}
                assert get_fields('convert_gi_list') == {'identifier_list_converted_count': 3}
                assert get_fields('inspect_seqid_list') == {'identifier_list_count': 1, 'identifier_list_database_length': 33}
                assert get_fields('create_subset_alias') == {'database_sequence_count': 1, 'database_residue_count': 13}
                assert get_fields('aggregate_volumes') == {'database_sequence_count': 0, 'database_residue_count': 0}
                assert modes['show_filters'][0]['database_fields'] == []
                assert modes['aggregate_volumes'][0]['complete'] is False
                assert modes['aggregate_volumes'][1]['complete'] is True
                facts = {mode: {'database_fields': rows[-1]['database_fields'],
                    'preparation': rows[-1]['preparation']} for mode, rows in modes.items()}
            assert database.execute('SELECT count(*) FROM runtime_model_calls WHERE response IS NULL').fetchone()[0] == 0
            assert database.execute("SELECT count(*) FROM records WHERE record_type IN ('annotation','observation')").fetchone()[0] == 0
            examples[key] = {'original_case': pin(case_path), 'numerical_facts': facts,
                'histories': histories, 'completed_result_actions': len(actions), 'distinct_selections': len(modes)}
    assert all(pin(Path(row['path'])) == row for row in prior_pins)
    examples['stopped130b_original_files'] = {'pins': pin(prior_pins_path),
        'file_count': len(prior_pins), 'all_unchanged_before_and_after': True}
    save('ORIGINAL_NUMBERS_AND_HISTORIES_001.json', examples)


def test_export_completed_verification_status(monkeypatch):
    """Summarize bounded test evidence without reopening scientific artifacts."""
    def forbidden(*args, **kwargs):
        raise AssertionError('verification-status export denied native or network work')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    request = json.loads((Path(os.environ['HMMER529_ATTEMPT']) / 'selected_request.json').read_text())
    packet = Path(request['repository_root']) / PACKET_NAME
    locations = {
        '096': packet / 'check113b_workflow654/check130b_vdb_historical672/original_tree_evidence/ORIGINAL_096_COMPATIBILITY_001.json',
        '654': packet / 'check130e_vdb_historical672/original_tree_evidence/ORIGINAL_654_COMPATIBILITY_001.json',
    }
    result = {}
    for key, path in locations.items():
        data = json.loads(path.read_text())
        calls = data.get('original_input_list_validation_calls', [])
        identities = {}
        for call in calls:
            assert call['call_path'] == ['_validate_saved_realizations', 'realize_selected_list', 'parse_blast_preparation_list']
            occurrence = call['occurrence']
            identity = canonical([call['grammar'], occurrence])
            value = identities.setdefault(identity, {'grammar': call['grammar'],
                'occurrence': occurrence, 'calls': 0, 'document_sha256': [],
                'original_operation_keys': [], 'materialization_receipt_sha256': []})
            value['calls'] += 1
            value['document_sha256'].append(call['validated_document_sha256'])
            for selection in call['original_selections']:
                value['original_operation_keys'].append(selection['operation_key'])
                value['materialization_receipt_sha256'].append(hashlib.sha256(canonical(
                    selection['original_materialization_receipt']).encode()).hexdigest())
        for value in identities.values():
            for field in ('document_sha256', 'original_operation_keys', 'materialization_receipt_sha256'):
                value[field] = sorted(set(value[field]))
            assert len(value['document_sha256']) == len(value['materialization_receipt_sha256']) == 1
        assert len(identities) == (0 if key == '096' else 2)
        result[key] = {'evidence': pin(path), 'deliveries': len(data['deliveries']),
            'result_actions': len(data['result_actions']),
            'original_files_unchanged': data['all_original_files_unchanged'],
            'original_file_count': len(data['original_file_pins']),
            'database_unchanged': data['database_unchanged'],
            'database_sha256': data['database_sha256'], 'database_dump_sha256': data['database_dump_sha256'],
            'immutable_comparisons': len(data['immutable_exact_byte_comparisons']),
            'unique_immutable_paths': len({row['path'] for row in data['immutable_exact_byte_comparisons']}),
            'original_prefix': data['original_prefix'],
            'input_list_validation_calls': len(calls), 'input_list_identities': list(identities.values()),
            'native_commands': data['native_commands'], 'acquisition': data['acquisition'],
            'native_result_parsing': data['native_result_parsing'],
            'new_selections_or_observations': data['new_selections_or_observations'],
            'explicit_grant_checks': sum(len(row['admitted']) for row in data['deliveries']),
            'denied_unrequested_artifact_checks': sum(len(row['denied_unrequested_artifacts']) for row in data['deliveries'])}
    save('COMPLETED_VERIFICATION_STATUS_001.json', result)
    print(json.dumps(result, sort_keys=True))
