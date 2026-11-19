"""episode_runtime contract hooks shared by A107's 28 descendant bindings.

Each descendant binding (one ``episode.py`` per home below the head) declares
its ``binding_path``, ``goal``, ``unit``, ``result``, ``child_slots`` and
``commissioning_parent``, and takes its own ``build_episode`` from the runtime
it mixes in (job submission, API, HPC and local job execution, progress
monitoring, result acquisition, HPC planning, prediction and allocation) or
from ``published_evidence_assessment/literature_binding.LiteratureBinding``,
the subclass of this class the literature bindings use. This module supplies the remaining hooks:
``grain_name``, ``required_collaborators``, ``assignment_form`` /
``return_form``, ``entry_request`` (a root or inner ``Commission``),
``build_controller`` (the A107 accumulation yield controller over unbounded
cumulative credit, with the caller's explicit continuation settings) and
``restore_controller_input``. A runtime mixed in before this class may
override any of them.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from episode_runtime import Commission, Field, RecordForm, grain_name_for
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract


class RuntimeBindingError(ValueError):
    """A collaborator or input does not satisfy this binding's contract."""


@dataclass(frozen=True)
class UnitRecord(ClosedRecord):
    """One A107 controller input or request message: plain JSON values."""
    value: dict

    def as_record(self):
        return dict(self.value)


def _contract(value, what):
    if not isinstance(value, Mapping) or set(value) != {'decision', 'measurements', 'information'}:
        raise RuntimeBindingError('a107_report_contract_required:' + what)
    return {'decision': value['decision'], 'measurements': dict(value['measurements']),
            'information': dict(value['information'])}


RETURN_FORM = RecordForm({
    'credit': Field('number', "This episode's own cumulative credit; unbounded, never clamped or rescaled"),
    'finding': Field('record', 'Its report: the retained typed findings with source, subject, scope and limits'),
})
DESCENDANT_ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', "The commissioning parent's Store scope for this episode"),
    'assignment': Field('record', "The binding's own commissioned assignment"),
})


class DescendantBinding:
    """The episode_runtime hooks of an A107 descendant binding (see module docstring)."""

    required_collaborators = ('store', 'model_provider', 'continuation')
    assignment_form = DESCENDANT_ASSIGNMENT_FORM
    return_form = RETURN_FORM

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping) or set(entry_input) - {'objective', 'scope', 'assignment',
                                                                        'report_contract'} \
                or not isinstance(entry_input.get('objective'), str) or not entry_input['objective'].strip():
            raise RuntimeBindingError('a107_entry_objective_scope_and_assignment_required:' + self.binding_path)
        assignment = self.assignment_form.admit(
            {'scope': entry_input.get('scope'), 'assignment': entry_input.get('assignment')}, self.binding_path)
        message = UnitRecord({'objective': entry_input['objective']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'],
                                    result_contract={'binding_path': self.binding_path, 'result': self.result})
            return Commission(EpisodeRequest(goal, message), assignment)
        contract = _contract(entry_input.get('report_contract'), self.binding_path)
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment)

    def build_controller(self, bound, collaborators):
        from yield_control import AccumulationYieldController, YieldParameters
        continuation = collaborators['continuation']
        settings = continuation.get(self.binding_path) if isinstance(continuation, Mapping) else None
        if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters'}:
            raise RuntimeBindingError('a107_continuation_settings_required:' + self.binding_path)
        # Cumulative credit from zero; never bounded or rescaled.
        return AccumulationYieldController(bound.episode_id, 0.0, settings['cutoff'], YieldParameters(**settings['parameters']))

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping) or 'credit' not in record:
            raise RuntimeBindingError('a107_recorded_unit_requires_credit:' + self.binding_path)
        return UnitRecord(dict(record))


__all__ = ['DESCENDANT_ASSIGNMENT_FORM', 'DescendantBinding', 'RETURN_FORM',
           'RuntimeBindingError', 'UnitRecord']
