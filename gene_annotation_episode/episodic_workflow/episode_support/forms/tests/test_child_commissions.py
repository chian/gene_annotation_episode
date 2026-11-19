"""Child assignment, commission and requested report form, with the real runtime forms and method-loop goals."""
import pytest

from method_loop import ChoiceField, Commission, DeclaredField, Field, FormError, RecordForm
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.child_commissions import (
    commission_child, commissioned_report_form, fill_assignment)
from gene_annotation_episode.episodic_workflow.episode_support.records.closed_json import closed_record

REQUEST_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['resource_id', 'threads'],
                  'properties': {'resource_id': {'type': 'string', 'enum': ['blast_remote']},
                                 'threads': {'type': 'integer', 'minimum': 1}}}

CHILD_FORM = RecordForm({
    'scope': Field('record', 'The sub-scope the child works on'),
    'evidence_task': DeclaredField('text', 'The task the child fixes', 'search homologs'),
    'request_schema': DeclaredField('record', 'The JSON Schema of request', REQUEST_SCHEMA),
    'request': Field('record', 'The selected job request'),
    'thought_pattern': ChoiceField('text', 'The thought pattern', ('survey', 'verify')),
    'notes': Field('text', 'Optional notes', required=False),
})


def test_declared_values_are_copied_and_supplied_values_are_admitted():
    value = fill_assignment(CHILD_FORM, {'scope': {'subject_refs': ['input:1']}, 'thought_pattern': 'verify',
                                         'request': {'resource_id': 'blast_remote', 'threads': 2}},
                            schemas={'request': 'request_schema'})
    assert value['evidence_task'] == 'search homologs'
    assert value['request_schema'] == REQUEST_SCHEMA
    assert value['request'] == {'resource_id': 'blast_remote', 'threads': 2}
    assert 'notes' not in value


def test_a_value_violating_the_child_declared_schema_is_rejected_before_any_child_exists():
    with pytest.raises(FormError, match='violates_declared_schema:request.threads'):
        fill_assignment(CHILD_FORM, {'scope': {}, 'thought_pattern': 'survey',
                                     'request': {'resource_id': 'blast_remote', 'threads': 0}},
                        schemas={'request': 'request_schema'})


@pytest.mark.parametrize('supplied, code', [
    ({'scope': {}, 'thought_pattern': 'survey', 'request': {}, 'evidence_task': 'other'}, 'supplies_a_declared_field'),
    ({'scope': {}, 'request': {}}, 'missing_field:thought_pattern'),
    ({'scope': {}, 'thought_pattern': 'guess', 'request': {}}, 'not_an_offered_option:thought_pattern'),
    ({'scope': {}, 'thought_pattern': 'survey', 'request': {}, 'extra': 1}, 'unknown_field:extra'),
])
def test_assignment_errors_are_explicit(supplied, code):
    with pytest.raises(FormError, match=code):
        fill_assignment(CHILD_FORM, supplied)


def test_a_schema_must_be_declared_by_the_child():
    with pytest.raises(FormError, match='schema_is_not_a_declared_field'):
        fill_assignment(CHILD_FORM, {'scope': {}, 'thought_pattern': 'survey', 'request': {}},
                        schemas={'request': 'scope'})


def test_commission_child_refines_the_parent_goal_and_carries_the_contract():
    parent = EpisodeRequest(EpisodeGoal.root(objective='parent', result_contract={'credit': 'number'}),
                            closed_record({'subject': 'input:1'}))
    contract = ReportContract('Choose the next job', {'schema': REQUEST_SCHEMA}, {'form': 'The typed job form'})
    form = commissioned_report_form(RecordForm({'credit': Field('number', 'credit')}),
                                    {'form': Field('record', 'The typed job form')})
    commission = commission_child(parent, objective='child', result_contract={'form': 'record'},
                                  message=closed_record({'initial_report': {}}), report_contract=contract,
                                  assignment={'scope': {}}, report_form=form)
    assert isinstance(commission, Commission)
    assert commission.request.goal.parent_goal_id == parent.goal.goal_id
    assert commission.request.report_contract is contract
    assert set(commission.report_form.fields) == {'credit', 'form'}


def test_commissioned_report_form_never_replaces_a_return_field():
    with pytest.raises(ValueError, match='commissioned_report_field_is_a_return_field:credit'):
        commissioned_report_form(RecordForm({'credit': Field('number', 'credit')}),
                                 {'credit': Field('number', 'another credit')})
