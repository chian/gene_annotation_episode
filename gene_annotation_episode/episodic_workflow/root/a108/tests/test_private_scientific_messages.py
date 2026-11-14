"""The existing scientific head owns its recursion and literature exchanges."""
from types import SimpleNamespace

import pytest

from .test_private_literature_messages import (
    test_receipt_dispatch_uses_saved_original_child_counterpart as _check_receipt,
)
from .test_private_scientific_process import scientific_binding


@pytest.fixture(params=[('scientific_process', 'scientific_process'),
                        ('literature', 'published_evidence_assessment')])
def scientific_edge(request):
    role, name = request.param
    return 'scientific_process', role, name, scientific_binding()


def request_fixture(edge):
    _, role, _, binding = edge
    parent = SimpleNamespace(role='scientific_process', scope={'subject_refs': ['target']})
    source = SimpleNamespace(path=(('scientific_process', 'original-parent'),),
                             scope=parent.scope, episode_id='parent')
    selection = {'kind': 'episode_child', 'role': role, 'scope': parent.scope,
                 'goal': 'Examine original evidence', 'purpose': 'Return qualified findings',
                 'assignment': {'original': 'selection'}}
    calls = []
    child = SimpleNamespace(required_return_sources=lambda *args: ())
    child.prepare_assignment = lambda *args: calls.append(('assignment', args)) or {'admitted': 'literature'}
    child.prepare_invocation = lambda *args, **kwargs: calls.append(('invocation', args, kwargs)) or {
        'assignment': {'admitted': 'scientific'}, 'scientific_process': {'original': 'invocation'}}
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    workflow = SimpleNamespace(run_id='original-run',
        store=SimpleNamespace(validate_scope=lambda scope, **kwargs: scope),
        expanded_contract_form=lambda *args: (schema, {'original': 'typed-contract'}),
        episode_bindings=SimpleNamespace(for_child=lambda *args: child),
        binding_context=lambda source: parent, child_initial_report_input=lambda *args: '{}',
        specialist=lambda source: binding, annotation_child_roles=('scientific_process', 'literature'),
        available_child_roles=lambda source: ('scientific_process', 'literature'),
        launch_instructions=SimpleNamespace(materialize=lambda value: None),
        scientific_process_binding=child if role == 'scientific_process' else object(),
        journal=SimpleNamespace(row=lambda *args: None))
    return workflow, source, selection, parent, child, calls, schema


def test_original_scientific_request_preparation(scientific_edge):
    _, role, name, binding = scientific_edge
    workflow, source, selection, parent, child, calls, schema = request_fixture(scientific_edge)
    handler = binding.child_request_preparer(role)
    assert handler.__module__.endswith('.scientific_process.to_child_' + name)
    result = handler(workflow, source, selection, 4)
    assert result['scope'] == selection['scope'] and result['schema'] is schema
    assert result['initial'] == {} and result['role'] == role
    args = (parent, role, selection['assignment'], selection['scope'], 'original-run:parent:4')
    if role == 'scientific_process':
        assert calls == [('invocation', args, {'invocation': {
            'objective': selection['goal'], 'purpose': selection['purpose'],
            'report_schema': schema, 'initial_report': {}}})]
        assert result['scientific_process'] == {'original': 'invocation'}
    else:
        assert calls == [('assignment', args)]
        assert result['scientific_process'] is None


def test_scientific_typed_result_required_before_child(scientific_edge):
    from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
    _, role, _, binding = scientific_edge
    workflow, source, selection, parent, child, calls, schema = request_fixture(scientific_edge)
    child.required_return_sources = lambda *args: ('qualified_original_result',)
    with pytest.raises(ContractError, match='child_return_requires_qualified_original_result'):
        binding.child_request_preparer(role)(workflow, source, selection, 4)
    assert calls == []


@pytest.mark.parametrize('redelivery', [False, True])
def test_scientific_receipt_uses_saved_counterpart(scientific_edge, tmp_path, monkeypatch, redelivery):
    _check_receipt(scientific_edge, tmp_path, monkeypatch, redelivery)
