"""Actual private parent selectors and Workflow.build envelope boundary.

Real own-axis registry lookup, EpisodeGoal/EpisodeRef/EpisodeRequest and typed
contract serialization are used. Owner constructors are bypassed: configuration,
acquisition and science are outside this request-assembly check. Only receipt
binding and launch-instruction materialization are controlled, with ordered call
logs. A sentinel stops before the child decision-source constructor executes.
Original source is a permanent, nonimportable own-axis fixture.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace
import textwrap
import pytest
AXIS = 'a110'
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.' + AXIS

def module(name):
    return importlib.import_module(PACKAGE + '.' + name)

def cases():
    result = [('scientific_process', 'scientific_process/hpc_work_planning', 'hpc'), ('scientific_process', 'scientific_process/published_evidence_assessment', 'literature')]
    for base in ('published_evidence_assessment', 'scientific_process/published_evidence_assessment'):
        strategy = base + '/evidence_search_strategy_improvement'
        relevance = strategy + '/source_relevance_assessment'
        examination = relevance + '/source_evidence_examination'
        result.extend([(base, strategy, 'literature_strategy'), (strategy, relevance, 'literature_search'), (relevance, examination, 'literature_page')])
        result.extend(((examination, examination + '/' + name, role) for name, role in (('table_evidence_extraction', 'literature_table'), ('source_coverage_improvement', 'literature_ordered'), ('passage_evidence_extraction', 'literature_targeted'))))
    assert len(result) == 14
    return result

class EnvelopeCaptured(Exception):
    pass

def original_envelope(runtime):
    path = Path(__file__).parent / 'fixtures/organization_original/workflow_build.py.source'
    tree = ast.parse(textwrap.dedent(path.read_text()))
    function, = tree.body
    assert isinstance(function, ast.FunctionDef) and function.name == 'build'
    index, = [i for i, node in enumerate(function.body) if isinstance(node, ast.Assign) and [ast.unparse(target) for target in node.targets] == ['request'] and (ast.unparse(node.value) == 'EpisodeRequest(goal, Record(message), contract)')]
    function.body = function.body[:index + 1] + [ast.Return(ast.Tuple(elts=[ast.Name(id=name, ctx=ast.Load()) for name in ('path', 'goal', 'message', 'identity', 'request')], ctx=ast.Load()))]
    function.name = 'original_envelope'
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), namespace)
    return namespace['original_envelope']

def setup(parent_home, child_home, role, *, fail_port=None):
    runtime = module('runtime')
    catalog = {**module('private_execution_hpc_reconstruction').CATALOG, **module('private_scientific_literature_reconstruction').CATALOG}
    bindings = {}
    for home, declaration in catalog.items():
        owner = getattr(module(home.replace('/', '.') + '.episode'), declaration['owner_class'])
        bindings[home] = object.__new__(owner)
    registry = object.__new__(module('episode_bindings').EpisodeBindingRegistry)
    registry._bindings = list(bindings.values())
    registry._by_path = dict(bindings)
    registry._by_role = {}
    for binding in bindings.values():
        for registered_role in binding.roles:
            registry._by_role.setdefault(registered_role, []).append(binding)
    ancestors, current = ([], parent_home)
    while current != 'legacy_annotation':
        ancestors.append((catalog[current]['roles'][0], current.rsplit('/', 1)[-1]))
        current = catalog[current]['parent']
    parent_path = (('annotation', 'root'), *reversed(ancestors))
    assert registry.for_path(parent_path) is bindings[parent_home]
    events, selectors, assemblies, captures = ([], [], [], [])
    parent_binding = bindings[parent_home]
    original_selector = getattr(parent_binding, 'child_request_assembler', None)

    def select(selected_role):
        selectors.append(selected_role)
        chosen = None if original_selector is None else original_selector(selected_role)
        if chosen is None:
            return None

        def assemble(*args, **kwargs):
            assemblies.append(chosen.__module__)
            return chosen(*args, **kwargs)
        return assemble
    parent_binding.child_request_assembler = select

    def materialize(value):
        events.append(('materialize', deepcopy(value)))
        if fail_port == 'materialize':
            raise ValueError('controlled_original_instruction_failure')

    def bind(child_id, parent_id):
        events.append(('bind', child_id, parent_id))
        if fail_port == 'bind':
            raise ValueError('controlled_original_receipt_failure')
        return {'child': child_id, 'parent': parent_id, 'version': 'controlled_inheritance_v1'}

    def capture(workflow, path, request, scope):
        captures.append({'path': path, 'request': runtime._plain(request.as_record()), 'scope': scope})
        raise EnvelopeCaptured()
    bindings[child_home].decision_source_type = capture
    workflow = SimpleNamespace(episode_bindings=registry, context=SimpleNamespace(require_run_id=lambda: 'controlled-parent-envelope'), grains={name: SimpleNamespace(name=name) for name in ('annotation', *registry.roles)}, inprocess_completion_order='controlled_original_order', run_id='controlled-parent-envelope', scientific_process_binding=bindings['scientific_process'], launch_instructions=SimpleNamespace(materialize=materialize), receipts=SimpleNamespace(bind=bind))
    schema = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'enum': ['unresolved']}}, 'required': ['qualification'], 'additionalProperties': False}
    contract = runtime.TypedReportContract('Preserve the requested qualification', schema, lambda *_: False)
    kwargs = {'parent': runtime.EpisodeGoal.root(objective='Original commissioned question', result_contract={'role': 'scientific_process'}), 'parent_path': parent_path, 'contract': contract, 'initial': {'qualification': 'unresolved'}, 'episode_assignment': {'version': 'controlled_supplied_assignment', 'launch_instructions': {'original': 'entry'}, 'retained_reference': 'source:original'}}
    args = (role, 'child_fixed', 'Inspect the exact supplied question', {'subject_refs': ['subject:original']})
    return SimpleNamespace(runtime=runtime, workflow=workflow, args=args, kwargs=kwargs, events=events, selectors=selectors, assemblies=assemblies, captures=captures)

@pytest.mark.parametrize('parent_home,child_home,role', cases())
def test_actual_parent_assembler_preserves_original_request_once(parent_home, child_home, role):
    old = setup(parent_home, child_home, role)
    expected = original_envelope(old.runtime)(old.workflow, *old.args, **old.kwargs)
    live = setup(parent_home, child_home, role)
    with pytest.raises(EnvelopeCaptured):
        live.runtime.Workflow.build(live.workflow, *live.args, **live.kwargs)
    assert live.captures == [{'path': expected[0], 'request': old.runtime._plain(expected[4].as_record()), 'scope': old.args[3]}]
    assert live.events == old.events
    assert [event[0] for event in live.events] == ['materialize', 'bind']
    assert live.selectors == [role]
    assert live.assemblies == [PACKAGE + '.' + parent_home.replace('/', '.') + '.to_child_' + child_home.rsplit('/', 1)[-1]]
    assert live.captures[0]['request']['goal']['parent_goal_id'] == live.kwargs['parent'].goal_id

@pytest.mark.parametrize('role,child_home', [('hpc', 'scientific_process/hpc_work_planning'), ('literature', 'scientific_process/published_evidence_assessment')])
@pytest.mark.parametrize('failure', ['materialize', 'bind', 'typed_declaration', 'invalid_parent'])
def test_original_failure_type_message_and_side_effect_order(role, child_home, failure):
    observed = []
    for use_original in (True, False):
        value = setup('scientific_process', child_home, role, fail_port=failure)
        if failure == 'typed_declaration':
            value.kwargs['report_contract_declaration'] = {}
        if failure == 'invalid_parent':
            value.kwargs['parent'] = object()
        try:
            if use_original:
                original_envelope(value.runtime)(value.workflow, *value.args, **value.kwargs)
            else:
                value.runtime.Workflow.build(value.workflow, *value.args, **value.kwargs)
        except Exception as error:
            assert not isinstance(error, EnvelopeCaptured)
            observed.append((type(error), str(error), getattr(error, 'code', None), value.events))
        else:
            pytest.fail('original_invalid_request_was_accepted')
    assert observed[0] == observed[1]

def test_parent_without_declared_assembler_keeps_original_envelope():
    home = 'execution_job_submission/local_job_execution'
    old = setup('execution_job_submission', home, 'launch_local')
    expected = original_envelope(old.runtime)(old.workflow, *old.args, **old.kwargs)
    live = setup('execution_job_submission', home, 'launch_local')
    live.workflow.episode_bindings.for_path(live.kwargs['parent_path']).child_request_assembler = lambda role: None
    with pytest.raises(EnvelopeCaptured):
        live.runtime.Workflow.build(live.workflow, *live.args, **live.kwargs)
    assert live.captures[0]['request'] == old.runtime._plain(expected[4].as_record())
    assert live.events == old.events and live.assemblies == []
