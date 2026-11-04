"""Synthetic stopped sources, actual Store and readers; no external execution."""
from copy import deepcopy
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
from unittest.mock import patch

import jsonschema
import pytest

from method_loop.durable import DurableExecutionStore
from method_loop.identities import EpisodeRef, UnitRef
from gene_annotation_episode import scientific_checkpoint_fork as custody
from gene_annotation_episode import assembled_case_policy
from gene_annotation_episode.application_execution_binding import bind_episode_execution
from gene_annotation_episode.case_execution import _load_policy, prepare_case_run, prepared_case_bindings
from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_commissions import CommissionCoordinator
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_recording import NativeMeasurement
from gene_annotation_episode.materials import source_window, register_material, parse_material
from gene_annotation_episode.native_timing_information import NativeTimingInformation, record_native_measurement
from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic
from gene_annotation_episode.state import RevisionConflict, Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PLAN = Path('/home/chia/repos/gene_annotation_episode/verification/scientific_checkpoint_custody_plan_2026-10-22_001')
SCHEMAS = json.loads((PLAN/'SCHEMAS004.json').read_text())
PUBLICATION = ROOT/'research/slotted_process_library/publications/2026-10-21-001'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(kind, value):
    jsonschema.Draft202012Validator({'$ref': '#/$defs/'+kind, '$defs': SCHEMAS['$defs']}).validate(value)


def write_json(path, value):
    path.write_text(canonical(value)+'\n', encoding='utf-8')


