"""Scientific commissioning rejects job-child alternatives before acquisition."""
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105 import runtime
from .test_private_experimental_activity_evidence import scientific_binding


@pytest.mark.parametrize('role', ['experimental_activity_evidence', 'literature'])
def test_scientific_parent_accepts_declared_episode_kind_and_rejects_job_kind(role):
    binding = scientific_binding()
    source = SimpleNamespace(path=(('annotation', 'original-parent'), ('experimental_activity_evidence', 'original-child')))
    roles = binding.child_roles('experimental_activity_evidence')
    workflow = SimpleNamespace(project_credit=SimpleNamespace(), annotation_child_roles=roles,
        available_child_roles=lambda source: roles, specialist=lambda source: binding,
        job_episodes=SimpleNamespace(roles=roles), episode_bindings=SimpleNamespace(roles=roles))
    runtime.Workflow.validate_child_choice(workflow, source, role,
        selection={'kind': 'episode_child', 'role': role})
    with pytest.raises(ValueError, match='child_kind_not_available_to_parent'):
        runtime.Workflow.validate_child_choice(workflow, source, role,
            selection={'kind': 'job_child', 'role': role})
