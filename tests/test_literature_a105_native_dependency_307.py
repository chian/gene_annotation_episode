"""One A105 worksheet links reused Pa0142 source estimates across contrasts.

The primary PDF/SI and its geometry-checked transcription are owned by the
earlier original-source case. These checks add a dependent-sheet meaning; they
do not count another experiment or calculate annotation credit.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_contract_information import expand_fact_form
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import (
    NATIVE, VERSION, VERSION_V2, QUANTITY_RELATIONS, QUANTITY_RELATIONS_V2,
    a105_worksheet_template, validate_a105_worksheet_links,
)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, kinetic_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_literature_pa0142_kinetic_original_303 import (
    _transcription, _source, _selection, _reason, Spans,
)


REQUESTED = ['numerator_parameter', 'denominator_parameter', 'parameter_ratio', 'log_parameter_contrast']
TEMPLATE = a105_worksheet_template(
    [{'field': 'kinetics', 'source': NATIVE, 'components': REQUESTED}], worksheet_version=VERSION_V2)
FORM = TEMPLATE['submitted_form']
EMPTY = {'version': VERSION_V2, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}


def _expanded():
    facts = {NATIVE: {'type': 'array', 'meaning': 'Selected source kinetic cells.',
        'report_schema': kinetic_cells_schema()}}
    return expand_fact_form(json.dumps(FORM), child_role='experimental',
        facts_by_role={'experimental': facts}, permitted_child_roles=['experimental'])['expanded_schema']


def _link(rows):
    numerators = [row for row in rows if row['component'] == 'numerator_parameter']
    assert len(numerators) == 2 and numerators[0]['sheet_ref'] != numerators[1]['sheet_ref']
    first, second = numerators
    metadata = first['numerator']
    return {'left': {'field': 'kinetics', 'sheet_ref': first['sheet_ref'],
            'component': 'numerator_parameter', 'quantity': 'cell_value'},
        'right': {'field': 'kinetics', 'sheet_ref': second['sheet_ref'],
            'component': 'numerator_parameter', 'quantity': 'cell_value'},
        'relation': 'same_physical_measurement',
        'support_record_refs': [metadata['physical_observation_ref'], metadata['measurement_ref']]}


def test_v1_schema_remains_original_and_v2_requires_explicit_selection():
    request = [{'field': 'kinetics', 'source': NATIVE, 'components': REQUESTED}]
    old = a105_worksheet_template(request)['submitted_form']['properties']['assessment_context']
    new = TEMPLATE['submitted_form']['properties']['assessment_context']
    assert old['properties']['version']['const'] == VERSION
    assert old['properties']['quantity_links']['items']['properties']['relation']['enum'] == list(QUANTITY_RELATIONS)
    assert 'same_physical_measurement' not in QUANTITY_RELATIONS
    assert new['properties']['version']['const'] == VERSION_V2
    assert new['properties']['quantity_links']['items']['properties']['relation']['enum'] == list(QUANTITY_RELATIONS_V2)


def test_pa0142_reused_numerator_links_in_selected_return_and_cold_read(tmp_path, monkeypatch):
    pdf, si, xml, transcription = _transcription()
    path = tmp_path / 'state'
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    pdf_ref = _source(store, 'author_pdf', pdf)
    si_ref = _source(store, 'author_si_pdf', si, (pdf_ref,))
    xml_ref = _source(store, 'pdf_glyph_geometry', xml, (pdf_ref,))
    source_ref = _source(store, 'geometry_checked_transcription', transcription, (pdf_ref, si_ref, xml_ref))
    spans = Spans(transcription, source_ref)
    captured = []
    def commission(role, assignment):
        return {'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment,
            'goal': 'Evaluate Pa0142 8-oxoG efficiency against guanine and isocytosine',
            'scope': store.validate_scope(), 'purpose': 'Return two source kinetic contrasts with shared measurement dependence',
            'schema_json': json.dumps(FORM), 'initial_report_json': json.dumps({'assessment_context': EMPTY})},
            'report_update': {'assessment_context': EMPTY}}
    def receive(inputs):
        form, = inputs['child_reports']
        rows = form['kinetics']
        assert len(rows) == 2 * len(REQUESTED)
        context = {**EMPTY, 'quantity_links': [_link(rows)]}
        assert context['quantity_links'][0]['support_record_refs'][0] is not None
        captured.append(deepcopy({'kinetics': rows, 'assessment_context': context}))
        decision = _reason(store, source_ref)
        decision['report_update'] = {'assessment_context': context}
        return decision
    strategy = {'version': 'strategy_assignment_v1', 'question_context_refs': [],
        'prior_search_refs': [source_ref], **TEMPLATE['assignment_rosters']}
    literature = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [source_ref], **TEMPLATE['assignment_rosters']}
    provider = ScriptedProvider([
        commission('literature', literature), commission('literature_strategy', strategy),
        {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
            'arguments': _selection(spans, 'guanine')}, 'report_update': {'assessment_context': EMPTY}},
        {'selection': {'kind': 'tool', 'tool': 'literature.kinetic.populate',
            'arguments': _selection(spans, 'isocytosine')}, 'report_update': {'assessment_context': EMPTY}},
        receive, receive])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path/'run', controller_factory=lambda p, initial: FixtureController(str(p), initial, 2),
            project_credit=scorer, initial_known_record_refs=[source_ref, xml_ref, si_ref, pdf_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[source_ref]),), binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and captured[0] == captured[1]
        assert len(provider.contexts) == 6
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 6
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
        assert len(store.db.execute('SELECT * FROM literature_kinetic_operations').fetchall()) == 2
        schema = _expanded()
        assignment = TEMPLATE['assignment_rosters']
        validate_a105_worksheet_links(captured[1], schema, assignment, read_public_record=store.get)
        rows = captured[1]['kinetics']
        link = captured[1]['assessment_context']['quantity_links'][0]
        assert link['support_record_refs'][0] == next(r for r in rows if r['sheet_ref'] == link['right']['sheet_ref']
            and r['component'] == 'numerator_parameter')['numerator']['physical_observation_ref']
        assert sorted(r['value'] for r in rows if r['component'] == 'parameter_ratio') == pytest.approx(
            sorted([200/13, 100/11]))
        # Equal numerical values from distinct physical observations do not
        # supply a reusable estimate. The same physical ID cannot carry a
        # conflicting numerical estimate, either.
        for mutation in ('distinct_physical_identity', 'conflicting_estimate', 'different_source_token', 'missing_support'):
            invalid = deepcopy(captured[1])
            pair = [r for r in invalid['kinetics'] if r['component'] == 'numerator_parameter']
            if mutation == 'distinct_physical_identity':
                pair[1]['numerator']['physical_observation_ref'] = next(r for r in invalid['kinetics']
                    if r['sheet_ref'] == pair[1]['sheet_ref'] and r['component'] == 'denominator_parameter')['denominator']['physical_observation_ref']
            elif mutation == 'conflicting_estimate':
                pair[1]['value'] = 1.3
            elif mutation == 'different_source_token':
                pair[1]['numerator']['measurement_ref'] = next(r for r in invalid['kinetics']
                    if r['sheet_ref'] == pair[1]['sheet_ref'] and r['component'] == 'denominator_parameter')['denominator']['measurement_ref']
            else:
                invalid['assessment_context']['quantity_links'][0]['support_record_refs'] = []
            with pytest.raises(ContractError, match='a105_worksheet_link_not_supported'):
                validate_a105_worksheet_links(invalid, schema, assignment, read_public_record=store.get)
        before = list(store.db.iterdump())
        run_id = store.db.execute('SELECT run_id FROM literature_kinetic_operations LIMIT 1').fetchone()[0]
        refs = [row['sheet_ref'] for row in rows if row['component'] == 'numerator_parameter']
        saved = [LiteratureKineticRepository(store, run_id).read(ref) for ref in refs]
        source_artifacts = {store.get(ref)['artifact_ref'] for ref in (pdf_ref, si_ref, xml_ref, source_ref)}
    finally:
        store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError('cold reconstruction cannot reacquire or recalculate')
    monkeypatch.setattr('gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast', forbidden)
    with Store(path) as reopened:
        original_get = reopened.get_artifact
        monkeypatch.setattr(reopened, 'get_artifact',
            lambda ref: forbidden() if ref in source_artifacts else original_get(ref))
        reopened.db.execute('PRAGMA query_only=ON')
        repo = LiteratureKineticRepository(reopened, run_id)
        assert [repo.read(ref) for ref in refs] == saved
        cold_rows = repo.project_cells(refs, permitted_record_refs=refs, components=REQUESTED)
        cold = {'kinetics': cold_rows, 'assessment_context': captured[1]['assessment_context']}
        validate_a105_worksheet_links(cold, schema, assignment, read_public_record=reopened.get)
        assert list(reopened.db.iterdump()) == before
