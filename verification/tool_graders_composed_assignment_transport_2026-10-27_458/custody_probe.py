"""Classify pre-admission custody with actual Workflow construction/writers.

Scripted provider choices are not scientific measurements. No HTTP/native call
is allowed. The old direct call executes the exact pinned old call method.
"""
import ast
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import runtime
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_bvbrc_appservice_custody import request
from test_composed_episode_assignment_transport import obj, Provider, historical, OLD_RUNTIME_SHA
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_public_search import Client
from test_runtime import FixtureController


class Classified(Exception):
    pass


class CompactProvider(Provider):
    async def complete(self, episode_id, role, instructions, context, schema):
        assert self.responses
        response = self.responses[0]
        errors = list(Draft202012Validator(schema).iter_errors(response))
        if errors:
            selected = response.get('response', response)
            host = schema.get('properties', {}).get('response', {}).get('anyOf', [None, schema])[1]
            branch = next(node for node in host['properties']['selection']['anyOf']
                if node.get('properties', {}).get('role', {}).get('enum') == [selected['selection']['role']])
            leaves = []
            def walk(error):
                if error.context:
                    for child_error in error.context:
                        walk(child_error)
                else:
                    leaves.append({'instance_path': list(error.absolute_path),
                        'schema_path': list(error.absolute_schema_path), 'message': error.message})
            for error in Draft202012Validator(branch).iter_errors(selected['selection']):
                walk(error)
            raise AssertionError(json.dumps(leaves))
        return await super().complete(episode_id, role, instructions, context, schema)


def old_call(historical):
    path = Path(runtime.__file__).resolve().parents[1] / (
        'verification/tool_graders_composed_assignment_transport_2026-10-27_458/baseline/runtime.py')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == OLD_RUNTIME_SHA
    tree = ast.parse(raw)
    klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DecisionSource')
    method = next(node for node in klass.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'call')
    namespace = {**vars(runtime), '_action_generation_schema': historical.generate}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['call']


@pytest.mark.parametrize('transport', ['old_direct', 'current_direct', 'old_exchange'])
def test_actual_pre_admission_custody_shape(tmp_path, monkeypatch, historical, transport):
    def forbidden(*args, **kwargs):
        raise AssertionError('Custody probe cannot use live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    with Store(tmp_path / 'state') as store:
        provider = CompactProvider()
        factory = ExecutionServiceFactory({'selected-api': CONFIG}, {}, 2, 3, .5)
        workflow = runtime.Workflow(store, ToolRegistry(store, clients=Client()), provider,
            tmp_path / 'run', 'custody458',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1),
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'results'), episode_record_receipts=True,
            initial_known_record_refs=[], decision_protocol=None)
        scope = {'subject_refs': store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']}
        api = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': request(), 'endpoint': 'usable_handoff', 'constraints': {}}
        # This typed preparation request has explicitly empty parameters. It
        # makes no claim of being ready for native submission; no prepare or
        # submission action is executed. Keeping that open object empty allows
        # the pre-existing expanded provider representation to be valid too.
        api['request']['parameters'] = {}
        api['request']['start_parameters'] = {name: '' for name in (
            'parent_id', 'workspace', 'base_url', 'container_id', 'user_metadata',
            'reservation', 'data_container_id', 'user_override', 'constraint')}
        api['request']['start_parameters'].update(disable_preflight=0, preflight_data={})
        launch = launch_assignment({'selected-api': api})
        root = workflow.build('annotation', 'root', 'Inspect exact original custody', scope)
        response = child('launch', launch, deepcopy(scope), form('execution_handoff_refs'))
        response['selection']['assignment'] = json.dumps(launch)
        response['selection']['scope'].update(read_selection_refs=None, segments=None)
        provider.responses.append(response)
        returned, index, context, schema = asyncio.run(root.source.call(
            {'visible_record_refs': [], 'scope': scope}, workflow.action_schema(root.source)))
        unit = root.source.apply_response(returned, index, context, schema)
        assert unit is not None, root.source.feedback
        source = unit.child.source
        schema = workflow.action_schema(source)
        raw = child('launch_api', {**api, 'launch_instructions': None}, deepcopy(scope), form('execution_handoff_refs'))
        raw['selection']['scope'].update(read_selection_refs=None, segments=None)
        if transport == 'current_direct':
            raw['selection']['assignment'] = json.dumps(raw['selection']['assignment'])
            provider.responses.append(raw)
            returned, index, context, schema = asyncio.run(source.call(
                {'visible_record_refs': [], 'scope': scope}, schema))
        elif transport == 'old_direct':
            provider.responses.append(raw)
            returned, index, context, schema = asyncio.run(old_call(historical)(source,
                {'visible_record_refs': [], 'scope': scope}, schema))
        else:
            from gene_annotation_episode.decision_exchanges import DecisionExchanges
            workflow.decision_protocol = 'decision_exchange_v1'
            workflow.decision_exchanges = DecisionExchanges(workflow.journal)
            provider.responses.append({'response': {'response_type': 'select_action', **raw}})
            with monkeypatch.context() as patch:
                patch.setattr(runtime, '_action_generation_schema', historical.generate)
                returned, index, context, schema = asyncio.run(source.call(
                    {'visible_record_refs': [], 'scope': scope}, schema))
        saved = dict(workflow.journal.row('runtime_model_calls', source.episode_id, index))
        sent = json.loads(saved['request'])
        current = runtime._decode_action_response(returned, schema)
        prior = historical.decode(returned, schema)
        Draft202012Validator(schema).validate(current)
        assert workflow.journal.row('runtime_actions', source.episode_id, index) is None
        source.calls = 0
        replayed, same_index, same_context, same_schema = asyncio.run(source.call({}, obj({})))
        if transport == 'old_direct':
            assert 'assignment_transport' not in sent
            assert current['selection'] != prior['selection']
            assert source.apply_response(replayed, same_index, same_context, same_schema) is None
            assert source.feedback['detail'] == 'original_assignment_transport_unavailable'
        captured = []
        authenticate = AppServiceCustody.authenticate
        def inspect(self, ctx, *, allow_unsaved=False):
            value = authenticate(self, ctx, allow_unsaved=allow_unsaved)
            if ctx.role == 'launch_api' and ctx.path[-1][1] == 'child_0':
                captured.append(runtime._plain(ctx.assignment))
                raise Classified()
            return value
        monkeypatch.setattr(AppServiceCustody, 'authenticate', inspect)
        selection = (prior if transport == 'old_exchange' else current)['selection']
        # Construct the unsaved child through actual Workflow.selected/build.
        # This intentionally inspects custody in isolation after the ordinary
        # old-direct admission path above has already refused that selection.
        with pytest.raises(Classified):
            workflow.selected(source, selection, index)
        assert len(captured) == 1
        assert dict(workflow.journal.row('runtime_model_calls', source.episode_id, index)) == saved
        assert workflow.journal.row('runtime_actions', source.episode_id, index) is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        (tmp_path / 'classification.json').write_text(json.dumps({
            'transport': transport, 'current_marker': sent.get('assignment_transport'),
            'old_current_selection_equal': current['selection'] == prior['selection'],
            'custody_authenticated': True, 'runtime_rejected_unproven': transport == 'old_direct',
            'launch_instructions_supplied': 'launch_instructions' in captured[0],
            'raw_call_unchanged': True, 'action_count_for_pending_call': 0, 'observations': 0}, indent=2))
