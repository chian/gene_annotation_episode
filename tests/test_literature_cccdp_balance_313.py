"""Original CcCdP Figure 2D workbook through selected A105 typed return."""
import asyncio
from copy import deepcopy
from functools import partial
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template, VERSION
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, EXPERIMENTAL_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.literature_stoichiometric_balance_inputs import (
    VERSION as INPUT_VERSION, read_stoichiometric_balance_inputs)
from gene_annotation_episode.literature_stoichiometric_balance_calculations import (
    COMPONENTS, populate_stoichiometric_balance_components)
from gene_annotation_episode.literature_stoichiometric_balance_prompt import STOICHIOMETRIC_BALANCE_TASK
from gene_annotation_episode.literature_stoichiometric_balance_storage import (
    LiteratureStoichiometricBalanceRepository, NAMESPACE)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'verification/a105_cccdp_mass_balance_312/source/Open_data_Fig2.xlsx'
ARTICLE = ROOT/'verification/a105_cccdp_mass_balance_312/source/article.html'
PIN = '7d5fbe5b3eb18aa18417bcd8f151951e021e7619f306c1dd11b6e508b3e972af'
TEMPLATE = a105_worksheet_template([{'field': 'balance', 'source': NAMESPACE,
                                     'components': list(COMPONENTS)}])
FORM = TEMPLATE['submitted_form']
EMPTY = {'version': VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}


def _selection(source_ref, **changes):
    return {'version': INPUT_VERSION, 'source_ref': source_ref, 'expected_sha256': PIN,
        'sheet_name': 'Data', 'panel': 'D', 'row_number': 61, 'time_minutes': 90, **changes}


def _change_cell(raw, sheet, address, *, value=None, inline=None):
    output = BytesIO()
    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(BytesIO(raw)) as source, zipfile.ZipFile(output, 'w') as target:
        for member in source.infolist():
            content = source.read(member.filename)
            if member.filename == 'xl/worksheets/' + sheet:
                root = ET.fromstring(content)
                cell = root.find(f'.//{{{main}}}c[@r="{address}"]')
                assert cell is not None
                for child in list(cell):
                    cell.remove(child)
                if inline is not None:
                    cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, f'{{{main}}}is'), f'{{{main}}}t').text = inline
                elif value is not None:
                    cell.set('t', 'n')
                    ET.SubElement(cell, f'{{{main}}}v').text = value
                content = ET.tostring(root)
            target.writestr(member, content)
    return output.getvalue()


def _source(store, raw, *, provider, accession, media):
    artifact = store.artifact(raw, media)
    source = store.put('source', {'provider': provider, 'accession': accession, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None, 'parent_source_refs': []}, origin='caller')['id']
    return source, artifact


