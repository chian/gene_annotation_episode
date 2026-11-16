"""Statistical premise custody; no arithmetic changes or primary-paper inference."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.communication import (
    ReportBoundaryError, form_with_facts, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_perturbation_summary_storage import LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema
from gene_annotation_episode.episodic_workflow.root.a106.tests.test_literature_perturbation_summary import source_data, extract
from gene_annotation_episode.episodic_workflow.root.a106.tests.test_literature_perturbation_summary_integration import fixture, source, binding_for
from gene_annotation_episode.episodic_workflow.root.a106.tests.test_literature_perturbation_integration import locations

ROOT = Path(__file__).resolve().parents[5]
FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale',
          'count_n', 'count_unit', 'count_independence')
REQUIRED = ['W_summary_value', 'perturbation_difference', 'symmetric_effect',
    'restoration_difference', 'restoration_fraction_raw', 'amount_comparability',
    'effect_isolation', 'reference_restoration_index']


def basis(**overrides):
    return {**dict.fromkeys(FIELDS, 'source_reported'), **overrides}


def data_with_basis():
    data = source_data()
    for role, entry in data['measurements'].items():
        entry['interpretation_basis'] = basis(summary_scale='conditional_assumption')
    return data


@pytest.mark.parametrize('mutation', [
    lambda b: b.pop('summary_scale'),
    lambda b: b.update(extra='source_reported'),
    lambda b: b.update(summary_scale='probably_reported'),
    lambda b: b.update(count_n=None),
    lambda b: b.update(spread_kind=True),
])
def test_basis_is_closed_without_changing_selected_numerical_meanings(mutation):
    data = data_with_basis()
    mutation(data['measurements']['W']['interpretation_basis'])
    with pytest.raises(ExperimentalContractError):
        extract(data)



@pytest.mark.parametrize('kind', ['changed_enum', 'unknown_field', 'unknown_source', 'nested', 'generic_optional'])
def test_registered_schema_exception_is_exact_and_does_not_relax_generic_forms(kind):
    node = perturbation_summary_cells_schema()
    if kind == 'changed_enum':
        node['items']['properties']['statistical_interpretation_basis']['properties']['W']['properties']['summary_scale']['enum'].append('guessed')
    elif kind == 'unknown_field':
        node['items']['properties']['extra'] = {'type': 'number'}
    elif kind == 'unknown_source':
        node['x-source'] = 'unregistered_perturbation_cells'
    if kind == 'nested':
        schema = obj({'nested': obj({'measurements': node})})
    elif kind == 'generic_optional':
        schema = obj({'metadata': {'type': 'object', 'properties': {'optional': {'type': 'number'}},
            'required': [], 'additionalProperties': False}})
    else:
        schema = obj({'measurements': node})
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


def populated(tmp_path):
    store, context, args = fixture(tmp_path)
    data = source(store, canonical(data_with_basis()), parents=[args['source_ref']])
    args['data_source_ref'] = data['id']
    context = replace(context, assignment={**context.assignment,
        'source_refs': [*context.assignment['source_refs'], data['id']],
        'requested_perturbation_summary_components': REQUIRED},
        received_record_refs=(*context.received_record_refs, data['id']))
    binding = binding_for(store, context)
    outcome = asyncio.run(binding.execute(context, 'literature.perturbation.populate', locations(args), 'basis-selected'))
    assert outcome['status'] == 'completed', outcome.get('feedback')
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    sheet = outcome['result']['sheet_ref']
    projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
    return store, context, binding, projection, sheet


def test_exact_contributing_roles_and_qualification_survive_typed_receipt(tmp_path):
    store, context, binding, projection, sheet = populated(tmp_path)
    try:
        rows = projection.project_cells([sheet], permitted_record_refs=context.received_record_refs, components=REQUIRED)
        expected = [('W',), ('W', 'K'), ('W', 'K'), ('K', 'R'), ('W', 'K', 'R'),
            ('A_reference', 'A_restored'), ('W', 'K', 'R', 'B_pert', 'B_rest'),
            ('W', 'K', 'R', 'A_reference', 'A_restored', 'B_pert', 'B_rest')]
        for row, roles in zip(rows, expected):
            assert tuple(row['statistical_interpretation_basis']) == roles
            assert all(item == basis(summary_scale='conditional_assumption')
                for item in row['statistical_interpretation_basis'].values())
        form_schema = obj({'measurements': perturbation_summary_cells_schema()})
        validate_closed_schema(form_schema)
        form = form_with_facts({}, form_schema, binding.facts(context, {'committed_record_refs': [sheet]}))
        binding.validate_report(context, form, form_schema)
        assert form['measurements'] == rows
        with pytest.raises(ReportBoundaryError) as unavailable:
            validate_form(form, form_schema, lambda reference, namespace: False)
        assert unavailable.value.diagnostic['code'] == 'unknown_reference'
        parent = replace(context, episode_id='basis-parent', role='annotation', assignment={}, path=(('annotation', 'root'),))
        binding.received_form_references(parent, form, form_schema, 'basis-admission')
        assert projection.received_cells(parent) == rows
        for kind in ('omission', 'mutation', 'irrelevant_role'):
            bad = deepcopy(rows)
            if kind == 'omission':
                bad[0].pop('statistical_interpretation_basis')
            elif kind == 'mutation':
                bad[0]['statistical_interpretation_basis']['W']['summary_scale'] = 'source_reported'
            else:
                bad[0]['statistical_interpretation_basis']['K'] = basis()
            with pytest.raises(ContractError, match='differs_from_saved'):
                projection.validate_returned_values(bad, permitted_record_refs=context.received_record_refs)
            with pytest.raises(ContractError):
                projection.receive_cells(parent, bad, 'bad-' + kind)
        bad = deepcopy(rows)
        bad[0]['statistical_interpretation_basis']['K'] = basis()
        with pytest.raises(ContractError):
            validate_schema(bad, perturbation_summary_cells_schema())
    finally:
        store.close()


