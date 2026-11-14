"""Required post-install resource controls; no native or model work.

These controls do not substitute for actual three-role Workflow close/reopen.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from .homology_family_boundaries import (HOMES, ROLES, monitoring_credit, operational_credit,
    options, original_family_type, own, registry, registry_files, registry_rows, task_credit)


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('homology_family_control_does_not_authorize_external_work')
    import socket
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def actual(tmp_path):
    with registry(tmp_path / 'actual') as values:
        store, jobs, policy, scope, job_ref = values
        Family = own('homology_binding_family').HomologyBindingFamily
        yield SimpleNamespace(store=store, jobs=jobs, policy=policy, scope=scope,
            job_ref=job_ref, family=Family(jobs, **options(policy)), Family=Family)






def test_native_event_view_preserves_typed_resources_and_caller(actual, tmp_path):
    family = actual.family; before = family.as_record()
    provider = own('native_events').NativeEventProvider(tmp_path.resolve() / 'events',
        run_id='explicit-resource-view', resource_id='explicit-caller-resource')
    view = family.with_native_events(provider)
    assert type(view) is actual.Family and view is not family
    assert view.__dict__ is not family.__dict__
    assert view.native_event_provider is provider and family.native_event_provider is None
    assert view.jobs is family.jobs and view.parser_policy is family.parser_policy
    assert view._role_credit_bindings is family._role_credit_bindings
    assert view.as_record() == family.as_record() == before
    for role in ROLES:
        assert type(view.for_role(role)) is type(family.for_role(role))
        assert view.for_role(role) is not family.for_role(role)
        assert view.for_role(role).__dict__ is view.__dict__
        assert family.for_role(role).native_event_provider is None
    with pytest.raises(TypeError, match='^typed_native_event_provider_required$'):
        family.with_native_events(SimpleNamespace(resource_id=provider.resource_id))






def test_registry_close_reopen_and_explicit_family_restore(actual):
    family = actual.family; descriptor = family.as_record()
    directory, saved_rows = actual.jobs.directory, registry_rows(actual.jobs)
    actual.jobs.close(); files = registry_files(directory)
    reopened = own('homology_jobs').HomologyJobs(directory)
    try:
        restored = own('homology_family_restore').restore_homology_family(descriptor,
            reopened, **options(actual.policy))
        assert type(restored) is actual.Family and restored.as_record() == descriptor
        assert registry_rows(reopened) == saved_rows
        for role in ROLES:
            assert restored.for_role(role).jobs is reopened
            assert restored.for_role(role).parser_policy is actual.policy
            assert type(restored.for_role(role)) is type(family.for_role(role))
            assert restored.for_role(role)._job_credit_calculator is operational_credit
            assert restored.for_role(role).monitoring_projector is monitoring_credit
    finally:
        reopened.close()
    assert registry_files(directory) == files


@pytest.mark.parametrize('change', ('legacy_v3', 'unknown_version', 'singleton_binding',
    'registry_directory', 'recorded_cpu_allocation', 'parser_policy', 'operational_definition', 'monitoring_definition'))
def test_changed_saved_record_is_not_aliased_or_activated(actual, change):
    descriptor = actual.family.as_record()
    if change == 'legacy_v3': descriptor['version'] = 'shared_homology_episode_binding_v3'
    elif change == 'unknown_version': descriptor['version'] = 'unknown_original_version'
    elif change == 'singleton_binding': descriptor['binding_id'] = HOMES[0]
    elif change == 'registry_directory': descriptor['registry_directory'] += '-changed'
    elif change == 'recorded_cpu_allocation':
        # Tamper saved JSON only: no live allocation or old CPU reinterpretation.
        descriptor['registry_configuration'] = deepcopy(descriptor['registry_configuration'])
        descriptor['registry_configuration']['max_cpu'] = 2
    elif change == 'parser_policy': descriptor['parser_policy']['memory_bytes'] = 123
    elif change == 'operational_definition': descriptor['role_credit_bindings']['job_launch']['changed'] = True
    else: descriptor['role_credit_bindings']['job_monitor']['changed'] = True
    before = registry_rows(actual.jobs)
    with pytest.raises(own('runtime').WorkflowError,
            match='^resumption requires the original job episode resources and scoring binding$'):
        own('homology_family_restore').restore_homology_family(descriptor, actual.jobs, **options(actual.policy))
    assert registry_rows(actual.jobs) == before




@pytest.mark.parametrize('role', ROLES)
def test_actual_family_runtime_selects_private_task_and_retains_returned_failure(actual, role, tmp_path, record_property):
    def forbidden(*args, **kwargs):
        raise AssertionError('family_runtime_control_does_not_authorize_native_or_model_work')
    calls = []
    def controller(path, initial_credit):
        calls.append((path, initial_credit))
        return own('numerical').YieldController('family-original-controller', initial_credit, .5)
    workflow = own('runtime').Workflow(actual.store,
        own('tools').ToolRegistry(actual.store, clients=SimpleNamespace(request=forbidden)),
        SimpleNamespace(complete=forbidden), tmp_path / 'workflow', 'family-private-runtime',
        controller_factory=controller, project_credit=task_credit, job_episodes=actual.family,
        annotation_child_roles=(), root_role=role, episode_binding_factories=(),
        wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
    assignment = {'job_ref': actual.job_ref, 'query_ref': actual.scope['subject_refs'][0], 'cpu': 1}
    if 'search_modes' in actual.jobs.config:
        assignment['search_mode'] = actual.jobs._row(actual.job_ref)['search_mode']
    if role != 'job_launch':
        assignment['handoff'] = {'job_ref': actual.job_ref, 'registry_ref': actual.jobs.config['registry_ref'],
            'backend': own('homology_jobs').VERSION, 'status_interface': 'homology.status.v1',
            'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
    if role == 'job_monitor': assignment.update(prior_sample_refs=[], prior_samples=[])
    # Like the retained original51 fixture, this is an explicit standalone
    # assignment. It does not claim the unsubmitted parent handoff was admitted.
    episode = workflow.build(role, 'actual-private-owner', 'Preserve actual family ownership',
        actual.scope, job_assignment=deepcopy(assignment))
    leaf = actual.family.for_role(role)
    assert type(episode.source) is leaf.decision_source_type
    assert type(episode.source).__module__ == type(leaf).__module__.removesuffix('.episode') + '.task'
    assert workflow.job_episodes is actual.family
    selected_controller = workflow.controller(episode.source.path)
    assert calls == [(episode.source.path, 0.)]
    assert workflow.action_schema(episode.source)
    assert leaf.instructions(role) in episode.source.instructions({})
    action = {'kind': 'tool', 'tool': {'job_launch': 'homology.configure', 'job_monitor': 'homology.sample',
        'job_results': 'homology.extract'}[role], 'arguments': {'limit': 1} if role == 'job_results' else {}}
    returned = asyncio.run(episode.source.execute(deepcopy(action), 0))
    row = workflow.journal.row('runtime_actions', episode.source.episode_id, 0)
    result = json.loads(row['result'])
    assert result['status'] == 'failed' and json.loads(row['action']) == action
    assert result['feedback']['code'] == ('configured_executable_unavailable_or_changed'
        if role == 'job_launch' else 'job_submission_handoff_unresolved')
    assert returned.as_record()['credit'] == 0.
    before = dict(row)
    assert asyncio.run(episode.source.execute(deepcopy(action), 0)).as_record() == returned.as_record()
    assert dict(workflow.journal.row('runtime_actions', episode.source.episode_id, 0)) == before
    assert not actual.jobs._row(actual.job_ref)['submission_requested']
    record_property('actual_private_family_failed_action_replay', json.dumps({'role': role,
        'private_task': type(episode.source).__module__ + '.' + type(episode.source).__qualname__,
        'request': episode.request.as_record(), 'action': action, 'result': result,
        'returned_progress': returned.as_record(), 'controller': selected_controller.state().as_record(),
        'selected_action_replay_identity_preserved': True, 'parent_handoff_admission_claimed': False,
        'complete_iterator_claimed': False}, sort_keys=True))


@pytest.mark.parametrize('role', ROLES)
def test_private_family_attachment_requires_actual_original_operand_identities(actual, role):
    leaf_type = type(actual.family.for_role(role))
    definition = options(actual.policy)
    # A same-shaped copy is not the explicit admitted owner's resource object.
    definition['_family_resources'] = actual.family
    with pytest.raises(ValueError, match='^original_homology_family_resource_identity_conflict$'):
        leaf_type(actual.jobs, **definition)
    definition['credit_binding'] = actual.family._role_credit_bindings['job_launch']
    definition['monitoring_binding'] = actual.family._role_credit_bindings['job_monitor']
    attached = leaf_type(actual.jobs, **definition)
    assert attached.__dict__ is actual.family.__dict__ and type(attached) is leaf_type
    definition['_family_resources'] = SimpleNamespace(**actual.family.__dict__)
    with pytest.raises(TypeError, match='^explicit_original_homology_family_resources_required$'):
        leaf_type(actual.jobs, **definition)


@pytest.mark.parametrize('role', ROLES)
def test_actual_parent_commission_preserves_admitted_launch_and_unsubmitted_read_denials(actual, role, tmp_path, record_property):
    def forbidden(*args, **kwargs):
        raise AssertionError('commission_boundary_does_not_authorize_model_or_native_work')
    workflow = own('runtime').Workflow(actual.store,
        own('tools').ToolRegistry(actual.store, clients=SimpleNamespace(request=forbidden)),
        SimpleNamespace(complete=forbidden), tmp_path / 'commission', 'original-homology-parent',
        controller_factory=lambda path, initial: own('numerical').YieldController('explicit-parent', initial, .5),
        project_credit=task_credit, job_episodes=actual.family, episode_binding_factories=(),
        annotation_child_roles=None, wait_inputs_version='wait_inputs_binding_v1',
        completed_action_inputs_version=None)
    parent = workflow.build('annotation', 'root', 'Original explicit job commissioner', actual.scope)
    selection = {'kind': 'job_child', 'role': role, 'goal': 'Inspect the assigned original job',
        'purpose': 'Retain actual custody without a native completion claim', 'scope': deepcopy(actual.scope),
        'schema_json': json.dumps({'type': 'object', 'properties': {
            'requested_role': {'type': 'string', 'enum': ['job_launch', 'job_monitor', 'job_results'],
                'description': 'Supplied parent-requested control role; no native outcome or submission claim.'}},
            'required': ['requested_role'], 'additionalProperties': False}),
        'initial_report_json': json.dumps({'requested_role': role})}
    if role == 'job_launch': selection['existing_job_ref'] = actual.job_ref
    else:
        selection['handoff'] = {'job_ref': actual.job_ref, 'registry_ref': actual.jobs.config['registry_ref'],
            'backend': own('homology_jobs').VERSION, 'status_interface': 'homology.status.v1',
            'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
        if role == 'job_monitor': selection['prior_sample_refs'] = []
    def rows(table):
        return [dict(row) for row in actual.store.db.execute(
            'SELECT * FROM ' + table + ' WHERE run_id=? ORDER BY rowid', (workflow.run_id,))]
    before_episodes, before_actions = rows('runtime_episodes'), rows('runtime_actions')
    before_jobs = registry_rows(actual.jobs)
    if role != 'job_launch':
        with pytest.raises(ValueError, match='^job_submission_handoff_unresolved$'):
            workflow.selected(parent.source, selection, 0)
        assert rows('runtime_episodes') == before_episodes and rows('runtime_actions') == before_actions
        observed = {'status': 'rejected_before_acquisition', 'reason': 'job_submission_handoff_unresolved',
            'executed_action': False, 'observation': False}
    else:
        unit = workflow.selected(parent.source, selection, 0)
        child = unit.child
        assert type(child.source) is actual.family.for_role(role).decision_source_type
        assert child.source.path == (*parent.source.path, (role, 'child_0'))
        request = child.request.as_record()
        assert request['message']['job_assignment']['job_ref'] == actual.job_ref
        assert request['message']['job_assignment']['cpu'] == 1
        saved = workflow.journal.row('runtime_actions', parent.source.episode_id, 0)
        assert json.loads(saved['action']) == selection and saved['result'] is saved['credit'] is None
        assert len(rows('runtime_episodes')) == len(before_episodes) + 1
        again = workflow.selected(parent.source, deepcopy(selection), 0)
        assert again.child.source.episode_id == child.source.episode_id
        assert again.child.request.as_record() == request
        assert dict(workflow.journal.row('runtime_actions', parent.source.episode_id, 0)) == dict(saved)
        observed = {'status': 'commissioned_not_executed', 'child_id': child.source.episode_id,
            'request': request, 'parent_action': selection, 'saved_credit': None,
            'reconstructed_same_child_request': True}
    assert registry_rows(actual.jobs) == before_jobs
    assert not actual.jobs._row(actual.job_ref)['submission_requested']
    record_property('actual_family_parent_commission', json.dumps({'role': role,
        'parent_id': parent.source.episode_id, 'parent_request': parent.request.as_record(),
        'observation': observed, 'native_submission_claimed': False,
        'unavailable_read_handoff_promoted_to_success': False}, sort_keys=True))