def test_original_workbook_cells_balances_and_source_guards():
    raw = SOURCE.read_bytes()
    assert sha256(raw).hexdigest() == PIN
    extraction = read_stoichiometric_balance_inputs(_selection('source_test'), raw)
    assert extraction['sheet_key'] == 'rId2'
    assert extraction['values']['g2_initial']['address'] == 'B52'
    assert extraction['values']['g2_initial']['exact_decimal'] == '25'
    assert extraction['values']['pi']['address'] == 'N61'
    assert extraction['values']['pi_sd']['address'] == 'O61'
    assert extraction['conditions']['aGlc1-P']['value']['exact_decimal'] == '100'
    assert extraction['model_premise']['source_cell'] == 'Metadata!A29'
    assert extraction['initial_product_and_pi_entries']['pi']['address'] == 'N52'
    sheet = populate_stoichiometric_balance_components(extraction)
    cells = sheet['cells']
    expected = {'g2_loss': '21.9532159999999998',
        'soluble_product_molecules': '17.8841310000000005',
        'acceptor_balance_remainder': '4.0690849999999993',
        'soluble_added_glucosyl_equivalents': '37.8466430000000008',
        'glucosyl_balance_remainder': '5.4447800000000012',
        'nominal_donor_to_soluble_yield': '0.378466430000000008'}
    for component, value in expected.items():
        assert cells[component]['exact_decimal'] == value
    assert cells['acceptor_accounting_ratio']['value'] == pytest.approx(.8146474302443888)
    assert cells['soluble_glucosyl_accounting_ratio']['value'] == pytest.approx(.8742295904664533)
    assert cells['g2_initial']['origin'] == 'source_time_zero_nominal_matching'
    assert 'not established' in cells['g2_initial']['meaning']
    assert 'inferred' in cells['glucosyl_balance_remainder']['meaning']
    assert sheet['ratio_sd'] is sheet['joint_covariance'] is sheet['matched_no_enzyme_arm'] is None
    assert sheet['assay_validity_multiplier'] is sheet['annotation_credit'] is None
    assert cells['soluble_glucosyl_accounting_ratio']['input_measurement_keys'][0] == cells['soluble_added_glucosyl_equivalents']['input_measurement_keys'][0]
    with pytest.raises(ContractError, match='stoichiometric_balance_workbook_hash_mismatch'):
        read_stoichiometric_balance_inputs(_selection('source_test', expected_sha256='0'*64), raw)
    with pytest.raises(ContractError):
        read_stoichiometric_balance_inputs(_selection('source_test', panel='C'), raw)
    with pytest.raises(ContractError, match='stoichiometric_balance_selected_time_mismatch'):
        read_stoichiometric_balance_inputs(_selection('source_test', time_minutes=60), raw)
    with pytest.raises(ContractError, match='stoichiometric_balance_outside_calibration_range'):
        read_stoichiometric_balance_inputs(_selection('source_test', row_number=62, time_minutes=120), raw)
    below = _change_cell(raw, 'sheet2.xml', 'J61', value='0.5')
    with pytest.raises(ContractError, match='stoichiometric_balance_outside_calibration_range'):
        read_stoichiometric_balance_inputs(_selection('source_test', expected_sha256=sha256(below).hexdigest()), below)
    missing = _change_cell(raw, 'sheet2.xml', 'D61')
    with pytest.raises(ContractError, match='stoichiometric_balance_literal_numeric_cell_required'):
        read_stoichiometric_balance_inputs(_selection('source_test', expected_sha256=sha256(missing).hexdigest()), missing)
    nonzero_initial = _change_cell(raw, 'sheet2.xml', 'D52', value='1')
    with pytest.raises(ContractError, match='stoichiometric_balance_nonzero_initial_product_or_pi'):
        read_stoichiometric_balance_inputs(_selection('source_test', expected_sha256=sha256(nonzero_initial).hexdigest()), nonzero_initial)
    wrong_range = _change_cell(raw, 'sheet1.xml', 'A22', inline='Calibration: G2 (2.5–50 mM), G3/G4 (2.5–15 mM), G5 (1.0–7.5 mM), G6 (1.0–25 mM).')
    with pytest.raises(ContractError, match='stoichiometric_balance_calibration_source_missing'):
        read_stoichiometric_balance_inputs(_selection('source_test', expected_sha256=sha256(wrong_range).hexdigest()), wrong_range)


