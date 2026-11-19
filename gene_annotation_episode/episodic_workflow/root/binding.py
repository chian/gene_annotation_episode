"""The root annotation episode's binding on ``episode_runtime``.

Its child slots are the nine attached evidence-axis heads (``axes.ATTACHMENTS``);
each slot is the head's role and binding path. The entry input is
``{'subject', 'proposed_annotation_ref'?, 'constraints'?}``; the subject must be
a scope the run's ``store`` admits. Weights, cutoffs and the yield setting are
explicit construction arguments; nothing is defaulted.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from episode_runtime import Commission, RecordForm
from method_loop import Episode, EpisodeGoal, EpisodeRequest

from .axes import AXIS_ROLES
from .continuation import AnnotationController, AxisReturn
from .credit import finite_number
from .decisions import CONSTRAINTS_FIELD, MODEL_PROVIDER, PROPOSED_FIELD, RootDecisionSource
from .goal import GOAL, RESULT, UNIT
from .report import RETURN_FORM, Record, build_report

STORE = 'store'
SCOPE_KEYS = frozenset({'subject_refs', 'segments', 'read_selection_refs'})


def _per_axis(values, what):
    if not isinstance(values, Mapping) or set(values) != set(AXIS_ROLES):
        raise KeyError(what + '_must_name_exactly_the_attached_axes')
    return MappingProxyType({role: finite_number(values[role], what + ':' + role) for role in AXIS_ROLES})


class RootAnnotationBinding:
    """The root annotation episode: nine evidence-axis children, hypervolume credit, per-axis continuation."""

    binding_path = 'annotation'
    grain_name = 'annotation'
    goal, unit, result = GOAL, UNIT, RESULT
    child_slots = MappingProxyType({role: role for role in AXIS_ROLES})
    required_collaborators = (STORE, MODEL_PROVIDER)
    assignment_form = RecordForm({})
    return_form = RETURN_FORM

    def __init__(self, axis_weights, axis_cutoffs, uncertainty_alpha):
        self.axis_weights = _per_axis(axis_weights, 'axis_weight')
        if any(weight <= 0 for weight in self.axis_weights.values()):
            raise ValueError('axis_weights_must_be_positive')
        self.axis_cutoffs = _per_axis(axis_cutoffs, 'axis_cutoff')
        if any(cutoff < 0 for cutoff in self.axis_cutoffs.values()):
            raise ValueError('axis_cutoffs_must_not_be_negative')
        self.uncertainty_alpha = finite_number(uncertainty_alpha, 'uncertainty_alpha')
        AnnotationController(self.axis_weights, self.axis_cutoffs, self.uncertainty_alpha)  # settings admitted now

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if parent_goal is not None:
            raise ValueError('annotation_root_has_no_parent_goal')
        if (not isinstance(entry_input, Mapping)
                or not {'subject'} <= set(entry_input) <= {'subject', PROPOSED_FIELD, CONSTRAINTS_FIELD}):
            raise ValueError('annotation_entry_requires_subject_and_optional_proposed_annotation_ref_and_constraints')
        subject = entry_input['subject']
        if not isinstance(subject, Mapping) or 'subject_refs' not in subject or not set(subject) <= SCOPE_KEYS:
            raise ValueError('annotation_subject_must_be_a_store_scope:' + repr(subject)[:200])
        try:
            message = {'subject': collaborators[STORE].validate_scope(dict(subject))}
        except ValueError as error:
            raise ValueError('annotation_subject_scope_not_admitted:' + str(error)) from error
        if PROPOSED_FIELD in entry_input:
            if type(entry_input[PROPOSED_FIELD]) is not str or not entry_input[PROPOSED_FIELD]:
                raise ValueError('annotation_proposed_annotation_ref_must_be_text')
            message[PROPOSED_FIELD] = entry_input[PROPOSED_FIELD]
        if CONSTRAINTS_FIELD in entry_input:
            if not isinstance(entry_input[CONSTRAINTS_FIELD], Mapping):
                raise ValueError('annotation_constraints_must_be_a_record')
            message[CONSTRAINTS_FIELD] = dict(entry_input[CONSTRAINTS_FIELD])
        goal = EpisodeGoal.root(objective=self.goal, result_contract={
            'credit': 'weighted offset-product hypervolume over ' + ', '.join(AXIS_ROLES)})
        return Commission(EpisodeRequest(goal, Record(message)), {})

    def build_controller(self, bound, collaborators):
        return AnnotationController(self.axis_weights, self.axis_cutoffs, self.uncertainty_alpha)

    def build_episode(self, grain, bound, collaborators, child_builders):
        source = RootDecisionSource(self, bound, collaborators, child_builders)
        subject = bound.request.message.as_record()['subject']
        return Episode(grain, bound.key, source, bound.request, lambda record: build_report(subject, record))

    def restore_controller_input(self, record):
        return AxisReturn.from_record(record)


__all__ = ['RootAnnotationBinding', 'STORE']
