"""Real two-parent Workflow/Store/Journal controls; no invented scientific work."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import json
import pytest
from .homology_direction_checks import actual, commission, form, module, raw_rows, forbidden, zero


@contextmanager
def paired(directory, role):
    with actual(directory, parent='annotation', receipts=True, role=role) as annotation:
        runtime = module('runtime')
        supplied = annotation.families['legacy_improvement'][role]
        workflow = runtime.Workflow(annotation.store, annotation.flow.tools,
            annotation.flow.provider, directory / 'improvement-workflow',
            'homology-parent-counterpart-improvement', controller_factory=forbidden,
            project_credit=zero, job_episodes=supplied, episode_binding_factories=(),
            root_role='improvement', annotation_child_roles=(role,),
            episode_record_receipts=True,
            initial_known_record_refs=list(annotation.scope['subject_refs']),
            root_action_boundary=None)
        root = workflow.build('improvement', 'original-parent',
            'Preserve the requested execution information.', annotation.scope)
        family = workflow.homology_episode_bindings
        improvement = SimpleNamespace(**{**vars(annotation), 'flow': workflow,
            'root': root, 'source': root.source, 'binding': family['legacy_improvement'][role],
            'bindings': family['legacy_improvement'], 'families': family,
            'parent': 'improvement', 'parent_home': 'legacy_improvement'})
        assert annotation.binding.jobs is improvement.binding.jobs
        yield annotation, improvement


def assert_parent_implementations(directory, role):
    with paired(directory, role) as pair:
        left, right = pair
        assert type(left.binding) is not type(right.binding)
        assert type(left.binding).__module__ != type(right.binding).__module__
        own_fields = {'binding_id', 'commissioning_parent', 'owner_class', 'task_class', 'implementation_sha256'}
        records = [value.binding.as_record() for value in pair]
        assert {key: value for key, value in records[0].items() if key not in own_fields} == {
            key: value for key, value in records[1].items() if key not in own_fields}
        assert records[0]['implementation_sha256'] != records[1]['implementation_sha256']
        assert left.binding.parser_policy is right.binding.parser_policy
        assert left.binding.statistics is right.binding.statistics
        assert left.binding.native_event_provider is right.binding.native_event_provider
        for value, descriptor in zip(pair, records):
            parent = value.flow.legacy_parent_for_path(value.source.path)
            assert parent.binding_path == value.parent_home
            assert type(value.source) is parent.decision_source_type
            assert value.flow.specialist(value.source) is None
            commissioned = commission(value)
            unit = value.flow.selected(value.source, deepcopy(value.selection), 0)
            assert value.flow.job_episode_for_path(unit.child.source.path) is value.binding
            assert type(unit.child.source) is value.binding.decision_source_type
            assert value.binding.roles == (role,)
            assert value.binding.binding_path.startswith(value.parent_home + '/')
            assert descriptor['binding_id'] == value.binding.binding_path
            assert descriptor['commissioning_parent'] == value.parent_home
            assert descriptor['owner_class'] == type(value.binding).__module__ + '.' + type(value.binding).__qualname__
            assert descriptor['task_class'] == type(unit.child.source).__module__ + '.' + type(unit.child.source).__qualname__
            assert commissioned['descriptor'] == descriptor
            family_record = module('homology_service_setup').homology_binding_record(
                value.binding, family=value.flow.homology_episode_bindings)
            assert family_record['version'] == 'parent_private_homology_bindings_v1'
            assert family_record['active_roles'] == [role]
            assert set(family_record['parents']) == {'legacy_annotation', 'legacy_improvement'}
            saved = family_record['parents'][value.parent_home]
            assert saved['parent'] == parent.as_record() and saved['children'] == {role: descriptor}


def assert_saved_parent_counterpart(directory, role):
    with paired(directory, role) as pair:
        for value, foreign in (pair, tuple(reversed(pair))):
            first = commission(value)
            assert commission(value) == first
            unit = value.flow.selected(value.source, deepcopy(value.selection), 0)
            child = unit.child.source
            value.flow.save_attempt(value.source.episode_id, 0, 'original-parent-specific-delivery',
                child.episode_id, unit.child.request.report_contract, form={'state': 'unresolved'})
            parent = value.flow.legacy_parent_for_path(value.source.path)
            assert value.flow.receive_form(value.source, {'state': 'unresolved'}, form(), 0) == []
            before = raw_rows(value.flow)
            assert value.flow.receive_form(value.source, {'state': 'unresolved'}, form(), 0, redelivery=True) == []
            assert raw_rows(value.flow) == before

            # Persist the actual repair boundary without inventing a completed
            # action, scientific evidence, or controller credit. The saved
            # attempt, rather than a role in this selection, identifies its child.
            repair = {'kind': 'redeliver_report',
                'delivery_ref': 'original-parent-specific-delivery',
                'purpose': value.selection['purpose'],
                'schema_json': value.selection['schema_json']}
            value.flow.journal.save('runtime_actions', {'episode_id': value.source.episode_id,
                'decision_index': 1, 'action': json.dumps(repair), 'result': None, 'credit': None})
            value.flow.save_attempt(value.source.episode_id, 1, repair['delivery_ref'],
                child.episode_id, unit.child.request.report_contract, form={'state': 'unresolved'})
            assert module('delivery_counterpart').child_role_for_delivery(value.flow, value.source, 1) == role
            receiver = parent.child_report_receiver(role)
            endpoint = module(value.parent_home + '.episode')
            assert getattr(endpoint, receiver.__name__) is receiver
            calls = []
            def observed(workflow, source, admitted, schema, index, *, redelivery=False):
                calls.append((workflow, source, index, redelivery))
                return receiver(workflow, source, admitted, schema, index, redelivery=redelivery)
            with patch.object(endpoint, receiver.__name__, observed):
                assert value.flow.receive_form(value.source, {'state': 'unresolved'}, form(), 1, redelivery=True) == []
                repaired = raw_rows(value.flow)
                assert value.flow.receive_form(value.source, {'state': 'unresolved'}, form(), 1, redelivery=True) == []
                assert raw_rows(value.flow) == repaired
            assert calls == [(value.flow, value.source, 1, True)] * 2
            repair_row = value.flow.journal.row('runtime_actions', value.source.episode_id, 1)
            assert json.loads(repair_row['action']) == repair
            assert repair_row['result'] is None and repair_row['credit'] is None
            attempts = raw_rows(value.flow)['runtime_report_attempts']
            assert [row['child_episode_id'] for row in attempts] == [child.episode_id, child.episode_id]
            assert [row['decision_index'] for row in attempts] == [0, 1]
            assert value.flow.job_episode_for_path(child.path) is value.binding
            assert value.flow.journal.row('runtime_episodes', child.episode_id)['request'] == first['request_raw']
            assert value.flow.journal.row('runtime_episodes', child.episode_id)['path'] == first['path_raw']
            foreign_parent = foreign.flow.legacy_parent_for_path(foreign.source.path)
            receiver = foreign_parent.child_report_receiver(role)
            assert receiver is not parent.child_report_receiver(role)
            both_before = [raw_rows(item.flow) for item in pair]
            with pytest.raises(ValueError, match='^private_legacy_' + foreign.parent + '_path_required$'):
                receiver(value.flow, value.source, {'state': 'unresolved'}, form(), 1, redelivery=True)
            with pytest.raises(ValueError, match='^private_legacy_' + foreign.parent + '_path_required$'):
                foreign.binding.decision_source_type(value.flow, child.path, child.request, child.scope)
            assert [raw_rows(item.flow) for item in pair] == both_before
            assert value.flow.journal.row('runtime_actions', value.source.episode_id, 0)['result'] is None
            assert raw_rows(value.flow)['runtime_observations'] == []

        # Save assertions about actual records, not a new reconstruction format.
        # The original explicit caller below reconstructs its own bindings and
        # Workflow from the same real Store and registry directories.
        originals = pair
        configuration_bytes = (pair[0].jobs.directory / 'configuration.json').read_bytes()
        registry_bytes = (pair[0].jobs.directory / 'jobs.sqlite').read_bytes()
        expected = []
        for value in pair:
            parent = value.flow.legacy_parent_for_path(value.source.path)
            expected.append({'run_id': value.flow.run_id, 'parent': value.parent,
                'parent_home': value.parent_home, 'parent_id': value.source.episode_id,
                'parent_descriptor': parent.as_record(),
                'child_descriptor': value.binding.as_record(),
                'family_descriptor': module('homology_service_setup').homology_binding_record(
                    value.binding, family=value.flow.homology_episode_bindings),
                'selection': value.selection, 'rows': raw_rows(value.flow)})
        checkpoint = directory / 'saved-parent-counterpart.json'
        checkpoint_bytes = json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()
        checkpoint.write_bytes(checkpoint_bytes)

    # Exiting paired() closes the real registry and Store. A new paired context
    # uses their saved configuration/data and the unchanged public constructor.
    with paired(directory, role) as reopened:
        assert reopened[0].store is not originals[0].store
        assert reopened[0].store.db is not originals[0].store.db
        assert reopened[0].jobs is not originals[0].jobs
        assert reopened[0].jobs.db is not originals[0].jobs.db
        assert reopened[0].store.path == originals[0].store.path
        assert reopened[0].jobs.directory == originals[0].jobs.directory
        assert reopened[0].store is reopened[1].store
        assert reopened[0].binding.jobs is reopened[1].binding.jobs
        assert checkpoint.read_bytes() == checkpoint_bytes
        saved_pair = json.loads(checkpoint.read_bytes())
        assert (reopened[0].jobs.directory / 'configuration.json').read_bytes() == configuration_bytes
        assert (reopened[0].jobs.directory / 'jobs.sqlite').read_bytes() == registry_bytes

        for value, original, saved, foreign in zip(reopened, originals, saved_pair, reversed(reopened)):
            assert value.flow is not original.flow
            assert value.flow.run_id == saved['run_id']
            assert value.parent == saved['parent'] and value.parent_home == saved['parent_home']
            assert value.source.episode_id == saved['parent_id']
            assert type(value.source) is type(original.source)
            assert value.binding is not original.binding and type(value.binding) is type(original.binding)
            parent = value.flow.legacy_parent_for_path(value.source.path)
            assert parent.as_record() == saved['parent_descriptor']
            assert value.binding.as_record() == saved['child_descriptor']
            family_record = module('homology_service_setup').homology_binding_record(
                value.binding, family=value.flow.homology_episode_bindings)
            assert family_record == saved['family_descriptor']
            assert family_record['active_roles'] == [role]
            assert set(family_record['parents']) == {'legacy_annotation', 'legacy_improvement'}
            assert raw_rows(value.flow) == saved['rows']
            value.source.restore()
            assert value.source._restored is True

            # Reuse the saved action; build authenticates the immutable request.
            action = value.flow.journal.row('runtime_actions', value.source.episode_id, 0)
            selection = json.loads(action['action'])
            assert selection == saved['selection']
            unit = value.flow.selected(value.source, selection, 0)
            child = unit.child.source
            attempts = saved['rows']['runtime_report_attempts']
            assert child.episode_id == attempts[0]['child_episode_id'] == attempts[1]['child_episode_id']
            assert value.flow.job_episode_for_child(value.source.path, role) is value.binding
            assert value.flow.job_episode_for_path(child.path) is value.binding
            assert type(child) is value.binding.decision_source_type
            assert value.flow.specialist(value.source) is None
            assert value.flow.specialist(child) is None
            child.restore()
            assert child._restored is True
            assert raw_rows(value.flow) == saved['rows']

            # The saved repair action has no child role. Its original attempt
            # must still select this parent's actual receiver after reopening.
            repair_row = value.flow.journal.row('runtime_actions', value.source.episode_id, 1)
            assert 'role' not in json.loads(repair_row['action'])
            assert module('delivery_counterpart').child_role_for_delivery(value.flow, value.source, 1) == role
            receiver = parent.child_report_receiver(role)
            endpoint = module(value.parent_home + '.episode')
            assert getattr(endpoint, receiver.__name__) is receiver
            calls = []
            def observed(workflow, source, admitted, schema, index, *, redelivery=False):
                calls.append((workflow, source, index, redelivery))
                return receiver(workflow, source, admitted, schema, index, redelivery=redelivery)
            with patch.object(endpoint, receiver.__name__, observed):
                for _ in range(2):
                    assert value.flow.receive_form(value.source, {'state': 'unresolved'}, form(), 1, redelivery=True) == []
                    assert raw_rows(value.flow) == saved['rows']
            assert calls == [(value.flow, value.source, 1, True)] * 2
            foreign_parent = foreign.flow.legacy_parent_for_path(foreign.source.path)
            foreign_receiver = foreign_parent.child_report_receiver(role)
            assert foreign_receiver is not receiver
            with pytest.raises(ValueError, match='^private_legacy_' + foreign.parent + '_path_required$'):
                foreign_receiver(value.flow, value.source, {'state': 'unresolved'}, form(), 1, redelivery=True)
            with pytest.raises(ValueError, match='^private_legacy_' + foreign.parent + '_path_required$'):
                foreign.binding.decision_source_type(value.flow, child.path, child.request, child.scope)
            assert raw_rows(value.flow) == saved['rows']
            assert all(row['result'] is None and row['credit'] is None
                       for row in saved['rows']['runtime_actions'])
            assert saved['rows']['runtime_observations'] == []

        assert [raw_rows(value.flow) for value in reopened] == [saved['rows'] for saved in saved_pair]
        assert checkpoint.read_bytes() == checkpoint_bytes
        assert (reopened[0].jobs.directory / 'configuration.json').read_bytes() == configuration_bytes
        assert (reopened[0].jobs.directory / 'jobs.sqlite').read_bytes() == registry_bytes