def test_selected_episode_typed_return_and_cold_projection(tmp_path, monkeypatch):
    raw = SOURCE.read_bytes()
    path = tmp_path/'state'
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    source_ref, source_artifact = _source(store, raw, provider='author_figure2_workbook',
        accession='10.5281/zenodo.4555807', media='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    article = ARTICLE.read_bytes()
    assert sha256(article).hexdigest() == 'bed5ff3b157dae8567f9d810fe292fa573a3bf54ebcd9a819a259686362f03a6'
    article_ref, article_artifact = _source(store, article, provider='original_article_html',
        accession='10.1186/s13068-021-01982-2', media='text/html')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [source_ref, article_ref], **TEMPLATE['assignment_rosters']}
    def commission(role, selected_assignment):
        return {'selection': {'kind': 'episode_child', 'role': role,
            'assignment': selected_assignment,
            'goal': 'Evaluate CcCdP Figure 2D soluble-product and phosphate balance',
            'scope': store.validate_scope(),
            'purpose': 'Return requested source-bound A105 numerical balance section',
            'schema_json': json.dumps(FORM),
            'initial_report_json': json.dumps({'assessment_context': EMPTY})},
            'report_update': {'assessment_context': EMPTY}}
    empty_commit = {key: [] for key in store.reasoning_schema()['required']}
    label = 'cellodextrin phosphorylase'
    start = article.index(label.encode())
    empty_commit['source_subjects'] = [{'alias': 'assayed_cccdp', 'reference_type': 'assay',
        'source_ref': article_ref, 'label': label,
        'anchor': {'source_ref': article_ref, 'artifact_ref': article_artifact,
                   'start': start, 'end': start+len(label), 'quote': label}}]
    class Provider:
        def __init__(self):
            self.calls = {}; self.prompts = []; self.contexts = []
        async def complete(self, episode_id, role, instructions, context, output_schema):
            assert role == 'REASONING'
            self.contexts.append(deepcopy(context)); self.prompts.append((deepcopy(context), instructions))
            index = self.calls.get(episode_id, 0); self.calls[episode_id] = index+1
            if 'reference_evidence_parent' in context:
                if index == 0:
                    return commission('literature', assignment)
                if context['child_reports']:
                    assert len(context['child_reports'][0]['balance']) == len(COMPONENTS)
                    return {'selection': {'kind': 'reason', 'commit': empty_commit},
                            'report_update': {'assessment_context': EMPTY}}
                if not context['pending_work']['items']:
                    raise AssertionError('closed_child_without_report')
                pending, = context['pending_work']['items']
                return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
                    'events': [{'handle': pending['handle'], 'event': 'returned', 'after_cursor': 0}],
                    'reconsider_at': None}}, 'report_update': {'assessment_context': EMPTY}}
            if index == 0:
                return {'selection': {'kind': 'tool', 'tool': 'literature.stoichiometric_balance.populate',
                    'arguments': _selection(source_ref)}, 'report_update': {'assessment_context': EMPTY}}
            return {'selection': {'kind': 'reason', 'commit': empty_commit},
                    'report_update': {'assessment_context': EMPTY}}
        async def release(self, episode_id):
            pass
    provider = Provider()
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path/'run', controller_factory=lambda p, initial: FixtureController(str(p), initial, 2),
            project_credit=scorer, initial_known_record_refs=[source_ref, article_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                stoichiometric_balance_population=True, reference_parent_sources=[source_ref]),),
            binding_definitions={'credit': scorer.as_record()}))
        child_prompts = [render_literature_experimental_prompt(c, i) for c, i in provider.prompts
                         if 'literature_assignment' in c]
        assert child_prompts and all(p.startswith('TASK\n\n') and STOICHIOMETRIC_BALANCE_TASK in p
            and EXPERIMENTAL_TASK in p for p in child_prompts)
        parent_prompts = [render_literature_experimental_prompt(c, i) for c, i in provider.prompts
                          if c.get('child_reports')]
        assert parent_prompts and any(p.startswith('TASK\n\n'+REFERENCE_PARENT_TASK)
            and 'Requested soluble-product balance numerical components' in p
            and 'inferred remainder, not measured insoluble product' in p
            and all(component in p for component in COMPONENTS) for p in parent_prompts)
        operation = store.db.execute('SELECT run_id,outcome FROM literature_stoichiometric_balance_operations').fetchone()
        assert operation is not None
        run_id = operation['run_id']; sheet_ref = json.loads(operation['outcome'])['result']['sheet_ref']
        repo = LiteratureStoichiometricBalanceRepository(store, run_id)
        saved = repo.read(sheet_ref)
        assert saved['extraction']['values']['pi']['address'] == 'N61'
        delivered = json.loads(store.db.execute('SELECT cells FROM literature_stoichiometric_balance_received').fetchone()['cells'])
        assert delivered == repo.project_cells([sheet_ref], permitted_record_refs=[sheet_ref], components=COMPONENTS)
        assert delivered[0]['reaction_conditions'] == {
            'nominal_donor_mM': 100.0, 'nominal_acceptor_mM': 25.0,
            'enzyme_U_per_mL': 1.0, 'MES_mM': 50.0,
            'pH': 7.0, 'temperature_C': 45.0}
        assert all(r['assay_validity_multiplier'] is None for r in delivered)
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE action LIKE '%literature.stoichiometric_balance.populate%'").fetchone()[0] == 1
        before = list(store.db.iterdump())
    finally:
        store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError('cold projection must use saved records only')
    monkeypatch.setattr('gene_annotation_episode.literature_stoichiometric_balance_storage.read_stoichiometric_balance_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_stoichiometric_balance_storage.populate_stoichiometric_balance_components', forbidden)
    with Store(path) as reopened:
        original_get = reopened.get_artifact
        monkeypatch.setattr(reopened, 'get_artifact', lambda ref: forbidden() if ref == source_artifact else original_get(ref))
        reopened.db.execute('PRAGMA query_only=ON')
        cold = LiteratureStoichiometricBalanceRepository(reopened, run_id)
        assert cold.read(sheet_ref) == saved
        assert cold.project_cells([sheet_ref], permitted_record_refs=[sheet_ref], components=COMPONENTS) == delivered
        assert list(reopened.db.iterdump()) == before
