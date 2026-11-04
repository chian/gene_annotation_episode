"""Synthetic partner interpretation instructions and ordinary transport.

These tests check supplied meanings, deterministic components and presentation.
Controlled responses do not demonstrate scientific interpretation by a model.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from method_loop.durable import DurableExecutionError
from gene_annotation_episode.composition_information import CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_contract_information import operation_contract_information
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.decision_context import state_frame
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_partner_native_storage import fixture, witness
from test_runtime import FixtureController, ScriptedProvider


FORM = obj({'selected_components': partner_cells_schema()})
RECORDS = (Path(__file__).resolve().parents[1] /
    'verification/literature_reference_evidence_2026-10-25_001/a105_partner_interpretation_task_160')


def assert_partner_instructions(task):
    assert task.count(PARTNER_TASK) == 1
    for meaning in (
        'source-backed nonpartner condition factors',
        'nonempty selected factor set with known levels',
        'do not invent factors or assume that unreported attributes match',
        'presence or absence is not penalized as a nonpartner difference',
        'Retain known selected factors under partial coverage',
        'use unreported only when no factors are selected',
        'does not establish that the publication omitted those conditions',
        'conditional on this supplied scope', 'global validity or purity proof',
        'actual measured molecular species and endpoint',
        'primary reaction participant or carrier',
        'enzyme that generates a reporter or coupled signal',
        'neither physiological partner necessity nor isolated intrinsic activity',
        'source organism, expression host and accessory-component source distinct',
        'Equal units or a shared paper do not establish',
        'reused reference is shared evidence, not an independent experiment',
        'missing addback remains unknown',
    ):
        assert meaning in task


def test_scientific_partner_task_repeats_on_delta_lookup_and_cold_restoration(tmp_path):
    first = snapshot()
    first['goal']['objective'] = 'Examine synthetic carrier omission and reporter dependence.'
    first['requested_form'] = FORM
    first['literature_assignment']['requested_partner_components'] = ['partner_loss_fraction']
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {
        'text': 'Synthetic assay: reporter formation was measured; carrier source differs from expression host.'}}
    lookup_result = {'status': 'completed', 'text':
        'Synthetic selected conditions: temperature is known; substrate concentration is unresolved.'}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 2, 'exchange_index': 1, 'result': lookup_result}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=2, restored_public_exchanges=[{
        'exchange_index': 1, 'lookup_result': lookup_result,
        'response': {'response_type': 'request_context', 'private_extra': 'DO_NOT_RENDER'}}])
    original = deepcopy((first, second, lookup, restored))
    wire, cold = LiteratureWire(tmp_path/'wire'), LiteratureWire(tmp_path/'cold')

    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(cold, restored)
    asyncio.run(exercise())
    tasks = []
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
        assert_partner_instructions(task)
        assert first['goal']['objective'] in task
        assert PARTNER_TASK not in steering and 'DO_NOT_RENDER' not in steering
        tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    assert lookup_result['text'] in wire.turns_sent()[-1]['input'][0]['text']
    assert lookup_result['text'] in cold.turns_sent()[0]['input'][0]['text']
    assert (first, second, lookup, restored) == original


def test_partner_operation_lookup_keeps_scientific_task_on_current_compact_and_cold_paths(tmp_path):
    state = snapshot()
    state['literature_assignment']['requested_partner_components'] = ['partner_loss']
    state['requested_form'] = FORM
    state['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    operation = next(row for row in _population_catalog()
        if row['name'] == 'literature.partner.source.populate')
    state['tools'] = [{**operation, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT}]
    information = operation_contract_information(catalog=[operation], operation=operation['name'])
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 1, 'exchange_index': 1, 'result': information,
        'pending_contract_information': [information]}
    restored = state_frame(state)
    restored.update(restored_pending_decision_index=1,
        restored_public_exchanges=[{'lookup_result': information}])
    wire, cold = LiteratureWire(tmp_path/'wire'), LiteratureWire(tmp_path/'cold')

    async def exercise():
        await complete(wire, state_frame(state))
        await complete(wire, lookup)
        await complete(cold, restored)
    asyncio.run(exercise())
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
        assert_partner_instructions(task)
        assert 'Operands for literature.partner.source.populate' not in task
        assert PARTNER_TASK not in steering
        assert information['result']['schema_sha256'] not in task + steering
    for turn in (wire.turns_sent()[-1], cold.turns_sent()[0]):
        task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
        assert information['result']['text'] in task
        assert information['result']['text'] not in steering


@pytest.mark.parametrize('coverage', ['partial', 'unreported'])
def test_selected_conditions_keep_native_values_and_explicit_unavailable_comparison(tmp_path, coverage):
    store, context, args, _ = fixture(tmp_path)
    for arm in args['arms'].values():
        arm['conditions']['coverage'] = coverage
        if coverage == 'unreported':
            arm['conditions']['factors'] = []
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert [saved['sheet']['cells'][name]['value'] for name in
            ('reference_rate', 'omitted_rate', 'addback_rate')] == [100, 20, 90]
        assert saved['sheet']['cells']['partner_loss_fraction']['unavailable_reason'] == 'conditions_incomplete'
        factors = saved['extraction']['native_evidence']['reference']['conditions']['factors']
        assert [factor['factor'] for factor in factors] == (
            ['nitrogen_source', 'temperature', 'pH'] if coverage == 'partial' else [])
        assert outcome['result']['partner_necessity'] == 'not_inferred'
        assert outcome['result']['statistical_uncertainty'] == 'not_evaluated'


def test_prompt_change_rejects_original_binding_and_restores_current_descriptor(monkeypatch):
    binding = LiteratureEpisodes(None, rate_population=True)
    current = binding.as_record()
    old_prompt = (RECORDS/'PARTNER_PROMPT_BEFORE_001.py').read_bytes()
    read_bytes = Path.read_bytes
    prompt_path = Path(__file__).resolve().parents[1]/'gene_annotation_episode/literature_partner_prompt.py'
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', lambda path:
            old_prompt if path.resolve() == prompt_path else read_bytes(path))
        original = binding.as_record()
    assert original['configuration'] == current['configuration']
    assert original['implementation_sha256'] != current['implementation_sha256']
    store = object()
    arguments = dict(store=store, journal=SimpleNamespace(store=store, run_id='synthetic-run'),
        execution_backend=None, job_episodes=None, resource_estimator=None, role_credit_bindings={})
    with pytest.raises(DurableExecutionError, match='identity_conflict'):
        compose_episode_bindings(None, descriptors=[original], **arguments)
    restored, = compose_episode_bindings(None, descriptors=[current], **arguments).bindings
    assert restored.as_record() == current


def test_ordinary_child_parent_transport_preserves_task_ownership_partial_meaning_and_observations(tmp_path):
    store, template, args, records = fixture(tmp_path/'state', page=False)
    for arm in args['arms'].values():
        arm['conditions']['coverage'] = 'partial'
    args['arms']['addback'] = None
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': list(template.received_record_refs),
        'requested_partner_components': ['reference_rate', 'partner_loss_fraction', 'addback_fraction']}
    captured = {}
    raw = store.get_artifact(records['data']['artifact_ref'])

    def reason():
        selected = witness(records['data'], raw, 'SubjectS')
        selected.pop('representation')
        selected['artifact_ref'] = records['data']['artifact_ref']
        commit = {key: [] for key in store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias': 'examined', 'reference_type': 'assay',
            'source_ref': records['data']['id'], 'label': 'SubjectS', 'anchor': selected}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

    def child_first(inputs):
        text = render_literature_experimental_prompt(inputs, 'Examine the assigned synthetic source.')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert_partner_instructions(task)
        assert 'Compare synthetic omission and addback conditions' in task
        assert 'Return selected native rates and unresolved comparisons' in task
        assert PARTNER_TASK not in steering
        captured['child_task'] = task
        return {'selection': {'kind': 'tool', 'tool': 'literature.partner.source.populate',
            'arguments': args}, 'report_update': {}}

    def child_next(inputs):
        task, steering = render_literature_experimental_prompt(inputs,
            'Examine the assigned synthetic source.').split('\n\nSTEERING\n', 1)
        assert task == captured['child_task']
        for value in ('conditions_incomplete', 'partial', 'arm_unreported', 'not_inferred'):
            assert value in steering
        return reason()

    def parent_next(inputs):
        text = render_literature_experimental_prompt(inputs, 'Evaluate the synthetic reference evidence.')
        task, steering = text.split('\n\nSTEERING\n', 1)
        assert REFERENCE_PARENT_TASK in task and PARTNER_TASK not in task
        form, = inputs['child_reports']
        rows = form['selected_components']
        assert [row['component'] for row in rows] == assignment['requested_partner_components']
        assert [row['value'] for row in rows] == [100, None, None]
        assert rows[1]['unavailable_reason'] == 'conditions_incomplete'
        assert rows[2]['unavailable_reason'] == 'conditions_incomplete'
        assert rows[0]['arm_metadata']['reference']['condition_coverage'] == 'partial'
        assert rows[0]['arm_metadata']['addback'] is None
        for meaning in ('conditions_incomplete', 'partial', 'not_inferred', 'glutamine', 'SubjectS'):
            assert meaning in steering
        assert 'omitted_rate' not in steering and 'addback_rate' not in steering
        captured['returned'] = deepcopy(form)
        return reason()

    commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': assignment, 'goal': 'Compare synthetic omission and addback conditions',
        'scope': plain(template.scope), 'purpose': 'Return selected native rates and unresolved comparisons',
        'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    with store:
        result = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, child_first, child_next, parent_next]), run_dir=tmp_path/'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=list(template.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args['source_ref']]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert 'returned' in captured and result['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_partner_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
