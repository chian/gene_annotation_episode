"""Public projection -> source panel custody, with original numerical semantics.

The Rhea response is retained real input; compound bytes are explicitly synthetic
interface fixtures. These checks make no live acquisition or HPC run claim.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode import a110_reference_accounting as panels
from gene_annotation_episode.a110_chemical_accounting import calculate
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.a110_tools import A110ToolRegistry
from gene_annotation_episode.communication import plain
from test_component_axis_source_receipts import saved_context
import asyncio


FIXTURES = Path(__file__).parent / 'fixtures/a110_evaluation/reference-reaction-01'


class ChemicalInputs:
    """Retained reaction and marked synthetic compound-interface records."""
    def __init__(self):
        self.when = '2026-11-07T00:00:00Z'
        self.reaction = (FIXTURES / 'reaction-record.json').read_bytes()
        self.compounds = {cid: {'name': 'Synthetic compound-property interface fixture ' + cid,
            'chebi_accession': cid, 'chemical_data': {'formula': 'C3H5O6P', 'charge': -2},
            'ontology_relations': {}, 'default_structure': None}
            for cid in ('CHEBI:59776', 'CHEBI:57642')}

    def rhea_reaction(self, accession):
        return SourceSnapshot('rhea', 'https://example.invalid/retained-rhea',
            {'accession': accession}, self.when, self.reaction, 'application/json',
            {'representation': 'explicit_retained_response_fixture; no_network'})

    def chebi_compound(self, accession):
        return SourceSnapshot('chebi', 'https://example.invalid/synthetic-compound-interface',
            {'accession': accession}, self.when,
            canonical(self.compounds[accession]).encode(), 'application/json',
            {'representation': 'explicit_synthetic_compound_interface_fixture; no_network'})


def acquire(store, inputs, *, compounds=('CHEBI:59776', 'CHEBI:57642'), prefix='original'):
    tools = ToolRegistry(store, clients=inputs)
    reaction = tools.execute('public.rhea.reaction', {'accession': 'RHEA:18585'},
        operation_key=prefix + '-reaction')
    assert reaction['status'] == 'completed', reaction
    known = set(reaction['record_refs']) | set(store.validate_scope()['subject_refs'])
    chemical_refs = []
    for ordinal, cid in enumerate(compounds):
        result = tools.execute('public.chebi.compound', {'accession': cid},
            operation_key=prefix + '-compound-' + str(ordinal))
        assert result['status'] == 'completed', result
        known.update(result['record_refs'])
        chemical_refs.append(result['result']['records'][0]['reference_ref'])
    return reaction['result']['records'][0]['reference_ref'], chemical_refs, known


def context(store, known):
    return BindingContext('reference-accounting-check', 'scientific-owner', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'chemical-reference')),
        store.validate_scope(), {'selection': {'evidence_axis': {'option_id': 'A110'}}},
        {}, tuple(sorted(known)))


def prepare(store, ctx, known, reaction, chemicals):
    target, = ctx.scope['subject_refs']
    ref = panels.request(store, {'target_ref': target, 'reaction_ref': reaction,
        'chemical_refs': chemicals}, context=ctx, known=known)
    known.add(ref)
    ctx = replace(ctx, received_record_refs=tuple(sorted(known)))
    generated, needs = panels.refresh(store, ctx, known)
    known.update(generated)
    returned = [row for row in panels.received(store, known, ctx.scope)
        if row['request_ref'] == ref and row['current']]
    row, = returned
    panel = None if row['panel_source_ref'] is None else json.loads(store.get_artifact(
        store.get(row['panel_source_ref'])['artifact_ref']))
    proof = json.loads(store.get_artifact(store.get(row['provenance_source_ref'])['artifact_ref']))
    return ref, row, panel, proof, needs


@pytest.mark.parametrize('opposing_formula', [False, True])
def test_original_public_fields_feed_the_unchanged_calculator(tmp_path, opposing_formula):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        inputs = ChemicalInputs()
        if opposing_formula:
            inputs.compounds['CHEBI:57642']['chemical_data']['formula'] = 'C3H5O5P'
        reaction, chemicals, known = acquire(store, inputs)
        original_reaction = deepcopy(store.get(reaction))
        ctx = context(store, known)
        request, result, panel, proof, needs = prepare(store, ctx, known, reaction, chemicals)
        assert result['state'] == 'reference_panel_available', result
        assert not needs and not result['missing']
        assert [row['coefficient'] for row in panel['reactions'][0]['participants']] == ['-1', '1']
        assert [row['charge'] for row in panel['species']] == [-2, -2]
        assert all(row['compartment'] is None for row in panel['species'])
        assert panel['reactions'][0]['standard_gibbs'] is None
        assert proof['source_balanced_assertion'] is True and proof['balance_calculated'] is False
        assert set(proof['shared_source_keys']) == {'RHEA:18585', 'CHEBI:59776', 'CHEBI:57642'}
        numerical = calculate(panel, {'reaction_ids': ['reaction_1'],
            'include_declared_pathway': False, 'include_reported_constraints': False})
        accounting = numerical['reactions'][0]['accounting']
        # Rhea's assertion must never override an actual opposing input formula.
        assert accounting['atom_balance'] == ('imbalanced' if opposing_formula else 'balanced')
        assert accounting['charge_balance'] == 'balanced'
        assert store.get(reaction) == original_reaction
        assert result['scientific_credit'] is None and not result['native_execution_requested']
        # Cached source assembly produces no fresh evidence or source publication.
        generated, cached_needs = panels.refresh(store, replace(ctx,
            received_record_refs=tuple(sorted(known))), known)
        assert generated == [] and cached_needs == []
        assert request in known


def test_missing_chemical_fields_do_not_suppress_the_received_equation(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        inputs = ChemicalInputs()
        reaction, chemicals, known = acquire(store, inputs, compounds=('CHEBI:59776',))
        _, result, panel, proof, needs = prepare(store, context(store, known), known, reaction, chemicals)
        assert result['state'] == 'reference_panel_partial' and panel is not None
        assert result['unresolved_chemical_accessions'] == ['CHEBI:57642']
        assert panel['species'][0]['formula'] == 'C3H5O6P'
        assert panel['species'][1]['formula'] is None and panel['species'][1]['charge'] is None
        assert needs and not proof['balance_calculated']
        calculated = calculate(panel, {'reaction_ids': ['reaction_1'],
            'include_declared_pathway': False, 'include_reported_constraints': False})
        assert calculated['reactions'][0]['accounting']['atom_balance'] == 'unknown'


def test_receipt_of_the_named_missing_source_refreshes_only_the_original_request(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        reaction, chemicals, known = acquire(store, ChemicalInputs())
        absent = store.get(chemicals[1])['source_ref']
        absent_artifact = store.get(absent)['artifact_ref']
        known.remove(absent)
        original_get = store.get_artifact
        def received_only(ref, *args, **kwargs):
            assert ref != absent_artifact, 'the private source bytes were reopened before receipt'
            return original_get(ref, *args, **kwargs)
        with monkeypatch.context() as guarded:
            guarded.setattr(store, 'get_artifact', received_only)
            request, initial, panel, _, _ = prepare(store, context(store, known), known, reaction, chemicals)
        assert panel is not None and initial['required_record_refs'] == [absent]
        assert panel['species'][1]['formula'] is None
        original_body = deepcopy(panels.read(store, initial['source_ref'], result=True))
        known.add(absent)
        generated, needs = panels.refresh(store, context(store, known), known)
        known.update(generated)
        current, = [row for row in panels.received(store, known, store.validate_scope())
            if row['request_ref'] == request and row['current']]
        assert current['state'] == 'reference_panel_available' and not needs
        assert current['panel_source_ref'] != initial['panel_source_ref']
        assert panels.read(store, initial['source_ref'], result=True) == original_body
        # Receiving the result alone cannot reopen any undisclosed source record.
        narrow = {current['source_ref']}
        with monkeypatch.context() as guarded:
            guarded.setattr(store, 'get_artifact', received_only)
            row, = panels.received(store, narrow, store.validate_scope())
            assert row['current']
            historical, = panels.received(store, {initial['source_ref']}, store.validate_scope())
            assert historical['current']


def test_secondary_accession_or_same_name_does_not_fill_another_chemical_state(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        inputs = ChemicalInputs()
        inputs.compounds['CHEBI:57642']['chebi_accession'] = 'CHEBI:27732'
        inputs.compounds['CHEBI:57642']['name'] = inputs.compounds['CHEBI:59776']['name']
        inputs.compounds['CHEBI:57642']['secondary_ids'] = ['CHEBI:57642']
        reaction, chemicals, known = acquire(store, inputs)
        _, result, panel, _, _ = prepare(store, context(store, known), known, reaction, chemicals)
        assert result['unresolved_chemical_accessions'] == ['CHEBI:57642']
        assert panel['species'][1]['formula'] is None


def test_symbolic_coefficient_stays_unresolved_instead_of_becoming_one(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        inputs = ChemicalInputs()
        document = json.loads(inputs.reaction)
        document['results'][0]['htmlequation'] = document['results'][0]['htmlequation'].replace(
            '<span class="stoichiometry"> </span>', '<span class="stoichiometry">n+1</span>', 1)
        inputs.reaction = canonical(document).encode()
        reaction, chemicals, known = acquire(store, inputs)
        _, result, panel, proof, _ = prepare(store, context(store, known), known, reaction, chemicals)
        assert panel is None and result['state'] == 'reference_panel_unavailable'
        assert 'participant_requires_supported_constant_stoichiometry' in result['missing']
        assert proof['participant_bindings'][0]['native_participant']['coefficient_expression'] == 'n+1'
        assert result['dataset_id'] is None


def test_reacquisition_preserves_dataset_identity_and_conflicting_selection_stays_unknown(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        inputs = ChemicalInputs()
        reaction, chemicals, known = acquire(store, inputs)
        _, first, panel, _, _ = prepare(store, context(store, known), known, reaction, chemicals)
        inputs.when = '2026-11-07T01:00:00Z'
        again_reaction, again_chemicals, again_known = acquire(store, inputs, prefix='reacquired')
        known.update(again_known)
        assert again_reaction != reaction
        _, again, _, _, _ = prepare(store, context(store, known), known, again_reaction, again_chemicals)
        assert first['dataset_id'] == again['dataset_id']
        inputs.when = '2026-11-07T02:00:00Z'
        inputs.compounds['CHEBI:59776']['chemical_data']['formula'] = 'C3H5O5P'
        conflict_reaction, conflicting, conflict_known = acquire(store, inputs,
            prefix='conflicting', compounds=('CHEBI:59776',))
        known.update(conflict_known)
        _, result, unresolved, proof, _ = prepare(store, context(store, known), known,
            conflict_reaction, [*chemicals, *conflicting])
        assert result['state'] == 'reference_panel_partial'
        assert 'select_one_native_compound_record_per_chemical_state' in result['missing']
        assert unresolved['species'][0]['formula'] is None
        assert len(proof['participant_bindings'][0]['candidate_compound_refs']) == 2
        assert panel['species'][0]['formula'] == 'C3H5O6P'
        assert not store.list('assessment') and not store.current_annotations()


def test_original_registry_action_exposes_the_panel_and_replays_without_another_job(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']
        reaction, chemicals, known = acquire(store, ChemicalInputs())
        ctx = saved_context(store, target, sorted(known - {target}), 'A110')
        tools = A110ToolRegistry(store)
        arguments = {'target_ref': target, 'reaction_ref': reaction, 'chemical_refs': chemicals}
        assert panels.TOOL in tools.catalog(scope=plain(ctx.scope))
        assert panels.TOOL in tools.operation_resource_limits()['component_native_metadata']['tool_names']
        with tools.current_invocation(ctx, read_received=None, tool_name=panels.TOOL,
                arguments=arguments, operation_key='original-panel-action'):
            result = asyncio.run(tools.execute_async(panels.TOOL, arguments,
                scope=plain(ctx.scope), operation_key='original-panel-action'))
            replay = asyncio.run(tools.execute_async(panels.TOOL, arguments,
                scope=plain(ctx.scope), operation_key='original-panel-action'))
        assert result['status'] == 'completed', result
        assert result == replay
        assert panels.read(store, result['result']['request_ref'])['version'] == panels.VERSION
        prepared, = result['result']['preparation_results']
        assert prepared['state'] == 'reference_panel_available', prepared
        assert prepared['panel_source_ref'] in result['record_refs']
        assert result['result']['scientific_credit'] is None
        assert not result['result']['native_execution_requested']
        assert not store.list('assessment') and not store.current_annotations()
