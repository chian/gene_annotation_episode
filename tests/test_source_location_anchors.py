"""Source locations materialize exact text before semantic identity and grading."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_a105_assay_type_binding_322 import grading_fixture
from test_state import empty_payload, source


def test_coordinate_anchors_save_exact_utf8_and_preserve_aliases_and_identity(tmp_path):
    raw = 'prefix µ\nprotein α binds zinc; culture at pH 7.\n'
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACD', molecule='protein')
        src = source(store, raw)
        location = dict(source_ref=src['id'], artifact_ref=src['artifact_ref'],
                        start=len('prefix µ\n'.encode()), end=len(raw.encode()))
        payload = empty_payload()
        payload['terms'] = [dict(alias='zinc', term_type='chemical', label='zinc',
                                source_ref=src['id'], anchor=location)]
        payload['source_subjects'] = [dict(alias='protein', reference_type='protein',
            label='protein α', source_ref=src['id'], anchor=location)]
        payload['contexts'] = [dict(alias='culture', context_type='growth_condition',
            name='culture', source_ref=src['id'], attributes=[],
            related_refs=['@protein'], anchor=location)]
        payload['observations'] = [dict(alias='observation', kind='source_content',
            subject_refs=store.problem()['subject_refs'], source_subject_refs=['@protein'],
            source_ref=src['id'], measurements=[], dependencies=['@culture'], anchor=location)]
        before = deepcopy(payload)
        validate_schema(payload, store.reasoning_schema())
        scope = {'subject_refs': store.problem()['subject_refs']}
        accepted = store.commit_reasoning(payload, scope, 'coordinates')
        assert accepted['status'] == 'completed', accepted
        for alias in ('zinc', 'protein', 'culture', 'observation'):
            assert store.get(accepted['aliases'][alias])['anchor'] == {
                **location, 'quote': 'protein α binds zinc; culture at pH 7.\n'}
        assert store.get(accepted['aliases']['culture'])['related_refs'] == [accepted['aliases']['protein']]
        assert payload == before
        assert store.commit_reasoning(payload, scope, 'coordinates') == accepted
        legacy = deepcopy(payload)
        for section in ('terms', 'source_subjects', 'contexts', 'observations'):
            legacy[section][0]['anchor'] = {**location, 'quote': raw.encode()[location['start']:].decode()}
        repeated = store.commit_reasoning(legacy, scope, 'legacy')
        assert repeated['aliases'] == accepted['aliases']
        assert repeated['changed_record_refs'] == []


@pytest.mark.parametrize('mistake,code', [
    ('foreign_artifact', 'anchor_source_mismatch'),
    ('outside', 'anchor_transcription_mismatch'),
    ('utf8_boundary', 'anchor_utf8_boundary_required'),
    ('missing_label', 'subject_label_not_in_source_span'),
])
def test_coordinate_selection_cannot_guess_or_change_source_span(tmp_path, mistake, code):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACD', molecule='protein')
        raw = 'α protein'
        src = source(store, raw)
        anchor = dict(source_ref=src['id'], artifact_ref=src['artifact_ref'],
                      start=0, end=len(raw.encode()))
        label = 'protein'
        if mistake == 'foreign_artifact':
            anchor['artifact_ref'] = store.artifact('protein elsewhere')
        elif mistake == 'outside':
            anchor['end'] += 1
        elif mistake == 'utf8_boundary':
            anchor['start'] = 1
        else:
            label = 'different protein'
        payload = empty_payload()
        payload['source_subjects'] = [dict(alias='p', reference_type='protein',
            label=label, source_ref=src['id'], anchor=anchor)]
        outcome = store.commit_reasoning(payload, {'subject_refs': store.problem()['subject_refs']}, mistake)
        assert outcome['status'] == 'invalid', outcome
        assert outcome['errors'][0]['code'] == code
        assert not store.list('reference')


def _coordinates(value):
    if isinstance(value, dict):
        return {key: _coordinates(child) for key, child in value.items() if key != 'quote'}
    if isinstance(value, list):
        return [_coordinates(child) for child in value]
    return value


def test_same_action_coordinate_anchors_and_grader_operands_save_full_sheets(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACD', molecule='protein')
        context, original, _ = grading_fixture(store)
        services = WorkflowServices(SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store)))
        binding = LiteratureEpisodes(services, rate_population=True, assay_grading_population=True)
        support = store.get(original['experiment_ref'])
        commit = empty_payload()
        commit['source_subjects'] = [dict(alias='assay', reference_type='assay',
            label=support['label'], source_ref=original['source_ref'], anchor=_coordinates(support['anchor']))]
        arguments = _coordinates(original)
        arguments['experiment_ref'] = '@assay'
        for criterion in arguments['interpretations'].values():
            criterion['support_refs'] = ['@assay']
        arguments['prediction_model']['support_refs'] = ['@assay']
        selection = dict(kind='reason', commit=commit, evidence_processing={
            'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]})
        schema = binding.reasoning_action_schema(context, store.reasoning_schema())
        validate_schema(selection, schema)
        outcome = binding.execute_reasoning(context, selection, 'same-action-coordinates')
        assert outcome['status'] == 'completed', outcome
        record = store.get(outcome['aliases']['assay'])
        assert record['anchor'] == support['anchor']
        grading = outcome['evidence_processing']['gradings'][0]
        assert grading['result']['sheet_ref'] in outcome['record_refs']
        cells = {cell['component']: cell for cell in grading['result']['cells']}
        assert cells['measured_effect']['value'] == .8
        assert cells['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
        operations = store.db.execute('SELECT outcome FROM literature_assay_grading_operations').fetchall()
        assert len(operations) == 1
        assert store.commit_reasoning(commit, plain(context.scope), 'same-action-coordinates')['aliases'] == outcome['aliases']


def test_public_population_coordinates_are_materialized_before_closed_reader(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACD', molecule='protein')
        context, args, _ = grading_fixture(store)
        services = WorkflowServices(SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store)))
        binding = LiteratureEpisodes(services, rate_population=True, assay_grading_population=True)
        args = _coordinates(args)
        public_schema = next(entry['input_schema'] for entry in binding.catalog(context)
                             if entry['name'] == 'literature.assay_grading.populate')
        validate_schema(args, public_schema)
        original = deepcopy(args)
        outcome = asyncio.run(binding.execute(context, 'literature.assay_grading.populate', args, 'coordinate-tool'))
        assert outcome['status'] == 'completed', outcome
        assert next(cell for cell in outcome['result']['cells'] if cell['component'] == 'measured_effect')['value'] == .8
        assert args == original


def test_examined_source_coordinates_and_legacy_quotes_use_same_action(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MACD', molecule='protein')
        context, _, _ = grading_fixture(store)
        metadata = 'This bibliographic index contains publication identifiers only.\n'
        src = source(store, metadata)
        context = replace(context, received_record_refs=[*context.received_record_refs, src['id']])
        services = WorkflowServices(SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store)))
        binding = LiteratureEpisodes(services, rate_population=True, assay_grading_population=True)
        raw = metadata.encode()
        start = 0
        witness = dict(source_ref=src['id'], representation='original', start=start, end=len(raw))
        selection = dict(kind='reason', commit=empty_payload(), evidence_processing={
            'kind': 'no_applicable_evidence', 'examined': [witness],
            'reason': 'The examined index contains identifiers, with no experiment or result.'})
        public = binding.reasoning_action_schema(context, store.reasoning_schema())
        validate_schema(selection, public)
        outcome = binding.execute_reasoning(context, selection, 'coordinate-examined')
        assert outcome['status'] == 'completed', outcome
        assert outcome['evidence_processing']['examined'][0]['quote'] == raw[start:].decode()
        legacy = deepcopy(selection)
        legacy['evidence_processing']['examined'][0]['quote'] = raw[start:].decode()
        with pytest.raises(ContractError, match='representation_error'):
            validate_schema(legacy, public)
        validate_schema(legacy, binding.accept_reasoning_action_schema(context, {'type': 'object'}))
        assert binding.execute_reasoning(context, legacy, 'legacy-examined')['status'] == 'completed'
