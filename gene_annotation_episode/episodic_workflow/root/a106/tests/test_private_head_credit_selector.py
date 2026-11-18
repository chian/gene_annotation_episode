"""Actual private credit selection over prepared binding contexts.

The context is a validated preparation fixture, not an authenticated journal
commission. No caller projector, provider, native operation or iterator is used.
"""
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest
PACKAGE = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]
AXIS = ROOT.name.upper()

def module(name):
    return import_module(PACKAGE + '.' + name)

@pytest.fixture(scope='module')
def selected_binding(tmp_path_factory):
    directory = tmp_path_factory.mktemp('private-head-credit')
    library = module('perturbation_evidence_library').PerturbationEvidenceLibrary.freeze(directory / 'library', source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
    tools = module('scientific_tool_library').ScientificToolLibrary.freeze(directory / 'tools', catalog=[])
    services = SimpleNamespace(tool_catalog=lambda scope: [])
    Binding = module('perturbation_evidence.episode').PerturbationEvidenceEpisode
    binding = Binding(services, library=library, tool_library=tools, child_roles=('perturbation_evidence',))
    with module('state').Store(directory / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        Context = module('episode_bindings').BindingContext
        parent = Context('selector-fixture', 'parent', 'annotation', (('annotation', 'parent'),), scope, {}, {})
        schema = {'type': 'object', 'properties': {'constructor_input_supplied': {'type': 'boolean', 'description': 'Whether this engineering-only preparation input was supplied.'}}, 'required': ['constructor_input_supplied'], 'additionalProperties': False}
        invocation = {'objective': 'Inspect the original private credit binding', 'purpose': 'Return engineering preparation metadata', 'report_schema': schema, 'initial_report': {'constructor_input_supplied': True}}

        def context(task_context=None):
            assignment = {'selection': {'version': 'perturbation_evidence_selection_v3', 'evidence_axis': library.reference(AXIS), 'thought_pattern': library.reference('P01'), 'child_tool_info': []}, 'evidence_refs': [], 'constraints': {}, 'context': deepcopy(task_context or {})}
            prepared = binding.prepare_invocation(parent, 'perturbation_evidence', assignment, scope, 'selector:prepare', invocation=invocation)
            path = parent.path + (('perturbation_evidence', 'child'),)
            contracts = module('perturbation_evidence.scientific_contracts')
            request = {'goal': {'objective': invocation['objective']}, 'report_contract': {'decision': invocation['purpose'], 'measurements': {'schema': schema}}, 'message': {'scope': scope, 'episode_assignment': prepared['assignment'], 'initial_report': invocation['initial_report'], 'perturbation_evidence': prepared['perturbation_evidence'], 'scientific_invocation_ref': contracts.scientific_invocation_ref(parent.run_id, path)}}
            result = Context(parent.run_id, 'child', 'perturbation_evidence', path, scope, prepared['assignment'], request)
            binding.validate_context(result)
            return result
        yield (binding, store, context)

def evidence_task(unit=2.5):
    return {'evidence_task': {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': AXIS, 'credit_unit': unit}}

def test_selector_rejects_changed_filled_identity_with_own_contract_error(selected_binding):
    binding, _, context = selected_binding
    valid = context(evidence_task() if AXIS == 'A106' else {})
    request = module('communication').plain(valid.request)
    request['message']['perturbation_evidence']['assignment_sha256'] = '0' * 64
    with pytest.raises(module('domain').ContractError, match='scientific_filled_identity_mismatch') as caught:
        binding.credit_projector(replace(valid, request=request))
    assert type(caught.value) is module('domain').ContractError

def test_selector_other_role_remains_inapplicable(selected_binding):
    binding, _, context = selected_binding
    valid = context(evidence_task() if AXIS == 'A106' else {})
    other = replace(valid, role='annotation', path=(('annotation', 'parent'),))
    assert binding.credit_projector(other) is None

def test_original_a106_task_missing_is_rejected_after_valid_preparation(selected_binding):
    if AXIS != 'A106':
        return
    binding, _, context = selected_binding
    valid = context({})
    with pytest.raises(module('domain').ContractError, match='original_axis_finding_task_required') as caught:
        binding.credit_projector(valid)
    assert type(caught.value) is module('domain').ContractError

@pytest.mark.parametrize('field,value', [('evidence_axis', 'A105'), ('credit_unit', 0), ('credit_unit', True), ('kind', 'other')])
def test_original_a106_invalid_task_is_rejected_before_projection(selected_binding, field, value):
    if AXIS != 'A106':
        return
    _, _, context = selected_binding
    invalid = evidence_task()
    invalid['evidence_task'][field] = value
    with pytest.raises(module('domain').ContractError, match='representation_error') as caught:
        context(invalid)
    assert type(caught.value) is module('domain').ContractError
