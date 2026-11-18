"""Actual source-task/service callbacks, with explicit instruction-only ports.

The fixed binding is a controlled text port. There is no Store, scientific
projection, provider/native process or executed episode in these cases.
"""
import importlib
from types import SimpleNamespace
from unittest.mock import patch
import pytest

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a103'
TOP = 'published_evidence_assessment'
STRATEGY = TOP + '/evidence_search_strategy_improvement'
SEARCH = STRATEGY + '/source_relevance_assessment'
PAGE = SEARCH + '/source_evidence_examination'
HOMES = tuple(prefix + home for prefix in ('', 'gene_context_evidence/') for home in (
    TOP, STRATEGY, SEARCH, PAGE, PAGE + '/table_evidence_extraction',
    PAGE + '/source_coverage_improvement', PAGE + '/passage_evidence_extraction'))
def own(name): return importlib.import_module(PREFIX + '.' + name)
def actual_type(home):
    binding = own(home.replace('/', '.') + '.episode').LiteratureEpisode(None)
    return getattr(binding, 'decision_source_type', own('runtime').DecisionSource)
class OriginalInstructionFailure(Exception): pass
class ExplicitNoneSource(own('runtime').DecisionSource): instruction_composer = None

def source_for(cls):
    source = object.__new__(cls); calls = []
    binding = SimpleNamespace(replaces_default_instructions=True,
        instructions=lambda context: 'Original fixed source instruction port.')
    def specialist(actual):
        assert actual is source; calls.append('original-specialist'); return binding
    source.path = (('literature', 'original-commission'),)
    source.workflow = SimpleNamespace(is_job_source=lambda source: False, specialist=specialist,
        binding_context=lambda source: object(), permits_common_action=lambda source, action: action in {'reason', 'wait'},
        knowledge=SimpleNamespace(instructions=' Original knowledge.'),
        launch_instructions=SimpleNamespace(instructions=' Original launch instructions.'),
        native_event_information=object(), decision_protocol=None)
    source.workflow.services = own('episode_services').WorkflowServices(source.workflow)
    return source, calls

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
@pytest.mark.parametrize('boundary', ('custom_return', 'custom_exception', 'default_composition'))
def test_original_source_instruction_service(home, boundary):
    source, lookups = source_for(actual_type(home))
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    original = own('runtime').DecisionSource.instructions
    if boundary == 'default_composition':
        expected = own('runtime_prompt').instructions(source, context)
        assert lookups == ['original-specialist']; lookups.clear()
        assert source.instructions(context) == expected
        assert lookups == ['original-specialist']  # no new selection lookup
        return
    calls = []; marker = object(); failure = OriginalInstructionFailure('same original callback failure')
    def supplied(actual, passed):
        calls.append((actual is source, passed is context))
        if boundary == 'custom_exception': raise failure
        return marker
    source.workflow.services = SimpleNamespace(instructions=supplied)
    for callback in (lambda: original(source, context), lambda: source.instructions(context)):
        calls.clear()
        if boundary == 'custom_return': assert callback() is marker
        else:
            with pytest.raises(OriginalInstructionFailure) as caught: callback()
            assert caught.value is failure
        assert calls == [(True, True)] and lookups == []

@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_connected_source_private_composer_and_central_next(home):
    cls = actual_type(home); source, lookups = source_for(cls)
    private = own(home.replace('/', '.') + '.task_instructions').instructions
    assert getattr(cls, 'instruction_composer') is private
    assert 'next' in cls.__dict__
    context = {'tool_knowledge': {}, 'launch_instruction_library': {}}
    expected = own('runtime_prompt').instructions(source, context); lookups.clear()
    selected = []
    def composer(actual, supplied):
        selected.append((actual is source, supplied is context))
        return private(actual, supplied)
    with patch.object(cls, 'instruction_composer', staticmethod(composer)):
        assert source.instructions(context) == expected
    assert selected == [(True, True)] and lookups == ['original-specialist']

@pytest.mark.parametrize('explicit_none', (False, True), ids=('absent-composer', 'explicit-none-composer'))
def test_source_nonparticipant_original_service_fallback(explicit_none):
    source, lookups = source_for(ExplicitNoneSource if explicit_none else own('runtime').DecisionSource)
    assert getattr(type(source), 'instruction_composer', None) is None
    context = {'tool_knowledge': {}}
    expected = own('runtime_prompt').instructions(source, context); lookups.clear()
    assert source.instructions(context) == expected and lookups == ['original-specialist']

