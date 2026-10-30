"""Original Bcd/Etf source units through ordinary controlled literature returns.

Scientific conversion/reset: primary_bcd_partner_018. The providers/controllers
are fixtures; primary numerical source bytes are actual retained PMC HTML/text.
No new model-backed scientific interpretation or complete matched effect is claimed.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_partner_calculations import COMPONENTS
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE / 'primary_partner_matched_017_research'
FORM = obj({'measurements': partner_cells_schema()})
CASES = ('nadh', 'h2')


def setup_case(path, *, case):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    html = (PRIMARY / 'PRIMARY_PMC_001.html').read_bytes()
    raw = (PRIMARY / 'PRIMARY_ARTICLE_TEXT_001.txt').read_bytes()
    original = store.artifact(html, 'text/html')
    text = store.artifact(raw, 'text/plain')
    paper = store.put('source', {'provider': 'retained_primary_pmc_html',
        'accession': 'PMC2223550', 'uri': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/',
        'artifact_ref': original, 'text_ref': text, 'request_ref': None,
        'version': 'retained_html_with_deterministic_text_projection',
        'retrieved_at': None, 'parent_source_refs': []}, origin='caller')

    def witness(quote, *, after=0):
        start = raw.index(quote.encode(), after)
        return {'source_ref': paper['id'], 'representation': 'text',
            'start': start, 'end': start + len(quote.encode()), 'quote': quote}

    def number(selected, token):
        start = selected['quote'].index(token)
        return {'witness': deepcopy(selected), 'number_start': start, 'number_end': start+len(token)}

    table = raw.index(b'TABLE 2.')
    caption = 'Crotonyl-CoA-dependent NADH oxidation and ferredoxin reduction catalyzed by purified butyryl-CoA dehydrogenase/Etf complex from C. kluyveri'
    subject = witness('butyryl-CoA dehydrogenase/Etf complex', after=table)
    partner = witness('Ferredoxin from Clostridium pasteurianum')
    if case == 'nadh':
        endpoint_text = 'NADH oxidation (measured photometrically)'
        entity = 'NADH'
        rows = {'reference': ('Fd + Hyd\n7 (14)a', '7'), 'omitted': ('Hyd\n0.1', '0.1')}
        mass = '0.01 mg purified butyryl-CoA dehydrogenase/Etf complex'
        protocol = ('For NADH oxidation each 1-ml assay mixture incubated at 25°C contained '
            '50 mM Tris-HCl (pH 7.5), 0.1 mM NADH, 0.1 mM crotonyl-CoA, 5 μM FAD, '
            '2 mM DTT, 0.01 mg purified butyryl-CoA dehydrogenase/Etf complex, and, '
            'where indicated, 20 μM ferredoxin (Fd), 0.4 U hydrogenase (Hyd) from '
            'C. pasteurianum, and/or 1 mM methyl viologen.')
        clause_text = '1 μmol of NADH oxidized per min'
    else:
        assert case == 'h2'
        endpoint_text = 'Ferredoxin reduction (measured via H2 formation in the presence of hydrogenase)'
        entity = 'H2'
        rows = {'reference': ('Fd + Hyd\n5', '5'), 'omitted': ('Hyd\n<0.01', '0.01')}
        mass = '0.05 mg purified butyryl-CoA dehydrogenase/Etf complex'
        protocol = ('For ferredoxin reduction each 0.5-ml assay mixture incubated at 37°C contained '
            '50 mM Tris-HCl (pH 7.5), 2 mM DTT, 2.5 mM NADH, 1 mM crotonyl-CoA, '
            '10 μM FAD, 0.05 mg purified butyryl-CoA dehydrogenase/Etf complex, '
            'and, where indicated, 50 μM ferredoxin, 1.6 U hydrogenase from '
            'C. pasteurianum, and/or 1 mM methyl viologen.')
        clause_text = '1 μmol of H2 formed per min'
    endpoint = witness(endpoint_text, after=table)
    endpoint_start = endpoint['start']
    bridge_text = ('One unit was equivalent to 1 μmol of NADH oxidized per min, '
        '1 μmol of TTC reduced per min, or 1 μmol of H2 formed per min.')
    bridge = witness(bridge_text, after=table)
    clause = witness(clause_text, after=bridge['start'])
    defined = {'kind': 'source_defined_rate_unit', 'witness': witness('U/mg', after=table),
        'definition': {'bridge': bridge, 'clause': clause, 'amount': number(clause, '1'),
            'amount_unit': witness('μmol', after=clause['start']),
            'time_unit': witness('min', after=clause['start']),
            'endpoint': deepcopy(endpoint),
            'endpoint_entity': witness(entity, after=endpoint_start),
            'definition_entity': witness(entity, after=clause['start'])}}
    protocol_witness = witness(protocol, after=table)
    normalization = witness(mass, after=protocol_witness['start'])
    conditions = {'coverage': 'partial', 'factors': [
        {'factor': 'reported_nonpartner_protocol',
         'level': {'kind': 'literal', 'witness': protocol_witness}}]}
    arms = {}
    row_witnesses = []
    for role, (row_text, token) in rows.items():
        selected = witness(row_text, after=endpoint_start)
        row_witnesses.append(selected)
        arms[role] = {'subject': deepcopy(subject), 'partner': deepcopy(partner),
            'endpoint': deepcopy(endpoint), 'normalization': deepcopy(normalization),
            'partner_state': 'present' if role == 'reference' else 'absent',
            'conditions': deepcopy(conditions), 'measurement_identity': None,
            'origin': 'reported', 'rate': {'value': number(selected, token),
                'unit': deepcopy(defined), 'spread': {'kind': 'unreported',
                    'magnitude': None, 'unit': None, 'witnesses': []}}}
    arms['addback'] = None
    fields = ('subject', 'partner', 'experiment', 'endpoint', 'normalization',
        'reference_condition', 'omitted_condition', 'addback_condition', 'function')
    literals = dict.fromkeys(fields)
    literals.update(subject=subject, partner=partner, experiment=witness(caption, after=table),
        endpoint=endpoint, normalization=normalization,
        reference_condition=witness('Fd + Hyd', after=row_witnesses[0]['start']),
        omitted_condition=witness('Hyd', after=row_witnesses[1]['start']),
        function=witness(caption, after=table))
    args = {'source_ref': paper['id'], 'data_source_ref': paper['id'],
        'source_kind': 'primary_source', 'input_mode': 'native_source_spans',
        'literals': literals, 'interpretation_witnesses': [protocol_witness, bridge], 'arms': arms}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [paper['id']], 'requested_partner_components': list(COMPONENTS)}
    context = BindingContext('defined-partner-run', 'defined-partner-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, (paper['id'],))
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def check_rows(rows, case):
    assert [row['component'] for row in rows] == list(COMPONENTS)
    assert rows[0]['value'] == (7_000_000 if case == 'nadh' else 5_000_000)
    if case == 'nadh':
        assert rows[1]['value'] == 100_000
    else:
        assert rows[1]['value'] is None
        assert (rows[1]['lower'], rows[1]['upper']) == (0, 10_000)
    assert all(row['value'] is None for row in rows[2:])
    assert all(row['statistical_uncertainty'] == 'not_evaluated' for row in rows)
    assert all(row['partner_necessity'] == 'not_inferred' for row in rows)
    assert rows[0]['arm_metadata']['reference']['spread'] == {'kind': 'unreported', 'magnitude': None}
    assert rows[0]['arm_metadata']['reference']['condition_coverage'] == 'partial'


@pytest.mark.parametrize('case', CASES)
def test_primary_defined_units_are_selected_and_saved_without_a_numeric_recipe(tmp_path, case):
    store, context, args = setup_case(tmp_path, case=case)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'defined-primary')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['version'] == 'literature_partner_inputs_extraction_v3'
        parsed = saved['extraction']['native_evidence']['reference']['rate']['unit']
        assert parsed['raw_unit'] == 'U/mg' and parsed['multiplier'] == 1_000_000
        assert parsed['definition']['amount']['raw_number'] == '1'
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        check_rows(rows, case)
        if case == 'h2':
            assert saved['extraction']['native_evidence']['omitted']['rate']['value']['relation'] == 'lt'
        assert not store.list('observation') and not store.list('assessment')


@pytest.mark.parametrize('case', CASES)
def test_primary_defined_units_reach_the_actual_ordinary_parent_form(tmp_path, case):
    store, context, args = setup_case(tmp_path / 'state', case=case)
    with store:
        received = []
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the reported ferredoxin-omission endpoint',
            'scope': plain(context.scope), 'purpose': 'Return requested native components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.partner.source.populate',
            'arguments': args}, 'report_update': {}}

        def receive(inputs):
            form, = inputs['child_reports']
            check_rows(form['measurements'], case)
            received.append(form)
            commit = {key: [] for key in store.reasoning_schema()['required']}
            selected = deepcopy(args['literals']['subject'])
            selected.pop('representation')
            selected['artifact_ref'] = store.get(args['source_ref'])['text_ref']
            commit['source_subjects'] = [{'alias': 'assayed_complex', 'reference_type': 'assay',
                'source_ref': args['source_ref'], 'label': selected['quote'], 'anchor': selected}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, action, receive]), run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path)==1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and summary['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_partner_received').fetchone()[0] == 1
        admitted, = store.db.execute('SELECT cells FROM literature_partner_received').fetchall()
        assert json.loads(admitted[0]) == received[0]['measurements']
