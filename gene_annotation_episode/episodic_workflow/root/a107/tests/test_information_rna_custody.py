"""Nonempty original RNA values through actual saved receipt/form readers.

Scientific native output and its saved producer reservation are controlled test inputs.
The actual current twenty-GiB producer preflight remains rejected and is recorded separately.
No current resource authorization or genuine producer execution is claimed. Target observation is controlled. The
worker process port calls the exact pure calculation function in-process; it
does not start Python/native workers. Store publication, original actions,
report attempts, frozen forms, target reads and received authentication are real.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from .fixtures.initial_information_rna import fixture_helpers as F
from .fixtures.initial_information_rna.saved_producer_port import (
    controlled_saved_producer_reservation, record_current_preflight_rejection,
)
from .test_information_connected import module, original_initial


def pure_worker(command, *, cwd, policy, stdout_path, stderr_path, env):
    # A controlled process boundary, not an alias for another implementation.
    assert command[1:3] == ['-B', '-m'] and len(command) == 5
    assert command[3] in {'gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_worker',
        'gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_worker'}
    plan = json.loads(Path(command[4]).read_text())
    if command[3].endswith('.rna_structure_comparison_worker'):
        module('rna_structure_comparison_worker').run_rna_comparison_worker(plan)
    else:
        worker = module('native_rna_structure_result_worker')
        run = worker.run_saved_rna_structure_grading_worker if plan.get('version') == 'native_rna_structure_saved_grading_plan_v1' else worker.run_rna_structure_grading_worker
        run(plan)
    Path(stdout_path).write_bytes(b'Controlled process port; exact pure worker function ran in-process.\n')
    Path(stderr_path).write_bytes(b'')
    return SimpleNamespace(returncode=0, metadata={'fixture': 'inprocess_original_pure_worker'},
        stdout_path=Path(stdout_path), stderr_path=Path(stderr_path))


def selected_comparison(descriptor):
    contracts = module('rna_structure_comparison_contracts')
    value = {'version': 'native_rna_structure_comparison_selector_v1', 'acquisition': 'retained_inputs_only',
        'question': {'kind': 'scan', 'baseline_member_id': 'original',
            'membership': [{'member_id': 'original', 'kind': 'saved_sheet', 'saved_input': deepcopy(descriptor)}],
            'comparisons': [], 'scan': {'scan_id': 'one-retained-structure',
                'population_unit': 'unique_analyzed_sequence_variant', 'baseline_in_rank': True,
                'member_order': 'as_declared', 'energy': None, 'topology_selection_ids': []}},
        'parameters': {key: field['const'] for key, field in contracts.RNA_COMPARISON_PARAMETERS_SCHEMA['properties'].items()},
        'projections': [{'projection_id': 'exact-retained-strings', 'family': 'structures',
            'member_ids': ['original'], 'fields': ['original_sequence', 'dot_bracket']}]}
    return contracts.validate_rna_comparison_selector(value)


def commissioned(fixture, parent, role, index, assignment, schema):
    contract = module('runtime').TypedReportContract('Return exactly the selected original RNA facts', schema, lambda *_: True)
    context = fixture.context(parent.path + ((role, 'child_' + str(index)),), assignment, contract, parent)
    action = {'kind': 'episode_child', 'role': role, 'assignment': assignment,
        'scope': deepcopy(fixture.scope), 'purpose': contract.decision, 'schema_json': F.canonical(schema)}
    fixture.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
        'action': F.canonical(action), 'result': None, 'credit': None})
    return context


def delivered(fixture, parent, child, facts, adapters):
    contract = F.plain(child.request)['report_contract']
    schema = contract['measurements']['schema']
    form = F.form_with_facts({}, schema, facts)
    fixture.journal.save('runtime_forms', {'episode_id': child.episode_id,
        'facts': F.canonical(facts), 'form': F.canonical(form)})
    index = int(child.path[-1][1].removeprefix('child_'))
    fixture.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': index,
        'delivery_ref': 'delivery_' + F.digest([parent.episode_id, index])[:24], 'child_episode_id': child.episode_id,
        'contract': F.canonical(contract), 'form': F.canonical(form), 'failure': None})
    references = []
    for adapter in adapters:
        references.extend(adapter.record_admission(parent, form, schema,
            f'{fixture.run_id}:{parent.episode_id}:{index}:typed_form'))
    fixture.receipts.receive(parent.episode_id, list(dict.fromkeys(references)), kind='child_form', source_index=index)
    return form


def build_received(tmp_path, *, connected=True):
    record_current_preflight_rejection(F, tmp_path / 'actual-current-preflight')
    with module('state').Store(tmp_path / 'store') as store, ExitStack() as ports:
        with patch.object(module('native_rna_structure_local').native, 'prepare_job',
                controlled_saved_producer_reservation):
            fixture = F.Fixture(store, tmp_path / 'original-rna')
        resources = {'local-rna': {'kind': 'local', 'workspace': fixture.assignment['workspace'],
            'policy': deepcopy(F.POLICY), 'native_rna_structure': [
                {key: deepcopy(fixture.job[key]) for key in ('operation', 'mode', 'software')}]}}
        factory = module('execution_service_setup').ExecutionServiceFactory(resources,
            {'local-rna': {'fixture': 'controlled saved producer reservation and synthetic output; current native preflight rejected; received application custody is real'}},
            2., 3., 1., log_window_bytes=1024)
        definition = F.plain(factory.as_record())
        owner = module('hpc_work_planning/execution_result_acquisition/episode').ExecutionEpisode(
            SimpleNamespace(annotation_task_required=lambda: False), store=store, run_id=fixture.run_id,
            directory=fixture.owner.directory, tool_registry=None,
            **{key: definition[key] for key in ('resources', 'initial_information', 'handoff_unit',
                'acquired_record_unit', 'log_window_bytes', 'log_roles')})
        assert owner.job_progress_provider.targets.read_target(fixture.handoff, fixture.scope) == fixture.target
        fixture.owner, fixture.results, fixture.returns = owner, owner.native_rna_structure_results, owner.native_rna_structure_returns
        ports.enter_context(patch.object(owner.job_progress_provider.targets, 'observe_target', fixture.targets.observe_target))
        ports.enter_context(patch.object(module('native_rna_structure_result_publication'), 'run_local_job', pure_worker))
        ports.enter_context(patch.object(module('rna_structure_comparison_publication'), 'run_local_job', pure_worker))
        native = module('rna_structure_result_views')
        compare = module('rna_structure_comparison_views')
        sources = (native.FAMILY_SOURCES['summary'], native.REFERENCE_SOURCE, native.SAVED_SOURCE)
        properties = {name: deepcopy(native.rna_structure_fact_sources()[source]['report_schema'])
            for name, source in zip(('summary', 'references', 'saved'), sources)}
        properties['comparison'] = deepcopy(compare.rna_comparison_fact_sources()[compare.PROJECTION_SOURCE]['report_schema'])
        combined = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
        science = commissioned(fixture, fixture.root, 'scientific_process', 0, {}, combined)
        child = fixture.child(parent=science, index=0, sources=sources)
        body = fixture.execute(child)
        assert body['delivery_complete'] and body['rows']
        fixture.returned(science, child)
        descriptor = fixture.results.saved_descriptor(body)
        selector = selected_comparison(descriptor)
        comparison_schema = {'type': 'object', 'properties': {'comparison': properties['comparison']},
            'required': ['comparison'], 'additionalProperties': False}
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': fixture.handoff, 'selector': selector}
        comparison_child = commissioned(fixture, science, 'results', 1, assignment, comparison_schema)
        operation = f'{fixture.run_id}:{comparison_child.episode_id}:0'
        action = {'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}
        fixture.journal.save('runtime_actions', {'episode_id': comparison_child.episode_id, 'decision_index': 0,
            'action': F.canonical(action), 'result': None, 'credit': None})
        outcome = asyncio.run(owner.rna_structure_comparison_results.execute(comparison_child, fixture.target,
            action['tool'], {}, operation))
        assert outcome['result']['delivery_complete'] and outcome['result']['projection_rows']
        fixture.journal.save('runtime_actions', {'episode_id': comparison_child.episode_id, 'decision_index': 0,
            'action': F.canonical(action), 'result': F.canonical(outcome), 'credit': 0})
        compare_facts = owner.rna_structure_comparison_results.facts(comparison_child)
        delivered(fixture, science, comparison_child, compare_facts, [owner.rna_structure_comparison_returns])
        facts = {**owner.native_rna_structure_returns.received_facts(science, combined),
            **owner.rna_structure_comparison_returns.received_facts(science, combined)}
        delivered(fixture, fixture.root, science, facts,
            [owner.native_rna_structure_returns, owner.rna_structure_comparison_returns])
        configuration = catalog = None
        if connected:
            configuration = module('library/execution_initial_information/information_configuration').InitialInformationConfiguration.original_global_factory(factory)
            catalog = configuration.construct(store=store, run_id=fixture.run_id, directory=owner.directory,
                tool_registry=None, services=owner.services)
        yield SimpleNamespace(fixture=fixture, owner=owner, science=science, child=child,
            comparison_child=comparison_child, catalog=catalog, configuration=configuration,
            original_body=body, comparison_body=outcome['result'], directory=tmp_path)


@pytest.fixture
def received(tmp_path):
    yield from build_received(tmp_path)


def received_information(case, context):
    return case.owner.initial_decision_context(context) if case.catalog is None else case.catalog.original_global_information(context)


def test_complete_received_structure_and_comparison_equal_original_callback(received):
    case = received
    before = list(case.fixture.store.db.iterdump())
    observed = list(case.fixture.targets.observations)
    for context in (case.science, case.fixture.root):
        expected = original_initial(case.owner, context)
        actual = received_information(case, context)
        assert actual == expected
        assert actual['received_rna_structure_values'] and actual['received_rna_comparison_values']
        (case.directory / (context.role + '-original-and-current.json')).write_text(json.dumps(
            {'context': context.as_record(), 'expected': expected, 'actual': actual}, indent=2) + '\n')
    assert case.fixture.targets.observations == observed
    assert list(case.fixture.store.db.iterdump()) == before


@pytest.mark.parametrize('which', ['structure', 'comparison'])
def test_changed_frozen_form_is_rejected_by_both_original_and_private_readers(received, which):
    case = received
    child = case.child if which == 'structure' else case.comparison_child
    row = case.fixture.store.db.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
        (case.fixture.run_id, child.episode_id)).fetchone()
    changed = json.loads(row['form'])
    field = next(iter(changed))
    assert changed[field]
    changed[field] = []
    case.fixture.store.db.execute('UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?',
        (F.canonical(changed), case.fixture.run_id, child.episode_id))
    errors = []
    for callback in (lambda: original_initial(case.owner, case.science),
            lambda: received_information(case, case.science)):
        with pytest.raises(Exception) as error:
            callback()
        errors.append((type(error.value), str(error.value)))
    assert errors[0] == errors[1] and 'frozen_form_conflict' in errors[0][1]


def test_restored_factory_readers_retain_full_authenticated_received_payload(received):
    case = received
    config = type(case.configuration).from_record(case.configuration.as_record())
    restored = config.construct(store=case.fixture.store, run_id=case.fixture.run_id,
        directory=case.owner.directory, tool_registry=None, services=case.owner.services)
    restored.check_saved(case.catalog.as_record())
    assert restored.original_global_information(case.fixture.root) == case.catalog.original_global_information(case.fixture.root)


def test_same_scope_without_original_received_form_confers_no_rna_values(received):
    case = received
    path = (('annotation', 'unrelated-original-parent'),)
    ident = module('method_loop/identities').EpisodeRef(case.fixture.run_id, path).episode_id
    context = replace(case.fixture.root, path=path, episode_id=ident)
    expected = original_initial(case.owner, context)
    actual = received_information(case, context)
    assert actual == expected
    assert actual['received_rna_structure_values'] == actual['received_rna_comparison_values'] == []
