"""Primary-source numerical delivery with scripted decisions/controllers.

The source measurements are published; this is controlled engineering execution,
not an independent model interpretation, a new assay, or a reliability policy.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import partial
import hashlib
import json
from pathlib import Path
import runpy
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_rate_domains import rate_source_domain_cells_schema
from gene_annotation_episode.literature_rate_native_inputs import rate_source_population_schema
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIMARY = ROOT / 'research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin'
RENDER = HERE.parent / 'a105_optical_parent_repair_138/ROOT_ARTICLE_TEXT_001.txt'
SOURCE_SHA = '318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf'
REQUESTED = ['reference_rate', 'test_rate', 'rate_difference', 'retained_fraction',
             'fractional_decrease', 'reference_mean_se', 'test_mean_se']


def save(path, value):
    path.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + '\n')


def setup_primary(path, case):
    raw = PRIMARY.read_bytes()
    assert len(raw) == 198525 and hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    text = RENDER.read_text()
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    original = store.artifact(raw, 'text/html')
    rendered = store.artifact(text.encode(), 'text/plain')
    source = store.put('source', {'provider': 'retained_primary_PMC2223550',
        'accession': 'PMC2223550', 'uri': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/',
        'artifact_ref': original, 'text_ref': rendered, 'request_ref': None,
        'version': 'retained_original_html_with_root138_text_render', 'retrieved_at': None}, origin='caller')
    ref = source['id']
    def at(start, end):
        return {'source_ref': ref, 'representation': 'text',
            'start': len(text[:start].encode()), 'end': len(text[:end].encode()), 'quote': text[start:end]}
    def w(phrase, after=0):
        start = text.index(phrase, after)
        return at(start, start + len(phrase))
    def inside(outer, phrase):
        start = outer['quote'].index(phrase)
        left = outer['start'] + len(outer['quote'][:start].encode())
        return {**outer, 'start': left, 'end': left + len(phrase.encode()), 'quote': phrase}
    table_start = text.index('TABLE 2.')
    table_end = text.index('(ii) NADH oxidation assay.', table_start)
    table_text = text[table_start:table_end]
    is_nadh = case == 'nadh_methyl_viologen'
    block_label = ('NADH oxidation (measured photometrically)' if is_nadh else
        'Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)')
    block = text.index(block_label, table_start)
    expected_reference = '7 (14)a' if is_nadh else '5'
    test_label = 'Fd + Hyd − crotonyl-CoA' if case == 'h2_crotonyl_omission' else 'Fd + Hyd + methyl viologen'
    expected_test = '<0.01' if case == 'h2_crotonyl_omission' else '5' if is_nadh else '0.02'
    # Check the retained rendering against the original HTML table itself.
    # The existing tiny HTMLParser class has no numerical model/assay meaning;
    # loading its definitions does not invoke its guarded research-arithmetic main.
    parser_class = runpy.run_path(str(HERE.parent / 'a105_optical_parent_repair_138/read_primary_controls_001.py'))['Tables']
    parser = parser_class(); parser.feed(raw.decode())
    original_tables = [table for table in parser.tables if any('Sp act (U/mg)' in cell for row in table for cell in row)]
    assert len(original_tables) == 1
    original_rows = original_tables[0]
    original_block = original_rows.index([block_label, ''])
    next_block = next((i for i in range(original_block + 1, len(original_rows))
        if len(original_rows[i]) == 2 and original_rows[i][1] == ''), len(original_rows))
    values = dict(original_rows[original_block + 1:next_block])
    assert values['Fd + Hyd'] == expected_reference
    assert values[test_label] == expected_test
    save(path.parent / 'original_html_table_binding.json', {'source_sha256': SOURCE_SHA,
        'endpoint_block': block_label, 'original_table_rows': original_rows,
        'reference': {'label': 'Fd + Hyd', 'raw_html_parsed_token': values['Fd + Hyd']},
        'test': {'label': test_label, 'raw_html_parsed_token': values[test_label]},
        'native_reader_consumes': 'Retained primary text render; independent deterministic original HTML table token check agrees.'})
    rows = {'reference': w('Fd + Hyd\n' + expected_reference + '\n', block),
            'test': w(test_label + '\n' + expected_test + '\n', block)}
    # Exact row location owns the reported observation; no replicate identity is
    # invented from row count, temperature footnote, or repeated representation.
    for row in rows.values():
        assert row['quote'] in table_text
    footnote_start = text.index('Assays with activity are indicated by bold type.', table_start)
    start = text.index('For NADH oxidation each' if is_nadh else 'For ferredoxin reduction each', footnote_start)
    protocol = at(start, text.index('. The reactions were started', start) if not is_nadh else
        text.index('. For TTC reduction', start))
    definition_start = text.index('One unit was equivalent to', footnote_start)
    bridge = at(definition_start, text.index('.', definition_start) + 1)
    endpoint = w(block_label, table_start)
    entity = 'NADH' if is_nadh else 'H2'
    clause = inside(bridge, '1 μmol of ' + entity + (' oxidized per min' if is_nadh else ' formed per min'))
    unit = {'kind': 'source_defined_rate_unit', 'witness': w('U/mg', table_start),
        'definition': {'bridge': bridge, 'clause': clause,
            'amount': {'witness': clause, 'number_start': 0, 'number_end': 1},
            'amount_unit': inside(clause, 'μmol'), 'time_unit': inside(clause, 'min'),
            'endpoint': endpoint, 'endpoint_entity': inside(endpoint, entity),
            'definition_entity': inside(clause, entity)}}
    subject = w('purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri', table_start)
    relation = {'value': 'same', 'witnesses': [protocol]}
    args = {'input_mode': 'native_source_spans', 'source_ref': ref, 'source_kind': 'primary_source',
        'experiment': protocol, 'comparison': {name + '_relation': deepcopy(relation)
            for name in ('subject', 'endpoint', 'normalization')},
        'dependence': {'value': 'unknown', 'witnesses': []},
        'observation_model': {'value': 'none', 'witnesses': []}, 'arms': {}}
    args['comparison']['intended_change'] = inside(rows['test'], test_label)
    for role, token in [('reference', expected_reference.split()[0]), ('test', expected_test.lstrip('<'))]:
        row = rows[role]
        start = row['quote'].index('\n') + 1
        if row['quote'][start] == '<':
            start += 1
        args['arms'][role] = {'subject': subject, 'construct': None, 'preparation': None,
            'experiment': protocol, 'label': inside(row, row['quote'].splitlines()[0]),
            'condition': inside(row, row['quote'].splitlines()[0]), 'endpoint': endpoint,
            'normalization': w('Sp act (U/mg)', table_start), 'measurement_identity': row,
            'rate': {'number': {'witness': row, 'number_start': start, 'number_end': start + len(token)},
                'unit': deepcopy(unit)},
            'uncertainty': {'kind': 'unreported', 'magnitude': None, 'unit': None,
                'kind_witnesses': [], 'count': None,
                'sampling_basis': {'value': 'unspecified', 'witnesses': []}}}
    context = BindingContext('primary-139', 'owner-139', 'literature', (('literature', case),),
        store.validate_scope(), {'version': 'literature_assignment_v1', 'question_context_refs': [],
            'source_refs': [ref], 'requested_rate_components': REQUESTED}, {}, (ref,))
    return store, context, args


def reason(store, source_ref):
    # A controlled ordinary reasoning action retains an exact already read
    # subject statement. This is not independent live model interpretation.
    source = store.get(source_ref)
    text = store.get_artifact(source['text_ref']).decode()
    phrase = 'purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri'
    start = text.index(phrase)
    commit = {name: [] for name in store.reasoning_schema()['required']}
    commit['source_subjects'] = [{'alias': 'primary_assayed_complex', 'reference_type': 'assay',
        'source_ref': source_ref, 'label': phrase, 'anchor': {'source_ref': source_ref,
            'artifact_ref': source['text_ref'], 'start': len(text[:start].encode()),
            'end': len(text[:start + len(phrase)].encode()), 'quote': phrase}}]
    return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}


@pytest.mark.parametrize('case', ['h2_crotonyl_omission', 'h2_methyl_viologen', 'nadh_methyl_viologen'])
def test_primary_selected_native_original_return_and_saved_reconstruction(tmp_path, monkeypatch, case):
    path = tmp_path / 'state'
    store, template, args = setup_primary(path, case)
    form = obj({'requested_primary_components': rate_source_domain_cells_schema()})
    captured = {}
    def child_next(inputs):
        captured['child'] = deepcopy(inputs)
        prompt = render_literature_experimental_prompt(inputs, 'Read the selected original paper experiment and its controls.')
        (tmp_path / 'child_next_prompt.txt').write_text(prompt)
        assert 'purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri' in prompt
        assert 'Sp act (U/mg)' in prompt
        return reason(store, args['source_ref'])
    def parent_next(inputs):
        captured['parent'] = deepcopy(inputs)
        rows = inputs['child_reports'][0]['requested_primary_components']
        assert [row['component'] for row in rows] == REQUESTED
        assert inputs['literature_rate_source_domain_display']['cells'] == rows
        prompt = render_literature_experimental_prompt(inputs, 'Evaluate experimental support for activity of the source complex.')
        (tmp_path / 'parent_next_prompt.txt').write_text(prompt)
        steering = prompt.split('\n\nSTEERING\n', 1)[1]
        for phrase in ['purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri',
                       'Sp act (U/mg)', 'mean_uncertainty_unreported', 'not sampling confidence intervals']:
            assert phrase in steering
        assert ('0.01 mg' if case == 'nadh_methyl_viologen' else '0.05 mg') in steering
        assert ('25°C' if case == 'nadh_methyl_viologen' else '37°C') in steering
        assert '1.6 U hydrogenase from C. pasteurianum' in steering if case != 'nadh_methyl_viologen' else '0.4 U hydrogenase' in steering
        assert 'Reference mean standard error' in steering
        assert 'Signed profile log ratio' not in steering
        return reason(store, args['source_ref'])
    provider = ScriptedProvider([
        {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': plain(template.assignment),
            'goal': 'Read the source-bound Table2 control comparison for the purified complex.',
            'scope': plain(template.scope), 'purpose': 'Return the requested endpoint-specific native numerical components.',
            'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}},
        {'selection': {'kind': 'tool', 'tool': 'literature.rate.source.populate', 'arguments': args}, 'report_update': {}},
        child_next, parent_next])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run',
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
        project_credit=scorer, initial_known_record_refs=[args['source_ref']],
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args['source_ref']]),), binding_definitions={'credit': scorer.as_record()}))
    assert result['credit'] == 0
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
    operation, = store.db.execute('SELECT * FROM literature_rate_operations').fetchall()
    attempt, = store.db.execute('SELECT * FROM runtime_report_attempts').fetchall()
    assert attempt['failure'] is None
    returned = json.loads(attempt['form'])['requested_primary_components']
    assert returned == captured['parent']['child_reports'][0]['requested_primary_components']
    outcome = json.loads(operation['outcome'])
    sheet_ref = outcome['result']['sheet_ref']
    repo = LiteratureRateRepository(store, operation['run_id'])
    saved = repo.read(sheet_ref)
    sheet = saved['sheet']
    by = {row['component']: row for row in returned}
    for arm in sheet['extraction']['rows']:
        assert arm['uncertainty']['kind'] == 'unreported' and arm['uncertainty']['count'] is None
        assert arm['source']['measurement_identity'] is not None
        assert arm['source']['unit']['source_defined_unit']['definition']['endpoint_entity']['quote'] == ('NADH' if case == 'nadh_methyl_viologen' else 'H2')
    if case == 'h2_crotonyl_omission':
        assert by['test_rate']['value'] is None and by['test_rate']['threshold'] == .01
        assert by['test_rate']['bound'] == 'lt'
        for component, exact in [('rate_difference', Fraction(499, 100)), ('fractional_decrease', Fraction(499, 500))]:
            domain = by[component]['reported_domain']
            assert domain['kind'] == 'lower_bounded' and domain['upper'] is None
            assert domain['lower_inclusive'] is False
            assert Fraction(domain['lower']) <= exact
            image = sheet['native_bound_arithmetic']['components'][component]['image']
            assert image['lower'] == {'numerator': str(exact.numerator), 'denominator': str(exact.denominator)}
        # This establishes the current missing physical-domain capacity; it
        # must not be silently reported as the conditional finite enclosure.
        assert 'nonnegative' not in canonical(rate_source_population_schema())
        assert by['fractional_decrease']['reported_domain']['upper'] is None
    else:
        expected = Fraction(5, 7) if case == 'nadh_methyl_viologen' else Fraction(1, 250)
        assert by['retained_fraction']['value'] == pytest.approx(float(expected))
        assert by['retained_fraction']['reported_domain']['failure'] is None
    save(tmp_path / 'original_selection.json', args)
    save(tmp_path / 'saved_numerical_sheet.json', saved)
    save(tmp_path / 'original_typed_contract.json', json.loads(attempt['contract']))
    save(tmp_path / 'original_admitted_form.json', json.loads(attempt['form']))
    save(tmp_path / 'runtime_result.json', result)
    save(tmp_path / 'observations.json', [dict(row) for row in store.db.execute('SELECT * FROM runtime_observations')])
    rows = list(store.db.execute('SELECT * FROM runtime_episodes'))
    def context(row):
        request = json.loads(row['request'])
        role = json.loads(row['path'])[-1][0]
        return BindingContext(operation['run_id'], row['episode_id'], role,
            tuple(tuple(pair) for pair in json.loads(row['path'])), plain(template.scope),
            request['message'].get('episode_assignment', {}), request,
            tuple(EpisodeReceipts(store, operation['run_id']).known(row['episode_id'])))
    owner = context(next(row for row in rows if len(json.loads(row['path'])) == 2))
    receiver = context(next(row for row in rows if len(json.loads(row['path'])) == 1))
    source_artifacts = {store.get(args['source_ref'])[name] for name in ('artifact_ref', 'text_ref')}
    expected_display = captured['parent']['literature_rate_source_domain_display']
    store.close()
    denied_calls = []
    def forbidden(*args, **kwargs):
        denied_calls.append('forbidden callable invoked')
        raise AssertionError('Saved reconstruction reacquired, parsed, refit, reinterpreted, or wrote state')
    monkeypatch.setattr('gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_rate_storage.populate_rate_contrast', forbidden)
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection', forbidden)
    reopened = Store.__new__(Store)
    reopened.path = path.resolve(); reopened._savepoint = 0
    reopened.db = sqlite3.connect((path / 'state.sqlite3').as_uri() + '?mode=ro', uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    reopened.db.execute('PRAGMA query_only=ON')
    reopened.db.create_function('library_scope_record', 2, reopened._scope_filter_record)
    original_get = reopened.get_artifact
    def saved_only(ref):
        if ref in source_artifacts:
            forbidden()
        return original_get(ref)
    monkeypatch.setattr(reopened, 'get_artifact', saved_only)
    for method in ('put', 'artifact', 'transaction', 'register_material', 'parse_material'):
        monkeypatch.setattr(reopened, method, forbidden)
    try:
        services = WorkflowServices(SimpleNamespace(store=reopened, run_id=operation['run_id']))
        binding = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[args['source_ref']])
        restored = services.literature_rate_repository()
        assert restored.populate_native(owner, args, operation['operation_key']) == outcome
        assert restored.read(sheet_ref) == saved
        view = restored.source_domain_projection()
        assert view.received_cells(receiver) == returned
        assert view.fact_cells(receiver, [sheet_ref], components=['signed_profile_log_ratio']) == []
        assert binding._native_rate_domain_display_context(receiver)['literature_rate_source_domain_display'] == expected_display
        assert reopened.db.total_changes == 0 and denied_calls == []
        save(tmp_path / 'reconstruction.json', {'query_only': True, 'changes': 0,
            'source_and_text_artifacts_denied': sorted(source_artifacts),
            'reader_and_populator_and_model_denied': True, 'denied_call_attempts': denied_calls,
            'same_original_selection_replayed': True, 'same_original_admitted_subset': True,
            'note': 'saved domain validation recomputes retained rational operand algebra; no source parsing, model interpretation or statistical fit'})
    finally:
        reopened.close()
