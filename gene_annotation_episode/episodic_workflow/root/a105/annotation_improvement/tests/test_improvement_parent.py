"""Existing conditional improvement source and directional boundary preservation."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ...tests import implicit_parent_checks as original
from ...tests import improvement_parent_checks as check


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


@pytest.mark.parametrize('recursive', (False, True))
def test_actual_improvement_constructor_uses_private_owner_with_original_identity(tmp_path, recursive):
    runtime = original.module('runtime')
    records = []
    for old in (True, False):
        with original.actual_workflow(tmp_path / str(old)) as workflow:
            episode = check.improvement(workflow, original_build=old, recursive=recursive)
            source = episode.source
            assert type(source) is (runtime.DecisionSource if old else original.module('annotation_improvement/task').ImprovementTask)
            assert isinstance(source, runtime.DecisionSource) and workflow.specialist(source) is None
            assert source.path[-1][0] == 'improvement' and len(source.path) == (3 if recursive else 2)
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            records.append((source.episode_id, source.path, source.request.as_record(),
                            dict(workflow.journal.row('runtime_episodes', source.episode_id))))
    assert records[0] == records[1]


def test_original_improvement_reconstructs_same_saved_assignment(tmp_path):
    with original.actual_workflow(tmp_path) as workflow:
        old = check.improvement(workflow, original_build=True)
        before = dict(workflow.journal.row('runtime_episodes', old.source.episode_id))
        current = check.improvement(workflow)
        assert type(current.source) is original.module('annotation_improvement/task').ImprovementTask
        assert current.source.request.as_record() == old.source.request.as_record()
        assert dict(workflow.journal.row('runtime_episodes', current.source.episode_id)) == before


@pytest.mark.parametrize('parent_kind', ('improvement',))
@pytest.mark.parametrize('scenario', ('valid-return', 'invalid-return', 'saved-return'))
def test_actual_conditional_child_preserves_semantic_validation_and_return_custody(tmp_path, parent_kind, scenario):
    observed = check.paired_connected(tmp_path, parent_kind, scenario)
    assert len(observed['attempts']) == 1
    events = observed['events']
    assert events.index(('resolver', 'improvement')) < events.index(('validate_report', original.INITIAL)) < events.index('build')
    if scenario == 'invalid-return':
        assert observed['failure'] is not None and observed['last_outcome_index'] == 7
        assert observed['action']['credit'] == 0.375 and observed['action']['result'] is not None
    else:
        assert observed['failure'] is None and observed['result'] == original.INITIAL


@pytest.mark.parametrize('requires_task', (False, True))
def test_complete_original_continuation_retains_task_rejection_and_late_context(tmp_path, monkeypatch, requires_task):
    runtime = original.module('runtime')
    actual_context = runtime.ExecutionContextController
    records = []
    for old in (True, False):
        with monkeypatch.context() as edit, original.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.improvement(workflow).source
            events = []
            def context(*args, **kwargs):
                events.append('late_context')
                return actual_context(*args, **kwargs)
            def factory(path, initial, **kwargs):
                events.append('factory')
                edit.setattr(runtime, 'ExecutionContextController', context)
                numerical = original.module('numerical')
                return numerical.YieldController('original-improvement', initial, 0.5,
                    numerical.YieldParameters(uncertainty_alpha=0.05))
            factory.requires_original_task = requires_task
            workflow.controller_factory = factory
            call = original.original_function('Workflow', 'controller') if old else runtime.Workflow.controller
            if requires_task:
                with pytest.raises(ValueError, match='^scientific_continuation_task_not_declared:improvement$'):
                    call(workflow, source.path)
                records.append(('original rejection', events))
            else:
                value = call(workflow, source.path)
                assert type(value) is actual_context
                records.append((value.episode_id, events))
    assert records[0] == records[1]
    assert records[1][1] == ([] if requires_task else ['factory', 'late_context'])


def test_private_improvement_report_retains_original_late_job_branch(tmp_path):
    def private_root(workflow, **kwargs):
        return check.improvement(workflow)
    with patch.object(original, 'root', private_root):
        value, events = original.paired_report(tmp_path, 'late-job')
    assert value['job_marker'] == 'original late job body'
    assert events.count('credit') == events.count('received_facts') == 1


def test_private_improvement_instructions_retain_late_provider_and_text_reads(tmp_path, monkeypatch):
    prompt = original.module('runtime_prompt')
    records = []
    for old in (True, False):
        with monkeypatch.context() as edit, original.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.improvement(workflow).source
            if original.AXIS == 'a108':
                assert not hasattr(workflow, 'native_event_information')
                workflow.native_event_information = None
            events = []
            def specialist_text(context):
                events.append('specialist_text')
                edit.setattr(prompt, 'REASONING_COMMIT_REQUIREMENT', 'late improvement text')
                return 'late specialist'
            specialist = SimpleNamespace(instructions=specialist_text, replaces_default_instructions=False)
            def job_text(role):
                assert role == 'improvement'
                events.append('job_text')
                workflow.specialist = lambda actual: events.append('specialist_lookup') or specialist
                return 'late job'
            def is_job(actual):
                assert actual is source
                events.append('is_job')
                workflow.job_episodes = SimpleNamespace(instructions=job_text)
                return True
            workflow.is_job_source = is_job
            workflow.specialist = original.forbidden
            workflow.permits_common_action = lambda actual, action: events.append(('permits', action)) or action == 'reason'
            value = original.original_instructions()(source, {}) if old else source.instructions({})
            records.append((value, events))
    assert records[0] == records[1]
    assert records[1][0].startswith('late job\nlate specialist\nlate improvement text\n')
    assert records[1][1] == ['is_job', 'job_text', 'specialist_lookup', 'specialist_text', ('permits', 'reason'), ('permits', 'wait')]


def test_custom_registry_preserves_original_conditional_child_fallback(tmp_path):
    observed = check.paired_connected(tmp_path, 'improvement', 'valid-return', custom_registry=True)
    assert observed['owners'] == [] and 'custom_registry_roles' in observed['events']


def test_late_kind_mutation_keeps_actual_original_job_assignment_branch(tmp_path):
    observed = check.paired_connected(tmp_path, 'improvement', 'late-job-kind')
    assert observed['events'].index('expanded_form') < observed['events'].index('late_job_assignment') < observed['events'].index('build')
    assert observed['built'][0]['job_assignment'] == {'original_job_assignment': 'actual late callback result'}
    assert [name for _, name in observed['owners']] == ['prepare_request']


def test_late_kind_mutation_keeps_original_missing_registered_counterpart_rejection(tmp_path):
    runtime = original.module('runtime')
    records = []
    for old in (True, False):
        with original.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.improvement(workflow, original_build=old).source
            events = []
            workflow.root_action_boundary = None
            workflow._closed_child_commission = lambda *args: None
            def expanded(actual_source, selection, index, role):
                events.append('expanded_form')
                assert selection['kind'] == 'child'
                selection['kind'] = 'episode_child'
                return deepcopy(original.SCHEMA), None
            workflow.expanded_contract_form = expanded
            selection = {'kind': 'child', 'scope': deepcopy(source.scope),
                'goal': 'Original conditional improvement', 'purpose': 'Preserve uncertainty'}
            call = original.original_function('Workflow', 'selected') if old else runtime.Workflow.selected
            with pytest.raises(LookupError) as caught:
                call(workflow, source, selection, 7)
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            records.append((original.error_record(caught.value), events))
    assert records[0] == records[1]
    assert records[1][0][2] == 'episode_role_not_bound:improvement'
    assert records[1][1] == ['expanded_form']


def test_private_improvement_receiver_preserves_empty_receipts_without_action_row(tmp_path):
    runtime = original.module('runtime')
    records = []
    for old in (True, False):
        with original.actual_workflow(tmp_path / str(old)) as workflow:
            source = check.improvement(workflow).source
            events = []
            workflow.receipts = None
            workflow.progress_provider = SimpleNamespace(
                receive_form=lambda *args: events.append('original_progress'))
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            call = original.original_function('Workflow', '_receive_form') if old else runtime.Workflow._receive_form
            value = call(workflow, source, {}, {'type': 'object', 'properties': {}}, 13)
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            records.append((value, events))
    assert records[0] == records[1] == ([], ['original_progress'])


def test_default_nested_improvement_retains_original_undeclared_credit_rejection(tmp_path):
    records = []
    for old in (True, False):
        with original.actual_workflow(tmp_path / str(old)) as workflow:
            with pytest.raises(ValueError, match='^scientific_task_credit_not_declared:improvement$') as caught:
                check.improvement(workflow, original_build=old, supplied_initial_credit=False)
            assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()
            rows = [dict(row) for row in workflow.store.db.execute(
                'SELECT * FROM runtime_episodes ORDER BY episode_id')]
            assert len(rows) == 1
            assert all('improvement' not in row['path'] for row in rows)
            records.append((original.error_record(caught.value), rows))
    assert records[0] == records[1]
