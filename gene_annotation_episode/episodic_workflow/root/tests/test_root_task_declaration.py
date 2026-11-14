"""Actual root declaration/factory selection; engineering construction only.

No problem/input/coverage rows, missing child head, model response, alternate
source class, iterator run, or scientific assessment is supplied by this test.
"""
from dataclasses import FrozenInstanceError, fields

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.task import AnnotationTask
from gene_annotation_episode.episodic_workflow.root.root_axis_scalars import AXES, VERSION


class ConstructorTools:
    def catalog(self, *, scope=None):
        return []

    def execute(self, *args, **kwargs):
        raise AssertionError('declaration selection must not execute a tool')


class ConstructorProvider:
    async def complete(self, episode_id, purpose, instructions, context, output_schema):
        raise AssertionError('declaration selection must not call a model')


@pytest.fixture
def real_root(tmp_path):
    # Same existing engineering declaration as test_combined_genome_cli; no
    # controller is invoked and these operands do not impose a work cutoff.
    binding = SignedRootEpisodeBinding.from_record({
        'version': 'signed_root_episode_binding_v2', 'initial_known_record_refs': [],
        'annotation_support': {'version': VERSION},
        'root_task': {'kind': 'annotation_axis_credit', 'cutoffs': {axis: .01 for axis in AXES},
                      'yield_parameters': {'uncertainty_alpha': .05}}})
    with Store(tmp_path / 'store') as store:
        workflow = create_signed_evidence_root_workflow(store, ConstructorTools(), ConstructorProvider(),
            tmp_path / 'workflow', 'root-declaration-engineering', binding.yield_controller,
            initial_known_record_refs=binding.initial_known_record_refs,
            project_credit=binding.task_credit, credit_binding=binding.task_credit.as_record(),
            controller_binding=binding.controller_record(),
            episode_binding_factories=(), annotation_child_roles=())
        assert type(workflow) is Workflow
        assert not workflow.episode_bindings.roles
        yield store, binding, workflow
        # Construction and route lookup acquire no unit and fabricate no input.
        for table in ('problem', 'inputs', 'runtime_episodes', 'runtime_actions',
                      'runtime_observations', 'runtime_model_calls'):
            assert store.db.execute('SELECT count(*) AS n FROM ' + table).fetchone()['n'] == 0


def test_actual_factory_selects_explicit_root_declaration(real_root):
    _, binding, workflow = real_root
    assert SignedRootEpisodeBinding.decision_source_type is AnnotationTask
    assert binding.decision_source_type is AnnotationTask
    for key in ('root', 'independent-root-key'):
        assert workflow.task_source_for_path((('annotation', key),)) is binding.decision_source_type
    assert binding.roles == binding.entry_roles == ('annotation',)
    assert [field.name for field in fields(binding)] == [
        'initial_known_record_refs', 'axis_yield_cutoffs', 'yield_parameters', 'annotation_support']
    assert workflow.project_credit.task_credit is True
    assert workflow.project_annotation_score.task_credit is False
    assert workflow.controller_factory.__self__ is binding
    assert workflow.controller_binding == binding.controller_record()
    assert workflow.credit_binding == binding.task_credit.as_record()
    with pytest.raises(FrozenInstanceError):
        binding.annotation_support = None


def test_missing_root_declaration_is_rejected_without_hardcoded_fallback(real_root, monkeypatch):
    _, _, workflow = real_root
    # Removing an operand proves that selection reads the declared owner. No
    # alternate implementation or fabricated missing scientific head is used.
    monkeypatch.setattr(SignedRootEpisodeBinding, 'decision_source_type', None)
    with pytest.raises(LookupError, match='^private_episode_task_not_bound:annotation$'):
        workflow.task_source_for_path((('annotation', 'root'),))


@pytest.mark.parametrize('path,exception,message', [
    ((), ValueError, '^identity path must be a non-empty sequence$'),
    ((('scientific_process', 'root'),), LookupError, '^episode_role_not_bound:scientific_process$'),
    ((('improvement', 'root'),), LookupError, '^episode_role_not_bound:improvement$'),
    ((('annotation', 'parent'), ('annotation', 'child')), LookupError, '^episode_role_not_bound:annotation$'),
    ((('scientific_process', 'parent'), ('annotation', 'child')), LookupError, '^episode_role_not_bound:scientific_process$'),
])
def test_factory_selector_keeps_original_foreign_and_nested_rejection(real_root, path, exception, message):
    _, _, workflow = real_root
    with pytest.raises(exception, match=message):
        workflow.task_source_for_path(path)


class UnavailableRuntimeOperand:
    def __getattribute__(self, name):
        raise AssertionError('wrong path touched runtime operand: ' + name)


@pytest.mark.parametrize('path', [
    (), (('scientific_process', 'root'),), (('improvement', 'root'),),
    (('annotation', 'parent'), ('annotation', 'child')),
    (('scientific_process', 'parent'), ('annotation', 'child')),
])
def test_declared_task_preserves_original_constructor_path_guard(path):
    task_type = SignedRootEpisodeBinding.decision_source_type
    source = object.__new__(task_type)
    unavailable = UnavailableRuntimeOperand()
    with pytest.raises(ValueError, match='^annotation_task_requires_root_annotation_identity$'):
        task_type.__init__(source, unavailable, path, unavailable, unavailable)
    assert vars(source) == {}
