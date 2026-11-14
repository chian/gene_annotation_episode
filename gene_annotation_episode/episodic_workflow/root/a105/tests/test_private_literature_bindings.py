"""Private literature binding boundaries; external science uses explicit fixtures."""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import inspect

import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
ROOT = Path(__file__).parents[1]
HOMES = sorted(str(p.parent.relative_to(ROOT)).replace('/', '.')
    for p in ROOT.rglob('episode.py')
    if 'published_evidence_assessment' in p.parts and 'tests' not in p.parts)

@pytest.fixture(params=HOMES)
def binding(request):
    cls = import_module(f'{AXIS}.{request.param}.episode').LiteratureEpisode
    return cls(SimpleNamespace(scientific_credit=lambda context, selection:
        {'credit': 3.25, 'selected': selection}))


def test_private_registration_and_child_catalog(binding):
    role, = binding.roles
    assert binding.binding_path.replace('/', '.') in HOMES
    children = {'literature': ('literature_strategy',),
        'literature_strategy': ('literature_search',), 'literature_search': ('literature_page',),
        'literature_page': ('literature_table', 'literature_ordered', 'literature_targeted'),
        'literature_table': (), 'literature_ordered': (), 'literature_targeted': ()}
    context = SimpleNamespace(role=role)
    assert binding.child_roles(role, context=context) == children[role]
    assert binding.allowed_children(context, ()) == children[role]


def test_assignment_contract_preserves_role_and_requested_task(binding):
    role, = binding.roles
    schema = binding.assignment_schema(role)
    version = {'literature': 'literature_assignment_v1',
        'literature_strategy': 'strategy_assignment_v1', 'literature_search': 'search_assignment_v1',
        'literature_page': 'page_assignment_v1'}.get(role, 'reading_assignment_v1')
    assert schema['properties']['version']['const'] == version
    assert 'literature_task' in schema['properties']
    assert 'proposed_annotation_ref' in schema['properties']


def test_original_credit_and_no_wait(binding):
    context = SimpleNamespace(role=binding.roles[0])
    assert binding.credit_kind(context.role) == 'scientific'
    assert binding.credit_view(context, {'original': True}) == {'credit': 3.25, 'selected': {'original': True}}
    assert binding.supports_wait is False
    assert binding.yield_controller(context, 3.25, 2) is None


def test_instructions_keep_scientific_qualifications(binding):
    text = binding.instructions(SimpleNamespace(role=binding.roles[0]))
    assert 'experimental conditions' in text
    assert 'Negative findings and qualifications' in text
    assert 'reading earn no scientific credit' in text


@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_reasoning_keeps_original_grading_outcome(binding, monkeypatch, status):
    repository = object()
    context = SimpleNamespace(role=binding.roles[0])
    selection = {'kind': 'reason', 'commit': {'original': True}}
    result = {'status': status, 'record_refs': ['original'], 'changed_record_refs': []}
    seen = []
    def execute(actual_context, actual_selection, operation_key, actual_repository,
                *, authorize_source_access):
        seen.append((actual_context, actual_selection, operation_key, actual_repository))
        authorize_source_access('source-original', 'original')
        return result
    binding._required_grading_repository = lambda context=None: repository
    binding._tool_arguments = lambda *args: seen.append(args)
    module = inspect.getmodule(binding.execute_reasoning)
    monkeypatch.setattr(module, '_required_grading_logic', lambda repo: SimpleNamespace(execute=execute))
    assert binding.execute_reasoning(context, selection, 'original-action') is result
    assert seen[0] == (context, selection, 'original-action', repository)
    assert seen[1] == (context, 'source.read', {'source_ref': 'source-original', 'representation': 'original'})


@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_task_records_original_result_before_credit_and_replays(binding, status):
    import asyncio
    from contextlib import nullcontext
    import json
    from gene_annotation_episode.episodic_workflow.root.a105.runtime import DecisionSource
    events, rows = [], {}
    class Journal:
        def row(self, table, episode, index): return rows.get(index)
        def save(self, table, value): rows[value['decision_index']] = dict(value)
        def measure(self, *args): return nullcontext()
    def interpret(*args):
        events.append('interpret_and_grade')
        return {'status': status, 'record_refs': ['original-finding'], 'changed_record_refs': []}
    binding.execute_reasoning = interpret
    async def score(source, index, result):
        events.append('automatic_sheet_updates')
        return result
    def credit(source):
        events.append('credit')
        return {'credit': 0 if status in {'invalid', 'failed', 'unavailable'} else 7}
    workflow = SimpleNamespace(journal=Journal(), run_id='private-boundary',
        execution_binding=None, wait_inputs_version=None, completed_action_inputs_version=None,
        specialist=lambda source: binding, binding_context=lambda source: SimpleNamespace(role=binding.roles[0]),
        receive_native_outcome=lambda *args: None, receive_outcome=lambda *args: events.append('receive'),
        automatic_score_updates=score, source_credit_view=credit,
        controller_value=lambda source, index, value: value)
    task_class = getattr(binding, 'decision_source_type', DecisionSource)
    source = object.__new__(task_class)
    source.workflow, source.episode_id, source.path, source.scope = workflow, 'source', ((binding.roles[0], 'source'),), {}
    source.checkpoint = lambda: None
    selection = {'kind': 'reason', 'commit': {}}
    expected = 0 if status in {'invalid', 'failed', 'unavailable'} else 7
    assert asyncio.run(source.execute(selection, 0)) == expected
    assert events.index('interpret_and_grade') < events.index('automatic_sheet_updates') < events.index('credit')
    prior_events = list(events)
    assert asyncio.run(source.execute(selection, 0)) == expected
    assert events == prior_events
    assert json.loads(rows[0]['action']) == selection
    assert json.loads(rows[0]['result'])['status'] == status
    assert json.loads(rows[0]['result'])['record_refs'] == ['original-finding']
