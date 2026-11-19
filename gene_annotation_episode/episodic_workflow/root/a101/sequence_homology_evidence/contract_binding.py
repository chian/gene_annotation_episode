"""A101 episode bindings under the generic ``episode_runtime`` contract.

Every A101 binding mixes in ``A101ContractBinding`` and declares its own
``goal``, ``unit``, ``result`` and ``child_slots``; ``grain_name`` is the
path-qualified name of its ``binding_path``
(docs/axis_restructure_20261117/BINDING_CONTRACT.md). Bindings are constructed
only by ``a101_home_factory`` (``home_factory.py``).

Each binding supplies its own ``build_controller`` and ``build_episode``. The
head (``episode.py``) runs its own decision source (``runtime_source.py``) and
continuation (``runtime_credit.py``); the seven literature bindings share
``published_evidence_assessment/literature_binding.py``.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType

from episode_runtime import Commission, Field, RecordForm, grain_name_for
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

AXIS = 'A101'
REPORT = MappingProxyType({
    'decision': 'Use the child finding in the parent cycle',
    'measurements': {'credit': "This commission's credit on the child binding's own unbounded scale"},
    'information': {'finding': 'What the child established, with the record references it rests on'},
})

SCOPE = Field('record', 'The Store scope this episode investigates (subject references held by the commissioner)')
CREDIT = Field('number', "This episode's own credit for its findings; unbounded, never clamped or rescaled")
FINDING = Field('record', 'What this episode established, with the record references it rests on')
RETURN_FORM = RecordForm({'credit': CREDIT, 'finding': FINDING})

# The standard runtime collaborators A101 decision behaviour reads: model decisions and
# the run's one shared Store. Each binding's tools are its own (built by the home factory).
COLLABORATORS = ('model_provider', 'store')


@dataclass(frozen=True)
class Record(ClosedRecord):
    """A closed A101 record: request message, controller input or result."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(dict(self.value), sort_keys=True, allow_nan=False))


class A101ContractBinding:
    """Contract hooks shared by A101 bindings; each class declares its own values."""

    goal: str
    unit: str
    result: str
    child_slots: Mapping
    required_collaborators = COLLABORATORS
    assignment_form = RecordForm({'scope': SCOPE})
    return_form = RETURN_FORM
    report_contract = REPORT

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping) or set(entry_input) != set(self.entry_fields()):
            raise ValueError('a101_entry_input_requires_exactly:' + ','.join(self.entry_fields()) + ':'
                             + self.binding_path)
        assignment = {**dict(entry_input), **self.assignment_form.declared}
        message = Record({'scope': assignment['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=dict(REPORT),
                                    task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT)), assignment)

    def entry_fields(self):
        """The assignment fields an entry caller supplies: every field this binding does not declare itself."""
        return tuple(sorted(name for name in self.assignment_form.fields if name not in self.assignment_form.declared))

    def restore_controller_input(self, record):
        return Record(dict(record))
