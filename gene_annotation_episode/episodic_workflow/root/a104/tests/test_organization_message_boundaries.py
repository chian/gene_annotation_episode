"""Actual named envelopes and original build prelude, before initialization.

Real configured binding constructors, registry selection, task constructors,
typed requests, instruction materialization and Store receipt inheritance run.
The deliberate constructor stop prevents credit, controller, model or native
work. Assignment admission is covered separately by the original exchange
tests; opaque extra message fields below are assembler operands, not admitted
scientific assignments. The scientific-head Monitor edge is a direct interface
and does not widen the head's selected-child policy.
"""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
from .test_source_request_assembly import original_methods

BASE = 'gene_annotation_episode.episodic_workflow.root.a104.'
EDGES = json.loads((Path(__file__).parent / 'fixtures/organization_boundaries/remaining_envelopes.json').read_text())
PHASE = os.environ.get('A104_ORGANIZATION_PHASE', 'candidate')
assert PHASE in {'baseline', 'candidate'}


def own(name):
    return importlib.import_module(BASE + name.replace('/', '.'))


class ConstructionObserved(Exception):
    pass


@pytest.fixture(scope='module')
def configured_graph(tmp_path_factory):
    directory = tmp_path_factory.mktemp('a104-envelope-graph')
    adapter = SimpleNamespace(axis='a104', module=own)
    generator = ScientificHeadBoundaryChecks.scientific.__wrapped__(adapter, directory)
    frame = next(generator)
    homes = {edge[key] for edge in EDGES for key in ('parent', 'child')}
    bindings = {'scientific_process': frame.binding}
    for home in sorted(homes - set(bindings)):
        module = own(home + '/episode')
        if home.endswith('execution_progress_assessment'):
            binding = module.MonitorEpisode(frame.services)
        else:
            binding = module.HPCEpisode(frame.services, store=frame.store,
                run_id=frame.context.run_id, directory=directory, resources=resources(), commissions={})
        assert binding.binding_path == home
        bindings[home] = binding
    registry = own('episode_bindings').EpisodeBindingRegistry(tuple(bindings.values()))
    launch_instructions = own('launch_instructions').LaunchInstructions.freeze(directory / 'launch-instructions')
    try:
        yield SimpleNamespace(frame=frame, bindings=bindings, registry=registry,
            instructions=launch_instructions, directory=directory)
    finally:
        with pytest.raises(StopIteration):
            next(generator)


def parent_path(graph, home):
    binding = graph.bindings[home]
    parent = binding.commissioning_parent
    prefix = (('annotation', 'root'),) if parent in {'annotation', 'legacy_annotation'} else parent_path(graph, parent)
    assert len(binding.roles) == 1
    return (*prefix, (binding.roles[0], home.replace('/', '_')))


