"""Explicit scientific-score binding for the shared episode runtime.

This binds the existing evidence projection; it adds no second scoring path.
The caller supplies the complete policy. Scientific children use that projection
over their fixed commissioned scope, with the runtime recording inherited credit
as their initial baseline. Local scores are never added to the parent's score.
"""
from dataclasses import dataclass, replace

from .credit import CreditPolicy, FORMULA_VERSION, PROJECTION_VERSION, STABLE_INTEGRATION, project_credit
from .finding_validity import VALIDITY_VERSION


@dataclass(frozen=True)
class ScientificEvidenceCredit:
    policy: CreditPolicy

    def __post_init__(self):
        if not isinstance(self.policy, CreditPolicy):
            raise TypeError('explicit_scientific_CreditPolicy_required')

    def as_record(self):
        return {
            'kind': 'softened_evidence_hypervolume',
            'projection_version': PROJECTION_VERSION,
            'formula_version': FORMULA_VERSION,
            'policy': self.policy.as_record(),
            'scope': 'fixed_original_input_scope_of_this_episode',
            'baseline': 'inherited_current_scoped_evidence_credit',
            'parent_projection': 'same_recorded_scientific_state_not_sum_of_child_scores',
            'interpretation': 'evidence_progress_proxy_not_probability_of_correctness',
        }

    @staticmethod
    def _scope(store, scope, assignment):
        effective = store.validate_scope(scope)
        if assignment is not None and store.validate_scope(assignment['scope']) != effective:
            raise ValueError('scientific_credit_scope_differs_from_original_commission')
        return effective

    def __call__(self, store, scope, *, assignment=None, episode_id=None, run_id=None):
        # IDs identify the runtime invocation, not additional evidence or score.
        return project_credit(store, self._scope(store, scope, assignment), self.policy,
                              details_limit=0)

    def read_details(self, store, scope, *, details_limit, details_offset,
                     assignment=None, episode_id=None, run_id=None):
        return project_credit(store, self._scope(store, scope, assignment), self.policy,
            details_limit=details_limit, details_offset=details_offset).as_record()


@dataclass(frozen=True)
class ScientificInvestigationCredit(ScientificEvidenceCredit):
    """Same evidence projection, admitting recorded local interpretation accounts.

    Existing scoped accounts form the inherited baseline. Accounts compete as
    whole coherent explanations; copied accounts and child scalar scores are
    never added together. Root annotation credit remains a separate projection.
    """

    def as_record(self):
        return {**super().as_record(),
            'eligible_account_kinds': ['annotation', 'interpretation_account'],
            'account_selection': 'same_whole_coherent_account_maximum_not_sum',
            'parent_projection': 'parent_uses_its_own_binding_not_sum_of_child_scores',
            'task_projection': 'controlled_by_the_separate_task_credit_binding',
            'account_ownership': 'runtime_bound_episode_and_immutable_commission_scope',
            'version': 'scientific_investigation_accounts_v1'}

    def __call__(self, store, scope, *, assignment=None, episode_id=None, run_id=None):
        return project_credit(store, self._scope(store, scope, assignment), self.policy,
            details_limit=0, include_interpretation_accounts=True)

    def read_details(self, store, scope, *, details_limit, details_offset,
                     assignment=None, episode_id=None, run_id=None):
        return project_credit(store, self._scope(store, scope, assignment), self.policy,
            details_limit=details_limit, details_offset=details_offset,
            include_interpretation_accounts=True).as_record()


@dataclass(frozen=True)
class AnnotationSupportScore(ScientificEvidenceCredit):
    """Separately reported annotation support, with invariant cell integration.

    Legacy scientific-credit adapters retain their frozen arithmetic. This
    adapter is an explicit new binding, not a change to old yield histories or
    an investigation-progress formula. Evidence operands and hypervolume match
    the existing rule; equal component vectors share exact integer masses.
    """

    def as_record(self):
        return {'kind': 'softened_evidence_hypervolume_annotation_support',
            'projection_version': PROJECTION_VERSION, 'formula_version': FORMULA_VERSION,
            'integration_arithmetic': STABLE_INTEGRATION, 'policy': self.policy.as_record(),
            'finding_validity_version': VALIDITY_VERSION,
            'scope': 'fixed_original_input_scope_of_this_episode',
            'interpretation': 'annotation_support_not_investigation_progress',
            'controller_effect': 'none_in_the_separate_annotation_score_channel'}

    def __call__(self, store, scope, *, assignment=None, episode_id=None, run_id=None):
        projected = project_credit(store, self._scope(store, scope, assignment), self.policy,
            details_limit=0, integration_arithmetic=STABLE_INTEGRATION)
        return replace(projected, interpretation='annotation_support_not_investigation_progress')

    def read_details(self, store, scope, *, details_limit, details_offset,
                     assignment=None, episode_id=None, run_id=None):
        result = project_credit(store, self._scope(store, scope, assignment), self.policy,
            details_limit=details_limit, details_offset=details_offset,
            integration_arithmetic=STABLE_INTEGRATION).as_record()
        result['interpretation'] = 'annotation_support_not_investigation_progress'
        return result
