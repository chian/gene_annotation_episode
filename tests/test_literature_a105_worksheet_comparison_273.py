"""Mechanical composition of already interpreted comparison268 evidence.

No new paper interpretation, new assay, numerical rule or configured-model claim.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from gene_annotation_episode import literature_a105_worksheet as worksheet
from gene_annotation_episode import literature_a105_worksheet_render as renderer
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_measurement_comparison_storage import (
    COMPONENTS, NAMESPACE, REQUESTED, OPERATION, measurement_comparison_cells_schema,
    LiteratureMeasurementComparisonRepository,
)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_a105_worksheet import expand, render_text
from test_literature_measurement_comparison_binding_268 import setup
from test_runtime import FixtureController, ScriptedProvider

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT/'verification/a105_worksheet_comparison_section_273'
RETAINED = ROOT/'verification/a105_measurement_comparison_binding_268/pytest_005/test_selected_shared_loop_retu1'
SELECTED = ['protocol_ratio', 'protocol_difference', 'required_nuisance_equivalent_scenario', 'combined_estimate']


def empty_context():
    return {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}


def comparison_template(components=SELECTED):
    return worksheet.a105_worksheet_template([{'field': 'comparison', 'source': NAMESPACE, 'components': list(components)}])


def retained():
    return json.loads((RETAINED/'ORIGINAL_FORM_268.json').read_text())['numbers']


def test_exact_existing_v2_schema_roster_and_order_without_new_format_version():
    requested = list(reversed(COMPONENTS))
    template = comparison_template(requested)
    assert len(COMPONENTS) == 26
    assert template['submitted_form']['properties']['comparison'] == {'$ref': 'episode-fact:'+NAMESPACE}
    assert expand(template)['properties']['comparison'] == measurement_comparison_cells_schema()
    assert template['assignment_rosters'] == {REQUESTED: requested}
    assert template['section_roles'] == [{'field': 'comparison', 'source': NAMESPACE,
        'components': requested, 'numerical_role': 'measurement_comparison_validity'}]
    assert worksheet.VERSION == 'a105_source_evidence_worksheet_v1'


@pytest.mark.parametrize('other_source,other_field,component', [
    (worksheet.NATIVE, 'native_parameter', 'numerator_parameter'),
    (worksheet.SUMMARY, 'precision', 'source_reported_parameter'),
])
@pytest.mark.parametrize('relation', ['same_reported_parameter', 'same_reported_spread',
    'same_count_report', 'conditional_precision_of_report'])
def test_comparison_cross_format_positives_remain_unsupported_but_unresolved_is_valid(other_source, other_field, component, relation):
    # Distinct retained sources are fixtures for a boundary test, not one experiment.
    existing = json.loads((ROOT/'verification/a105_worksheet_pure_266/RETAINED_JOINT_NUMERICAL_ROWS_001.json').read_text())
    form = {other_field: existing[other_field], 'comparison': retained(), 'assessment_context': empty_context()}
    template = worksheet.a105_worksheet_template([
        {'field': other_field, 'source': other_source, 'components': [r['component'] for r in form[other_field]]},
        {'field': 'comparison', 'source': NAMESPACE, 'components': SELECTED}])
    schema = expand(template)
    link = {'left': {'field': other_field, 'sheet_ref': form[other_field][0]['sheet_ref'],
        'component': component, 'quantity': 'cell_value'}, 'right': {'field': 'comparison',
        'sheet_ref': form['comparison'][0]['sheet_ref'], 'component': 'protocol_ratio', 'quantity': 'cell_value'},
        'relation': 'unresolved', 'support_record_refs': []}
    form['assessment_context']['quantity_links'] = [link]
    validate_form(form, schema, lambda *_: True)
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: pytest.fail('unresolved requires no records'))
    link['relation'] = relation
    with pytest.raises(ContractError, match='a105_worksheet_link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: None)


def test_comparison_empty_partial_and_unrequested_selector_are_distinct():
    template = comparison_template([]); schema = expand(template)
    form = {'comparison': [], 'assessment_context': empty_context()}
    validate_form(form, schema, lambda *_: pytest.fail('no references in empty partial'))
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: pytest.fail('no references'))
    assert schema['properties']['assessment_context']['properties']['quantity_links']['maxItems'] == 0
    template = comparison_template(['protocol_ratio']); schema = expand(template)
    form['comparison'] = retained()[:1]
    selector = {'field': 'comparison', 'sheet_ref': form['comparison'][0]['sheet_ref'],
        'component': 'protocol_ratio', 'quantity': 'reported_spread'}
    form['assessment_context']['quantity_links'] = [{'left': selector, 'right': selector,
        'relation': 'unresolved', 'support_record_refs': []}]
    with pytest.raises(ContractError, match='a105_worksheet_subquantity_not_delivered'):
        worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: None)


def test_renderer_preserves_existing_qualified_comparison_presentation_without_hydration(monkeypatch):
    rows = retained()
    # Explicit presentation sentinels exercise existing fields; these are not scientific facts.
    row = rows[0]
    row['cell']['input_origins'] = ['primary_source', 'synthetic']
    row['model_settings']['optical_nuisance_sign'] = 'opposes_signal'
    row['model_settings']['optical_observation_equation'] = 'presentation_sentinel_equation'
    row['covariance_provenance'] = [{'basis': 'presentation_basis', 'variance_status': 'unknown',
        'origin': 'synthetic', 'systematic_coverage': 'not_established', 'derivation': 'presentation_derivation', 'status': 'unavailable'}]
    monkeypatch.setattr(worksheet, '_schema', lambda *_: pytest.fail('renderer cannot hydrate schemas'))
    form = {'comparison': rows, 'assessment_context': empty_context()}
    actual = render_text(form, {})
    direct = []
    renderer.comparison.render_received(direct, rows,
        section=lambda parts, title, value: parts.extend([title, value]),
        table=lambda headers, values: '\n'.join(' | '.join(map(str, r)) for r in [headers, *values]))
    assert '\n'.join(direct) in actual
    for token in ('primary source', 'synthetic', 'opposes signal', 'presentation sentinel equation',
            'presentation basis', 'sampling unknown', 'Conditional values retain their declared premises'):
        assert token in actual
    for block in row['assertion_context'].values():
        for fragment in block['fragments']:
            assert fragment['text'] in actual
    assert 'Requested comparison limitations' in actual


def test_one_selected_original_source_common_worksheet_and_first_cold(tmp_path):
    store, ctx, args, _, _ = setup(tmp_path/'state', SELECTED, original=True)
    for name in ('molecule', 'functional_assertion'):
        witness = args['selection']['assertion'][name]
        args['return_assertion_context'][name] = [{'start': witness['start'], 'end': witness['end']}]
    template = comparison_template(); literal = expand(template)
    sources = list(ctx.received_record_refs)
    assignment = {**plain(ctx.assignment), **template['assignment_rosters']}
    captured = []
    def work(view):
        return {'selection': {'kind': 'tool', 'tool': OPERATION, 'arguments': args},
            'report_update': {'assessment_context': empty_context()}}
    def integrate(view):
        form, = view['child_reports']; captured.append(deepcopy(form))
        assert [r['component'] for r in form['comparison']] == SELECTED
        worksheet.validate_a105_worksheet_links(form, literal, assignment, read_public_record=store.get)
        prompt = render_literature_experimental_prompt(view, 'Assess the received source comparison and retain its qualifications.')
        (tmp_path/'ORIGINAL_PARENT_PROMPT_273.txt').write_text(prompt)
        assert 'A105 experimental evidence worksheet' in prompt and 'Source comparison scope' in prompt
        commit = {key: [] for key in store.reasoning_schema()['required']}
        witness = args['selection']['quantities']['left']['subject']['molecule']
        artifact = store.get(witness['source_ref'])['artifact_ref']
        commit['source_subjects'] = [{'alias': 'studied_molecule273', 'reference_type': 'assay',
            'source_ref': witness['source_ref'], 'label': witness['quote'], 'anchor': {
                'source_ref': witness['source_ref'], 'artifact_ref': artifact,
                'start': witness['start'], 'end': witness['end'], 'quote': witness['quote']}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
    provider = ScriptedProvider([{'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': assignment, 'goal': 'Compare the already selected source measurements with their qualifications.',
        'scope': plain(ctx.scope), 'purpose': 'Return only requested comparison cells in the common worksheet.',
        'schema_json': json.dumps(template['submitted_form']),
        'initial_report_json': json.dumps({'assessment_context': empty_context()})}, 'report_update': {}}, work, integrate])
    progress = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=progress, binding_definitions={'credit': progress.as_record()}, initial_known_record_refs=sources,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=sources),)))
        assert len(captured) == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_measurement_comparison_operations').fetchone()[0] == 1
        run_id, parent = store.db.execute('SELECT run_id,episode_id FROM literature_measurement_comparison_received ORDER BY rowid DESC LIMIT 1').fetchone()
        original = captured[0]; ref = original['comparison'][0]['sheet_ref']
        repo = LiteratureMeasurementComparisonRepository(store, run_id); saved = repo.read(ref)
        descriptors = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])['episode_bindings']
        assert saved['original_implementation']['bound_descriptor'] == descriptors[0]
        assert original['comparison'][-1]['cell']['value'] is None
        assert original['comparison'][2]['cell']['conditional_value'] is not None
        receiver = replace(ctx, run_id=run_id, episode_id=parent, role='annotation', path=(('annotation', parent),),
            assignment={}, received_record_refs=tuple(repo.cell_record_refs(original['comparison'])))
        for name, value in [('ORIGINAL_FORM_273.json', original), ('ORIGINAL_SCHEMA_273.json', literal),
                ('ORIGINAL_TEMPLATE_273.json', template), ('ORIGINAL_ASSIGNMENT_273.json', assignment),
                ('ORIGINAL_SHEET_273.json', saved), ('ORIGINAL_DESCRIPTOR_273.json', descriptors),
                ('ORIGINAL_RECEIVER_273.json', receiver.as_record()),
                ('ORIGINAL_ARTIFACTS_273.json', sorted(store.get(ref)[k] for k in ('artifact_ref', 'request_ref')))]:
            (tmp_path/name).write_text(json.dumps(value, indent=2)+'\n')
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
        completed = subprocess.run([sys.executable, '-B', str(PACKET/'first_cold_process_001.py'), str(tmp_path)],
            cwd=ROOT, text=True, capture_output=True)
        (tmp_path/'FIRST_COLD_STDOUT_273.txt').write_text(completed.stdout)
        (tmp_path/'FIRST_COLD_STDERR_273.txt').write_text(completed.stderr)
        assert completed.returncode == 0, completed.stderr
        probe = json.loads((tmp_path/'FIRST_COLD_PROOF_273.json').read_text())
        assert probe['fresh_process'] and probe['state_byte_hashes_unchanged']
        assert probe['only_original_two_receipt_artifacts_read'] and probe['sqlite_changes'] == 0
    finally:
        store.close()
