"""A110 bindings' implementation of the episode_runtime contract.

Each A110 binding class declares its own ``binding_path``, ``grain_name``
(``binding_path.replace('/', '__')``), ``goal``, ``unit``, ``result``,
``child_slots``, ``required_collaborators``, ``assignment_form`` and
``return_form`` explicitly (see each ``episode.py``). This mixin supplies the other
callable hooks of docs/axis_restructure_20261117/BINDING_CONTRACT.md.

Every binding supplies its own ``build_episode`` from its decision source: the
head and the literature bindings the A110 unit source (``unit_source.py``), the
others their own runtime (job submission, local and HPC job execution, HPC
planning, prediction and allocation, progress monitors and result acquisition).

Nothing is defaulted: a missing collaborator, setting or field raises. Credit
is the episode's own unbounded cumulative value; it is never clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from episode_runtime import Commission, Field, RecordForm
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import ContractError

# Runtime collaborators the A110 episodes read (standard episode_runtime names):
# the model provider that makes their decisions, the run's shared evidence Store
# (gene_annotation_episode.state.Store, ruling C4), and the numerical continuation
# settings of each episode's YieldController, keyed by binding path. Each A110
# binding's tool registry is its own, built by the A110 home factory (ruling C4).
REQUIRED_COLLABORATORS = ('model_provider', 'store', 'continuation')

SCOPE = Field('record', 'The subject this A110 episode investigates (the annotation subject record)')
# An A110 child receives the subject and the record its commissioning parent prepared for it.
ASSIGNMENT = Field('record', 'The commissioning parent\'s record for this episode: its question, context and '
                             'the received records it passes on')
CHILD_ASSIGNMENT_FORM = RecordForm({'scope': SCOPE, 'assignment': ASSIGNMENT})
RETURN_FORM = RecordForm({
    'credit': Field('number', "This episode's own cumulative credit on its unbounded scale"),
    'finding': Field('text', 'What this A110 episode established'),
    'assessment_refs': Field('list', 'The assessment records whose retained findings this episode knows: '
                                     'its own committed assessments and those its children returned'),
})
# What an A110 parent asks of an A110 child's report (method_loop ReportContract information).
CHILD_REPORT = {'finding': 'What this A110 episode established',
                'credit': "This episode's own cumulative credit on its unbounded scale"}
# The continuation settings each A110 episode's YieldController requires.
CONTINUATION_FIELDS = frozenset({'cutoff', 'parameters'})


@dataclass(frozen=True)
class RuntimeRecord(ClosedRecord):
    """A JSON record crossing the runner's journal boundary."""
    value: Mapping

    def as_record(self):
        return dict(self.value)


class EpisodeRuntimeContract:
    """The callable contract hooks; declarations live on each binding class."""

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        """``entry_input`` = ``{'objective', 'assignment'}``; the assignment is admitted against ``assignment_form``."""
        if not isinstance(entry_input, Mapping) or set(entry_input) != {'objective', 'assignment'}:
            raise ContractError('a110_entry_input_requires_objective_and_assignment:' + self.binding_path)
        assignment = self.assignment_form.admit(entry_input['assignment'], 'a110_entry_assignment')
        message = RuntimeRecord({'binding_path': self.binding_path, 'scope': assignment['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'],
                                    result_contract={'binding_path': self.binding_path, 'result': self.result})
            return Commission(EpisodeRequest(goal, message), assignment)
        report = ReportContract(decision=self.goal, measurements={}, information=CHILD_REPORT)
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=report.as_record())
        return Commission(EpisodeRequest(goal, message, report), assignment)

    def build_controller(self, bound, collaborators):
        """The episode's own AccumulationYieldController over its unbounded cumulative credit."""
        settings = collaborators['continuation']
        if self.binding_path not in settings:
            raise ContractError('a110_continuation_settings_missing:' + self.binding_path)
        declared = settings[self.binding_path]
        if not isinstance(declared, Mapping) or set(declared) != CONTINUATION_FIELDS:
            raise ContractError('a110_continuation_settings_require_cutoff_and_parameters:' + self.binding_path)
        from yield_control import AccumulationYieldController, YieldParameters
        return AccumulationYieldController('a110:' + bound.episode_id, 0., declared['cutoff'],
                                           YieldParameters(**declared['parameters']))

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping):
            raise ContractError('a110_recorded_controller_input_must_be_a_record:' + self.binding_path)
        return RuntimeRecord(record)
