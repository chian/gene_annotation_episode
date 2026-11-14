"""Actual private job_launch credit."""
from __future__ import annotations
from .message_contracts import ROLES, deepcopy, math
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_credit import project_homology_credit
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_fact_readers import project_credit_view_for_role

def project_credit_view(owner, source):
    role = source.path[-1][0]
    information = owner.monitoring_projector.information_view(source.workflow.store, assignment=owner.assignment(source), episode_id=source.episode_id, run_id=source.workflow.run_id) if owner.has_information_channel(role) else {}
    value = owner.initial_credit(source.workflow.store, role, owner.assignment(source), source.episode_id, source.workflow.run_id)
    return {'credit': value, **information}

class HomologySubmissionCredit:

    def credit_kind(self, role):
        """Declare the information kind of the existing controller projection."""
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        return 'operational'
