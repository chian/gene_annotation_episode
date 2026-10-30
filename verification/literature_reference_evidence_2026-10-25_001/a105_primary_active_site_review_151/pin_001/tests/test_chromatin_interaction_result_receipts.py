"""448 completed-action receipts with actual Store/runtime and native controls.

The returns port below is an explicitly labeled strict test double. The harness
writes selected runtime rows using Journal, runs actual PracticalResourceEpisodes,
C3 native/worker and root's result host, and freezes typed form records. It does
not run Workflow/method_loop or prove the production returns implementation.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_progress import ExecutionTargetReader
from gene_annotation_episode.chromatin_interaction_return_views import (
    FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE, chromatin_fact_sources,
)
from gene_annotation_episode import chromatin_interaction_result_receipts as R
from gene_annotation_episode.native_chromatin_interaction_results import NativeChromatinInteractionResults
from gene_annotation_episode.native_chromatin_interaction_contracts import POLICY, requested_job_from_chromatin, _dependency_roots
from gene_annotation_episode.native_chromatin_interaction_preparation import freeze_chromatin_software_binding
from gene_annotation_episode.native_chromatin_interaction_local import local_chromatin_interaction_plan
from gene_annotation_episode.native_file_capture import retained_native_file, NativeFileCaptureError
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.state import Store

ROOT = Path(os.environ['RECEIPT448_REPO'])
ATTEMPT = Path(os.environ['RECEIPT448_ATTEMPT'])
WORKED = {r['example_key']: r['record'] for r in json.loads((ROOT /
    'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json').read_text())['records']}


def deny(*args, **kwargs):
    pytest.fail('historical read attempted science, software or native execution')


class StrictReturnsDouble(EpisodeReturnRecords):
    """External447 port isolation; verifies actual Journal rows, not metadata hints."""
    def __init__(self, owner):
        super().__init__(owner.store, owner.run_id, failure_prefix='strict448_')
        self.owner = owner
        self.calls = []

    def _commission(self, parent, child, *, construction=False):
        self.authenticate(parent)
        self.authenticate(child, allow_unsaved=construction)
        assert child.path[:-1] == parent.path
        index = int(child.path[-1][1].removeprefix('child_'))
        row = self.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
            (self.run_id, parent.episode_id, index)).fetchone()
        assert row is not None
        selected = json.loads(row['action'])
        assert selected == {'kind': 'episode_child', 'role': child.role,
            'assignment': plain(child.assignment), 'scope': plain(child.scope),
            'purpose': child.request['report_contract']['decision'],
            'schema_json': canonical(child.request['report_contract']['measurements']['schema'])}

    def _received(self, context, sources, *, allowed=None):
        self.authenticate(context)
        self.calls.append(deepcopy(allowed))
        rows = self.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
            'AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()
        by_index = {r['decision_index']: r for r in rows}
        prefix = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
        if allowed is not None:
            selected = []
            for witness in allowed:
                row = by_index[witness['decision_index']]
                assert witness == {'decision_index': row['decision_index'], 'delivery_ref': row['delivery_ref'],
                    'child_episode_id': row['child_episode_id'], 'contract_sha256': digest(json.loads(row['contract'])),
                    'form_sha256': digest(json.loads(row['form']))}
                selected.append(row)
            rows = selected
        groups, origins = {s: [] for s in sources}, {}
        for row in rows:
            child, form, schema = self._attempt(context, row['decision_index'])
            self._commission(context, child)
            frozen = self.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, child.episode_id)).fetchone()
            assert form == json.loads(frozen['form'])
            for field, spec in schema['properties'].items():
                source = spec.get('x-source')
                if source not in sources:
                    continue
                for value in form[field]:
                    if value not in groups[source]:
                        groups[source].append(deepcopy(value))
                    if source == SAVED_SOURCE:
                        exact = self.owner.native_chromatin_interaction_results.completed_saved_bundle_origins(child, value)
                        assert exact
                        origins.setdefault(canonical(value), []).extend(o for o in exact
                            if o not in origins.get(canonical(value), []))
        return groups, origins, prefix

    def authenticate_received_saved_bundle(self, context, bundle):
        self.authenticate(context, allow_unsaved=True)
        if context.role == 'results':
            assert context.assignment['selector']['mode'] == 'saved_sheet_recalculation'
            assert plain(context.assignment)['selector']['saved_sheet_bundle'] == bundle
            manifest = EpisodeReceipts.read_manifest(self.db, self.run_id, context.episode_id)
            assert manifest == plain(context.request)['message']['knowledge_inheritance']
            parent = self.context(manifest['parent_episode_id'])
            self._commission(parent, context)
            groups, origins, _ = self._received(parent, (SAVED_SOURCE,), allowed=manifest['received_report_prefix']['attempts'])
        else:
            groups, origins, _ = self._received(context, (SAVED_SOURCE,))
        assert bundle in groups[SAVED_SOURCE]
        known = set(self.owner.received.known(context.episode_id, baseline=context.role == 'results'))
        assert {f['artifact_ref'] for f in (bundle['sheet'], *bundle['tables'])} <= known
        return tuple(origins[canonical(bundle)])


class Harness:
    _selected_result_action = ExecutionEpisodes._selected_result_action
    def __init__(self, directory, software, *, second_end=40):
        self.directory = directory
        directory.mkdir()
        self.run_id = 'receipt448-' + directory.name
        self.store = Store(directory / 'store')
        self.store.create_problem(raw_sequence='ACGT', molecule='dna')
        self.scope = self.store.validate_scope()
        self.journal = Journal(self.store, self.run_id)
        self.received = EpisodeReceipts(self.store, self.run_id)
        self.contexts, self.outcomes = [], []
        self.handoff_unit, self.acquired_record_unit = 7, 3
        self.native_chromatin_interaction_returns = StrictReturnsDouble(self)
        self.native_chromatin_interaction_results = NativeChromatinInteractionResults(self)
        self.host = self.native_chromatin_interaction_results
        self.root = self.context('annotation', None, 0, {}, {'properties': {}})
        request = deepcopy(WORKED['raw.request'])
        request['populations'] = [dict(request['populations'][0], population_key='p0'),
            dict(request['populations'][0], population_key='p1', end_bp=second_end)]
        fixtures = ROOT / 'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures'
        bindings = []
        for key, raw, format in [('contact', (fixtures / 'four-bin-raw-weighted.cool').read_bytes(), 'cooler_hdf5_v3'),
                ('elements', b'chrA\t0\t2\tE\nchrA\t20\t23\tP\nchrA\t30\t33\tQ\n', 'bed_outer_span_v1')]:
            artifact = self.store.artifact(raw)
            source = self.store.put('source', {'provider': 'synthetic448.' + key, 'accession': None, 'uri': None,
                'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
            meta = self.store.get(artifact)
            file = {'artifact_ref': artifact, 'sha256': meta['sha256'], 'size_bytes': meta['size'], 'format': format}
            request[key]['source_ref'], request[key]['file'] = source['id'], file
            bindings.append({'input_key': request[key]['input_key'], 'file': file, 'path': str(retained_native_file(self.store, file))})
            self.received.receive(self.root.episode_id, [source['id'], artifact], kind='initial')
        workspace = directory / 'workspace'
        workspace.mkdir()
        environment = {'PYTHONPATH': os.pathsep.join([software['module_root'], *_dependency_roots(software)]),
            'PYTHONHOME': os.sys.base_prefix, 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(workspace / 'tmp'), 'TMP': str(workspace / 'tmp'), 'TEMP': str(workspace / 'tmp'),
            'XDG_CACHE_HOME': str(workspace / 'cache'), 'PIP_CACHE_DIR': str(workspace / 'cache/pip'),
            'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
        requested = requested_job_from_chromatin({'request': request, 'software': software, 'input_bindings': bindings}, environment=environment)
        assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'native448', 'resource_id': 'local',
            'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': 'usable_handoff', 'requested_job': requested,
            'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
            'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
        self.resources = {'local': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
            'native_chromatin_interactions': [{'operation': 'analyze_chromatin_interactions', 'resource_kind': 'local',
                'analysis_modes': request['analysis_modes'], 'supported_formats': ['cooler_hdf5_v3'], 'software': software}]}}
        launch = self.context('launch', self.root, 0, {}, {'properties': {}})
        self.local = self.context('launch_local', launch, 0, assignment, {'properties': {}})
        self.practical = PracticalResourceEpisodes(None, directory=directory, resources=self.resources, store=self.store)
        self.practical.initialize(self.local)
        key = self.select(self.local, 'practical.job.start')
        result = asyncio.run(self.practical.execute(self.local, 'practical.job.start', {}, key))
        assert result['status'] == 'completed', result
        self.finish(self.local, 0, result)
        self.handoff = result['record_refs'][0]
        self.received.receive(self.root.episode_id, [self.handoff], kind='child_form', source_index=0)
        reader = ExecutionTargetReader(self.store, run_id=self.run_id, directory=directory, resources=self.resources, api_execution=None)
        self.job_progress_provider = SimpleNamespace(targets=reader)
        self.target = reader.read_target(self.handoff, self.scope)
        outcome = native.wait_job(native.NativeJobHandle(Path(self.target['execution_id'])))
        assert outcome.returncode == (0 if second_end == 40 else 1), outcome.stderr_path.read_text()
        self.plan = local_chromatin_interaction_plan(assignment, self.target['execution_id'])

    def _selection(self, context, receiver_selection=None):
        return {'initial_known_record_refs': list(self.received.known(context.episode_id, baseline=True))}

    def context(self, role, parent, index, assignment, schema):
        path = (('annotation', 'root'),) if parent is None else (*parent.path, (role, 'child_' + str(index)))
        episode_id = EpisodeRef(self.run_id, path).episode_id
        manifest = self.received.bind(episode_id, None if parent is None else parent.episode_id)
        request = {'message': {'scope': self.scope, 'episode_assignment': assignment, 'knowledge_inheritance': manifest},
            'report_contract': {'decision': 'fixture448 selected facts', 'measurements': {'schema': schema}}}
        context = BindingContext(self.run_id, episode_id, role, path, self.scope, assignment, request)
        with self.store.transaction():
            if parent is not None:
                selection = {'kind': 'episode_child', 'role': role, 'assignment': assignment, 'scope': self.scope,
                    'purpose': request['report_contract']['decision'], 'schema_json': canonical(schema)}
                self.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
                    'action': canonical(selection), 'result': None, 'credit': None})
            self.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(plain(path)),
                'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
        return context

    def select(self, context, name='execution.results.collect', index=0):
        with self.store.transaction():
            self.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
                'action': canonical({'kind': 'tool', 'tool': name, 'arguments': {}}), 'result': None, 'credit': None})
        return f'{self.run_id}:{context.episode_id}:{index}'

    def finish(self, context, index, result):
        with self.store.transaction():
            self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (canonical(result), self.run_id, context.episode_id, index))

    def result_context(self, *, saved=None, index=None, projection=None):
        selector = deepcopy(WORKED['raw.selector'])
        selector['population_keys'] = ['p1', 'p0']  # Explicit request order is legal.
        if saved is not None:
            selector.update(mode='saved_sheet_recalculation', saved_sheet_bundle=deepcopy(saved))
            selector['parameters']['contact']['fold_threshold'] = 1
        if projection is not None:
            selector['projection'] = deepcopy(projection)
        schema = {'type': 'object', 'properties': {name: chromatin_fact_sources()[name]['report_schema'] for name in FACT_SOURCES},
            'required': list(FACT_SOURCES), 'additionalProperties': False}
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': self.handoff, 'selector': selector}
        context = self.context('results', self.root, len(self.contexts) + 1 if index is None else index, assignment, schema)
        self.contexts.append(context)
        return context

    def collect(self, context, *, index=0, deliver=True):
        key = self.select(context, index=index)
        result = asyncio.run(self.host.execute(context, self.target, 'execution.results.collect', {}, key))
        self.finish(context, index, result)
        self.outcomes.append(result)
        if deliver:
            self.deliver(context)
        return result['result']

    def deliver(self, context):
        facts = self.host.own_fact_groups(context, verify_artifacts=False)
        form = deepcopy(facts)
        index = int(context.path[-1][1].removeprefix('child_'))
        with self.store.transaction():
            self.journal.save('runtime_forms', {'episode_id': context.episode_id, 'facts': canonical(facts), 'form': canonical(form)})
            self.journal.save('runtime_report_attempts', {'parent_episode_id': self.root.episode_id, 'decision_index': index,
                'delivery_ref': 'delivery448-' + context.episode_id, 'child_episode_id': context.episode_id,
                'contract': canonical(plain(context.request)['report_contract']), 'form': canonical(form), 'failure': None})
        refs = [file['artifact_ref'] for bundle in facts[SAVED_SOURCE] for file in (bundle['sheet'], *bundle['tables'])]
        self.received.receive(self.root.episode_id, refs, kind='child_form', source_index=index)
        return facts


@pytest.fixture(scope='module')
def software():
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    return freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(ATTEMPT / 'native_software'), python_executable=os.sys.executable)


@pytest.fixture(scope='module')
def case(tmp_path_factory, software):
    value = Harness(tmp_path_factory.mktemp('receipt-parent') / 'complete', software)
    first = value.result_context()
    original = value.collect(first)
    bundle, = original['facts'][SAVED_SOURCE]
    saved = value.result_context(saved=bundle)
    value.collect(saved)
    yield value
    value.store.close()


def test_actual_native_multiple_tables_duplicate_bytes_and_exact_projection(case):
    first, second = [r['result'] for r in case.outcomes]
    bundle, = first['facts'][SAVED_SOURCE]
    assert len(first['qualified_files']['tables']) == 10
    assert len(bundle['tables']) == 6
    assert len({canonical(f) for f in bundle['tables']}) == 3
    assert first['facts'][SAVED_SOURCE] == second['facts'][SAVED_SOURCE]
    projection, = first['facts'][PROJECTION_SOURCE]
    assert projection['population_keys'] == ['p1', 'p0']
    assert [r['fields']['fold_enrichment']['value'] for r in projection['rows']] == [1.5, None, 1.5, None]
    assert projection['rows'][1]['fields']['raw_contact']['value'] == 0
    assert projection['rows'][1]['fields']['expected_contact']['value'] == 0
    assert projection['rows'][1]['fields']['fold_enrichment']['reason'] == 'zero_denominator'
    assert first['delivery_complete'] and second['delivery_complete']
    assert first['acquired_population'] == digest(case.plan['identity'])
    assert second['acquired_population'] is None
    assert case.host.credit_view(case.contexts[0], None)['new_acquired_record_count'] == 1
    assert case.host.credit_view(case.contexts[1], None)['new_acquired_record_count'] == 0
    assert first['worker_execution']['metadata']['verified_cgroup']['memory_swap_max'] == 0


def test_historical_replay_after_all_retained_byte_loss(case, monkeypatch):
    before = [case.host.own_fact_groups(c, verify_artifacts=False) for c in case.contexts]
    removed = []
    try:
        # Includes input bytes, practical receipt artifacts and worker outputs.
        for path in (case.store.path / 'artifacts').glob('*/*'):
            removed.append((path, path.read_bytes()))
            path.unlink()
        monkeypatch.setattr('gene_annotation_episode.native_file_capture.retained_native_file', deny)
        monkeypatch.setattr('gene_annotation_episode.native_chromatin_interaction_local.local_chromatin_interaction_plan', deny)
        monkeypatch.setattr(type(case.job_progress_provider.targets), 'observe_target', deny)
        for context, expected in zip(case.contexts, before):
            assert case.host.own_fact_groups(context, verify_artifacts=False) == expected
            assert case.host.completion(context) is not None
            key = f'{case.run_id}:{context.episode_id}:0'
            assert asyncio.run(case.host.execute(context, case.target, 'execution.results.collect', {}, key))['result']['facts'] == expected
    finally:
        for path, raw in removed:
            path.write_bytes(raw)


def test_saved_new_use_requires_current_whole_bundle(case):
    bundle = case.outcomes[0]['result']['facts'][SAVED_SOURCE][0]
    context = case.result_context(saved=bundle)
    file = bundle['tables'][1]
    path = retained_native_file(case.store, file)
    raw = path.read_bytes()
    try:
        path.unlink()
        receipt = case.collect(context, deliver=False)
        assert receipt['acquired_population'] is None and not receipt['delivery_complete']
        assert receipt['facts'][SAVED_SOURCE] == []
        assert any(f['code'] == 'input_unavailable' and f['artifact_ref'] == file['artifact_ref'] for f in receipt['host_failures'])
        assert case.host.completion(case.contexts[0]) is not None
    finally:
        path.write_bytes(raw)


@pytest.mark.parametrize('field', ['scope', 'request', 'assignment', 'run_id', 'role'])
def test_foreign_original_context_rejected(case, field):
    context = case.contexts[0]
    value = plain(getattr(context, field)) if field in ('scope', 'request', 'assignment') else getattr(context, field)
    if field == 'scope': value['subject_refs'] = []
    elif field == 'request': value['foreign'] = True
    elif field == 'assignment': value['selector']['parameters']['contact']['fold_threshold'] = 99
    else: value = 'foreign'
    with pytest.raises((ValueError, AssertionError)):
        case.host.receipts.completed_receipts(replace(context, **{field: value}))


def test_staged_receipt_never_completed_authority(case):
    context = case.contexts[0]
    row = case.journal.row('runtime_actions', context.episode_id, 0)
    try:
        case.finish(context, 0, None)
        # SQL NULL is the incomplete action, not the JSON value null.
        with case.store.transaction():
            case.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
                (case.run_id, context.episode_id))
        assert case.host.receipts.completed_receipts(context) == []
        with pytest.raises(ValueError):
            case.host.receipts.read_completed(episode_id=context.episode_id,
                operation_key=f'{case.run_id}:{context.episode_id}:0', scope=case.scope)
    finally:
        case.finish(context, 0, json.loads(row['result']))


@pytest.mark.parametrize('mutation', ['table_key', 'table_order', 'table_digest', 'request_digest', 'population', 'worker_policy', 'worker_command', 'projection', 'extra'])
def test_receipt_corruptions_fail(case, mutation):
    receipt = deepcopy(case.outcomes[0]['result'])
    if mutation == 'table_key': receipt['qualified_files']['tables'][0]['table_key'] = 'foreign'
    elif mutation == 'table_order': receipt['sheet_evidence']['data_tables'][0:2] = reversed(receipt['sheet_evidence']['data_tables'][0:2])
    elif mutation == 'table_digest': receipt['sheet_evidence']['data_tables'][0]['file'] = receipt['sheet_evidence']['data_tables'][1]['file']
    elif mutation == 'request_digest': receipt['sheet_evidence']['request_sha256'] = 'a' * 64
    elif mutation == 'population': receipt['sheet_evidence']['populations'][0]['selected_region']['end_bp'] = 100
    elif mutation == 'worker_policy': receipt['worker_execution']['policy']['wall_seconds'] = 1
    elif mutation == 'worker_command': receipt['worker_execution']['intent']['command'] = ['/bin/true']
    elif mutation == 'projection': receipt['projection']['rows'][0]['fields']['fold_enrichment']['value'] = 123
    else: receipt['extra'] = 'undeclared'
    with pytest.raises((ValueError, AssertionError)):
        case.host.receipts.validate(receipt, receipt['intent'])


def test_control_and_runtime_reconciliation(case):
    context, receipt = case.contexts[0], case.outcomes[0]['result']
    path = case.host.receipts.action_directory(context.episode_id, receipt['intent']['operation_key']) / 'sheet-evidence.json'
    raw = path.read_bytes()
    try:
        changed = deepcopy(receipt['sheet_evidence'])
        changed['populations'][0]['raw_cell_population']['stored_rows'] += 1
        path.chmod(0o600)
        path.write_text(canonical(changed))
        with pytest.raises(ValueError): case.host.receipts.completed_receipts(context)
    finally:
        path.write_bytes(raw)
        path.chmod(0o444)
    row = case.journal.row('runtime_actions', context.episode_id, 0)
    try:
        changed = json.loads(row['result']); changed['result']['delivery_complete'] = False
        case.finish(context, 0, changed)
        with pytest.raises(ValueError): case.host.receipts.completed_receipts(context)
    finally: case.finish(context, 0, json.loads(row['result']))


def test_frozen_baseline_requires_entire_received_bundle(case):
    first, saved = case.contexts[:2]
    bundle = case.outcomes[0]['result']['facts'][SAVED_SOURCE][0]
    refs = [file['artifact_ref'] for file in (bundle['sheet'], *bundle['tables'])]
    population = case.outcomes[0]['result']['acquired_population']
    receipts = case.host.receipts
    assert receipts.baseline_populations(first, refs) == set()
    assert receipts.baseline_populations(saved, refs) == {population}
    assert receipts.baseline_populations(saved, [bundle['sheet']['artifact_ref']]) == set()
    manifest = case.received.manifest(saved.episode_id)
    assert case.native_chromatin_interaction_returns.calls[-2] == manifest['received_report_prefix']['attempts']


def test_partial_native_population_keeps_actual_acquisition_and_no_endpoint(tmp_path, software):
    case = Harness(tmp_path / 'partial', software, second_end=50)
    try:
        receipt = case.collect(case.result_context())
        assert receipt['acquired_population'] == digest(case.plan['identity'])
        assert not receipt['delivery_complete']
        assert receipt['sheet_evidence']['populations'][0]['extent'] == 'complete'
        assert receipt['sheet_evidence']['populations'][1]['extent'] != 'complete'
        projection = receipt['facts'][PROJECTION_SOURCE][0]
        values = [row['fields']['fold_enrichment']['value'] for row in projection['rows'] if row['population_key'] == 'p0']
        assert values == [1.5, None]
        saved = case.result_context(saved=receipt['facts'][SAVED_SOURCE][0])
        recalculated = case.collect(saved)
        assert recalculated['acquired_population'] is None and not recalculated['delivery_complete']
    finally: case.store.close()


def test_strict_decoding_and_fixed_table_capture(case, tmp_path):
    for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a": 1}'):
        with pytest.raises(ValueError): R.decode(raw)
    assert R.decode(b'{"a":1}') == {'a': 1}
    malformed = tmp_path / 'control.json'
    malformed.write_bytes(b'null')
    with pytest.raises(ValueError, match='invalid_record'):
        R.read_control(malformed)
    receipt = case.outcomes[0]['result']
    capture = deepcopy(receipt['worker_capture'])
    # One table loss preserves all declared table-key positions and other roles.
    row = capture['outputs'][4]['capture']
    row.update(observed=None, outcome='unavailable', failure='capture_file_unavailable')
    qualified = R.qualified_files(capture, receipt['worker_execution'])
    assert len(qualified['tables']) == 10 and qualified['tables'][0]['file'] is None
    assert qualified['tables'][1]['file'] is not None and qualified['tables'][5]['file'] is not None
    from gene_annotation_episode.native_chromatin_interaction_contracts import failure
    selected = deepcopy(receipt)
    selected['worker_capture'] = capture
    selected['intent']['assignment']['selector']['population_keys'] = ['p1']
    issue = failure('input_unavailable', 'capture', field_path='/outputs/table')
    assert case.host.receipts.selected_failures(selected, [issue]) == []


def test_repeated_original_status_and_collection_add_no_acquisition(case):
    context = case.result_context()
    key = case.select(context, 'execution.results.status')
    status = asyncio.run(case.host.execute(context, case.target, 'execution.results.status', {}, key))
    case.finish(context, 0, status)
    assert status['result']['facts'] == R.empty_facts()
    assert status['result']['acquired_population'] is None
    assert case.host.receipts.completed_receipts(context) == []
    receipt = case.collect(context, index=1)
    assert receipt['acquired_population'] == case.outcomes[0]['result']['acquired_population']
    assert case.host.credit_view(context, None)['new_acquired_record_count'] == 0
    assert receipt['delivery_complete']


def test_all_saved_origin_actions_and_private_reference_classification(case):
    bundle = case.outcomes[0]['result']['facts'][SAVED_SOURCE][0]
    context = case.result_context(saved=bundle)
    origins = case.host.receipts.origins(context, plain(context.assignment))
    assert len(origins) == 3
    assert len({(r['intent']['episode_id'], r['intent']['operation_key']) for r in origins}) == 3
    assert any(r['original_origins'] for r in origins)
    for receipt in origins:
        for file in receipt['qualified_files']['tables']:
            if file['file'] is not None:
                assert case.host.owns_reference(file['file']['artifact_ref'])
        assert case.host.owns_reference(receipt['worker_capture']['worker_result_file']['artifact_ref'])
    foreign = plain(context.assignment)
    foreign['handoff_ref'] = 'source_foreign'
    with pytest.raises(ValueError, match='handoff_conflict'):
        case.host.receipts.origins(context, foreign)


def test_production_returns_join_uses_completed_receipts_without_science_reads(case, monkeypatch):
    """Real449 ports on the448 manual Journal harness; still no Workflow claim."""
    from gene_annotation_episode.chromatin_interaction_returns import ChromatinInteractionReturns
    strict = case.native_chromatin_interaction_returns
    expected, _, _ = strict._received(case.root, FACT_SOURCES)
    production = ChromatinInteractionReturns(case)
    monkeypatch.setattr(case, 'native_chromatin_interaction_returns', production)
    monkeypatch.setattr('gene_annotation_episode.native_file_capture.retained_native_file', deny)
    monkeypatch.setattr(type(case.job_progress_provider.targets), 'observe_target', deny)
    schema = plain(case.contexts[0].request)['report_contract']['measurements']['schema']
    assert production.facts(case.root, schema) == expected
    original = case.outcomes[0]['result']
    bundle = original['facts'][SAVED_SOURCE][0]
    origins = production.authenticate_received_saved_bundle(case.contexts[1], bundle)
    assert origins == ({'episode_id': original['intent']['episode_id'], 'operation_key': original['intent']['operation_key']},)
    references = [f['artifact_ref'] for f in (bundle['sheet'], *bundle['tables'])]
    assert case.host.receipts.baseline_populations(case.contexts[1], references) == {original['acquired_population']}


def test_current_table_qualification_does_not_rewrite_historical_credit(case):
    context = case.contexts[0]
    original = case.outcomes[0]['result']
    before = (case.host.own_fact_groups(context, verify_artifacts=False), case.host.completion(context),
        case.host.credit_view(context, None))
    table = next(row['file'] for row in original['qualified_files']['tables'] if row['file'] is not None)
    path = retained_native_file(case.store, table)
    raw = path.read_bytes()
    try:
        path.unlink()
        with pytest.raises(NativeFileCaptureError):
            case.host.own_fact_groups(context, verify_artifacts=True)
        assert (case.host.own_fact_groups(context, verify_artifacts=False), case.host.completion(context),
            case.host.credit_view(context, None)) == before
    finally:
        path.write_bytes(raw)


@pytest.mark.parametrize('origin', ['unselected_action', 'wrong_owner', 'wrong_run'])
def test_saved_origin_requires_exact_existing_completed_result_action(case, monkeypatch, origin):
    context = case.contexts[1]
    first = case.outcomes[0]['result']['intent']
    selected = {'episode_id': first['episode_id'], 'operation_key': first['operation_key']}
    if origin == 'unselected_action': selected['operation_key'] = f'{case.run_id}:{first["episode_id"]}:999'
    elif origin == 'wrong_owner': selected = {'episode_id': case.local.episode_id, 'operation_key': f'{case.run_id}:{case.local.episode_id}:0'}
    else: selected['operation_key'] = 'foreign:' + first['operation_key']
    monkeypatch.setattr(case.native_chromatin_interaction_returns, 'authenticate_received_saved_bundle', lambda *_: (selected,))
    with pytest.raises((ValueError, AssertionError)):
        case.host.receipts.origins(context, plain(context.assignment))


def test_failed_projection_retains_complete_acquisition_and_allows_saved_repair(case):
    selection = deepcopy(WORKED['raw.selector']['projection'])
    selection['selection'] = {'by': 'keys', 'pair_keys': ['no_such_pair']}
    context = case.result_context(projection=selection)
    failed = case.collect(context)
    assert failed['projection'] is None and failed['qualified_files']['components'] is not None
    assert failed['acquired_population'] == digest(case.plan['identity'])
    assert case.host.receipts.original_acquisition_complete(failed)
    assert not failed['delivery_complete'] and failed['facts'][PROJECTION_SOURCE] == []
    bundle, = failed['facts'][SAVED_SOURCE]
    repaired = case.collect(case.result_context(saved=bundle))
    assert repaired['delivery_complete'] and repaired['acquired_population'] is None
    # This particular authenticated complete native witness suffices even
    # though its own originally requested projection was unavailable.
    _, complete = case.host.receipts.publication(repaired, originals=[failed])
    assert complete


def test_direct_target_rejects_incompatible_analysis_parameters(case):
    assignment = plain(case.contexts[0].assignment)
    assignment['selector']['parameters']['contact'] = None
    with pytest.raises(ValueError, match='analysis_mode_conflict'):
        case.host.receipts._target(case.contexts[0], assignment, deepcopy(case.target))
