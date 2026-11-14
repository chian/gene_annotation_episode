"""Private A108 binding boundaries; external acquisition is controlled."""
import asyncio
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest
AXIS = 'gene_annotation_episode.episodic_workflow.root.a108'
AXIS_PATH = Path(__file__).parents[1]
HOMES = tuple(sorted((str(path.parent.relative_to(AXIS_PATH)).replace('/', '.') for path in AXIS_PATH.rglob('episode.py') if 'published_evidence_assessment' in path.parts and 'tests' not in path.parts)))

@pytest.fixture(params=HOMES)
def binding(request):
    cls = import_module(f'{AXIS}.{request.param}.episode').LiteratureEpisode
    return cls(SimpleNamespace())

def test_private_role_instruction_and_children(binding):
    role, = binding.roles
    context = SimpleNamespace(role=role)
    assert binding.instructions(context)
    expected = {'literature': ('literature_strategy',), 'literature_strategy': ('literature_search',), 'literature_search': ('literature_page',), 'literature_page': ('literature_table', 'literature_ordered', 'literature_targeted')}
    assert binding.child_roles(role) == expected.get(role, ())
    assert binding.permitted_common_actions(context) == ('tool', 'reason', 'child', 'redeliver_report')

def test_private_assignment_declares_contextual_sheet_requests(binding):
    role, = binding.roles
    schema = binding.assignment_schema(role)
    assert schema['type'] == 'object'
    assert 'literature_task' in schema['properties']
    assert not any(('a105' in key for key in schema['properties']))
    assert any(('a108' in key for key in schema['properties']))

def test_invalid_executed_tool_keeps_original_operation_identity(binding):
    from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError, identity

    def reject(*args):
        raise ContractError('controlled_unavailable_source')
    binding._tool_arguments = reject
    context = SimpleNamespace(role=binding.roles[0])
    outcome = asyncio.run(binding.execute(context, 'source.read', {'source_ref': 'missing'}, 'original-key'))
    assert outcome['status'] == 'invalid'
    assert outcome['operation_ref'] == identity('operation', {'key': 'original-key', 'name': 'source.read', 'arguments': {'source_ref': 'missing'}})
    assert outcome['changed_record_refs'] == []
    assert outcome['result'] is None
    assert outcome['feedback']['code'] == 'controlled_unavailable_source'

def test_interpretation_uses_context_grading_repository_and_original_key(binding, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a108.library import literature_required_grading
    repository = SimpleNamespace(provider='literature.a108.context_grading')
    binding._required_grading_repository = lambda context: repository
    selection = {'commit': {'actual': 'source claim'}}
    context = SimpleNamespace(role=binding.roles[0])
    seen = []

    def execute(actual_context, actual_selection, key, actual_repository, **kwargs):
        seen.append((actual_context, actual_selection, key, actual_repository))
        assert callable(kwargs['authorize_source_access'])
        return {'status': 'partial', 'record_refs': ['saved-sheet', 'typed-finding']}
    monkeypatch.setattr(literature_required_grading, 'execute', execute)
    result = binding.execute_reasoning(context, selection, 'original-action')
    assert result == {'status': 'partial', 'record_refs': ['saved-sheet', 'typed-finding']}
    assert seen == [(context, selection, 'original-action', repository)]

def test_wrong_grader_provider_cannot_substitute_for_context_grading(binding):
    from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
    binding._required_grading_repository = lambda context: SimpleNamespace(provider='foreign-grader')
    with pytest.raises(ContractError, match='a108_context_grading_required'):
        binding.execute_reasoning(SimpleNamespace(role=binding.roles[0]), {'commit': {}}, 'original')
