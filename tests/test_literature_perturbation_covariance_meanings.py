"""Constructed covariance meaning custody, without new statistical arithmetic."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_experimental_prompt import _steering
from gene_annotation_episode.literature_perturbation_summary_storage import (
    LiteraturePerturbationSummaryProjection, perturbation_summary_cells_schema,
)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_perturbation_summary import source_data, extract, calculate, covariance
from test_literature_perturbation_summary_integration import fixture, source, binding_for
from test_runtime import FixtureController, ScriptedProvider


FIELDS = ('summary_kind', 'summary_scale', 'spread_kind', 'spread_scale',
          'count_n', 'count_unit', 'count_independence')
SUPPORT = b'Constructed covariance design; covariance 0.000000000000000000, unrelated arm value 987654321.'
NAMES = ['perturbation_mean_variance']
LEGACY = Path(__file__).with_name('fixtures') / 'a106_summary_legacy_056_128.json'


def data_for(kind='mean_covariance', basis='source_reported', *, qualify=True, all_pairs=False):
    data = source_data(); data['exposure_unit'] = 'unreported'
    for role in ('W', 'K', 'R'):
        entry = data['measurements'][role]
        entry['count'].update(n=5, unit_kind='culture')
        entry['uncertainty'].update(kind='sem', value=1)
        entry['interpretation_basis'] = dict.fromkeys(FIELDS, 'source_supported_inference')
    if kind == 'paired_units':
        for role, values in [('W', [8, 13, 13, 13, 13]), ('K', [3, 0, 2, 4, 6])]:
            entry = data['measurements'][role]; entry['value'] = None
            entry['uncertainty'].update(kind='unreported', value=None)
            entry['raw_units'] = [{'unit_id': 'unit' + str(i), 'values': [value]}
                                  for i, value in enumerate(values)]
    pairs = (('W', 'K'), ('W', 'R'), ('K', 'R')) if all_pairs else (('W', 'K'),)
    data['covariances'] = []
    for first, second in pairs:
        item = covariance(first, second, kind, 0 if kind == 'mean_covariance' else None)
        if qualify:
            item['interpretation_basis'] = basis
        data['covariances'].append(item)
    return data


def covariance_fixture(path, kind='mean_covariance', basis='source_reported', *, names=NAMES,
                       with_support=True, data=None):
    store, context, args = fixture(path)
    data = data_for(kind, basis) if data is None else deepcopy(data)
    additions = []
    if with_support:
        support = source(store, SUPPORT, parents=[args['source_ref']])
        additions.append(support['id'])
        witness = {'source_ref': support['id'], 'representation': 'original',
            'start': 0, 'end': len(SUPPORT), 'quote': SUPPORT.decode()}
        for row in data['covariances']:
            row['witnesses'] = [deepcopy(witness)]
    retained = source(store, canonical(data), parents=[args['source_ref']])
    additions.append(retained['id']); args['data_source_ref'] = retained['id']
    context = replace(context, assignment={**context.assignment,
        'source_refs': [*context.assignment['source_refs'], *additions],
        'requested_perturbation_summary_components': names},
        received_record_refs=(*context.received_record_refs, *additions))
    return store, context, args


def selected(path, kind='mean_covariance', basis='source_reported', **kwargs):
    store, context, args = covariance_fixture(path, kind, basis, **kwargs)
    binding = binding_for(store, context)
    outcome = asyncio.run(binding.execute(context, 'literature.perturbation.populate', args, 'covariance-selected'))
    assert outcome['status'] == 'completed', outcome.get('feedback')
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    schema = obj({'measurements': perturbation_summary_cells_schema()})
    form = form_with_facts({}, schema, binding.facts(context, {'committed_record_refs': [outcome['result']['sheet_ref']]}))
    binding.validate_report(context, form, schema)
    return store, context, binding, outcome, schema, form


@pytest.mark.parametrize('basis', [None, True, 1, 'probably_reported'])
def test_covariance_interpretation_basis_is_closed_and_never_inferred(basis):
    data = data_for(); data['covariances'][0]['interpretation_basis'] = basis
    with pytest.raises(ExperimentalContractError, match='unsupported_summary_meaning'):
        extract(data)


def test_optional_capture_does_not_change_any_numerical_cell_or_old_payload_shape():
    old = calculate(data_for(qualify=False))
    new = calculate(data_for())
    assert old['cells'] == new['cells']
    assert 'covariance_descriptors' not in old
    assert new['covariance_descriptors'][0]['interpretation_basis'] == 'source_reported'
    assert new['covariance_descriptors'][1]['interpretation_basis'] is None
    assert new['covariance_descriptors'][1]['selection'] == 'unreported'


def test_same_numbers_keep_distinct_meanings_and_actual_parent_presentation(tmp_path):
    outcomes = {}
    for kind, basis in [('mean_covariance', 'source_reported'), ('uncorrelated', 'conditional_assumption'),
                        ('paired_units', 'source_supported_inference')]:
        store, context, binding, outcome, schema, form = selected(tmp_path / kind, kind, basis)
        try:
            row, = form['measurements']; qualifier, = row['covariance_interpretations']
            assert row['value'] == 2
            assert (qualifier['first'], qualifier['second']) == ('W', 'K')
            assert qualifier['kind'] == kind and qualifier['interpretation_basis'] == basis
            assert qualifier['use'] == 'used_selected_covariance'
            assert 'value' not in qualifier
            parent = replace(context, role='annotation', episode_id='covariance-parent', assignment={},
                path=(('annotation', 'root'),))
            binding.received_form_references(parent, form, schema, 'covariance-admission')
            captured = binding._received_fact_display_context(parent)
            text = _steering({'child_reports': [form], **captured}, ())
            assert kind in text and basis in text and 'Selected covariance meanings' in text
            assert '0.000000000000000000' not in text and '987654321' not in text
            assert 'Covariance interpretation support' in text
            own = _steering({'last_local_outcome': outcome, **binding._received_fact_display_context(context)}, ())
            assert kind in own and basis in own and 'Selected covariance meanings' in own
            assert '0.000000000000000000' not in own and '987654321' not in own
            outcomes[kind] = text
        finally:
            store.close()
    assert len(set(outcomes.values())) == 3


def test_unrelated_covariance_named_field_and_caller_record_are_not_masked():
    reference = 'reference_' + 'a' * 24
    record = {'id': reference, 'record_type': 'reference', 'origin': 'caller',
        'reference_type': 'literature_result', 'label': 'Ordinary scientific proof',
        'accession': 'scientific_accession', 'source_ref': 'source_' + 'b' * 24,
        'anchor': {'source_ref': 'source_' + 'b' * 24, 'artifact_ref': 'artifact_' + 'c' * 64,
            'start': 0, 'end': len(SUPPORT), 'quote': SUPPORT.decode()}}
    unrelated = {'unrelated': {'covariance_interpretations': [{'support_refs': [reference]}]}}
    display = {'literature_received_fact_display': {'records': {reference: record}, 'received_refs': [reference]}}
    assert SUPPORT.decode() in _steering({'child_reports': [unrelated], **display}, ())
    # A scope/formula-shaped caller object still cannot hide an unrelated record.
    shaped = {'unrelated': [{'evaluated_scope': 'interpreted_reference_perturbation',
        'component': 'perturbation_mean_variance', 'formula_code': 'perturbation_summary_perturbation_mean_variance_v2',
        'covariance_interpretations': [{'first': 'W', 'second': 'K', 'selection': 'selected',
            'kind': 'mean_covariance', 'interpretation_basis': 'conditional_assumption',
            'variance_status': 'estimated', 'use': 'used_selected_covariance', 'support_refs': [reference]}]}]}
    assert SUPPORT.decode() in _steering({'child_reports': [shaped], **display}, ())


def test_explicit_source_text_is_not_changed_by_covariance_support_mask(tmp_path):
    store, context, binding, outcome, schema, form = selected(tmp_path)
    try:
        display = binding._received_fact_display_context(context)
        selected_read = {'status': 'completed', 'result': {'text': SUPPORT.decode()}}
        text = _steering({'child_reports': [form], 'last_local_outcome': selected_read, **display}, ())
        assert SUPPORT.decode() in text
    finally:
        store.close()


def test_only_component_relevant_pairs_cross_the_exact_original_form(tmp_path):
    data = data_for('uncorrelated', 'conditional_assumption', all_pairs=True)
    names = ['W_summary_value', 'perturbation_mean_variance', 'restoration_mean_variance', 'shared_contrast_covariance']
    store, context, binding, outcome, schema, form = selected(tmp_path, data=data, names=names)
    try:
        rows = form['measurements']
        assert 'covariance_interpretations' not in rows[0]
        assert [(r['first'], r['second']) for r in rows[1]['covariance_interpretations']] == [('W', 'K')]
        assert [(r['first'], r['second']) for r in rows[2]['covariance_interpretations']] == [('K', 'R')]
        assert [(r['first'], r['second']) for r in rows[3]['covariance_interpretations']] == [('W', 'K'), ('W', 'R'), ('K', 'R')]
        projection = LiteraturePerturbationSummaryProjection(store, context.run_id)
        for defect in ('omission', 'basis', 'kind', 'support'):
            bad = deepcopy(rows[1:2])
            if defect == 'omission':
                bad[0].pop('covariance_interpretations')
            else:
                qualifier = bad[0]['covariance_interpretations'][0]
                if defect == 'basis': qualifier['interpretation_basis'] = 'source_reported'
                elif defect == 'kind': qualifier['kind'] = 'mean_covariance'
                else: qualifier['support_refs'] = [rows[2]['covariance_interpretations'][0]['support_refs'][0]]
            with pytest.raises(ContractError, match='differs_from_saved'):
                projection.validate_returned_values(bad, permitted_record_refs=context.received_record_refs)
        wrong_pair = deepcopy(rows[1:2]); wrong_pair[0]['covariance_interpretations'][0]['second'] = 'R'
        with pytest.raises(ContractError): validate_schema(wrong_pair, perturbation_summary_cells_schema())
        resolver_denied = set(rows[1]['covariance_interpretations'][0]['support_refs'])
        with pytest.raises(ReportBoundaryError) as denied:
            validate_form(form, schema, lambda ref, namespace: ref not in resolver_denied)
        assert denied.value.diagnostic['code'] == 'unknown_reference'
        parent = replace(context, role='annotation', episode_id='covariance-parent', assignment={}, path=(('annotation', 'root'),))
        one = {'measurements': rows[1:2]}
        binding.received_form_references(parent, one, schema, 'one-pair-admission')
        assert projection.received_cells(parent) == rows[1:2]
        assert projection.fact_cells(parent, [rows[1]['sheet_ref']], components=['restoration_mean_variance']) == []
        with pytest.raises(ContractError, match='cell_not_received'):
            projection.validate_fact_values(parent, rows[2:3])
        next_parent = replace(parent, episode_id='covariance-grandparent')
        projection.receive_cells(next_parent, projection.received_cells(parent), 'forward-pair')
        assert projection.received_cells(next_parent) == rows[1:2]
    finally:
        store.close()


@pytest.mark.parametrize('unavailable', ['unknown_covariance', 'incompatible_estimator'])
def test_unknown_or_unavailable_estimator_is_not_presented_as_applied_covariance(tmp_path, unavailable):
    data = data_for('unknown' if unavailable == 'unknown_covariance' else 'uncorrelated',
                    'unresolved' if unavailable == 'unknown_covariance' else 'conditional_assumption')
    if unavailable == 'incompatible_estimator':
        data['measurements']['W']['summary_kind'] = 'median'
    names = ['perturbation_mean_variance', 'perturbation_variance_upper']
    store, context, binding, outcome, schema, form = selected(tmp_path, data=data, names=names, with_support=False)
    try:
        exact, bound = form['measurements']
        assert exact['value'] is None
        assert exact['covariance_interpretations'][0]['use'] == 'component_unavailable'
        if unavailable == 'unknown_covariance':
            assert exact['unavailable_reason'] == 'cross_arm_covariance_unknown'
            assert bound['value'] == 4
            assert bound['covariance_interpretations'][0]['use'] == 'unknown_covariance_enclosure'
        else:
            assert exact['unavailable_reason'] == 'mean_variance_unavailable'
            assert bound['value'] is None and bound['covariance_interpretations'][0]['use'] == 'component_unavailable'
        assert exact['covariance_interpretations'][0]['support_refs'] == []
    finally:
        store.close()


def test_registered_legacy55_and56_schemas_remain_exact_and_new_tree_is_not_generic(tmp_path):
    original55 = json.loads((Path(__file__).with_name('fixtures') / 'a106_summary_legacy_119_122.json').read_text())['frozen_schema']
    original56 = json.loads(LEGACY.read_text())['frozen_schema']
    assert perturbation_summary_cells_schema(include_interpretation_basis=False) == original55
    assert perturbation_summary_cells_schema(include_covariance_interpretations=False) == original56
    for node in (original55, original56, perturbation_summary_cells_schema()):
        validate_closed_schema(obj({'measurements': node}))
    changed = perturbation_summary_cells_schema()
    changed['items']['properties']['covariance_interpretations']['items']['properties']['kind']['enum'].append('guessed')
    with pytest.raises(ReportBoundaryError): validate_closed_schema(obj({'measurements': changed}))


def test_actual_prechange56_saved_rows_reconstruct_without_source_or_basis_backfill():
    fixture = json.loads(LEGACY.read_text()); form = fixture['form']; rows = form['measurements']
    assert all(len(row) == 56 and 'covariance_interpretations' not in row for row in rows)
    assert hashlib.sha256((json.dumps(form, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()).hexdigest() == fixture['provenance']['original_form_sha256']
    class SavedOnlyStore:
        def __init__(self):
            self.db = sqlite3.connect(':memory:'); self.db.row_factory = sqlite3.Row
            self.db.execute('create table literature_perturbation_operations(run_id,episode_id,operation_key,signature,outcome)')
            self.db.execute('insert into literature_perturbation_operations values(?,?,?,?,?)',
                tuple(fixture['operation'][k] for k in ('run_id', 'episode_id', 'operation_key', 'signature', 'outcome')))
            self.db.execute('pragma query_only=ON')
        def get(self, reference): return deepcopy(fixture['records'][reference])
        def get_artifact(self, reference):
            assert reference in fixture['saved_artifacts'], 'original source/recipe bytes unavailable'
            return fixture['saved_artifacts'][reference].encode()
        def forbidden(self, *args, **kwargs): raise AssertionError('saved replay may not mutate')
        put = artifact = transaction = forbidden
    reopened = SavedOnlyStore()
    try:
        projection = LiteraturePerturbationSummaryProjection(reopened, fixture['operation']['run_id'])
        actual = projection.project_cells([rows[0]['sheet_ref']], permitted_record_refs=[rows[0]['sheet_ref']],
            components=[row['component'] for row in rows])
        assert canonical(actual) == canonical(rows) and reopened.db.total_changes == 1
    finally:
        reopened.db.close()


def test_ordinary_child_parent_and_first_read_only_reconstruction_keep_actual_covariance_meaning(tmp_path, monkeypatch):
    store, context, args = covariance_fixture(tmp_path / 'state', 'uncorrelated', 'conditional_assumption')
    captured = {}; root = store.get(args['source_ref'])
    original_artifacts = {store.get(ref)['artifact_ref'] for ref in context.received_record_refs}
    def reason(inputs, role):
        captured[role] = deepcopy(inputs)
        text = _steering(inputs, ())
        assert 'uncorrelated' in text and 'conditional_assumption' in text
        assert '987654321' not in text and '0.000000000000000000' not in text
        commit = {name: [] for name in store.reasoning_schema()['required']}
        body = store.get_artifact(root['artifact_ref']).decode(); quote = 'matched endpoint'; start = body.index(quote)
        commit['source_subjects'] = [{'alias': role, 'reference_type': 'assay', 'source_ref': root['id'], 'label': quote,
            'anchor': {'source_ref': root['id'], 'artifact_ref': root['artifact_ref'], 'start': start, 'end': start + len(quote), 'quote': quote}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    schema = obj({'only_variance': perturbation_summary_cells_schema()})
    provider = ScriptedProvider([
        {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(context.assignment),
            'goal': 'Compare source-supported covariance meanings', 'scope': plain(context.scope),
            'purpose': 'Return only the selected variance with its actual covariance premise',
            'schema_json': json.dumps(schema), 'initial_report_json': '{}'}, 'report_update': {}},
        {'selection': {'kind': 'tool', 'tool': 'literature.perturbation.populate', 'arguments': args}, 'report_update': {}},
        lambda inputs: reason(inputs, 'own'), lambda inputs: reason(inputs, 'parent')])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args['source_ref']]),), binding_definitions={'credit': scorer.as_record()}))
        assert set(captured) == {'own', 'parent'}
        rows = captured['parent']['child_reports'][0]['only_variance']
        assert len(rows) == 1 and rows[0]['value'] == 2
        assert [row['component'] for row in rows] == NAMES
        observations = [dict(row) for row in store.db.execute('select * from runtime_observations')]
        assert len(observations) == 4
        assert store.db.execute('select count(*) from literature_perturbation_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_perturbation_summary_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
        parent_row = store.db.execute('select * from runtime_episodes where json_array_length(path)=1').fetchone()
        parent = BindingContext(result['run_id'], parent_row['episode_id'], 'annotation',
            tuple(tuple(x) for x in json.loads(parent_row['path'])), plain(context.scope), {}, json.loads(parent_row['request']),
            tuple(captured['parent']['literature_received_fact_display']['received_refs']))
        store.close()
        reopened = Store.__new__(Store); reopened.path = (tmp_path / 'state').resolve(); reopened._savepoint = 0
        reopened.db = sqlite3.connect((reopened.path / 'state.sqlite3').as_uri() + '?mode=ro', uri=True, isolation_level=None)
        reopened.db.row_factory = sqlite3.Row; reopened.db.execute('pragma query_only=ON')
        reopened.db.create_function('library_scope_record', 2, reopened._scope_filter_record)
        original = reopened.get_artifact
        def saved_only(reference):
            assert reference not in original_artifacts, 'first read-only reconstruction may not open sources/recipes'
            return original(reference)
        def forbidden(*a, **k): raise AssertionError('no source/reader/calculator/model/mutation')
        with patch.object(reopened, 'get_artifact', saved_only), patch.object(reopened, 'put', forbidden), \
            patch.object(reopened, 'artifact', forbidden), patch.object(reopened, 'transaction', forbidden), \
            patch('gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs', forbidden), \
            patch('gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration', forbidden), \
            patch('gene_annotation_episode.providers.ModelConnection', forbidden):
            projection = LiteraturePerturbationSummaryProjection(reopened, result['run_id'])
            assert projection.received_cells(parent) == rows
            assert projection.fact_cells(parent, [rows[0]['sheet_ref']], components=['restoration_mean_variance']) == []
            binding = LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=reopened, run_id=result['run_id'])), rate_population=True)
            view = binding._received_fact_display_context(parent)
            text = _steering({'child_reports': [{'only_variance': rows}], **view}, ())
            assert 'uncorrelated' in text and 'conditional_assumption' in text and '987654321' not in text
            assert reopened.db.total_changes == 0
            assert [dict(row) for row in reopened.db.execute('select * from runtime_observations')] == observations
        reopened.close()
    finally:
        store.close()
