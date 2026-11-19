"""Real A107 partner-sheet population over the shared Store with test-written synthetic sources.

No external source, model, parent scientific inference or autonomy is exercised. The literature
context is the A107 ``LiteratureContext`` a literature decision source builds from its episode.
"""
from copy import deepcopy
from fractions import Fraction
import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage import LiteraturePartnerRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs import literature_partner_sheet_population as population
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence import literature_sheet_updates as updates


def source(store, raw, *, parents=(), text=False):
    artifact = store.artifact(raw)
    return store.put('source', {'provider': 'synthetic_native_partner_fixture',
        'accession': None, 'uri': None, 'artifact_ref': artifact,
        'text_ref': artifact if text else None, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def witness(row, raw, quote, *, offset=0, representation='original'):
    data = raw if isinstance(raw, bytes) else raw.encode()
    start = data.index(quote.encode(), offset)
    return {'source_ref': row['id'], 'representation': representation,
        'start': start, 'end': start + len(quote.encode()), 'quote': quote}


def selector(row, raw, token, *, offset=0):
    selected = witness(row, raw, token, offset=offset)
    return {'witness': selected, 'number_start': 0, 'number_end': len(token)}


def partner_fixture(path, *, mode='matched', page=True, extra_unit=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    records = {'ancestor': source(store, 'Synthetic provenance.')}
    records['root'] = source(store, b'\xff\x00Synthetic original binary source.',
        parents=[records['ancestor']['id']])
    omitted = '<0.005' if mode == 'censored' else '0.02'
    raw = ('SubjectS; PartnerP; PLP assay; product formation; per mg SubjectS; '
        'glutamine; ammonium_sulfate; temperature 37 degC; pH 8; '
        'physicalW; physicalO; physicalA; '
        f'W rate 0.1 nmol/min/mg ± 0.01 SD; O rate {omitted} nmol/min/mg; '
        'A rate 0.09 nmol/min/mg. All declared conditions matched.').encode()
    records['data'] = source(store, raw, parents=[records['root']['id']], text=True)
    data = records['data']
    w = lambda quote: witness(data, raw, quote)
    n = lambda token: selector(data, raw, token)
    unit = w('nmol/min/mg')
    if extra_unit:
        records['unit'] = source(store, 'Assay units: nmol/min/mg.', parents=[records['root']['id']])
        unit = witness(records['unit'], b'Assay units: nmol/min/mg.', 'nmol/min/mg')
    arms = {}
    for role, token, physical in (('reference', '0.1', 'physicalW'),
            ('omitted', '0.005' if mode == 'censored' else '0.02', 'physicalO'),
            ('addback', '0.09', 'physicalA')):
        arms[role] = {'subject': w('SubjectS'), 'partner': w('PartnerP'),
            'endpoint': w('product formation'), 'normalization': w('per mg SubjectS'),
            'partner_state': 'absent' if role == 'omitted' else 'present',
            'conditions': {'coverage': 'complete', 'factors': [
                {'factor': 'nitrogen_source', 'level': {'kind': 'literal', 'witness': w('glutamine')}},
                {'factor': 'temperature', 'level': {'kind': 'number', 'selector': n('37'), 'unit_witness': w('degC')}},
                {'factor': 'pH', 'level': {'kind': 'number', 'selector': n('8'), 'unit_witness': None}}]},
            'measurement_identity': w(physical), 'origin': 'synthetic',
            'rate': {'value': n(token), 'unit': deepcopy(unit), 'spread': {
                'kind': 'SD' if role == 'reference' else 'unreported',
                'magnitude': n('0.01') if role == 'reference' else None,
                'unit': None,
                'witnesses': [w('SD')] if role == 'reference' else []}}}
    if mode == 'crossed':
        arms['omitted']['conditions']['coverage'] = 'partial'
        arms['omitted']['conditions']['factors'][0]['level']['witness'] = w('ammonium_sulfate')
        arms['reference']['normalization'] = arms['omitted']['normalization'] = None
        arms['addback'] = None
    elif mode == 'missing':
        arms['addback'] = None
    elif mode == 'unknown_identity':
        arms['omitted']['measurement_identity'] = None
    elif mode == 'all_missing':
        arms = dict.fromkeys(('reference', 'omitted', 'addback'))
    literal_quotes = ('SubjectS', 'PartnerP', 'PLP assay', 'product formation',
        'per mg SubjectS', 'glutamine', 'ammonium_sulfate' if mode == 'crossed' else 'glutamine',
        'glutamine', 'PLP assay')
    fields = ('subject', 'partner', 'experiment', 'endpoint', 'normalization',
        'reference_condition', 'omitted_condition', 'addback_condition', 'function')
    args = {'source_ref': records['root']['id'], 'data_source_ref': data['id'],
        'source_kind': 'synthetic_fixture', 'literals': {field: w(quote) for field, quote in zip(fields, literal_quotes)},
        'interpretation_witnesses': [w('All declared conditions matched.')],
        'input_mode': 'native_source_spans', 'arms': arms}
    if mode == 'crossed':
        args['literals']['normalization'] = None
    context = LiteratureContext('synthetic-native-partner-run', 'native-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}),
        {'page': {'source_ref': records['root']['id']}} if page else {},
        tuple(row['id'] for key, row in records.items() if key != 'ancestor'))
    return store, context, args, records


ADAPTER = 'gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_partner_storage:LiteraturePartnerRepository'

def test_original_population_and_repository_share_one_implementation():
    assert LiteraturePartnerRepository.populate is population.populate
    assert population.populate.__name__ == 'populate'
    assert population.populate._automatic_literature_updates is True
    assert LiteraturePartnerRepository.__module__ + ':' + LiteraturePartnerRepository.__name__ == ADAPTER

@pytest.mark.parametrize('mode', ['matched', 'missing', 'unknown_identity', 'all_missing', 'censored', 'crossed'])
def test_actual_saved_partner_values_and_partial_meanings(tmp_path, mode):
    store, context, args, records = partner_fixture(tmp_path, mode=mode)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        result = population.populate(repo, context, args, 'scientific-populate')
        reference = result['result']['sheet_ref']
        saved = repo.read(reference)
        rows = repo.project_cells([reference], permitted_record_refs=result['record_refs'])
        assert len(rows) == 8
        assert all(row['statistical_uncertainty'] == 'not_evaluated' for row in rows)
        assert all(row['partner_necessity'] == 'not_inferred' for row in rows)
        assert all(row['target_correspondence'] == 'not_evaluated' for row in rows)
        if mode == 'matched':
            assert [row['value'] for row in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
            assert saved['extraction']['native_evidence']['reference']['rate']['value']['raw_number'] == '0.1'
        elif mode == 'missing':
            assert rows[4]['value'] == .8 and rows[6]['unavailable_reason'] == 'arm_unreported'
        elif mode == 'unknown_identity':
            assert rows[4]['unavailable_reason'] == 'measurement_identity_unreported'
        elif mode == 'all_missing':
            assert all(row['value'] is None for row in rows)
        elif mode == 'censored':
            assert rows[1]['value'] is None and (rows[1]['lower'], rows[1]['upper']) == (0, 5)
            fraction = next(row for row in rows if row['component'] == 'addback_fraction')
            assert Fraction(fraction['lower']) <= Fraction(85, 95)
            assert Fraction(fraction['upper']) >= Fraction(9, 10)
        elif mode == 'crossed':
            assert rows[0]['value'] == 100 and rows[1]['value'] == 20
            assert all(row['value'] is None for row in rows[3:])
        assert not store.list('observation') and not store.list('assessment')

def test_actual_publication_identity_current_sheet_update_and_exact_replay(tmp_path, monkeypatch):
    store, context, args, records = partner_fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        first = population.populate(repo, context, args, 'first-publication')
        first_reference = first['result']['sheet_ref']
        first_row = dict(store.db.execute(f'SELECT * FROM {updates.TABLE} WHERE sheet_ref=?', (first_reference,)).fetchone())
        first_receipt = json.loads(first_row['receipt'])
        assert first_row['adapter'] == first_receipt['scientific_calculator'] == ADAPTER
        assert first_row['method'] == 'populate'
        assert first_receipt['publication_operation_ref'] == first['operation_ref']
        assert first_receipt['returned_record_refs'] == {name: first[name] for name in ('record_refs', 'changed_record_refs')}
        assert updates.current_sheet_refs(store, context) == [first_reference]
        second = repo.populate(context, args, 'second-publication')
        assert second['result']['cells'] == first['result']['cells']
        assert second['result']['sheet_ref'] != first_reference
        assert updates.current_sheet_refs(store, context) == [second['result']['sheet_ref']]
        before = [tuple(row) for row in store.db.execute(f'SELECT * FROM {updates.TABLE} ORDER BY rowid')]
        def forbidden(*args, **kwargs): raise AssertionError('saved replay attempted source reading/calculation')
        monkeypatch.setattr(population, 'read_partner_inputs', forbidden)
        assert population.populate(repo, context, deepcopy(args), 'first-publication') == first
        assert repo.populate(context, deepcopy(args), 'second-publication') == second
        assert before == [tuple(row) for row in store.db.execute(f'SELECT * FROM {updates.TABLE} ORDER BY rowid')]
        assert store.db.execute(f'SELECT count(*) FROM {repo.operations_table}').fetchone()[0] == 2
        assert updates.current_sheet_refs(store, context) == [second['result']['sheet_ref']]
        # A107's original partner component policy has no separate main sheet.
        assert updates.current_scoring_sheets(store, context) == []

def test_actual_population_failure_rolls_back_operation_and_sheet(tmp_path, monkeypatch):
    store, context, args, records = partner_fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        before = [row['id'] for row in store.list('source')]
        def fail(*args, **kwargs): raise ValueError('controlled-publication-failure')
        monkeypatch.setattr(updates, '_register', fail)
        with pytest.raises(ValueError, match='controlled-publication-failure'):
            population.populate(repo, context, args, 'failed-publication')
        assert [row['id'] for row in store.list('source')] == before
        assert store.db.execute(f'SELECT count(*) FROM {repo.operations_table}').fetchone()[0] == 0
