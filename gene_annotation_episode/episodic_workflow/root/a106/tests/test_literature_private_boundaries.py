"""All predefined literature bindings: original operands, custody, failure and credit."""
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
ROOT = Path(__file__).resolve().parents[1]
HOMES = sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.rglob('episode.py')
    if 'published_evidence_assessment' in p.parts and 'tests' not in p.parts and 'class LiteratureEpisode(' in p.read_text())


@pytest.fixture(params=HOMES)
def binding(request):
    module = importlib.import_module(PACKAGE + '.' + request.param.replace('/', '.') + '.episode')
    return module.LiteratureEpisode(SimpleNamespace())


def test_original_assignment_and_goal_remain_private_to_declared_role(binding):
    role, = binding.roles
    context = SimpleNamespace(role=role, scope={}, assignment={})
    schema = binding.assignment_schema(role)
    assert schema['additionalProperties'] is False
    assert 'version' in schema['properties']
    assert binding.instructions(context)
    assert isinstance(binding.child_roles(role), tuple)
    assert binding.supports_wait is True


def test_invalid_executed_operation_retains_original_identity(binding):
    domain = importlib.import_module(PACKAGE + '.domain')
    def invalid(*args):
        raise domain.ContractError('original_invalid_operand')
    binding._tool_arguments = invalid
    context = SimpleNamespace(role=binding.roles[0], scope={}, received_record_refs=())
    arguments = {'source_ref': 'original_source'}
    result = asyncio.run(binding.execute(context, 'source.read', arguments, 'original-key'))
    assert result['status'] == 'invalid'
    assert result['operation_ref'] == domain.identity('operation', {'key': 'original-key', 'name': 'source.read', 'arguments': arguments})
    assert result['record_refs'] == result['changed_record_refs'] == []
    assert result['feedback']['code'] == 'original_invalid_operand'


@pytest.mark.parametrize('status', ['completed', 'partial', 'failed', 'unavailable'])
def test_source_operation_returns_actual_status_and_received_authorization(binding, status):
    captured = []
    result = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': {'source': 'actual'}}
    async def execute(name, arguments, **kwargs):
        captured.append((name, deepcopy(arguments), kwargs))
        return deepcopy(result)
    binding.services.execute_tool = execute
    binding._tool_arguments = lambda context, name, arguments: arguments
    context = SimpleNamespace(role=binding.roles[0], scope={'original': 'scope'}, received_record_refs=('received-original',))
    assert asyncio.run(binding.execute(context, 'source.locate', {'offset': 3}, 'original-key')) == result
    assert captured == [('source.locate', {'offset': 3}, {'scope': {'original': 'scope'}, 'operation_key': 'original-key', 'permitted_record_refs': ('received-original',)})]


def test_source_identity_traversal_retains_real_parent_links(binding):
    records = {'derived': {'record_type': 'source', 'parent_source_refs': ['root']},
        'other': {'record_type': 'source', 'parent_source_refs': []}}
    binding.services.reference_in_scope = lambda ref, scope, namespace: ref in records
    binding.services.read_record = records.__getitem__
    assert binding._within_source('derived', 'root', {}) is True
    assert binding._within_source('other', 'root', {}) is False
    assert binding._artifact({'artifact_ref': 'original', 'text_ref': None}, 'text') == 'original'


def test_credit_keeps_original_service_projection(binding):
    calls = []
    binding.services.scientific_credit = lambda context, selection: calls.append(selection) or {'credit': 0.25}
    context = SimpleNamespace(role=binding.roles[0], scope={}, assignment={})
    assert binding.credit_view(context, {'original': 'selection'}) == {'credit': 0.25}
    assert calls == [{'original': 'selection'}]
