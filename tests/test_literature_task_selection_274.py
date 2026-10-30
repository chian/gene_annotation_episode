"""Full recurring TASK selection; synthetic work and read-only reconstruction."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_contract_information import operation_contract_information, return_contract_information
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK, SAVED_NUMERICAL_RETURN_TASK, render_literature_experimental_prompt
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt
from gene_annotation_episode.literature_task_selection import NATIVE_KINETIC_TASK, selected_literature_task_sections, population_task_metadata_specs
from gene_annotation_episode.literature_kinetic_summary_precision_prompt import KINETIC_SUMMARY_PRECISION_TASK
from gene_annotation_episode.literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from gene_annotation_episode.literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from gene_annotation_episode.literature_figure_prompt import FIGURE_TASK
from gene_annotation_episode.literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK
from gene_annotation_episode.literature_compiled_assay_prompt import COMPILED_ASSAY_TASK, COMMON_ASSESSMENT_TASK
from gene_annotation_episode.literature_product_coupling_prompt import PRODUCT_COUPLING_TASK
from gene_annotation_episode.literature_calibration_recovery_prompt import CALIBRATION_RECOVERY_TASK
from gene_annotation_episode.literature_numerical_contracts import registered_schema
from gene_annotation_episode.state import Store
from test_literature_kinetic_summary_precision_binding_251 import setup, selected, forbid


FORMATS = [
    ('literature_kinetic_cells', 'requested_kinetic_components', NATIVE_KINETIC_TASK),
    ('literature_kinetic_summary_precision_cells', 'requested_kinetic_summary_precision_components', KINETIC_SUMMARY_PRECISION_TASK),
    ('literature_endpoint_signal_cells', 'requested_endpoint_signal_components', ENDPOINT_SIGNAL_TASK),
    ('literature_measurement_comparison_cells', 'requested_measurement_comparison_components', MEASUREMENT_COMPARISON_TASK),
    ('literature_compiled_assay_v2_cells', 'requested_compiled_assay_components_v2', COMPILED_ASSAY_TASK),
    ('literature_compiled_assay_v3_cells', 'requested_compiled_assay_components_v3', COMMON_ASSESSMENT_TASK),
    ('literature_product_coupling_cells', 'requested_product_coupling_components', PRODUCT_COUPLING_TASK),
    ('literature_calibration_recovery_cells', 'requested_calibration_recovery_components', CALIBRATION_RECOVERY_TASK),
]


def state(parent=False):
    return {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
        'aspect': 'reference_evidence_parent' if parent else 'source_experimental_evidence'},
        'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': ['source_assigned']},
        'goal': {'objective': 'Read the actual assigned preparation and preserve this caller question.'},
        'scope': {}, 'literature_assignment': {}, 'working_state': {}, 'child_reports': [],
        'requested_form': None, 'current_report_update': {}, 'pending_work': {'items': []}}


def render(value, lookups=()):
    caller = 'Caller process: revise the selected investigation using the actual result.'
    return render_literature_experimental_prompt(value, caller, lookup_results=lookups)


@pytest.mark.parametrize('parent', [False, True])
@pytest.mark.parametrize('source,roster,full_task', FORMATS)
@pytest.mark.parametrize('selection', ['empty_roster', 'alias', 'literal'])
def test_explicit_single_family_repeats_exact_full_block_and_preserves_caller(parent, source, roster, full_task, selection):
    value = state(parent)
    if selection == 'empty_roster':
        value['literature_assignment'][roster] = []
    else:
        node = {'$ref': 'episode-fact:' + source} if selection == 'alias' else registered_schema(source)
        value['requested_form'] = {'type': 'object', 'properties': {'chosen': node}}
    before = deepcopy(value)
    for current in (value, deepcopy(value)):
        task, steering = render(current).split('\n\nSTEERING\n')
        assert full_task in task and task.count(full_task) == 1
        assert (REFERENCE_PARENT_TASK if parent else EXPERIMENTAL_TASK) in task
        assert SAVED_NUMERICAL_RETURN_TASK in task
        assert 'Caller process: revise the selected investigation' in task
        assert value['goal']['objective'] in task
        assert KINETIC_MODEL_TASK not in task
        for _, _, other in FORMATS:
            if other != full_task:
                assert other not in task
        assert 'literature_owned_population_sources' not in steering
    assert value == before


@pytest.mark.parametrize('parent', [False, True])
def test_capability_flags_catalogues_and_unknown_inputs_do_not_select_science(parent):
    value = state(parent)
    for code in ('completion_time', 'active_site', 'product_partition', 'compiled_assay',
            'common_assessment', 'ratio_source', 'controlled_response', 'gel', 'rate_grid',
            'channel', 'ion_discrimination', 'product_coupling', 'kinetic_summary_precision'):
        value['literature_' + code + '_work'] = {'version': 'enabled'}
    value['tools'] = [{'name': 'literature.kinetic.populate', 'description': 'Available kinetic work.'}]
    value['available_report_facts'] = {'literature_kinetic_cells': {'meaning': 'Available only.'}}
    value['literature_assignment']['unknown_requested_components'] = []
    assert selected_literature_task_sections(value) == ()
    task = render(value).split('\n\nSTEERING\n')[0]
    assert NATIVE_KINETIC_TASK not in task
    assert all(full not in task for _, _, full in FORMATS)


@pytest.mark.parametrize('parent', [False, True])
@pytest.mark.parametrize('operation,expected', [
    ('literature.kinetic.populate', (NATIVE_KINETIC_TASK, KINETIC_SUMMARY_PRECISION_TASK)),
    ('literature.figure.populate', (FIGURE_TASK, ENDPOINT_SIGNAL_TASK)),
    ('literature.assay.components.populate', (COMPILED_ASSAY_TASK, COMMON_ASSESSMENT_TASK)),
    ('literature.measurement_comparison.populate', (MEASUREMENT_COMPARISON_TASK,)),
])
def test_real_operation_lookup_producer_supplies_only_full_actual_alternatives(tmp_path, parent, operation, expected):
    store, ctx, args, binding, _ = setup(tmp_path/'source')
    try:
        binding.compiled_assay_population = True
        lookup = operation_contract_information(catalog=binding.catalog(ctx), operation=operation)
        value = state(parent)
        task = render(value, [lookup]).split('\n\nSTEERING\n')[0]
        assert tuple(text for _, text in selected_literature_task_sections(value, [lookup])) == expected
        assert all(text in task for text in expected)
        assert KINETIC_MODEL_TASK not in task
        assert selected_literature_task_sections(value, [{**lookup, 'status': 'invalid'}]) == ()
        # Explicit reconstruction retains actual lookup information, never a
        # capability marker masquerading as completion.
        restored = json.loads(json.dumps(lookup))
        assert selected_literature_task_sections(value, [restored]) == selected_literature_task_sections(value, [lookup])
    finally:
        store.close()


@pytest.mark.parametrize('parent', [False, True])
def test_real_return_lookup_is_exact_and_deduplicates_full_caller_guidance(tmp_path, parent):
    store, ctx, args, binding, _ = setup(tmp_path/'source')
    try:
        source = 'literature_kinetic_summary_precision_cells'
        schema = registered_schema(source)
        lookup = return_contract_information(facts_by_role={'literature': {source: {
            'type': 'array', 'meaning': 'Only selected precision.', 'report_schema': schema}}},
            permitted_child_roles=['literature'], role='literature', source=source)
        value = state(parent)
        value['literature_assignment']['requested_kinetic_summary_precision_components'] = []
        text = render_literature_experimental_prompt(value, 'Caller process retained.\n\n' + KINETIC_SUMMARY_PRECISION_TASK,
            lookup_results=[lookup])
        task = text.split('\n\nSTEERING\n')[0]
        assert task.count(KINETIC_SUMMARY_PRECISION_TASK) == 1
        assert 'Caller process retained.' in task
        assert NATIVE_KINETIC_TASK not in task and KINETIC_MODEL_TASK not in task
    finally:
        store.close()


def test_owned_selected_partial_metadata_is_readonly_scoped_and_cold(tmp_path, monkeypatch):
    store, ctx, args, binding, _ = setup(tmp_path/'source', case='both_units_missing')
    try:
        current, outcome, rows = selected(store, ctx, args, binding)
        clean = replace(current, assignment={'version': 'literature_assignment_v1',
            'source_refs': list(ctx.assignment['source_refs']), 'question_context_refs': []})
        before = store.db.total_changes
        monkeypatch.setattr(store, 'get_artifact', forbid)
        monkeypatch.setattr(binding._summary_precision_repository(), 'read', forbid)
        assert binding._owned_population_task_sources(clean) == ('literature_kinetic_summary_precision_cells',)
        assert binding._owned_population_task_sources(replace(clean, run_id='wrong_run')) == ()
        assert binding._owned_population_task_sources(replace(clean, episode_id='other_episode')) == ()
        assert binding._owned_population_task_sources(replace(clean, received_record_refs=ctx.received_record_refs)) == ()
        assert store.db.total_changes == before
        assert any(row['cell']['status'] == 'unavailable' for row in rows)
        # New binding/services, same authoritative existing store. No cache or
        # current source/scientific reader supplies the classification.
        cold = LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store, run_id=ctx.run_id)), rate_population=True)
        assert cold._owned_population_task_sources(clean) == binding._owned_population_task_sources(clean)
        for parent in (False, True):
            value = state(parent)
            value.update(cold._population_task_context(clean))
            task = render(value).split('\n\nSTEERING\n')[0]
            assert KINETIC_SUMMARY_PRECISION_TASK in task
            assert NATIVE_KINETIC_TASK not in task and KINETIC_MODEL_TASK not in task
    finally:
        store.close()


def test_actual_latest_failed_action_metadata_not_capability_or_obsolete_failure(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'source')
    try:
        journal = Journal(store, ctx.run_id)
        bad = {**args, 'requested_cells': ['wrong_component']}
        outcome = asyncio.run(binding.execute(ctx, 'literature.kinetic.populate', bad, 'failed274'))
        assert outcome['status'] == 'invalid'
        journal.save('runtime_actions', {'episode_id': ctx.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'tool', 'tool': 'literature.kinetic.populate', 'arguments': bad}),
            'result': canonical(outcome)})
        before = store.db.total_changes
        metadata = binding._population_task_context(ctx)
        assert metadata['literature_owned_population_sources'] == ()
        assert metadata['literature_selected_population_attempt']['arguments'] == {'version': args['version']}
        assert store.db.total_changes == before
        for parent in (False, True):
            value = state(parent); value.update(metadata)
            assert selected_literature_task_sections(value) == (('literature_kinetic_summary_precision_cells', KINETIC_SUMMARY_PRECISION_TASK),)
            assert KINETIC_SUMMARY_PRECISION_TASK in render(value)
        journal.save('runtime_actions', {'episode_id': ctx.episode_id, 'decision_index': 1,
            'action': canonical({'kind': 'reasoning'}), 'result': canonical({'status': 'completed'})})
        assert 'literature_selected_population_attempt' not in binding._population_task_context(ctx)
    finally:
        store.close()


def test_admitted_nested_rows_history_failure_and_parent_private_boundary(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'source')
    try:
        current, outcome, rows = selected(store, ctx, args, binding)
        value = state(True)
        # The parent may choose any declared field names, including names that
        # are host envelope fields elsewhere. The admitted rows inform its
        # STEERING without selecting the child's method as the parent's TASK.
        value['child_reports'] = [{'context': {'assignment': {'precision': rows}}}]
        assert selected_literature_task_sections(value) == ()
        assert KINETIC_SUMMARY_PRECISION_TASK not in render(value).split('\n\nSTEERING\n')[0]
        value['current_report_update'] = {'precision': rows}
        assert selected_literature_task_sections(value) == ()
        value['literature_assignment']['requested_kinetic_summary_precision_components'] = []
        assert selected_literature_task_sections(value) == (('literature_kinetic_summary_precision_cells', KINETIC_SUMMARY_PRECISION_TASK),)
        wrong = deepcopy(rows[0]); wrong['row_version'] = 'unknown_old_version'
        assert selected_literature_task_sections({**state(), 'child_reports': [{'wrong': [wrong]}]}) == ()
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [{
            'selection': {'kind': 'tool', 'tool': 'literature.kinetic.model.populate', 'arguments': {}},
            'outcome': {'status': 'invalid', 'result': None}}]}}
        assert KINETIC_MODEL_TASK in [task for _, task in selected_literature_task_sections(state(), [history])]
        # A received admitted form cannot import private child attempts or its
        # own source-method instructions into the parent's TASK.
        history['result']['records'][0]['admitted_report'] = {'precision': rows}
        tasks = [task for _, task in selected_literature_task_sections(state(True), [history])]
        assert tasks == []
        # The same actual returned history remains relevant on the next turn.
        own = deepcopy(history); del own['result']['records'][0]['admitted_report']
        assert KINETIC_MODEL_TASK in [task for _, task in selected_literature_task_sections({**state(), 'last_local_outcome': own})]
        own['result']['records'][0]['admitted_report'] = None
        assert KINETIC_MODEL_TASK in [task for _, task in selected_literature_task_sections(state(), [own])]
    finally:
        store.close()


def test_metadata_specs_distinguish_compiled_versions_and_discovery_installs_nothing(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path/'source')
    try:
        binding.completion_time_population = binding.active_site_population = binding.product_partition_population = True
        before = store.db.total_changes
        tables = tuple(store.db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        specs = list(population_task_metadata_specs())
        compiled = [row for row in specs if row[0] in ('literature_compiled_assay_v2_cells', 'literature_compiled_assay_v3_cells')]
        assert compiled[0][2:4] == compiled[1][2:4] and compiled[0][4] != compiled[1][4]
        assert binding._owned_population_task_sources(ctx) == ()
        assert store.db.total_changes == before
        assert tuple(store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")) == tables
        Journal(store, ctx.run_id)
        actual = binding.decision_context(ctx, None)
        assert not {'literature_completion_time_work', 'literature_active_site_work', 'literature_product_partition_work'} & actual.keys()
        assert [code for code, _ in selected_literature_task_sections(actual)] == ['literature_kinetic_summary_precision_cells']
    finally:
        store.close()


def test_actual_compiled_v2_owned_operation_does_not_select_shared_v3_or_accept_wrong_source(tmp_path, monkeypatch):
    from test_literature_compiled_assay_uncertainty_215 import setup as setup_compiled, v2, selected as selected_compiled
    store, ctx, args, _ = setup_compiled(tmp_path/'source')
    try:
        ctx, args = v2(ctx, args)
        binding, current, repo, outcome, saved, rows = selected_compiled(store, ctx, args)
        clean = replace(current, assignment={})
        before = store.db.total_changes
        monkeypatch.setattr(store, 'get_artifact', forbid)
        monkeypatch.setattr(repo, 'read', forbid)
        owned = binding._owned_population_task_sources(clean)
        assert 'literature_compiled_assay_v2_cells' in owned
        assert 'literature_compiled_assay_cells' not in owned and 'literature_compiled_assay_v3_cells' not in owned
        require = binding._require
        for field, wrong in [('version', 'unknown_record'), ('provider', 'wrong_provider'),
                ('origin', 'caller'), ('id', 'source_other')]:
            monkeypatch.setattr(binding, '_require', lambda reference, scope, namespace, field=field, wrong=wrong:
                {**require(reference, scope, namespace), field: wrong})
            assert binding._owned_population_task_sources(clean) == ()
        assert store.db.total_changes == before
    finally:
        store.close()


@pytest.mark.parametrize('parent', [False, True])
def test_actual_selected_amount_path_keeps_own_task_and_admitted_steering(tmp_path, monkeypatch, parent):
    from test_literature_amount_storage import setup as setup_amount
    from test_literature_amount_integration import binding_for as amount_binding
    from gene_annotation_episode.literature_amount_prompt import AMOUNT_TASK
    from gene_annotation_episode.literature_amount_storage import amount_cells_schema
    store, ctx, args = setup_amount(tmp_path/'amount')
    try:
        binding = amount_binding(store, ctx)
        assigned = replace(ctx, assignment={**plain(ctx.assignment), 'requested_amount_components': ['amount_ratio']})
        outcome = asyncio.run(binding.execute(assigned, 'literature.amount.populate', args, 'selected274amount'))
        assert outcome['status'] == 'completed', outcome
        current = replace(assigned, received_record_refs=(*assigned.received_record_refs, *outcome['record_refs']))
        repo = binding.services.literature_amount_repository()
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=current.received_record_refs,
            components=['amount_ratio'])
        lookup = operation_contract_information(catalog=binding.catalog(assigned), operation='literature.amount.populate')
        declarations = [{'type': 'object', 'properties': {'amount': {'$ref': 'episode-fact:literature_amount_cells'}}},
            {'type': 'object', 'properties': {'amount': amount_cells_schema()}}]
        # Metadata/selection never reopen the already read synthetic source.
        monkeypatch.setattr(store, 'get_artifact', forbid)
        monkeypatch.setattr(repo, 'read', forbid)
        before = store.db.total_changes
        owned = binding._population_task_context(replace(current, assignment={}))
        assert owned['literature_owned_population_sources'] == ('literature_amount_cells',)
        contexts = [state(parent) for _ in range(7)]
        contexts[0]['literature_assignment'] = {'requested_amount_components': []}
        contexts[1].update(owned)
        contexts[2]['child_reports'] = [{'measurements': rows}]
        contexts[3]['requested_form'], contexts[4]['requested_form'] = declarations
        contexts[5]['last_local_outcome'] = {'status': 'invalid', 'selected_tool': 'literature.amount.populate'}
        for value in (contexts[0], contexts[1], contexts[3], contexts[4], contexts[5]):
            assert selected_literature_task_sections(value) == (('literature_amount_cells', AMOUNT_TASK),)
            task, steering = render(value).split('\n\nSTEERING\n')
            assert AMOUNT_TASK in task and task.count(AMOUNT_TASK) == 1
            assert (REFERENCE_PARENT_TASK if parent else EXPERIMENTAL_TASK) in task
            assert 'literature_owned_population_sources' not in steering
        admitted_task, admitted_steering = render(contexts[2]).split('\n\nSTEERING\n')
        assert selected_literature_task_sections(contexts[2]) == ()
        assert AMOUNT_TASK not in admitted_task
        assert (REFERENCE_PARENT_TASK if parent else EXPERIMENTAL_TASK) in admitted_task
        assert 'amount_ratio' in admitted_steering
        assert AMOUNT_TASK in render(contexts[-1], [lookup]).split('\n\nSTEERING\n')[0]
        assert store.db.total_changes == before
        descriptor = binding.as_record()
        read = Path.read_bytes
        def changed(path):
            content = read(path)
            return content + b'\n# descriptor dependency probe\n' if path.name == 'literature_amount_prompt.py' else content
        with monkeypatch.context() as probe:
            probe.setattr(Path, 'read_bytes', changed)
            assert binding.as_record() != descriptor
    finally:
        store.close()
