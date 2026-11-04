"""Native source selectors, exact saved authority and backward-compatible rows."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import form_with_facts, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_partner_storage import (
    COMPONENTS, LiteraturePartnerRepository, partner_cells_schema,
    partner_population_schema, partner_source_population_schema,
)
from gene_annotation_episode.state import Store


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


def fixture(path, *, mode='matched', page=True, extra_unit=False):
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
    context = BindingContext('synthetic-native-partner-run', 'native-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(),
        {'page': {'source_ref': records['root']['id']}} if page else {}, {},
        tuple(row['id'] for key, row in records.items() if key != 'ancestor'))
    return store, context, args, records


def test_native_source_population_keeps_raw_tokens_and_canonical_numerical_rows(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        validate_schema(args, partner_source_population_schema())
        outcome = repo.populate(context, args, 'native')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['version'] == 'literature_partner_inputs_extraction_v2'
        assert saved['data_source_ref'] == records['data']['id']
        assert not store.get_artifact(records['data']['artifact_ref']).startswith(b'{')
        parsed = saved['extraction']['native_evidence']['reference']['rate']
        assert parsed['value']['raw_number'] == '0.1'
        assert parsed['unit']['raw_unit'] == 'nmol/min/mg'
        assert parsed['unit']['multiplier'] == 1000
        assert parsed['canonical_value'] == 100 and parsed['canonical_spread'] == 10
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        assert [row['value'] for row in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
        assert rows[0]['unit'] == 'pmol/min/mg'
        assert rows[0]['arm_metadata']['reference']['spread'] == {'kind': 'SD', 'magnitude': 10}
        assert rows[0]['statistical_uncertainty'] == 'not_evaluated'
        assert saved['extraction']['recipe']['inputs']['arms']['reference']['conditions']['factors'][1] == {
            'factor': 'temperature', 'level': 37, 'unit': 'degC'}
        schema = obj({'cells': partner_cells_schema()})
        validate_closed_schema(schema)
        form = form_with_facts({}, schema, {'literature_partner_cells': rows})
        validate_form(form, schema, lambda ref, namespace: ref in outcome['record_refs']
            and store.get(ref)['record_type'] == namespace)
        assert not store.list('observation') and not store.list('assessment')


@pytest.mark.parametrize('mode', ['censored', 'crossed', 'missing', 'unknown_identity', 'all_missing'])
def test_native_partial_meanings_and_censor_domains_survive_saved_projection(tmp_path, mode):
    store, context, args, _ = fixture(tmp_path, mode=mode)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'native')
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        assert len(rows) == 8
        if mode == 'censored':
            saved = repo.read(outcome['result']['sheet_ref'])
            assert saved['extraction']['native_evidence']['omitted']['rate']['value']['relation'] == 'lt'
            assert rows[1]['value'] is None and (rows[1]['lower'], rows[1]['upper']) == (0, 5)
            fraction = next(row for row in rows if row['component'] == 'addback_fraction')
            assert Fraction(fraction['lower']) <= Fraction(85, 95)
            assert Fraction(fraction['upper']) >= Fraction(9, 10)
        elif mode == 'crossed':
            assert rows[0]['value'] == 100 and rows[1]['value'] == 20
            assert all(row['value'] is None for row in rows[3:])
            factor, = rows[0]['comparison_checks']['reference_omitted']['differing_factor_refs']
            assert store.get(factor)['label'] == 'nitrogen_source'
            assert store.get(factor)['source_ref'] == args['data_source_ref']
        elif mode == 'missing':
            assert rows[4]['value'] == .8 and rows[6]['unavailable_reason'] == 'arm_unreported'
        elif mode == 'unknown_identity':
            assert rows[4]['unavailable_reason'] == 'measurement_identity_unreported'
        else:
            assert all(row['value'] is None for row in rows)


def test_native_nested_source_refs_are_in_stable_direct_order(tmp_path):
    store, context, args, records = fixture(tmp_path, extra_unit=True)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'native')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['direct_input_source_refs'] == [records[k]['id'] for k in ('root', 'data', 'unit')]
        assert saved['input_source_refs'] == [*saved['direct_input_source_refs'], records['ancestor']['id']]
        assert repo.populate(context, json.loads(json.dumps(args, sort_keys=True)), 'native') == outcome


@pytest.mark.parametrize('target', ['root', 'data', 'unit'])
def test_every_native_source_requires_receipt_on_population_and_replay(tmp_path, target):
    store, context, args, records = fixture(tmp_path, extra_unit=True)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, 'native')
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != records[target]['id']))
        for operation in ('native', 'new'):
            with pytest.raises(ContractError, match='not_received'):
                repo.populate(denied, args, operation)


@pytest.mark.parametrize('target', ['root', 'data', 'unit', 'ancestor'])
def test_every_native_direct_and_ancestor_source_requires_scope(tmp_path, monkeypatch, target):
    store, context, args, records = fixture(tmp_path, extra_unit=True)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        repo.populate(context, args, 'native')
        subset = store.reference_subset
        monkeypatch.setattr(store, 'reference_subset', lambda refs, scope:
            [] if records[target]['id'] in refs else subset(refs, scope))
        for operation in ('native', 'new'):
            with pytest.raises(ContractError, match='outside_scope'):
                repo.populate(context, args, operation)


def test_nested_unit_witness_requires_assigned_page_lineage(tmp_path):
    store, context, args, _ = fixture(tmp_path, extra_unit=True)
    with store:
        foreign = source(store, 'Foreign units: nmol/min/mg.')
        chosen = witness(foreign, b'Foreign units: nmol/min/mg.', 'nmol/min/mg')
        for arm in args['arms'].values():
            arm['rate']['unit'] = chosen
        context = replace(context, received_record_refs=(*context.received_record_refs, foreign['id']))
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ContractError, match='outside_assigned_source'):
            repo.populate(context, args, 'native')
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 0


@pytest.mark.parametrize('mode', ['matched', 'censored', 'crossed'])
def test_native_saved_only_reopening_never_reads_original_bytes_or_recalculates(tmp_path, monkeypatch, mode):
    store, context, args, records = fixture(tmp_path, mode=mode, extra_unit=True)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'native')
        reference = outcome['result']['sheet_ref']
        saved = repo.read(reference)
        rows = repo.project_cells([reference], permitted_record_refs=outcome['record_refs'], components=('partner_loss_fraction', 'reference_rate'))
        parent = replace(context, episode_id='native-parent')
        repo.receive_cells(parent, rows, 'delivery')
        original_artifacts = {row['artifact_ref'] for row in records.values()}
        for artifact in original_artifacts:
            digest = artifact.removeprefix('artifact_')
            (Path(tmp_path)/'artifacts'/digest[:2]/digest).unlink()
        sheet = store.get(reference)
        allowed = {sheet['artifact_ref'], sheet['request_ref']}

    def forbidden(*args, **kwargs):
        raise AssertionError('saved native partner read performed source/calculator work')

    import gene_annotation_episode.literature_partner_source_fields as scalar
    import gene_annotation_episode.literature_partner_native_inputs as native
    import gene_annotation_episode.literature_partner_calculations as core
    import gene_annotation_episode.literature_partner_inputs as dispatcher
    import gene_annotation_episode.literature_partner_storage as storage
    import gene_annotation_episode.literature_assay_inputs as assay
    disabled_origins = {module.__name__ for module in (scalar, native, core)}
    for module in (scalar, native, core, dispatcher, storage):
        for name, value in list(vars(module).items()):
            if callable(value) and getattr(value, '__module__', None) in disabled_origins:
                monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(storage, 'read_partner_inputs', forbidden)
    monkeypatch.setattr(storage, '_native_population_schema', forbidden)
    monkeypatch.setattr(storage, '_native_evidence_schema', forbidden)
    monkeypatch.setattr(dispatcher, 'read_partner_inputs', forbidden)
    monkeypatch.setattr(assay._Sources, 'source', forbidden)
    monkeypatch.setattr(assay._Sources, 'witness', forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteraturePartnerRepository(reopened, context.run_id)
        get_artifact = reopened.get_artifact
        reads = []
        def saved_only(ref):
            assert ref in allowed
            reads.append(ref)
            return get_artifact(ref)
        monkeypatch.setattr(reopened, 'get_artifact', saved_only)
        reopened.db.execute('PRAGMA query_only=ON')
        assert repo.populate(context, json.loads(json.dumps(args, sort_keys=True)), 'native') == outcome
        assert repo.read(reference) == saved
        assert repo.project_cells([reference], permitted_record_refs=outcome['record_refs'], components=('partner_loss_fraction', 'reference_rate')) == rows
        assert repo.received_cells(parent) == rows
        assert set(reads) == allowed


@pytest.mark.parametrize('mode', ['native_value', 'raw_number', 'unit_raw', 'entity_identity', 'measurement_identity', 'source_artifact', 'condition_value', 'canonical_value', 'canonical_spread', 'spread_unit', 'spread_meaning'])
def test_saved_native_evidence_and_normalized_core_relationships_cannot_be_changed(tmp_path, monkeypatch, mode):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'native')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        evidence = saved['extraction']['native_evidence']['reference']
        if mode == 'native_value':
            evidence['rate']['value']['selector']['number_start'] = 1
        elif mode == 'raw_number':
            evidence['rate']['value']['raw_number'] = '99'
        elif mode == 'unit_raw':
            evidence['rate']['unit']['raw_unit'] = 'umol/min/mg'
        elif mode == 'entity_identity':
            saved['extraction']['recipe']['inputs']['arms']['reference']['subject_ref'] = 'forged_subject'
            saved['extraction']['calculation']['inputs']['arms']['reference']['subject_ref'] = 'forged_subject'
        elif mode == 'measurement_identity':
            saved['extraction']['recipe']['inputs']['arms']['reference']['measurement']['measurement_id'] = 'number_token_is_not_measurement'
            saved['extraction']['calculation']['inputs']['arms']['reference']['measurement']['measurement_id'] = 'number_token_is_not_measurement'
        elif mode == 'source_artifact':
            evidence['subject']['artifact_ref'] = 'artifact_' + 'f' * 64
        elif mode == 'condition_value':
            evidence['conditions']['factors'][1]['level']['selector']['value'] = 99
        elif mode == 'canonical_value':
            evidence['rate']['canonical_value'] = 999
        elif mode == 'canonical_spread':
            evidence['rate']['canonical_spread'] = 999
        elif mode == 'spread_unit':
            evidence['rate']['spread']['unit'] = deepcopy(evidence['rate']['unit'])
        else:
            evidence['rate']['spread']['kind'] = 'SEM'
        artifact = store.get(ref)['artifact_ref']
        original = store.get_artifact
        monkeypatch.setattr(store, 'get_artifact', lambda key: canonical(saved).encode() if key == artifact else original(key))
        with pytest.raises(ContractError, match='sheet_source_mismatch'):
            repo.read(ref)


def test_native_publication_failure_rolls_back_bindings_and_selected_result(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path, mode='crossed')
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        before = {kind: store.list(kind) for kind in ('source', 'reference', 'term', 'context')}
        put = store.put
        def interrupted(kind, data, **kwargs):
            if kind == 'source' and data['provider'] == repo.provider:
                raise RuntimeError('synthetic native publication interruption')
            return put(kind, data, **kwargs)
        monkeypatch.setattr(store, 'put', interrupted)
        with pytest.raises(RuntimeError, match='publication interruption'):
            repo.populate(context, args, 'native')
        assert {kind: store.list(kind) for kind in before} == before
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 0


def test_native_schema_has_no_scientific_number_arguments_and_old_schema_is_unchanged(tmp_path):
    store, _, args, _ = fixture(tmp_path)
    with store:
        schema = partner_source_population_schema()
        validate_schema(args, schema)
        assert set(partner_population_schema()['properties']) == {
            'source_ref', 'data_source_ref', 'source_kind', 'literals', 'interpretation_witnesses'}
        changed = deepcopy(args)
        changed['arms']['reference']['rate']['canonical_value'] = 100
        with pytest.raises(ContractError):
            validate_schema(changed, schema)
        schema['properties']['arms'] = {}
        assert partner_source_population_schema()['properties']['arms'] != {}


def test_native_original_binary_and_text_projection_can_share_one_source_identity(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        projected = store.put('source', {'provider': 'synthetic_native_projected',
            'accession': None, 'uri': None, 'artifact_ref': records['root']['artifact_ref'],
            'text_ref': records['data']['artifact_ref'], 'request_ref': None, 'version': None,
            'retrieved_at': None, 'parent_source_refs': [records['ancestor']['id']]}, origin='caller')
        args['source_ref'] = args['data_source_ref'] = projected['id']
        def project(value):
            if isinstance(value, dict):
                if set(value) == {'source_ref', 'representation', 'start', 'end', 'quote'}:
                    value.update(source_ref=projected['id'], representation='text')
                else:
                    for child in value.values():
                        project(child)
            elif isinstance(value, list):
                for child in value:
                    project(child)
        project(args)
        context = replace(context, assignment={'page': {'source_ref': projected['id']}},
            received_record_refs=(projected['id'],))
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'projection')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['direct_input_source_refs'] == [projected['id']]
        assert saved['extraction']['native_evidence']['reference']['rate']['value']['selector']['witness']['artifact_ref'] == projected['text_ref']
        assert saved['input_artifact_ref'] == projected['artifact_ref']
        assert outcome['result']['cells']['partner_loss_fraction']['value'] == .8


def test_native_negative_temperature_is_metadata_not_a_negative_rate(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = b'Assay temperature -10 degC.'
        cold = source(store, raw, parents=[records['root']['id']])
        for arm in args['arms'].values():
            arm['conditions']['factors'][1]['level'].update(
                selector=selector(cold, raw, '-10'), unit_witness=witness(cold, raw, 'degC'))
        context = replace(context, received_record_refs=(*context.received_record_refs, cold['id']))
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'cold')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['recipe']['inputs']['arms']['reference']['conditions']['factors'][1]['level'] == -10
        assert outcome['result']['cells']['partner_loss_fraction']['value'] == .8


def test_separately_selected_absolute_spread_unit_preserves_custody_and_saved_conversion(tmp_path):
    store, context, args, records = fixture(tmp_path, extra_unit=True)
    with store:
        raw = b'Reference absolute error 10 pmol/min/mg SD.'
        spread_source = source(store, raw, parents=[records['root']['id']])
        args['arms']['reference']['rate']['spread'] = {
            'kind': 'SD', 'magnitude': selector(spread_source, raw, '10'),
            'unit': witness(spread_source, raw, 'pmol/min/mg'),
            'witnesses': [witness(spread_source, raw, 'SD')]}
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(context, args, 'mixed-spread')
        received = replace(context, received_record_refs=(*context.received_record_refs, spread_source['id']))
        outcome = repo.populate(received, args, 'mixed-spread')
        saved = repo.read(outcome['result']['sheet_ref'])
        parsed = saved['extraction']['native_evidence']['reference']['rate']
        assert parsed['unit']['raw_unit'] == 'nmol/min/mg'
        assert parsed['spread']['unit']['raw_unit'] == 'pmol/min/mg'
        assert parsed['spread']['magnitude']['value'] == parsed['canonical_spread'] == 10
        assert saved['direct_input_source_refs'] == [records['root']['id'], records['data']['id'],
            *sorted([records['unit']['id'], spread_source['id']])]
        assert repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])[0]['arm_metadata']['reference']['spread'] == {'kind': 'SD', 'magnitude': 10}
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(context, args, 'mixed-spread')


def test_different_numerical_tokens_do_not_establish_distinct_physical_measurements(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        args['arms']['omitted']['measurement_identity'] = deepcopy(args['arms']['reference']['measurement_identity'])
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ExperimentalContractError, match='shared_measurement_conflict'):
            repo.populate(context, args, 'shared-identity')
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 0


def test_separately_selected_spread_unit_must_share_rate_dimension(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = b'Reference error 10 per_s SD.'
        spread_source = source(store, raw, parents=[records['root']['id']])
        args['arms']['reference']['rate']['spread'] = {
            'kind': 'SD', 'magnitude': selector(spread_source, raw, '10'),
            'unit': witness(spread_source, raw, 'per_s'),
            'witnesses': [witness(spread_source, raw, 'SD')]}
        context = replace(context, received_record_refs=(*context.received_record_refs, spread_source['id']))
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ExperimentalContractError, match='spread_rate_dimension_mismatch'):
            repo.populate(context, args, 'bad-dimension')
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 0


@pytest.mark.parametrize('unit_suffix', ['%', 'percent', 'pmol/min/mg', 'per_s'])
def test_relative_or_unselected_different_spread_units_cannot_publish_a_sheet(tmp_path, unit_suffix):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = f'Reference error 58 {unit_suffix} SD.'.encode()
        spread_source = source(store, raw, parents=[records['root']['id']])
        args['arms']['reference']['rate']['spread'] = {
            'kind': 'SD', 'magnitude': selector(spread_source, raw, '58'), 'unit': None,
            'witnesses': [witness(spread_source, raw, 'SD')]}
        context = replace(context, received_record_refs=(*context.received_record_refs, spread_source['id']))
        repo = LiteraturePartnerRepository(store, context.run_id)
        expected = 'relative_spread_unit_unsupported' if unit_suffix in ('%', 'percent') else 'source_spread_unit_mismatch'
        with pytest.raises(ExperimentalContractError, match=expected):
            repo.populate(context, args, 'bad-spread')
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 0


@pytest.mark.parametrize('bad_args', [None, [], 42])
def test_nonobject_arguments_return_structured_contract_failure(tmp_path, bad_args):
    store, context, _, _ = fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        with pytest.raises(ContractError):
            repo.populate(context, bad_args, 'bad')