@pytest.mark.parametrize('edge', EDGES, ids=[row['parent'] + '->' + row['role'] for row in EDGES])
@pytest.mark.parametrize('variant', ('full_message', 'declaration_without_contract'))
def test_named_parent_envelope_matches_original_build(configured_graph, original_methods, monkeypatch, edge, variant):
    graph = configured_graph
    runtime, plain = own('runtime'), own('communication').plain
    frame, parent = graph.frame, graph.bindings[edge['parent']]
    child = graph.bindings[edge['child']]
    path = parent_path(graph, edge['parent'])
    assert graph.registry.for_path(path) is parent
    assert graph.registry.for_child(path, edge['role']) is child
    selector = getattr(parent, 'child_request_assembler', None)
    assembler = selector(edge['role']) if selector is not None else None
    if PHASE == 'candidate':
        owner = own(edge['request_owner'])
        assert assembler is owner.assemble_request
    else:
        assert assembler is None, 'baseline unexpectedly contains the proposed envelope'
    if edge['parent'] == 'scientific_process':
        assert parent.allowed_children(frame.context, {}) == ('scientific_process', 'hpc')

    role = edge['role']
    workflow = object.__new__(runtime.Workflow)
    workflow.run_id = frame.context.run_id
    workflow.context = SimpleNamespace(require_run_id=lambda: workflow.run_id)
    workflow.grains = {name: SimpleNamespace(name=name) for name in {'annotation', *graph.registry.roles}}
    workflow.episode_bindings = graph.registry
    workflow.store = frame.store
    workflow.inprocess_completion_order = own('inprocess_replay').VERSION
    workflow.scientific_process_binding = None
    workflow.launch_instructions = graph.instructions
    workflow.receipts = own('episode_receipts').EpisodeReceipts(frame.store, workflow.run_id)
    parent_identity = runtime.Episode.identity(workflow.context, workflow.grains[path[-1][0]], path[-1][1], parent_path=path[:-1])
    workflow.receipts.bind(parent_identity.episode_id)
    workflow.receipts.receive(parent_identity.episode_id, [frame.target], kind='initial')
    goal = runtime.EpisodeGoal.root(objective='Preserve the original message', result_contract={})
    schema = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'const': 'unresolved'}},
        'required': ['qualification'], 'additionalProperties': False}
    contract = runtime.TypedReportContract('Retain the original qualification', schema, lambda *_: True)
    operands = dict(parent=goal, parent_path=path, contract=contract,
        initial={'qualification': 'unresolved'}, episode_assignment={'original_envelope_operand': ['same', None]},
        job_assignment={'original_job_operand': ['same', 3]}, scientific_process={'original_process_operand': 'opaque'})
    if variant == 'declaration_without_contract':
        operands.update(contract=None, report_contract_declaration={'submitted_schema_json': '{}'})
    source_type = child.decision_source_type
    constructor = source_type.__init__
    observations = []
    for callback, request_assembler in ((original_methods.build, None), (runtime.Workflow.build, None),
            (runtime.Workflow.build, assembler)):
        captured = {}
        materialized = []
        original_materialize = graph.instructions.materialize
        def materialize(value):
            materialized.append(deepcopy(value))
            return original_materialize(value)
        def stop(self, *args, **kwargs):
            constructor(self, *args, **kwargs)
            captured.update(request=plain(self.request.as_record()), path=plain(self.path),
                identity=self.episode_id, known=sorted(workflow.receipts.known(self.episode_id)),
                source_type=type(self), goal_type=type(self.request.goal), request_type=type(self.request),
                message_type=type(self.request.message))
            raise ConstructionObserved()
        with monkeypatch.context() as patch:
            patch.setattr(source_type, '__init__', stop)
            patch.setattr(graph.instructions, 'materialize', materialize)
            try:
                with frame.store.transaction():
                    keyword = {} if request_assembler is None else {'request_assembler': request_assembler}
                    callback(workflow, role, 'controlled-envelope', 'Preserve the original message',
                        plain(frame.context.scope), **operands, **keyword)
            except (ConstructionObserved, AttributeError) as error:
                captured['exception'] = (type(error), str(error))
            else:
                raise AssertionError('constructor stop did not prevent episode execution')
        captured['materialized'] = materialized
        observations.append(captured)
    assert observations[0] == observations[1] == observations[2]
    result = observations[2]
    if variant == 'full_message':
        assert result['exception'][0] is ConstructionObserved
        assert result['source_type'] is source_type
        assert result['goal_type'] is runtime.EpisodeGoal and result['request_type'] is runtime.EpisodeRequest
        assert result['message_type'] is runtime.Record and frame.target in result['known']
        assert result['materialized'] == [None]
        message = result['request']['message']
        for key in ('initial_report', 'episode_assignment', 'job_assignment', 'scientific_process'):
            assert message[key] == operands['initial' if key == 'initial_report' else key]
        assert message['inprocess_completion_order'] == {'version': workflow.inprocess_completion_order}
    else:
        assert result == {'exception': (AttributeError, "'NoneType' object has no attribute 'schema'"), 'materialized': []}
