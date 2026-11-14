"""Original Terminal behavior on the six actual parent-private implementations."""
from copy import deepcopy
from importlib import import_module

import pytest

from gene_annotation_episode.episodic_workflow.root.numerical import NumericBand
from gene_annotation_episode.episodic_workflow.root import terminal_binding_catalogue as catalogue
from terminal_original_persistence import PracticalState
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
from terminal_private_boundary_checks import HOMES, ROOT, configuration, private, task_fixture, observe_next
import terminal_original_checks as original


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('check', [
    'test_receipt_replay_keeps_original_bytes_times_and_context',
    'test_progress_deduplicates_and_losses_remain_signed',
    'test_executed_unsuccessful_command_has_receipt_and_assessed_diagnostic',
])
def test_original_receipt_and_credit_controls(tmp_path, monkeypatch, home, check):
    private_state = import_module(ROOT + '.' + home.replace('/', '.') + '.execution_persistence').PracticalState
    with monkeypatch.context() as patch:
        patch.setattr(original, 'PracticalState', PracticalState)
        getattr(original, check)(tmp_path / 'original')
    with monkeypatch.context() as patch:
        patch.setattr(original, 'PracticalState', private_state)
        getattr(original, check)(tmp_path / 'private')


@pytest.mark.parametrize('home', HOMES)
def test_actual_private_estimator_keeps_verified_action_identity(tmp_path, home):
    binding, context = private(home, tmp_path)
    state = binding.state(context)
    original.finish(state, 'actual-completion', 'practical.job.collect', original.outcome_for(context.assignment))
    proof = state.completion_proof()
    assert proof is not None
    packet = original.completion_context(run_id=context.run_id, episode_id=context.episode_id)
    packet['practical_completion'].update(proof)
    before = deepcopy(packet)
    module = import_module(ROOT + '.' + home.replace('/', '.') + '.yield_estimator')
    estimate = binding.practical_estimator(context)((7,), module.YieldParameters(), (packet,))
    assert estimate.expected_next_gain == NumericBand.exact(0)
    assert estimate.turns == 1
    assert packet == before
    forged = deepcopy(packet)
    forged['practical_completion']['receipt_sha256'] = 'f' * 64
    # A valid-shaped but unverified claim must not close the assignment forecast.
    seen = []
    sentinel = object()
    estimator = binding.practical_estimator(context)
    estimator.base_estimate = lambda history, parameters: seen.append(history) or sentinel
    assert estimator((7,), module.YieldParameters(), (forged,)) is sentinel
    assert seen == [(7,)]




@pytest.mark.parametrize('home', HOMES)
def test_original_standalone_entries_and_nested_parent_requirement(tmp_path, home):
    if '/' in home:
        with pytest.raises(ValueError, match='terminal_task_identity_required'):
            task_fixture(home, tmp_path, standalone=True)
    else:
        value = task_fixture(home, tmp_path, standalone=True)
        try:
            assert value.task.path == ((value.context.role, 'child'),)
            assert value.context.role in value.binding.entry_roles
            assert value.task.episode_id
        finally:
            value.db.close()


@pytest.mark.parametrize('home', HOMES)
def test_recorded_parent_family_and_credit_routing(tmp_path, home):
    parent = ('legacy_annotation' if home.startswith('legacy_annotation/') else
              'scientific_process' if home.startswith('scientific_process/') else 'annotation')
    config = configuration(tmp_path)
    group = catalogue.construct_fixed_children(None, store=None, directory=tmp_path / 'group',
        configuration=config, parents=(parent,))
    descriptors = [value.as_record() for value in group]
    assert catalogue.descriptor_parents(config, descriptors) == (parent,)
    assert catalogue.fixed_descriptors(config, parents=(parent,)) == tuple(descriptors)
    binding = next(value for value in group if value.binding_path == home)
    _, context = private(home, tmp_path)
    registry = EpisodeBindingRegistry(group, owners=(catalogue.OWNER,) * len(group),
        terminal_configuration=config)
    assert registry.for_path(context.path, owner=catalogue.OWNER) is binding
    assert registry.for_child(context.path[:-1], context.role, owner=catalogue.OWNER) is binding
    assert registry.initial_decision_context(context) == {'execution_resource_information': {}}
    state = binding.state(context)
    original.finish(state, 'original-zero-return', 'practical.inspect', {'facts': {}})
    assert catalogue._project(group)(context, {}) == state.credit_view()
    if parent != 'annotation':
        assert all(value.entry_roles == () for value in group)
    changed = deepcopy(descriptors)
    changed[0]['version'] = 'not-the-recorded-definition'
    with pytest.raises(ValueError, match='root_terminal_fixed_group_conflict'):
        catalogue.descriptor_parents(config, changed)
