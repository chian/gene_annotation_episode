"""Controlled original Fluc and explicitly synthetic integration; no live model."""
from copy import deepcopy
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, validate_closed_schema, validate_form, form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_storage import LiteratureIonDiscriminationRepository, ion_discrimination_cells_schema, COMPONENTS, NAMESPACE, REQUESTED
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_ion_discrimination_prompt import ION_DISCRIMINATION_TASK
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import return_contract_information, expand_fact_form
from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_INFORMATION_PROFILE
REQUEST = ['nominal_threshold_ratio']
















@pytest.mark.parametrize('profile', [None, CONTRACT_INFORMATION_PROFILE])
def test_actual_prompt_and_form_information_keep_internal_sheet_out(profile):
    original = obj({'numbers': ion_discrimination_cells_schema(), 'judgment': {'type': 'string', 'enum': ['conditional', 'unresolved']}})
    facts = {NAMESPACE: {'type': 'array', 'meaning': 'Requested ion components.', 'report_schema': ion_discrimination_cells_schema()}}
    state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'literature_assignment': {REQUESTED: REQUEST}, 'requested_form': original, 'available_report_facts': facts, 'goal': {'result_contract': original}}
    if profile:
        state['contract_information_profile'] = profile
    before = deepcopy(state)
    for parent in (False, True):
        value = deepcopy(state)
        if parent:
            value['literature_experimental_work']['aspect'] = 'reference_evidence_parent'
            value['reference_evidence_parent'] = {'version': 'reference_evidence_parent_v1', 'source_refs': ['source_' + 'a' * 24]}
        prompt = render_literature_experimental_prompt(value, 'Evaluate ion discrimination.')
        task = prompt.split('\n\nSTEERING\n')[0]
        assert ION_DISCRIMINATION_TASK in task and 'conditional' in task and ('unresolved' in task)
        assert 'host supplies the saved values' in task
        for internal in ('formula_code', 'source_meanings', 'J_R*C*J_R_transpose', 'withheld_locations'):
            assert internal not in task
    assert state == before
    validate_closed_schema(original)
    lookup = return_contract_information(facts_by_role={'literature': facts}, permitted_child_roles=['literature'], role='literature', source=NAMESPACE)
    value = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}, 'contract_information_profile': CONTRACT_INFORMATION_PROFILE}
    task = render_literature_experimental_prompt(value, 'Choose the needed numerical return.', lookup_results=[lookup]).split('\n\nSTEERING\n')[0]
    assert ION_DISCRIMINATION_TASK in task and 'episode-fact:' + NAMESPACE in task
    assert 'formula_code' not in task and 'source_meanings' not in task
    submitted = obj({'chosen': {'$ref': 'episode-fact:' + NAMESPACE}})
    expanded = expand_fact_form(json.dumps(submitted), child_role='literature', facts_by_role={'literature': facts}, permitted_child_roles=['literature'])
    assert expanded['expanded_schema']['properties']['chosen'] == ion_discrimination_cells_schema()







