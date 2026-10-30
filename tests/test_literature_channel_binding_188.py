"""Synthetic channel custody and requested projection; integration follows binding.

These fixtures are invented source reports, not additional experimental papers.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import asyncio
from functools import partial
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_channel_inputs import read_channel_inputs
from gene_annotation_episode.literature_channel_storage import (
    COMPONENTS, LiteratureChannelRepository, channel_cells_schema,
)
from gene_annotation_episode import literature_channel_render as render
from gene_annotation_episode.state import Store
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, validate_closed_schema, plain
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_channel_prompt import CHANNEL_TASK
from gene_annotation_episode.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK
from gene_annotation_episode.literature_compiled_assay_storage import compiled_assay_cells_schema
from gene_annotation_episode.episode_contract_information import return_contract_information, expand_fact_form
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.tools import ToolRegistry
from test_literature_channel_components_179 import Source


REQUESTED = ['chord_conductance', 'charge_equivalent_rate', 'chord_conductance_variance']
FORM = {'type': 'object', 'properties': {'electrical': channel_cells_schema()},
    'required': ['electrical'], 'additionalProperties': False}


def binding_for(store, context, *, enabled=True):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, channel_population=enabled)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def setup(path, *, source=None, requested=REQUESTED, broad=False, covariance=False):
    source = source or Source()
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(source.content, 'application/xml')
    original = store.put('source', {'provider': 'synthetic_channel_fixture', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'synthetic_v1', 'retrieved_at': None}, origin='caller')['id']
    args = source.args()
    if broad:
        args['literals']['molecule'] = source.witness(source.text)
        args['literals']['current_baseline'] = source.witness('closed-channel baseline')
        for item in args['measurements'].values():
            item['context'] = source.witness(source.text)
    def substitute(value):
        if isinstance(value, dict):
            return {k: substitute(v) for k, v in value.items()}
        if isinstance(value, list):
            return [substitute(v) for v in value]
        return original if value == source.reference else value
    args = substitute(args)
    refs = [original]
    if covariance:
        def read(ref, representation):
            assert ref == original
            return {'artifact_ref': artifact, 'content': source.content}
        extraction = read_channel_inputs(args, read_source=read)
        data = {'version': 'a105_channel_covariance_v1',
            'primitive_order': ['current', 'applied_voltage', 'reversal_voltage'],
            'primitive_measurement_keys': [extraction['measurement_keys'][k] for k in ('current', 'applied_voltage', 'reversal_voltage')],
            'primitive_units': ['pA', 'mV', 'mV'], 'covariance': [[.04, .01, .02], [.01, 1, .5], [.02, .5, 4]],
            'origin': 'synthetic'}
        cov_artifact = store.artifact(canonical(data), 'application/json')
        cov_ref = store.put('source', {'provider': 'synthetic_channel_covariance', 'accession': None,
            'uri': None, 'artifact_ref': cov_artifact, 'text_ref': cov_artifact, 'request_ref': None,
            'version': 'synthetic_v1', 'retrieved_at': None}, origin='caller')['id']
        args.update(covariance_source_ref=cov_ref, variance_status='known',
            variance_witnesses=substitute([source.witness('Known synthetic primitive covariance')]))
        refs.append(cov_ref)
    context = BindingContext('channel-run', 'channel-child', 'literature', (('literature', 'channel-child'),),
        store.validate_scope(), {'version': 'literature_assignment_v1', 'question_context_refs': [],
            'source_refs': refs, 'requested_channel_components': list(requested)}, {}, refs)
    return store, context, args


def test_selected_numerical_sections_preserve_meanings_without_private_operands(tmp_path):
    source = Source(current='1.87654321', voltage='−207.654321', reversal='51.345678', conductance='7.23456789')
    store, context, args = setup(tmp_path, source=source, broad=True)
    with store:
        repo = LiteratureChannelRepository(store, context.run_id)
        assert not repo._installed(repo.operations_table)
        outcome = repo.populate(context, args, 'selected')
        rows = outcome['result']['cells']
        validate_schema(rows, channel_cells_schema())
        assert [r['component'] for r in rows] == REQUESTED
        assert rows[0]['value'] > 0 and rows[1]['unit'] == 'elementary_charge_equivalents_per_s'
        assert rows[2]['unavailable_reason'] == 'primitive_covariance_not_supplied'
        text = json.dumps(rows)
        assert all(token not in text for token in ('1.87654321', '207.654321', '51.345678', '7.23456789'))
        assert all(op['reading'] is None and op['spread_reading'] is None for row in rows for op in row['operands'])
        assert rows[0]['source_meanings']['molecule']['status'] == 'withheld_electrical_operand'
        assert rows[0]['source_meanings']['current_baseline']['witness']['quote'] == 'closed-channel baseline'
        assert rows[0]['operands'][0]['context']['status'] == 'withheld_electrical_operand'
        assert not store.list('observation') and not store.list('assessment')
        ref = outcome['result']['sheet_ref']
        assert repo.read(ref)['sheet']['cells']['current']['value'] == 1.87654321


def test_native_requested_reading_exposes_only_its_own_point_and_preserves_conversion(tmp_path):
    source = Source(current='0.00187654321', current_unit='nA', voltage='−207.654321', reversal='51.345678')
    store, context, args = setup(tmp_path, source=source, requested=['current'], broad=True)
    with store:
        row, = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')['result']['cells']
        assert row['value'] == 1.87654321 and row['origin'] == 'synthetic'
        reading = row['operands'][0]['reading']
        assert reading['native_value'] == .00187654321 and reading['native_unit'] == 'nA'
        assert reading['conversion_origin'] == 'derived'
        assert '207.654321' not in json.dumps(row) and '51.345678' not in json.dumps(row)


def test_reported_spread_is_preserved_only_for_requested_native_quantity(tmp_path):
    source = Source(reversal_spread='1')
    store, context, args = setup(tmp_path, source=source, requested=['reversal_voltage', 'chord_conductance'])
    m = args['measurements']['reversal_voltage']
    selected = source.number('1', container='<td>53 ± 1</td>')
    selected['witness']['source_ref'] = args['source_ref']
    m['spread'] = selected
    m['spread_kind'] = {'value': 'unspecified', 'witnesses': [{**source.witness('Spread meaning unspecified'), 'source_ref': args['source_ref']}]}
    with store:
        rows = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')['result']['cells']
        assert rows[0]['operands'][0]['spread_reading']['native_value'] == 1
        assert rows[0]['operands'][0]['spread_kind']['value'] == 'unspecified'
        assert all(o['spread_reading'] is None for o in rows[1]['operands'])
        assert rows[1]['variance_status'] == 'unknown'


def test_native_cell_does_not_expand_another_unselected_electrical_arrangement(tmp_path):
    source = Source()
    source.text = source.text.replace('</p>', ' NaF was 300 mM.</p>')
    source.content = source.text.encode()
    store, context, args = setup(tmp_path, source=source, requested=['reversal_voltage'])
    def witness(quote):
        return {**source.witness(quote), 'source_ref': args['source_ref']}
    args['measurements']['reversal_voltage']['context'] = witness('An unrelated biionic reversal was 119 mV')
    args['arrangement_relation']['witnesses'].append(witness('An unrelated biionic reversal was 119 mV'))
    args['literals']['ionic_conditions'] = witness('NaF was 300 mM')
    with store:
        row, = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')['result']['cells']
        assert row['value'] == 53 and row['operands'][0]['reading']['native_value'] == 53
        assert row['operands'][0]['context']['status'] == 'withheld_electrical_operand'
        assert row['arrangement_relation']['support'][-1]['status'] == 'withheld_electrical_operand'
        assert '119' not in json.dumps(row)
        assert row['source_meanings']['ionic_conditions']['witness']['quote'] == 'NaF was 300 mM'


def test_known_joint_covariance_populates_conditional_uncertainty_without_changing_scope(tmp_path):
    store, context, args = setup(tmp_path, covariance=True)
    with store:
        repo = LiteratureChannelRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        variance = outcome['result']['cells'][2]
        assert variance['value'] > 0 and variance['variance_status'] == 'known'
        assert variance['covariance_origin'] == 'synthetic'
        assert variance['replication_status'] == 'not_evaluated_by_this_component'
        assert 'first_order_covariance_propagation' in variance['conditional_on']
        assert repo.read(outcome['result']['sheet_ref'])['sheet']['inputs']['covariance'] == [[.04, .01, .02], [.01, 1, .5], [.02, .5, 4]]


@pytest.mark.parametrize('relation,reason', [('different_electrical_arrangements', 'different_electrical_arrangements'),
    ('unknown', 'reversal_condition_applicability_not_supplied')])
def test_incompatible_or_unknown_reversal_keeps_native_measurement_and_blocks_chord(tmp_path, relation, reason):
    source = Source()
    store, context, args = setup(tmp_path, source=source, requested=['reversal_voltage', 'chord_conductance'])
    selected = source.number('119', container='biionic reversal was 119 mV')
    selected['witness']['source_ref'] = args['source_ref']
    args['measurements']['reversal_voltage']['number'] = selected
    args['arrangement_relation'] = {'value': relation, 'witnesses': [] if relation == 'unknown' else [
        {**source.witness('biionic reversal was 119 mV'), 'source_ref': args['source_ref']}]}
    with store:
        rows = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')['result']['cells']
        assert rows[0]['value'] == 119
        assert rows[1]['value'] is None and rows[1]['unavailable_reason'] == reason


def test_genuine_empty_constructor_and_fact_view_do_not_install_state(tmp_path):
    store, context, args = setup(tmp_path, requested=[])
    with store:
        store.db.execute('PRAGMA query_only=ON')
        repo = LiteratureChannelRepository(store, context.run_id)
        assert repo.received_cells(context) == [] and repo.project_cells([], permitted_record_refs=[]) == []
        assert repo.available_sheet_refs(context) == [] and not repo.has_work(context)
        assert not repo._installed(repo.operations_table)
    with Store(tmp_path) as store:
        outcome = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected-empty')
        assert outcome['result']['cells'] == []


def test_parent_receives_only_the_actual_admitted_component_and_no_reference_expansion(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureChannelRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        ref = outcome['result']['sheet_ref']; rows = outcome['result']['cells'][:1]
        parent = replace(context, episode_id='parent', role='annotation', path=(('annotation', 'parent'),),
            assignment={}, received_record_refs=(ref,))
        repo.receive_cells(parent, rows, 'manual_trusted_admission')
        assert repo.received_cells(parent) == rows
        assert repo.fact_cells(parent, [ref], components=COMPONENTS) == rows
        private = outcome['result']['cells'][1:2]
        with pytest.raises(ContractError, match='cell_not_received'):
            repo.validate_fact_values(parent, private)
        with pytest.raises(ContractError, match='component_not_selected'):
            repo.project_cells([ref], permitted_record_refs=[ref], components=['current'])
        owner = replace(context, received_record_refs=(*context.received_record_refs, ref))
        assert repo.fact_cells(owner, [ref], components=COMPONENTS) == outcome['result']['cells']
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_cells([], sheet_refs=[ref], permitted_record_refs=[ref], components=REQUESTED)
        changed = deepcopy(rows); changed[0]['arrangement_relation']['value'] = 'unknown'
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_fact_values(parent, changed)
        with pytest.raises(ContractError, match='not_received'):
            repo.fact_cells(replace(parent, received_record_refs=()), [ref], components=['chord_conductance'])


def test_replay_and_readonly_reconstruction_never_reacquire_or_recalculate(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    repo = LiteratureChannelRepository(store, context.run_id)
    outcome = repo.populate(context, args, 'selected')
    ref = outcome['result']['sheet_ref']; saved = repo.read(ref); rows = outcome['result']['cells'][:1]
    parent = replace(context, episode_id='parent', role='annotation', path=(('annotation', 'parent'),), assignment={}, received_record_refs=(ref,))
    repo.receive_cells(parent, rows, 'manual_trusted_admission')
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); store.close()
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    def forbidden(*_args, **_kwargs):
        raise AssertionError('saved reconstruction must not read, parse, convert or calculate science')
    for module, functions in {
        'literature_channel_storage': ('read_channel_inputs', 'channel_calculation_inputs', 'populate_channel_components'),
        'literature_channel_inputs': ('read_channel_inputs', 'channel_calculation_inputs', '_number', '_read_unit', '_explicit_unit', '_covariance'),
        'literature_channel_calculations': ('populate_channel_components', '_validate', '_fraction'),
        'literature_partner_source_fields': ('read_source_number', 'convert_source_number'),
    }.items():
        for function in functions:
            monkeypatch.setattr(f'gene_annotation_episode.{module}.{function}', forbidden)
    read = Store.__new__(Store); read.path = Path(tmp_path); read._savepoint = 0
    read.db = sqlite3.connect((tmp_path / 'state.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    read.db.row_factory = sqlite3.Row; read.db.execute('PRAGMA query_only=ON')
    with read:
        allowed = {row[field] for row in read.list('source') if row['origin'] == 'tool' for field in ('artifact_ref', 'request_ref')}
        original = read.get_artifact
        def guarded(artifact):
            assert artifact in allowed
            return original(artifact)
        monkeypatch.setattr(read, 'get_artifact', guarded)
        repo = LiteratureChannelRepository(read, context.run_id)
        assert repo.read(ref) == saved and repo.populate(context, args, 'selected') == outcome
        assert repo.received_cells(parent) == rows and repo.fact_cells(parent, [ref], components=COMPONENTS) == rows
        assert read.db.total_changes == 0
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            read.db.execute('DELETE FROM records')
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mutation', ['signature', 'value', 'meaning', 'omission', 'operation', 'unselected_copy'])
def test_selected_operation_and_exact_saved_result_are_required(tmp_path, mutation):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureChannelRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected'); ref = outcome['result']['sheet_ref']
        if mutation == 'signature':
            store.db.execute('UPDATE literature_channel_operations SET signature=\'{}\'')
        elif mutation == 'unselected_copy':
            source = store.get(ref); value = {k: v for k, v in source.items() if k not in ('id', 'origin', 'record_type')}
            value['accession'] = 'synthetic-copy'
            ref = store.put('source', value, origin='tool')['id']
        else:
            changed = deepcopy(outcome)
            if mutation == 'value': changed['result']['cells'][0]['value'] = 900
            elif mutation == 'meaning': changed['result']['cells'][0]['arrangement_relation']['value'] = 'unknown'
            elif mutation == 'omission': changed['result']['cells'].pop()
            else: changed['operation_ref'] = 'operation_' + '0' * 24
            store.db.execute('UPDATE literature_channel_operations SET outcome=?', (canonical(changed),))
        with pytest.raises(ContractError):
            repo.read(ref)


def test_source_scope_and_original_selection_must_still_be_authorized_on_replay(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureChannelRepository(store, context.run_id)
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=()), args, 'selected')
        assert not repo._installed(repo.operations_table)
        outcome = repo.populate(context, args, 'selected')
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=()), args, 'selected')
        changed = deepcopy(args); changed['current_kind'] = {'value': 'unknown', 'witnesses': []}
        with pytest.raises(ContractError, match='reused_for_different_work'):
            repo.populate(context, changed, 'selected')
        with pytest.raises(ContractError, match='request_mismatch'):
            LiteratureChannelRepository(store, 'foreign-run').read(outcome['result']['sheet_ref'])


def test_pure_render_uses_exact_requested_rows_and_no_host_identifiers(tmp_path):
    source = Source(current='1.87654321', voltage='−207.654321', reversal='51.345678')
    store, context, args = setup(tmp_path, source=source, broad=True)
    with store:
        rows = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')['result']['cells']
        parts = []
        def section(target, title, text): target.append(title + '\n' + text)
        def table(headers, items): return '\n'.join(' | '.join(str(v) for v in row) for row in [headers, *items])
        render.render_received(parts, rows + rows, section=section, table=table)
        text = '\n'.join(parts)
        assert 'source_' not in text and 'artifact_' not in text and 'literature_measurement_' not in text
        assert all(token not in text for token in ('1.87654321', '207.654321', '51.345678'))
        assert 'closed-channel baseline' in text and 'not evaluated as independent preparation counts' in text
        assert text.count('chord_conductance |') == 3  # numerical cell, meaning and dependency tables, once each
        assert render.task_relevant({'literature_assignment': {'requested_channel_components': ['chord_conductance']}})
        assert render.task_relevant({'last_local_outcome': {'result': {'view': 'channel_components'}}})
        assert render.task_relevant({'child_reports': [{'numbers': rows}]})
        assert not render.task_relevant({'literature_assignment': {}})


def test_optional_binding_exact_registered_form_and_requested_omission(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        disabled = binding_for(store, context, enabled=False)
        baseline = LiteratureEpisodes(disabled.services, rate_population=True)
        assert disabled.catalog(context) == baseline.catalog(context)
        assert disabled.assignment_schema('literature') == baseline.assignment_schema('literature')
        assert 'literature_channel_cells' not in disabled.fact_sources('literature')
        assert 'channel_population' not in disabled.as_record()['configuration']
        enabled = binding_for(store, context)
        descriptor = enabled.as_record()
        assert LiteratureEpisodes(enabled.services, **descriptor['configuration']).as_record() == descriptor
        assert 'literature.channel.populate' in {r['name'] for r in enabled.catalog(context)}
        validate_closed_schema(FORM)
        weakened = deepcopy(FORM); del weakened['properties']['electrical']['items']['properties']['source_kind']
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(weakened)
        outcome = asyncio.run(enabled.execute(context, 'literature.channel.populate', args, 'binding-selected'))
        assert outcome['status'] == 'completed', outcome
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        form = form_with_facts({}, FORM, enabled.facts(current, {'committed_record_refs': outcome['record_refs']}))
        assert form['electrical'] == outcome['result']['cells']
        enabled.validate_report(current, form, FORM)
        with pytest.raises(ReportBoundaryError, match='subset_mismatch'):
            enabled.validate_report(current, {'electrical': []}, FORM)
        with pytest.raises(ReportBoundaryError, match='unrequested|subset_mismatch'):
            enabled.validate_report(replace(current, assignment={k:v for k,v in current.assignment.items()
                if k != 'requested_channel_components'}), form, FORM)
        # A saved original selected action is known even when the caller's
        # context snapshot predates delivery of that output reference.
        enabled.services.workflow.record_selection = lambda episode: {'run_id': context.run_id,
            'episode_id': episode, 'known_record_refs': list(current.received_record_refs)}
        with pytest.raises(ReportBoundaryError, match='subset_mismatch'):
            enabled.validate_report(context, {'electrical': []}, FORM)


def test_recurring_task_and_scoped_steering_for_own_return_history_lookup_and_parent(tmp_path):
    source = Source(current='1.87654321', voltage='−207.654321', reversal='51.345678')
    store, context, args = setup(tmp_path, source=source, broad=True)
    with store:
        outcome = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')
        rows = outcome['result']['cells']
        marker = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'}}
        states = [
            {**marker, 'literature_assignment': {'requested_channel_components': REQUESTED}},
            {**marker, 'last_local_outcome': outcome},
            {**marker, 'child_reports': [{'electrical': rows}]},
            {**marker, 'current_report_update': {'electrical': rows}},
        ]
        history = {'result': {'view': 'records', 'records': [{
            'selection': {'tool': 'literature.channel.populate', 'arguments': args}, 'outcome': outcome,
            'admitted_report': {'electrical': rows}}]}}
        for state, lookups in [(s, []) for s in states] + [(marker, [outcome]), (marker, [history])]:
            prompt = render_literature_experimental_prompt(state, 'Examine the source experiment.', lookup_results=lookups)
            task, steering = prompt.split('\n\nSTEERING\n')
            assert CHANNEL_TASK in task
            assert all(t not in steering for t in ('1.87654321', '207.654321', '51.345678', 'artifact_', 'source_', 'literature_measurement_'))
            if state != states[0]:
                assert 'closed-channel baseline' in steering
        parent = {**marker, 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'},
            'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': [args['source_ref']]},
            'child_reports': [{'electrical': rows}], 'goal': {'objective': 'Evaluate source evidence for the supplied sequence.'}}
        task, steering = render_literature_experimental_prompt(parent, 'Retain the parent scientific job.').split('\n\nSTEERING\n')
        assert CHANNEL_TASK in task and 'Retain the parent scientific job.' in task
        assert 'Requested electrical numerical sections' in steering and args['source_ref'] not in steering


def test_forwarded_child_outcome_and_history_do_not_expand_the_parent_admitted_subset(tmp_path):
    source = Source(current='1.87654321', voltage='−207.654321', reversal='51.345678')
    store, context, args = setup(tmp_path, source=source, requested=['current', 'chord_conductance'], broad=True)
    with store:
        outcome = LiteratureChannelRepository(store, context.run_id).populate(context, args, 'selected')
        admitted = {'electrical': outcome['result']['cells'][1:]}
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
            'child_reports': [admitted], 'last_local_outcome': outcome}
        history = {'result': {'view': 'records', 'records': [{'outcome': outcome, 'admitted_report': admitted}]}}
        prompt = render_literature_experimental_prompt(state, 'Evaluate the returned evidence.', lookup_results=[history])
        steering = prompt.split('\n\nSTEERING\n')[1]
        assert '1.87654321' not in steering and 'Printed point' not in steering


@pytest.mark.parametrize('source,schema,task,marker', [
    ('literature_channel_cells', channel_cells_schema, CHANNEL_TASK, 'literature_channel_work'),
    ('literature_compiled_assay_cells', compiled_assay_cells_schema, COMPILED_ASSAY_TASK, 'literature_compiled_assay_work'),
])
@pytest.mark.parametrize('profile', [None, CONTRACT_INFORMATION_PROFILE])
def test_recorded_numerical_schema_is_not_the_task_or_model_interpretation_form(source, schema, task, marker, profile):
    original = {'type':'object','properties':{'numbers':schema(),
        'judgment':{'type':'string','enum':['conditional','unresolved']}},
        'required':['numbers','judgment'],'additionalProperties':False}
    facts={source:{'type':'array','meaning':'Requested experimental numerical sections and qualifications.',
        'report_schema':schema()}}
    state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},
        marker:{'version':marker.removesuffix('_work')+'_task_v1'},'requested_form':original,
        'available_report_facts':facts,'goal':{'result_contract':original}}
    if profile is not None:state['contract_information_profile']=profile
    before=deepcopy(state)
    for parent in (False,True):
        value=deepcopy(state)
        if parent:
            value['literature_experimental_work']['aspect']='reference_evidence_parent'
            value['reference_evidence_parent']={'version':'reference_evidence_parent_v1',
                'source_refs':['source_'+'a'*24]}
        text=render_literature_experimental_prompt(value,'Evaluate the assigned reference evidence.')
        task_text=text.split('\n\nSTEERING\n')[0]
        assert task in task_text and 'conditional' in task_text and 'unresolved' in task_text
        assert source in task_text and 'host supplies the saved values' in task_text
        assert 'source_meanings' not in task_text and 'formula_code' not in task_text
        assert 'J*covariance*J_transpose; J=[' not in task_text
        assert 'calibrated_measured_endpoint_per_selected_amount_compiled_v1' not in task_text
        if profile is None:
            assert 'episode-fact:' + source in task_text
    assert state==before and original['properties']['numbers']==schema()
    validate_closed_schema(original)


@pytest.mark.parametrize('source,schema,task', [
    ('literature_channel_cells',channel_cells_schema,CHANNEL_TASK),
    ('literature_compiled_assay_cells',compiled_assay_cells_schema,COMPILED_ASSAY_TASK),
])
def test_requested_profile_fact_contract_keeps_exact_host_type_and_compact_reference(source,schema,task):
    facts={'literature':{source:{'type':'array','meaning':'Requested numerical experimental sections.',
        'report_schema':schema()}}}
    outcome=return_contract_information(facts_by_role=facts,permitted_child_roles=['literature'],
        role='literature',source=source)
    original=deepcopy(outcome)
    state={'literature_experimental_work':{'version':'literature_experimental_task_v1'},
        'contract_information_profile':CONTRACT_INFORMATION_PROFILE}
    text=render_literature_experimental_prompt(state,'Choose the needed experimental return.',lookup_results=[outcome])
    task_text=text.split('\n\nSTEERING\n')[0]
    assert task in task_text and 'episode-fact:'+source in task_text
    assert 'source_meanings' not in task_text and 'formula_code' not in task_text
    assert 'J*covariance*J_transpose; J=[' not in task_text
    submitted={'type':'object','properties':{'chosen':{'$ref':'episode-fact:'+source}},
        'required':['chosen'],'additionalProperties':False}
    expanded=expand_fact_form(json.dumps(submitted),child_role='literature',facts_by_role=facts,permitted_child_roles=['literature'])
    assert expanded['expanded_schema']['properties']['chosen']==schema()
    assert outcome==original
