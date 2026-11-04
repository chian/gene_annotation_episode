"""Engineering controls for real closed in-process Workflow commissions.

The fixture makes one synthetic source delivery through the ordinary method
loop. Its archives, forms, observations and receipts are produced by their real
owners. Tampering below changes only each test's owned engineering database.
No native science or external model request is performed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from method_loop import ClosedChildUnit
from method_loop.archive import iter_json

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_journal import WorkflowError
from gene_annotation_episode.runtime import Workflow, ReturnedActionUnit, _json
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import native_lifecycle
from test_runtime import FixtureController


QUESTION = 'Return the explicitly supplied engineering Source handle.'
FORM = obj({'source': {'type': 'string', 'format': 'reference',
    'x-reference-namespace': 'source', 'x-source': 'engineering_source'}})


def _encode(value, schema):
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            candidate = _encode(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get('type') == 'string' and isinstance(value, dict) and schema.get(
            'description', '').startswith('JSON encoding'):
        return json.dumps(value)
    if schema.get('type') == 'object' and isinstance(value, dict):
        result = dict(value)
        for key, node in schema.get('properties', {}).items():
            if key in result:
                result[key] = _encode(result[key], node)
            elif key in schema.get('required', []) and Draft202012Validator(node).is_valid(None):
                result[key] = None
        return result
    return value


class EngineeringBinding:
    roles = entry_roles = ('engineering',)

    def __init__(self, services, source_ref, input_ref, *, form=FORM, value=None):
        self.services, self.source_ref, self.input_ref = services, source_ref, input_ref
        self.form = deepcopy(form)
        self.fact_field, = self.form['properties']
        self.fact_source = self.form['properties'][self.fact_field]['x-source']
        self.value = source_ref if value is None else deepcopy(value)
        self.preparations = self.initializations = self.executions = 0

    def as_record(self): return {'binding_id': 'engineering_closed_commission', 'version': 'v1'}
    def child_roles(self, role): return ()
    def credit_kind(self, role): return 'scientific'
    def assignment_schema(self, role): return obj({'input_ref': {'type': 'string'}})
    def permitted_common_actions(self, context): return ('tool',)
    def allowed_children(self, parent, caller_capabilities): return ()
    def instructions(self, context): return 'Explicit engineering fixture; emit the supplied Source.'
    def decision_context(self, context, current_view): return {}
    def catalog(self, context): return [{'name': 'engineering.emit', 'input_schema': obj({})}]
    def fact_sources(self, role): return {self.fact_source: {
        'type': self.form['properties'][self.fact_field]['type'],
        'meaning': 'Supplied engineering data, with no native-producer claim.',
        'report_schema': self.form['properties'][self.fact_field]}}
    def facts(self, context, completion_snapshot): return {self.fact_source: deepcopy(self.value)}
    def received_form_references(self, context, form, schema, operation_key):
        if self.fact_source == 'macs2_peak_outcomes' and _json(schema) == _json(self.form):
            from gene_annotation_episode.macs2_peak_result_contracts import validate_macs2_peak_return
            return [validate_macs2_peak_return(value)['source_ref'] for value in form[self.fact_field]]
        return []
    def credit_view(self, context, receiver_selection): return {'credit': 0}
    def resolve(self, context, reference, namespace):
        return self.services.reference_in_scope(reference, context.scope, namespace)
    def validate_report(self, context, form, original_schema): pass
    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self.preparations += 1
        assert selection == {'input_ref': self.input_ref}
        assert self.services.workflow.store.get_artifact(self.input_ref) == b'engineering input'
        return {**deepcopy(selection), 'materialized_input_path': str(
            self.services.workflow.store.path / 'artifacts' / self.input_ref[9:11] / self.input_ref[9:])}
    def initialize(self, context): self.initializations += 1
    def execute(self, context, tool_name, arguments, operation_key):
        self.executions += 1
        assert tool_name == 'engineering.emit' and arguments == {}
        return {'status': 'completed', 'record_refs': [self.source_ref],
            'changed_record_refs': [], 'result': {'source_ref': self.source_ref}, 'feedback': None}


def _rows(store):
    tables = [r[0] for r in store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [dict(r) for r in store.db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
        for name in tables}


def _files(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob('*') if p.is_file()}


def _controller(path, initial): return FixtureController(str(path), initial, 1)


@pytest.fixture
def closed_case(tmp_path, request):
    store = Store(tmp_path / 'store')
    store.create_problem(raw_sequence='ACGT', molecule='dna')
    tools = ToolRegistry(store)
    input_ref = store.artifact(b'engineering input', 'application/octet-stream')
    public = store.put('source', {'provider': 'engineering.closed_commission', 'accession': None,
        'uri': None, 'artifact_ref': store.artifact(b'engineering output'), 'text_ref': None,
        'request_ref': None, 'version': None, 'retrieved_at': None}, origin='tool')
    scope = store.validate_scope()
    form, value, opaque_ref = FORM, None, None
    if getattr(request, 'param', None) == 'native_defs':
        from gene_annotation_episode.macs2_peak_result_contracts import macs2_peak_fact_sources
        from test_macs2_peak_presentation import _packet
        packet = _packet()  # Explicit existing engineering DTO; no calculator/native producer.
        packet['source_ref'] = public['id']
        opaque_ref = store.artifact(b'opaque engineering provenance')
        for row in packet['peak_window']['rows']:
            row['source']['artifact_ref'] = opaque_ref
        form = obj({'peaks': macs2_peak_fact_sources()['macs2_peak_outcomes']['report_schema']})
        value = [packet]
    bindings = []
    def binding(services):
        instance = EngineeringBinding(services, public['id'], input_ref, form=form, value=value)
        bindings.append(instance)
        return instance
    selection = {'kind': 'episode_child', 'role': 'engineering', 'goal': QUESTION,
        'scope': scope, 'purpose': QUESTION, 'schema_json': json.dumps(form),
        'initial_report_json': '{}', 'assignment': {'input_ref': input_ref}}
    class Choices:
        def __init__(self): self.calls = 0
        async def complete(self, episode_id, role, instructions, context, schema):
            self.calls += 1
            answer = {'selection': selection if self.calls == 1 else {
                'kind': 'tool', 'tool': 'engineering.emit', 'arguments': {}}, 'report_update': {}}
            value = _encode(answer, plain(schema))
            Draft202012Validator(plain(schema)).validate(value)
            return value
        async def release(self, episode_id): pass
    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', 'closed-commission-engineering',
        _controller, lambda *_: 0, episode_binding_factories=[binding],
        episode_record_receipts=True, initial_known_record_refs=[input_ref],
        annotation_child_roles=('engineering',))
    root = flow.build('annotation', 'root', QUESTION, scope)
    record = asyncio.run(root.run_async(flow.context))
    asyncio.run(root.build_result(record))
    archive = json.loads(''.join(iter_json(record.as_record())))
    action = flow.journal.row('runtime_actions', root.source.episode_id, 0)
    original = json.loads(action['action'])
    child = store.db.execute('SELECT * FROM runtime_episodes WHERE episode_id<>?',
        (root.source.episode_id,)).fetchone()
    case = dict(store=store, flow=flow, tools=tools, provider=provider, binding=bindings[0], root=root,
        archive=archive, selection=original, child_id=child['episode_id'], source=public,
        form=form, fact_value=value, opaque_ref=opaque_ref,
        directory=tmp_path / 'run', input_path=store.path / 'artifacts' / input_ref[9:11] / input_ref[9:])
    try:
        yield case
    finally:
        store.close()


def _forbid_replay_work(case, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('closed replay selected new work or a File read')
    async def no_decision(*args, **kwargs): return forbidden()
    monkeypatch.setattr(case['provider'], 'complete', no_decision)
    for name in ('prepare_assignment', 'initialize', 'execute'):
        monkeypatch.setattr(case['binding'], name, forbidden)
    monkeypatch.setattr(case['store'], 'get_artifact', forbidden)
    monkeypatch.setattr(case['store'], 'artifact', forbidden)
    monkeypatch.setattr(case['flow'].receipts, 'receive', forbidden)
    monkeypatch.setattr(case['tools'], 'execute', forbidden)
    monkeypatch.setattr(case['flow'], 'receive_form', forbidden)
    monkeypatch.setattr(case['flow'].episode_bindings, 'received_form_references', forbidden)
    monkeypatch.setattr(case['tools'], '_sequence_worker_async', forbidden)
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel'):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    case['input_path'].unlink()


def test_closed_commission_reuses_actual_archive_form_observation_without_preparation(closed_case, monkeypatch):
    c = closed_case
    assert c['provider'].calls == 2 and c['binding'].preparations == c['binding'].executions == 1
    before, files = _rows(c['store']), _files(c['directory'] / 'archive')
    class NoDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed reconstruction requested another decision')
        async def release(self, episode_id): pass
    fresh_bindings = []
    def fresh_binding(services):
        value = EngineeringBinding(services, c['source']['id'], c['selection']['assignment']['input_ref'],
            form=c['form'], value=c['fact_value'])
        fresh_bindings.append(value)
        return value
    tools = ToolRegistry(c['store'])
    flow = Workflow(c['store'], tools, NoDecisions(), c['directory'], c['flow'].run_id,
        c['flow'].controller_factory, c['flow'].project_credit,
        episode_binding_factories=[fresh_binding], episode_record_receipts=True,
        initial_known_record_refs=list(c['flow'].initial_known_record_refs),
        annotation_child_roles=c['flow'].annotation_child_roles)
    assert fresh_bindings[0].as_record() == c['binding'].as_record()
    replay_root = flow.build('annotation', 'root', QUESTION, c['root'].source.scope)
    assert _rows(c['store']) == before
    replay = dict(c, flow=flow, tools=tools, provider=flow.provider, binding=fresh_bindings[0])
    _forbid_replay_work(replay, monkeypatch)
    unit = flow.selected(replay_root.source, c['selection'], 0)
    assert isinstance(unit, ReturnedActionUnit) and isinstance(unit, ClosedChildUnit)
    assert unit.decision_index == 0 and unit.record.episode_id == c['child_id']
    assert unit.request.message.as_record()['episode_assignment'] != c['selection']['assignment']
    assert unit.result.as_record() == {'form': {'source': c['source']['id']}}
    replayed = asyncio.run(replay_root.run_async(flow.context))
    assert json.loads(''.join(iter_json(replayed.as_record()))) == c['archive']
    assert _rows(c['store']) == before
    assert _files(c['directory'] / 'archive') == files
    assert c['provider'].calls == 2


@pytest.mark.parametrize('closed_case', ['native_defs'], indirect=True)
def test_closed_projection_uses_local_defs_without_live_admission_or_opaque_File_grants(closed_case, monkeypatch):
    c = closed_case
    before = _rows(c['store'])
    _forbid_replay_work(c, monkeypatch)
    unit = c['flow'].selected(c['root'].source, c['selection'], 0)
    assert isinstance(unit, ReturnedActionUnit)
    assert unit.result.as_record() == {'form': {'peaks': c['fact_value']}}
    assert c['opaque_ref'] not in c['flow'].receipts.known(c['root'].source.episode_id)
    assert unit.result.as_record()['form']['peaks'][0]['peak_window']['rows'][0]['source'][
        'artifact_ref'] == c['opaque_ref']
    assert _rows(c['store']) == before


@pytest.mark.parametrize('conflict', ['scope', 'namespace'])
def test_closed_projection_rejects_metadata_conflicts_without_preparation(closed_case, monkeypatch, conflict):
    c = closed_case
    _forbid_replay_work(c, monkeypatch)
    reference = c['source']['id']
    if conflict == 'scope':
        original = c['store'].reference_subset
        def subset(candidates, scope):
            return [value for value in original(candidates, scope) if value != reference]
        monkeypatch.setattr(c['store'], 'reference_subset', subset)
    else:
        original = c['store'].get
        def record(value):
            result = original(value)
            return {**result, 'record_type': 'artifact'} if value == reference else result
        monkeypatch.setattr(c['store'], 'get', record)
    with pytest.raises(WorkflowError, match='closed_commission_reference_projection_conflict'):
        c['flow'].selected(c['root'].source, c['selection'], 0)


@pytest.mark.parametrize('changed', ['scope', 'assignment', 'goal', 'purpose', 'schema', 'initial', 'index',
    'form', 'parent_archive', 'child_archive', 'observation', 'credit', 'references', 'inheritance'])
def test_closed_commission_rejects_changed_historical_evidence_before_preparation(closed_case, monkeypatch, changed):
    c = closed_case
    selection, index = deepcopy(c['selection']), 0
    db, parent = c['store'].db, c['root'].source.episode_id
    if changed in {'scope', 'assignment', 'goal', 'purpose', 'schema', 'initial'}:
        key, value = {'scope': ('scope', {'subject_refs': []}),
            'assignment': ('assignment', {'input_ref': c['source']['artifact_ref']}),
            'goal': ('goal', 'Different engineering question'), 'purpose': ('purpose', 'Changed purpose'),
            'schema': ('schema_json', json.dumps(obj({'other': {'type': 'number'}}))),
            'initial': ('initial_report_json', '{"source":null}')}[changed]
        selection[key] = value
    elif changed == 'index': index = 1
    elif changed == 'form':
        db.execute('UPDATE runtime_report_attempts SET form=? WHERE parent_episode_id=?',
            (_json({'source': c['source']['artifact_ref']}), parent))
    elif changed in {'parent_archive', 'child_archive'}:
        eid = parent if changed == 'parent_archive' else c['child_id']
        descriptor = json.loads(c['flow'].journal.row('runtime_episodes', eid)['archive'])
        path = c['directory'] / 'archive' / descriptor['file']
        path.write_bytes(path.read_bytes() + b' ')
    elif changed == 'observation':
        row = db.execute('SELECT observation FROM runtime_observations WHERE episode_id=?', (parent,)).fetchone()
        value = json.loads(row[0]); value['credit']['credit'] = 1
        db.execute('UPDATE runtime_observations SET observation=? WHERE episode_id=?', (_json(value), parent))
    elif changed == 'credit':
        db.execute('UPDATE runtime_actions SET credit=1 WHERE episode_id=?', (parent,))
    elif changed == 'references':
        row = c['flow'].journal.row('runtime_actions', parent, 0); value = json.loads(row['result'])
        value['record_refs'] = []; value['changed_record_refs'] = []
        db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=?', (_json(value), parent))
    else:
        db.execute('UPDATE runtime_receipt_inheritance SET through_receipt_index=0 WHERE episode_id=?',
            (c['child_id'],))
    _forbid_replay_work(c, monkeypatch)
    with pytest.raises((WorkflowError, ValueError), match='closed_commission_|scope_|child_role_'):
        c['flow'].selected(c['root'].source, selection, index)


@pytest.mark.parametrize('state', ['active_parent', 'active_child', 'incomplete_action', 'execution_binding'])
def test_nonclosed_commission_retains_existing_preparation_path(closed_case, monkeypatch, state):
    c = closed_case
    db, parent = c['store'].db, c['root'].source.episode_id
    if state in {'active_parent', 'active_child'}:
        eid = parent if state == 'active_parent' else c['child_id']
        db.execute("UPDATE runtime_episodes SET state='active',completion=NULL,archive=NULL WHERE episode_id=?", (eid,))
    elif state == 'incomplete_action':
        db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=?', (parent,))
    else:
        c['flow'].execution_binding = {'engineering': 'durable-path-not-selected'}
        assert c['flow']._closed_child_commission(c['root'].source, c['selection'], 0) is None
        return
    assert c['flow']._closed_child_commission(c['root'].source, c['selection'], 0) is None
    def normal_prepare(*args, **kwargs): raise RuntimeError('normal current admission reached')
    monkeypatch.setattr(c['binding'], 'prepare_assignment', normal_prepare)
    with pytest.raises(RuntimeError, match='normal current admission reached'):
        c['flow'].selected(c['root'].source, c['selection'], 0)
