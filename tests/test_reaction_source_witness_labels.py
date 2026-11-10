"""Actual A11028 source selection retains quotations beyond display labels."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import LABEL, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_reaction_meanings import (
    MODEL_FIELDS, RESOURCE_FIELDS, publish_meanings,
)
from gene_annotation_episode.literature_reaction_source import (
    populate_source, reaction_source_population_schema,
)
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store
from test_literature_reaction_storage import source


FIXTURES = Path(__file__).parent / 'fixtures' / 'a110_evaluation'


def rebind_sources(value, original, replacement):
    if isinstance(value, dict):
        if 'source_ref' in value:
            assert value['source_ref'] == original
            value['source_ref'] = replacement
        for child in value.values():
            rebind_sources(child, original, replacement)
    elif isinstance(value, list):
        for child in value:
            rebind_sources(child, original, replacement)


@pytest.mark.parametrize('long_definition', [False, True])
def test_actual_source_selection_keeps_full_witness_and_original_ratio(tmp_path, long_definition):
    args = json.loads((FIXTURES / 'multiline-source-selection-arguments.json').read_text())
    text = (FIXTURES / 'declared-reaction-protocol.txt').read_text()
    if long_definition:
        quote = ('This declared model remains a conditional interpretation.\n' * 20).rstrip()
        text += '\n\n' + quote
        start = text.encode().index(quote.encode())
        args['native_selection']['meanings']['ratio']['claim']['definition'].update(
            start=start, end=start + len(quote.encode()), quote=quote)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        protocol = source(store, text)
        rebind_sources(args, args['source_ref'], protocol['id'])
        context = BindingContext('source-label-case', 'source-label-child', 'literature',
            (('literature', 'source-label-child'),), store.validate_scope(),
            {'version': 'literature_assignment_v1', 'source_refs': [protocol['id']],
             'question_context_refs': [], 'requested_reaction_components': ['reaction_comparison']},
            {}, (protocol['id'],))
        original = deepcopy(args)
        validate_schema(args, reaction_source_population_schema())
        repository = LiteratureReactionRepository(store, context.run_id)
        outcome = populate_source(repository, context, args, 'original-selection')
        saved = repository.read(outcome['result']['sheet_ref'])
        assert saved['sheet']['cells']['ratio_mean']['value'] == .8
        assert saved['sheet']['cells']['claim_mean_squared_error']['value'] == pytest.approx(.05)
        assert saved['sheet']['cells']['reaction_comparison']['value'] == pytest.approx(1 / 3)
        assert saved['sheet']['cells']['resource_capacity']['value'] is None
        rows = repository.semantic_projection().project_cells(
            [outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'],
            components=['reaction_comparison'])
        model = store.get(rows[0]['model_definitions'][0]['model_ref'])
        selected = args['native_selection']['meanings']['ratio']['claim']['definition']
        assert model['anchor'] == {**{key: selected[key] for key in
            ('source_ref', 'start', 'end', 'quote')}, 'artifact_ref': protocol['artifact_ref']}
        assert text.encode()[model['anchor']['start']:model['anchor']['end']].decode() == selected['quote']
        validate_schema(model['label'], LABEL)
        assert 'preview' in model['label']
        basis = [store.get(ref) for ref in saved['native_observations'][0]['basis_refs']]
        original_basis = args['native_selection']['meanings']['ratio']['alternatives'][0]['definition']
        assert any(row['anchor']['quote'] == original_basis['quote'] for row in basis)
        for record in basis:
            anchor = record['anchor']
            assert text.encode()[anchor['start']:anchor['end']].decode() == anchor['quote']
            validate_schema(record['label'], LABEL)
        assert args == original
        assert populate_source(repository, context, args, 'original-selection') == outcome


@pytest.mark.parametrize('namespace', ['reference', 'term', 'context'])
@pytest.mark.parametrize('long_quote', [False, True])
def test_each_meaning_record_preserves_exact_anchor(tmp_path, namespace, long_quote):
    quote = ('A retained source statement\nwith its original line wrapping.'
        if not long_quote else 'A retained source statement. ' * 40)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        paper = source(store, quote)
        witness = {'source_ref': paper['id'], 'artifact_ref': paper['artifact_ref'],
            'start': 0, 'end': len(quote.encode()), 'quote': quote}
        if namespace == 'context':
            entry = {**dict.fromkeys(RESOURCE_FIELDS), 'resource_key': 'declared-resource',
                'supply_basis': 'unresolved', 'coefficient_basis': 'unresolved',
                'biological_setting': witness}
            meanings = {'ratio': None, 'budget': {'resources': [entry], 'demand': {
                **dict.fromkeys(('definition', 'process', 'biological_setting',
                    'compartment', 'period', 'evidence')), 'demand_basis': 'unresolved'}}}
        else:
            entry = {**dict.fromkeys(MODEL_FIELDS), 'prediction_basis': 'unresolved',
                'definition' if namespace == 'reference' else 'reaction': witness}
            meanings = {'ratio': {'claim': entry, 'alternatives': []}, 'budget': None}
        extraction = {'arguments': {'data_source_ref': paper['id']}, 'meanings': meanings}
        original = deepcopy(extraction)
        published = []

        def publish(kind, record):
            saved = store.put(kind, record, origin='tool')
            published.append(saved)
            return saved['id']

        publish_meanings(extraction, publish)
        matched = [row for row in published if row['record_type'] == namespace
            and row.get('anchor') == witness]
        assert len(matched) == 1
        assert matched[0]['anchor']['quote'] == quote
        validate_schema(matched[0]['name' if namespace == 'context' else 'label'], LABEL)
        assert extraction == original
