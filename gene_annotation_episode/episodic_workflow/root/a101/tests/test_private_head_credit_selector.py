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
    library = module('sequence_homology_evidence_library').SequenceHomologyEvidenceLibrary.freeze(directory / 'library', source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
    tools = module('scientific_tool_library').ScientificToolLibrary.freeze(directory / 'tools', catalog=[])
    services = SimpleNamespace(tool_catalog=lambda scope: [])
    Binding = module('sequence_homology_evidence.episode').SequenceHomologyEvidenceEpisode
    binding = Binding(services, library=library, tool_library=tools, child_roles=('sequence_homology_evidence',))
    with module('state').Store(directory / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        Context = module('episode_bindings').BindingContext
        parent = Context('selector-fixture', 'parent', 'annotation', (('annotation', 'parent'),), scope, {}, {})
        schema = {'type': 'object', 'properties': {'constructor_input_supplied': {'type': 'boolean', 'description': 'Whether this engineering-only preparation input was supplied.'}}, 'required': ['constructor_input_supplied'], 'additionalProperties': False}
        invocation = {'objective': 'Inspect the original private credit binding', 'purpose': 'Return engineering preparation metadata', 'report_schema': schema, 'initial_report': {'constructor_input_supplied': True}}

        def context(task_context=None):
            assignment = {'selection': {'version': 'sequence_homology_evidence_selection_v3', 'evidence_axis': library.reference(AXIS), 'thought_pattern': library.reference('P01'), 'child_tool_info': []}, 'evidence_refs': [], 'constraints': {}, 'context': deepcopy(task_context or {})}
            prepared = binding.prepare_invocation(parent, 'sequence_homology_evidence', assignment, scope, 'selector:prepare', invocation=invocation)
            path = parent.path + (('sequence_homology_evidence', 'child'),)
            contracts = module('sequence_homology_evidence.scientific_contracts')
            request = {'goal': {'objective': invocation['objective']}, 'report_contract': {'decision': invocation['purpose'], 'measurements': {'schema': schema}}, 'message': {'scope': scope, 'episode_assignment': prepared['assignment'], 'initial_report': invocation['initial_report'], 'sequence_homology_evidence': prepared['sequence_homology_evidence'], 'scientific_invocation_ref': contracts.scientific_invocation_ref(parent.run_id, path)}}
            result = Context(parent.run_id, 'child', 'sequence_homology_evidence', path, scope, prepared['assignment'], request)
            binding.validate_context(result)
            return result
        yield (binding, store, context)

def evidence_task(unit=2.5):
    return {'evidence_task': {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': AXIS, 'credit_unit': unit}}

def test_bound_selector_returns_exact_original_scientific_class_and_empty_received_projection(selected_binding):
    binding, store, context = selected_binding
    actual_context = context(evidence_task() if AXIS == 'A106' else {})
    method = binding.credit_projector
    assert method.__self__ is binding
    assert method.__func__ is module('sequence_homology_evidence.credit').SequenceHomologyEvidenceCredit.credit_projector
    projector = method(actual_context)
    if AXIS == 'A101':
        Expected = module('sequence_homology_evidence.native_correspondence_credit').A101SequenceCredit
        assert type(projector) is Expected
        assert projector.as_record() == Expected().as_record()
        projected = projector(store, module('communication').plain(actual_context.scope), known_record_refs=[])
        assert projector.requires_known_record_refs and projector.yield_method == 'bounded_quality'
    else:
        progress = module('investigation_progress')
        assert type(projector) is progress.ScientificFindingProgress
        assert type(projector.policy) is progress.FindingProgressPolicy
        assert projector.policy.finding_unit == 2.5
        assert projector.as_record() == progress.ScientificFindingProgress(progress.FindingProgressPolicy(2.5)).as_record()
        projected = projector(store, module('communication').plain(actual_context.scope), known_assessment_refs=[])
        assert projected['retained_finding_count'] == 0 and projected['source_contributions'] == []
    assert projected['credit'] == 0
    assert projector.requires_episode_receipts

def test_selector_rejects_changed_filled_identity_with_own_contract_error(selected_binding):
    binding, _, context = selected_binding
    valid = context(evidence_task() if AXIS == 'A106' else {})
    request = module('communication').plain(valid.request)
    request['message']['sequence_homology_evidence']['assignment_sha256'] = '0' * 64
    with pytest.raises(module('domain').ContractError, match='scientific_filled_identity_mismatch') as caught:
        binding.credit_projector(replace(valid, request=request))
    assert type(caught.value) is module('domain').ContractError

def test_selector_other_role_remains_inapplicable(selected_binding):
    binding, _, context = selected_binding
    valid = context(evidence_task() if AXIS == 'A106' else {})
    other = replace(valid, role='annotation', path=(('annotation', 'parent'),))
    assert binding.credit_projector(other) is None