def tree(path):
    return {str(p.relative_to(path)): (sha(p.read_bytes()), p.stat().st_size, p.stat().st_mode & 0o777)
        for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def checkpoint_source_fixture(tmp_path):
    """Actual source preparation, isolated frozen code authority and raw journals.

    Shared root-join interface: arguments excludes destination_workspace;
    case_directory and configuration are the actual prepared case's operands.
    The frozen authority copy makes later fixture reads independent of edits to
    the checkout, while the recorded binding is produced by the real binder.
    """
    source_root = tmp_path/'original'
    source_root.mkdir()
    for package in ('gene_annotation_episode', 'method_loop'):
        for original in (ROOT/package).rglob('*.py'):
            relative = original.relative_to(ROOT)
            destination = source_root/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
    case = source_root/'case'
    run_dir = case/'runs/stopped'
    run_dir.mkdir(parents=True)
    workspace = run_dir/'workspace'
    (case/'target.fna').write_text('>synthetic_single_gene\nATGAAATAA\n')
    (case/'target.faa').write_text('>synthetic_product\nMK\n')
    with Store(workspace) as store:
        problem = store.create_problem(case/'target.fna', molecule='dna', role='gene')
        target, = problem['subject_refs']
        translated = ToolRegistry(store).execute('sequence.translate',
            {'subject_ref': target, 'code': 11, 'cds': True}, scope={'subject_refs': [target]})
        assert translated['status'] == 'completed'
        product = translated['result']['records'][0]['product_ref']
        content = store.artifact('SYNTHETIC custody finding. No biological inference.')
        source = store.put('source', {'provider': 'synthetic_fixture', 'accession': None,
            'uri': None, 'artifact_ref': content, 'text_ref': content, 'request_ref': None,
            'version': 'fixture', 'retrieved_at': None}, origin='external')
        observed = store.put('observation', {'subject_refs': [target], 'source_subject_refs': [target],
            'kind': 'alignment', 'source_ref': source['id'], 'measurements': [],
            'dependencies': [], 'anchor': None}, origin='external')
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')
        assessment = {'hypothesis_ref': hypothesis['id'], 'observation_ref': observed['id'],
            'relation': 'does_not_discriminate', 'applicability': 'incomparable',
            'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
            'expected_revision': 0, 'investigation_finding': {
                'source_claim': {'subject_refs': [target], 'predicate': 'growth_capability',
                    'value': {'type': 'enum', 'value': 'negative'}, 'context_refs': []},
                'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
                'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
                'same_source_claim_as_ref': None, 'replaces_refs': []}}
        old = store.put('assessment', assessment, origin='reasoning')
        assessment['expected_revision'] = old['revision']
        assessment['relation'] = 'weakens'
        current = store.put('assessment', assessment, origin='reasoning')
        with pytest.raises(RevisionConflict):
            store.put('assessment', {**assessment, 'relation': 'strengthens'}, origin='reasoning')
        measured = NativeMeasurement(ExecutionClass('pairwise_sequence_alignment', 'local',
            'synthetic-native', None, 'a'*64, 1024, 1024, None, 9, 9, 1, 'available'),
            RunStatistic('b'*64, 'c'*64, '2026-10-22T00:00:00+00:00',
                'succeeded', 'complete', 1.25, None), 'captured_before_submission')
        native = record_native_measurement(store, measured, operation='align_pair', operands=[
            {'role': 'query', 'subject_ref': target}, {'role': 'reference', 'subject_ref': target}])
        material = register_material(store, data='>packed-one\n'+'ACGT'*20+'\n>packed-two\nACGTAC\n',
            name='synthetic-packed-reads', format='fasta', molecule='dna', role='read')
        with patch.object(custody.packing, 'CHUNK_BYTES', 23):
            parsed = parse_material(store, material['id'])
        assert parsed['status'] == 'completed'
    write_json(case/'case.json', {'case_ref': 'synthetic_stopped_gene', 'target_kind': 'single_gene',
        'target_ref': target, 'problem_ref': problem['id'],
        'target_files': {name: sha((case/name).read_bytes()) for name in ('target.fna', 'target.faa')},
        'scientific_question': 'Synthetic custody fixture, no biological inference.'})
    write_json(case/'evidence-refs.json', {'target_ref': target, 'product_ref': product,
        'source_refs': {'synthetic': source['id']}, 'comparison_refs': [observed['id']]})
    reference = case/'references.faa'
    reference.write_text('>synthetic_reference\nMK\n')
    executable = Path('/bin/true').resolve()
    configuration = {'workspace': str(workspace), 'history': str(case/'history.sqlite'),
        'resource_id': 'synthetic-host', 'max_cpu': 1, 'reference_records': 1, 'reference_residues': 2,
        'executable': {'path': str(executable), 'sha256': sha(executable.read_bytes())},
        'reference_database': {'path': str(reference), 'sha256': sha(reference.read_bytes())},
        'local_jobs': {'memory_bytes': 128*1024**2, 'scratch_bytes': 4*1024**2},
        'models': {role: {'model': 'synthetic-never-called', 'reasoning_effort': 'none'}
            for role in ('FAST', 'REASONING')}}
    launch = prepare_case_run(case, run_dir, configuration)
    configuration = launch['configuration']
    with Store(workspace) as store:
        refs = tuple(sorted(row[0] for table in ('inputs', 'records') for row in
            store.db.execute('SELECT id FROM '+table)))
    roles = ['scientific_process', 'literature', 'launch', 'monitor', 'results']
    parameters = {'policy': {'scientific': CreditPolicy().as_record(), 'scientific_child': 'received_findings',
        'scientific_progress': {'finding_unit': 7, 'initial_known_record_refs': list(refs), 'loss_preview_size': 5},
        'operational': {'registry_ref': launch['registry_configuration']['registry_ref'],
            'handoff_unit': 1, 'acquired_record_unit': 1},
        'monitoring': {'information_unit': .5},
        'controller': {'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}},
        'services': {'version': 'assembled_case_services_v1', 'source_directory': str(PUBLICATION),
            'tool_retrieval': {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
                'model': {'model': 'synthetic-never-called', 'reasoning_effort': 'none'}},
            'scientific_child_roles': roles, 'annotation_child_roles': roles,
            'execution_planning_roles': ['annotation', 'scientific_process'], 'handoff_unit': 1,
            'acquired_record_unit': 1, 'monitoring_information_unit': .5,
            'literature_outcome_page_size': 2, 'monitor_outcome_page_size': 2,
            'log_window_bytes': 128, 'log_roles': ['native_stderr']}}
    policy, recorded = _load_policy(run_dir, Path(assembled_case_policy.__file__), parameters, resume=False)
    run_id = 'run_'+'1'*32
    episode = EpisodeRef(run_id, (('annotation', 'root'),))
    identity = {'policy_source_sha256': recorded['source_sha256'],
        'policy_parameters_sha256': sha(canonical(recorded['parameters']).encode())}
    with Store(workspace) as store, prepared_case_bindings(store, run_dir) as (_, actual_bindings):
        jobs_binding = actual_bindings['job_episodes'].as_record()
    settings = {'directory': str(run_dir), 'problem': problem, 'tool_configuration': configuration,
        'models': configuration['models'], 'restoration': configuration['restoration'],
        'job_episodes': jobs_binding,
        'binding_definitions': {name: {**identity, 'definition': recorded['definitions'][name]}
            for name in ('credit', 'scientific_child_credit', 'controller', 'annotation_score')},
        'scientific_knowledge': {'version': 'frozen_parent_receipt_prefix_v1',
            'initial_known_record_refs': sorted(refs)},
        'episode_record_receipts': recorded['episode_record_receipts'],
        'native_timing_information': recorded['definitions']['native_timing_information']}
    raw_observations = []
    pending_raw = json.dumps({'context': {'fixture': 'pending original Ω'}, 'schema': {'type': 'object'}},
        ensure_ascii=False, indent=2)+'\n'
    with Store(workspace) as store:
        journal = Journal(store, run_id)
        CommissionCoordinator(store, journal, DurableExecutionStore(run_dir/'episode-executions'))
        EpisodeReceipts(store, run_id).bind(episode.episode_id)
        with store.transaction():
            journal.save('runtime_runs', {'settings': canonical(settings), 'state': 'active',
                'started_at': '2026-10-22T00:00:00+00:00', 'updated_at': '2026-10-22T00:00:00+00:00'})
            journal.save('runtime_episodes', {'episode_id': episode.episode_id, 'path': canonical(episode.path),
                'request': canonical({'scope': {'subject_refs': [target]}}), 'initial_credit': 7, 'state': 'active'})
            for index, decision in enumerate((0, None, 'absent')):
                value = {'unit_ref': UnitRef(episode.episode_id, index).as_record(),
                    'credit': (7, 7, 6)[index], 'note': ('Ω\n原始' * 1800 if index == 1 else 'raw spacing')}
                if decision != 'absent':
                    value['decision_index'] = decision
                raw = json.dumps(value, ensure_ascii=False, indent=2)+'\n'
                raw_observations.append(raw)
                journal.save('runtime_observations', {'episode_id': episode.episode_id,
                    'unit_index': index, 'observation': raw})
                journal.save('runtime_actions', {'episode_id': episode.episode_id, 'decision_index': index,
                    'action': '{ "kind" : "synthetic_completed" }', 'result': '{ "retained" : true }',
                    'credit': value['credit']})
                journal.save('runtime_model_calls', {'episode_id': episode.episode_id, 'call_index': index,
                    'purpose': 'decision', 'request': '{ "old" : true }', 'response': '{ "old" : true }'})
            journal.save('runtime_model_calls', {'episode_id': episode.episode_id, 'call_index': 7,
                'purpose': 'decision', 'request': pending_raw, 'response': None})
            # Additional raw typed SQLite rows prove duplicate multiplicity,
            # text vs blob, integer vs real and embedded NUL are preserved.
            store.db.execute('CREATE TABLE fixture_typed_cells(value)')
            store.db.executemany('INSERT INTO fixture_typed_cells VALUES(?)',
                [(None,), (1,), (1.0,), ('a\0Ω',), (b'a\0\xff',), (1,)])
        bind_episode_execution(store, run_dir, settings=settings,
            use_saved_runtime=True, tool_configuration=configuration)
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    pin = custody._source_files(source_root)['implementation_sha256']
    return {'arguments': {'source_workspace': workspace, 'source_run_directory': run_dir,
        'source_implementation_root': source_root, 'source_run_id': run_id,
        'expected_source_implementation_sha256': pin,
        'expected_pending_request_sha256': sha(pending_raw.encode()), 'initial_known_record_refs': refs},
        'case_directory': case, 'configuration': configuration, 'target': target, 'product': product,
        'assessment': current['id'], 'native': native, 'parameters': parameters,
        'raw_observations': raw_observations, 'episode_id': episode.episode_id}


def fork(source, destination):
    return custody.prepare_scientific_checkpoint_fork(**source['arguments'], destination_workspace=destination)


def failure(source, destination, code):
    with pytest.raises(custody.ScientificCheckpointForkError) as error:
        fork(source, destination)
    value = error.value.as_record()
    validate('failure', value)
    assert value['code'] == code
    return value


def test_success_exact_checkpoint_and_actual_lineage_readers(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    original = source['arguments']['source_implementation_root']
    before = tree(original)
    destination = tmp_path/'new-workspace'
    opened = []
    original_init = Store.__init__
    def opening(self, path):
        opened.append(Path(path))
        assert Path(path) != source['arguments']['source_workspace']
        original_init(self, path)
    with patch.object(Store, '__init__', opening):
        result = fork(source, destination)
    assert len(opened) == 1
    validate('result', result)
    assert tree(original) == before
    receipt_raw = Path(result['receipt']['path']).read_bytes()
    assert sha(receipt_raw) == result['receipt']['sha256']
    receipt = json.loads(receipt_raw)
    validate('receipt', receipt)
    assert receipt['source']['counts'] == {'model_calls': 4, 'actions': 3, 'observations': 3, 'episodes': 1}
    checkpoint = destination/'checkpoint/state.sqlite3'
    assert checkpoint.read_bytes() == (source['arguments']['source_workspace']/'state.sqlite3').read_bytes()
    assert checkpoint.stat().st_ino != (destination/'state.sqlite3').stat().st_ino
    for name, kind in (('tables.json', 'table_manifest'), ('artifacts.json', 'artifact_manifest'),
            ('committed-references.json', 'committed_reference_manifest'),
            ('source-implementation-files.json', 'implementation_file_manifest')):
        validate(kind, json.loads((destination/'checkpoint'/name).read_bytes()))
    with Store(destination) as store:
        rows = store.db.execute('SELECT observation FROM runtime_observations ORDER BY unit_index').fetchall()
        assert [row[0] for row in rows] == source['raw_observations']
        stream = store.get_artifact(receipt['lineage']['observation_artifact_ref'])
        assert stream == b''.join(raw.encode()+b'\n' for raw in source['raw_observations'])
        index = json.loads(store.get_artifact(receipt['lineage']['index_artifact_ref']))
        validate('observation_index', index)
        assert [r['decision_index_present'] for r in index['rows']] == [True, True, False]
        for row, raw in zip(index['rows'], source['raw_observations']):
            start, end = row['raw_text_utf8_offset'], row['raw_text_utf8_offset']+row['raw_text_utf8_bytes']
            assert stream[start:end] == raw.encode()
            assert sha(stream[start:end]) == row['raw_text_utf8_sha256']
        first = source_window(store, result['lineage_source_refs']['observations'], representation='original', limit=12000)
        assert first['end'] < len(stream) and first['next_query'] is not None
        for ref in result['lineage_source_refs'].values():
            record = store.get(ref)
            validate('lineage_source_output', record)
            metadata = json.loads(store.get_artifact(record['request_ref']))
            validate('lineage_source_metadata', metadata)
        assert store.db.execute('SELECT count(*) FROM proposals').fetchone()[0] == 1
    assert set(result['initial_known_record_refs']) == set(source['arguments']['initial_known_record_refs']) | set(result['lineage_source_refs'].values())
    assert destination.stat().st_mode & 0o777 == 0o700


def mutate_database(source, sql, args=()):
    # Explicit synthetic fault injection, completed before custody captures it.
    path = source['arguments']['source_workspace']/'state.sqlite3'
    db = sqlite3.connect(path)
    try:
        with db:
            db.execute(sql, args)
    finally:
        db.close()


@pytest.mark.parametrize('operand,value', [('source_run_id', 'old'),
    ('expected_pending_request_sha256', 'A'*64), ('initial_known_record_refs', []),
    ('initial_known_record_refs', ('source_'+'1'*24,)*2)])
def test_request_rejects_malformed_typed_operands_before_creation(tmp_path, operand, value):
    source = {'arguments': {'source_workspace': tmp_path/'absent', 'source_run_directory': tmp_path/'absent',
        'source_implementation_root': tmp_path/'absent', 'source_run_id': 'run_'+'1'*32,
        'expected_source_implementation_sha256': 'a'*64, 'expected_pending_request_sha256': 'b'*64,
        'initial_known_record_refs': ('source_'+'1'*24,)}}
    source['arguments'][operand] = value
    result = failure(source, tmp_path/'new', 'invalid_request')
    assert result['publication_state'] == 'not_created'
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('kind', ['nested', 'existing', 'symlink', 'marker'])
def test_destination_boundaries_preserve_source_and_existing_output(tmp_path, kind):
    source = checkpoint_source_fixture(tmp_path)
    before = tree(source['arguments']['source_implementation_root'])
    destination = tmp_path/'new'
    expected = 'destination_invalid'
    if kind == 'nested':
        destination = source['case_directory']/'new'
        expected = 'destination_overlap'
    elif kind == 'existing':
        destination.mkdir()
        (destination/'sentinel').write_bytes(b'keep existing')
        expected = 'destination_exists'
    elif kind == 'symlink':
        destination.symlink_to(tmp_path/'missing')
    else:
        (tmp_path/'run.json').write_text('{}')
        expected = 'destination_overlap'
    result = failure(source, destination, expected)
    assert result['publication_state'] == 'not_created'
    assert tree(source['arguments']['source_implementation_root']) == before
    if kind == 'existing':
        assert (destination/'sentinel').read_bytes() == b'keep existing'


@pytest.mark.parametrize('native', [False, True])
def test_nonempty_wal_rejected_before_immutable_open(tmp_path, native):
    source = checkpoint_source_fixture(tmp_path)
    main = (source['arguments']['source_run_directory']/'native-jobs/jobs.sqlite' if native else
        source['arguments']['source_workspace']/'state.sqlite3')
    wal = Path(str(main)+'-wal')
    wal.write_bytes(b'synthetic nonempty WAL must never be interpreted')
    with patch.object(custody, '_readonly', side_effect=AssertionError('must not open before WAL check')):
        value = failure(source, tmp_path/'new', 'source_nonempty_wal_out_of_scope')
    assert value['publication_state'] == 'not_created'
    assert wal.read_bytes().startswith(b'synthetic')


@pytest.mark.parametrize('fault', ['provider', 'api', 'native', 'virtual', 'hidden'])
def test_unsupported_execution_inventory_and_schema_fail_closed(tmp_path, fault):
    source = checkpoint_source_fixture(tmp_path)
    if fault == 'provider':
        mutate_database(source, "INSERT INTO provider_job_failures VALUES('synthetic', '{}')")
    elif fault == 'api':
        mutate_database(source, 'CREATE TABLE api_unadopted(value)')
    elif fault == 'native':
        path = source['arguments']['source_run_directory']/'native-jobs/jobs.sqlite'
        db = sqlite3.connect(path)
        try:
            # An executable inventory cannot be represented as inherited facts.
            with db:
                columns = list(db.execute('PRAGMA table_info(handoffs)'))
                db.execute('INSERT INTO handoffs VALUES('+','.join('?' for _ in columns)+')',
                    [1 if 'INT' in row[2] else 'synthetic' for row in columns])
        finally:
            db.close()
    elif fault == 'virtual':
        mutate_database(source, 'CREATE VIRTUAL TABLE unsupported USING fts5(text)')
    else:
        mutate_database(source, 'CREATE TABLE unsupported(x, y GENERATED ALWAYS AS (x))')
    code = 'source_schema_unsupported' if fault in {'virtual', 'hidden'} else 'source_execution_inventory_out_of_scope'
    value = failure(source, tmp_path/'new', code)
    assert value['publication_state'] == 'not_created'


@pytest.mark.parametrize('fault', ['pending', 'implementation', 'target_faa', 'descriptor'])
def test_exact_original_authorities_are_required(tmp_path, fault):
    source = checkpoint_source_fixture(tmp_path)
    if fault == 'pending':
        source['arguments']['expected_pending_request_sha256'] = '0'*64
    elif fault == 'implementation':
        source['arguments']['expected_source_implementation_sha256'] = '0'*64
    elif fault == 'target_faa':
        (source['case_directory']/'target.faa').write_text('>changed\nM\n')
    else:
        path = source['arguments']['source_run_directory']/'episode-execution-binding.json'
        value = json.loads(path.read_text()); value['settings_sha256'] = '0'*64
        write_json(path, value)
    assert failure(source, tmp_path/'new', 'source_identity_mismatch')['publication_state'] == 'not_created'


@pytest.mark.parametrize('missing', ['assessment', 'native', 'target'])
def test_explicit_baseline_covers_every_committed_revision_and_native_fact(tmp_path, missing):
    source = checkpoint_source_fixture(tmp_path)
    ref = source[missing]
    source['arguments']['initial_known_record_refs'] = tuple(r for r in source['arguments']['initial_known_record_refs'] if r != ref)
    value = failure(source, tmp_path/'new', 'baseline_incomplete')
    assert ref in value['affected_refs'] and value['publication_state'] == 'not_created'


def test_dangling_extra_reference_retains_private_stage(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    source['arguments']['initial_known_record_refs'] += ('source_'+'0'*24,)
    value = failure(source, tmp_path/'new', 'reference_invalid')
    assert value['publication_state'] == 'retained_stage'
    assert Path(value['staging_workspace']).is_dir()
    assert not (tmp_path/'new').exists()


def test_all_registered_artifacts_including_unreachable_are_required(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    workspace = source['arguments']['source_workspace']
    with Store(workspace) as store:
        artifact = store.artifact(b'SYNTHETIC unreachable registered bytes')
    checksum = artifact.removeprefix('artifact_')
    (workspace/'artifacts'/checksum[:2]/checksum).write_bytes(b'corrupt')
    value = failure(source, tmp_path/'new', 'artifact_custody_failure')
    assert artifact in value['affected_refs']


@pytest.mark.parametrize('delta', ['table', 'index', 'artifact', 'old_row'])
def test_actual_destination_constructor_must_not_change_schema_or_old_data(tmp_path, delta):
    source = checkpoint_source_fixture(tmp_path)
    original = Store.__init__
    def changed(self, path):
        original(self, path)
        if delta == 'table':
            self.db.execute('CREATE TABLE implicit_upgrade(value)')
        elif delta == 'index':
            self.db.execute('CREATE INDEX implicit_upgrade ON fixture_typed_cells(value)')
        elif delta == 'artifact':
            self.artifact(b'not declared lineage')
        else:
            self.db.execute('UPDATE fixture_typed_cells SET value=2 WHERE typeof(value)=\'integer\'')
    with patch.object(Store, '__init__', changed):
        value = failure(source, tmp_path/'new', 'snapshot_mismatch')
    assert value['publication_state'] == 'retained_stage'
    assert value['affected_refs'][0] == 'destination_constructor_schema_or_rows'
    assert value['staging_workspace'] in value['affected_refs']


def test_packed_component_corruption_is_not_materialized_or_repaired(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    # Material metadata is copied opaquely, then its actual span reader checks
    # the component digest without materializing an independent sequence.
    mutate_database(source, 'UPDATE material_component_spans SET end=end+1 WHERE part=0')
    from gene_annotation_episode import materials_packing
    with patch.object(materials_packing, 'materialize', side_effect=AssertionError('must never materialize')):
        value = failure(source, tmp_path/'new', 'material_custody_failure')
    assert value['publication_state'] == 'retained_stage'


def test_new_run_receipts_inherit_findings_native_timing_and_no_local_history(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    result = fork(source, tmp_path/'new')
    new_run = 'run_'+'2'*32
    episode = EpisodeRef(new_run, (('annotation', 'new'),))
    with Store(tmp_path/'new') as store:
        receipts = EpisodeReceipts(store, new_run)
        receipts.bind(episode.episode_id)
        receipts.receive(episode.episode_id, result['initial_known_record_refs'], kind='initial')
        known = list(receipts.known(episode.episode_id, record_type='assessment'))
        baseline = list(receipts.known(episode.episode_id, record_type='assessment', baseline=True))
        assert source['assessment'] in known and known == baseline
        scope = {'subject_refs': [source['target']]}
        # Actual saved original factory, unchanged parameters; this read-only
        # preparation constructs no services and performs no controller action.
        policy, _ = _load_policy(source['arguments']['source_run_directory'], None, None, resume=True)
        first = policy.project_task_credit(store, scope, known_assessment_refs=known)
        initial = policy.project_task_credit(store, scope, known_assessment_refs=baseline)
        assert first['credit'] == initial['credit'] == 7
        assert first['credit']-initial['credit'] == 0
        natives = list(receipts.known(episode.episode_id, record_type='native_execution'))
        native_initial = list(receipts.known(episode.episode_id, record_type='native_execution', baseline=True))
        details = NativeTimingInformation(.5).read_details(store, scope, known_execution_refs=natives,
            initial_execution_refs=native_initial, details_limit=10, details_offset=0)
        assert details['monitoring_information_credit'] == 0 and details['native_execution_measurements'] == []
        assert natives == native_initial == [source['native']]
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?', (new_run,)).fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?',
            (source['arguments']['source_run_id'],)).fetchone()[0] == 3


@pytest.mark.parametrize('field', ['binding_definitions', 'scientific_knowledge',
    'native_timing_information', 'episode_record_receipts'])
def test_missing_original_policy_setting_cannot_bypass_saved_definitions(tmp_path, field):
    source = checkpoint_source_fixture(tmp_path)
    directory = source['arguments']['source_run_directory']
    # Rebuild consistent outer manifest/descriptor digests after removing one
    # required semantic setting. It must fail the original policy relationship.
    with Store(source['arguments']['source_workspace']) as store:
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
        settings.pop(field)
        digest = sha(canonical(settings).encode())
        binding = json.loads((directory/'episode-execution-binding.json').read_text())
        binding['settings_sha256'] = digest
        store.db.execute('UPDATE runtime_runs SET settings=?', (canonical(settings),))
        store.db.execute('UPDATE runtime_execution_bindings SET settings_sha256=?,runtime_binding=?',
            (digest, canonical(binding)))
        write_json(directory/'episode-execution-binding.json', binding)
        write_json(directory/'run.json', {'run_id': source['arguments']['source_run_id'], **settings})
    assert failure(source, tmp_path/'new', 'source_identity_mismatch')['publication_state'] == 'not_created'


def test_no_replace_handles_destination_appearing_after_preparation(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    destination = tmp_path/'new'
    publish = custody._publish
    def raced(owner, stage):
        destination.mkdir()
        (destination/'sentinel').write_bytes(b'other publisher')
        return publish(owner, stage)
    with patch.object(custody, '_publish', raced):
        value = failure(source, destination, 'destination_exists')
    assert value['publication_state'] == 'retained_stage'
    assert (destination/'sentinel').read_bytes() == b'other publisher'
    assert Path(value['staging_workspace']).is_dir()


@pytest.mark.parametrize('cut', ['before_rename', 'after_precheck', 'parent_fsync', 'unknown_stage'])
def test_publication_races_preserve_exact_state_and_actual_location(tmp_path, cut):
    source = checkpoint_source_fixture(tmp_path)
    parent = tmp_path/'publication-parent'
    parent.mkdir()
    moved = tmp_path/'moved-parent'
    destination = parent/'new'
    publish, load_library = custody._publish, ctypes.CDLL
    def move_parent():
        parent.rename(moved)
        parent.mkdir()
        (parent/'unrelated').write_bytes(b'preserve replacement')
    def publishing(owner, stage):
        if cut == 'before_rename':
            move_parent()
            return publish(owner, stage)
        if cut == 'after_precheck':
            library = load_library(None, use_errno=True)
            actual = library.renameat2
            actual.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            actual.restype = ctypes.c_int
            def renamed(*args):
                move_parent()
                return actual(*args)
            class Library:
                renameat2 = staticmethod(renamed)
            with patch.object(custody.ctypes, 'CDLL', return_value=Library()):
                return publish(owner, stage)
        if cut == 'parent_fsync':
            real_fsync = os.fsync
            def sync(fd):
                if fd == owner.parent_fd:
                    raise OSError(errno.EIO, 'synthetic parent fsync failure')
                return real_fsync(fd)
            with patch.object(custody.os, 'fsync', sync):
                return publish(owner, stage)
        raise AssertionError('unexpected publication')
    if cut == 'unknown_stage':
        sync_tree, readlink = custody._sync_tree, os.readlink
        deny_location = False
        def inaccessible(stage):
            nonlocal deny_location
            sync_tree(stage)
            move_parent()
            deny_location = True
            raise OSError(errno.EACCES, 'synthetic inaccessible external parent')
        def no_location(path, *args, **kwargs):
            if deny_location and str(path).startswith('/proc/self/fd/'):
                raise OSError(errno.EACCES, 'synthetic fd location unavailable')
            return readlink(path, *args, **kwargs)
        with patch.object(custody, '_sync_tree', inaccessible), patch.object(custody.os, 'readlink', no_location):
            value = failure(source, destination, 'publication_failure')
    else:
        with patch.object(custody, '_publish', publishing):
            value = failure(source, destination, 'publication_failure')
    if cut in {'before_rename', 'unknown_stage'}:
        assert value['publication_state'] == 'retained_stage'
        assert value['published_workspace'] is None
        if cut == 'unknown_stage':
            assert value['staging_workspace'] is None
        else:
            assert Path(value['staging_workspace']).parent == moved
    else:
        assert value['staging_workspace'] is None
        assert value['publication_state'] == ('published_location_unconfirmed' if cut == 'after_precheck'
            else 'published_durability_unconfirmed')
        assert Path(value['published_workspace']) == ((moved/'new') if cut == 'after_precheck' else destination)
        assert value['source_unchanged'] is True
    if cut != 'parent_fsync':
        assert (parent/'unrelated').read_bytes() == b'preserve replacement'


def test_source_external_change_detected_without_repair_or_publication(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    source_file = source['case_directory']/'target.faa'
    add_lineage = custody._add_lineage
    def external_writer(*args, **kwargs):
        result = add_lineage(*args, **kwargs)
        source_file.write_bytes(b'EXTERNAL synthetic mutation\n')
        return result
    with patch.object(custody, '_add_lineage', external_writer):
        value = failure(source, tmp_path/'new', 'source_changed')
    assert value['source_unchanged'] is False and value['publication_state'] == 'retained_stage'
    assert source_file.read_bytes() == b'EXTERNAL synthetic mutation\n'


def test_typed_row_digest_has_independent_storage_class_reference(tmp_path):
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE typed(value)')
    values = [None, 1, 1.0, 'a\0Ω', b'a\0\xff', 1]
    db.executemany('INSERT INTO typed VALUES(?)', [(v,) for v in values])
    def frame(raw):
        return struct.pack('>Q', len(raw))+raw
    cells = [b'N'+frame(b''), b'I'+frame(b'1'), b'R'+frame(struct.pack('>d', 1.0)),
        b'T'+frame('a\0Ω'.encode()), b'B'+frame(b'a\0\xff'), b'I'+frame(b'1')]
    expected = sha(b'sqlite_storage_class_frame_v1\0'+frame(b'typed')+struct.pack('>Q', 1)
        +frame(b'value')+struct.pack('>Q', 6)+b''.join(frame(v) for v in sorted(cells)))
    manifest = custody._table_manifest(db, tmp_path)
    assert manifest['tables'] == [{'name': 'typed', 'column_names': ['value'], 'row_count': 6,
        'typed_rows_sha256': expected}]
    db.close()


@pytest.mark.parametrize('cut', ['before_create', 'constructor', 'before_lineage'])
def test_fd_stage_and_actual_memory_store_resist_parent_replacement(tmp_path, cut):
    source = checkpoint_source_fixture(tmp_path)
    before = tree(source['arguments']['source_implementation_root'])
    parent, moved = tmp_path/'publication-parent', tmp_path/'moved-parent'
    parent.mkdir()
    destination = parent/'new'
    create, initialize, add_lineage = custody._create_stage, Store.__init__, custody._add_lineage
    observations = []
    def move():
        parent.rename(moved)
        parent.mkdir()
        (parent/'sentinel').write_bytes(b'replacement must stay untouched')
    def creating(owner):
        if cut == 'before_create':
            move()
        return create(owner)
    def constructor(self, path):
        if cut == 'constructor':
            move()
        initialize(self, path)
        assert type(self) is custody._PinnedStore
        assert [(r[1], r[2]) for r in self.db.execute('PRAGMA database_list')] == [('main', '')]
        assert self.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert type(self).artifact is Store.artifact and type(self).put is Store.put
        assert type(self).get is Store.get and type(self).transaction is Store.transaction
        observations.append('actual_super_constructor_on_original_pages')
    def lineage(*args, **kwargs):
        if cut == 'before_lineage':
            move()
        return add_lineage(*args, **kwargs)
    with patch.object(custody, '_create_stage', creating), patch.object(Store, '__init__', constructor), \
            patch.object(custody, '_add_lineage', lineage):
        value = failure(source, destination, 'publication_failure')
    assert observations == ['actual_super_constructor_on_original_pages']
    assert value['publication_state'] == 'retained_stage'
    stage = Path(value['staging_workspace'])
    assert stage.parent == moved and stage.is_dir()
    assert tree(parent) == {'sentinel': (sha(b'replacement must stay untouched'),
        len(b'replacement must stay untouched'), 0o644)}
    assert tree(source['arguments']['source_implementation_root']) == before
    assert (stage/'checkpoint/state.sqlite3').read_bytes() == (source['arguments']['source_workspace']/'state.sqlite3').read_bytes()
    assert (stage/'state.sqlite3').stat().st_ino != (stage/'checkpoint/state.sqlite3').stat().st_ino
    with Store(stage) as reopened:
        assert reopened.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert reopened.db.execute("SELECT count(*) FROM records WHERE json_extract(data,'$.provider')='caller.scientific_checkpoint_fork'").fetchone()[0] == 2
    assert not list(ROOT.glob('file:*'))


def test_replaced_working_inode_is_checked_before_truncation(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    add_lineage = custody._add_lineage
    replacement = b'EXTERNAL replacement must not be truncated'
    def changed(store, *args, **kwargs):
        result = add_lineage(store, *args, **kwargs)
        path = store.path.anchor/'state.sqlite3'
        path.unlink()
        path.write_bytes(replacement)
        return result
    with patch.object(custody, '_add_lineage', changed):
        value = failure(source, tmp_path/'new', 'destination_lineage_failure')
    assert value['publication_state'] == 'retained_stage'
    assert (Path(value['staging_workspace'])/'state.sqlite3').read_bytes() == replacement


@pytest.mark.parametrize('fault', ['invented', 'duplicate'])
def test_known_observation_decision_indices_require_distinct_actual_actions(tmp_path, fault):
    source = checkpoint_source_fixture(tmp_path)
    path = source['arguments']['source_workspace']/'state.sqlite3'
    db = sqlite3.connect(path)
    try:
        raw = json.loads(db.execute('SELECT observation FROM runtime_observations WHERE unit_index=1').fetchone()[0])
        raw['decision_index'] = 6 if fault == 'invented' else 0
        with db:
            db.execute('UPDATE runtime_observations SET observation=? WHERE unit_index=1', (canonical(raw),))
    finally:
        db.close()
    assert failure(source, tmp_path/'new', 'destination_lineage_failure')['publication_state'] == 'retained_stage'


@pytest.mark.parametrize('field', ['models', 'restoration', 'job_episodes'])
def test_original_job_and_model_operands_cannot_diverge_under_rehashed_settings(tmp_path, field):
    source = checkpoint_source_fixture(tmp_path)
    directory = source['arguments']['source_run_directory']
    with Store(source['arguments']['source_workspace']) as store:
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
        settings[field] = {}
        digest = sha(canonical(settings).encode())
        binding = json.loads((directory/'episode-execution-binding.json').read_text())
        binding['settings_sha256'] = digest
        store.db.execute('UPDATE runtime_runs SET settings=?', (canonical(settings),))
        store.db.execute('UPDATE runtime_execution_bindings SET settings_sha256=?,runtime_binding=?',
            (digest, canonical(binding)))
        write_json(directory/'episode-execution-binding.json', binding)
        write_json(directory/'run.json', {'run_id': source['arguments']['source_run_id'], **settings})
    assert failure(source, tmp_path/'new', 'source_identity_mismatch')['publication_state'] == 'not_created'


def test_dna_only_declared_case_and_extra_actual_member_artifact_refs(tmp_path):
    source = checkpoint_source_fixture(tmp_path)
    path = source['case_directory']/'case.json'
    case = json.loads(path.read_text()); case['target_files'].pop('target.faa'); write_json(path, case)
    (source['case_directory']/'target.faa').unlink()
    with Store(source['arguments']['source_workspace']) as store:
        member = store.db.execute('SELECT id FROM material_members ORDER BY id LIMIT 1').fetchone()[0]
        artifact = store.db.execute('SELECT id FROM artifacts ORDER BY id LIMIT 1').fetchone()[0]
    source['arguments']['initial_known_record_refs'] += (member, artifact)
    result = fork(source, tmp_path/'new')
    receipt = json.loads(Path(result['receipt']['path']).read_bytes())
    assert {member, artifact} <= set(result['initial_known_record_refs'])
    assert not any(row['source_path'].endswith('target.faa') for row in receipt['source']['authority_files'])




