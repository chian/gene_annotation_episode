"""Synthetic selected amount persistence and exact saved-subset return tests."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_amount_inputs import validate_amount_extraction, validate_amount_selection
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_amount_storage import LiteratureAmountRepository, OPERATIONS, amount_cells_schema
from .unit_world import in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_amount_inputs import fixture, SOURCE, TEXT

def setup(store, ctx, *, text=TEXT, arguments=None):
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_amount_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    args = deepcopy(arguments) if arguments is not None else fixture()[0]

    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment', 'question_context_refs': [], 'source_refs': [source]}, {}, [source])
    return (context, args)


@pytest.mark.parametrize('mutation', [lambda x: x.update(value=100), lambda x: x.update(unit='uM'), lambda x: x.update(unavailable_reason='amount_basis_unknown'), lambda x: x['numerator'].update(amount_role='nominal_molecule_amount'), lambda x: x['denominator'].update(qualification='unknown'), lambda x: x['numerator'].update(measurement_ref=None)])
@in_unit
def test_typed_subset_rejects_changed_value_or_scientific_meaning(store, ctx, mutation):
    context, args = setup(store, ctx)
    repo = LiteratureAmountRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    refs = outcome['record_refs']
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=refs, components=['amount_ratio'])
    mutation(rows[0])
    with pytest.raises(ContractError, match='differs_from_saved_cells'):
        repo.validate_returned_values(rows, permitted_record_refs=refs)

@in_unit
def test_missing_receipt_and_assigned_source_ancestry_are_not_global_access(store, ctx):
    context, args = setup(store, ctx)
    repo = LiteratureAmountRepository(store, context.run_id)
    with pytest.raises(ContractError, match='not_received'):
        repo.populate(replace(context, received_record_refs=[]), args, 'selected')
    unrelated_artifact = store.artifact('Other paper', 'text/plain')
    other = store.put('source', {'provider': 'synthetic_other', 'accession': None, 'uri': None, 'artifact_ref': unrelated_artifact, 'text_ref': unrelated_artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    page = replace(context, role='literature_page', path=(('literature_page', 'page'),), assignment={'source_ref': other})
    with pytest.raises(ContractError, match='outside_assigned_source'):
        repo.populate(page, args, 'outside')
    assert store.table(OPERATIONS).select() == []

@in_unit
def test_copied_provider_label_cannot_manufacture_a_selected_amount_sheet(store, ctx):
    context, args = setup(store, ctx)
    repo = LiteratureAmountRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    row = store.get(outcome['result']['sheet_ref'])
    request = json.loads(store.get_artifact(row['request_ref']))
    request['operation_key'] = 'never-selected'
    fields = {field: row[field] for field in ('provider', 'accession', 'uri', 'artifact_ref', 'text_ref', 'version', 'retrieved_at', 'parent_source_refs')}
    fields['request_ref'] = store.artifact(canonical(request), 'application/json')
    fake = store.put('source', fields, origin='tool', scope=plain(context.scope))
    with pytest.raises(ContractError, match='not_selected_output'):
        repo.read(fake['id'])

@pytest.mark.parametrize('field,value', [('value', 20), ('measurement_key', 'wrong'), ('owner_key', 'wrong')])
@in_unit
def test_saved_extraction_checks_source_token_scientific_owner_and_derived_associations(store, ctx, field, value):
    context, args = setup(store, ctx)
    repo = LiteratureAmountRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    extraction = repo.read(outcome['result']['sheet_ref'])['extraction']
    extraction['quantities']['numerator'][field] = value
    with pytest.raises(ValueError, match='amount_saved_quantity_mismatch'):
        validate_amount_extraction(extraction)
