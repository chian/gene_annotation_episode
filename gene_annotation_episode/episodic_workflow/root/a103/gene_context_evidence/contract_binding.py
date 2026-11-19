"""A103 episode bindings under the generic ``episode_runtime`` contract.

Every A103 binding implements each hook of
docs/axis_restructure_20261117/BINDING_CONTRACT.md and is constructed by the A103
home factory (``gene_context_evidence/home.py``).

The head ``gene_context_evidence`` is its own class (``episode.py`` + ``runtime_source.py``).
Every binding below it mixes its own runtime (decision source, ``build_controller`` and
``build_episode``) in before ``A103ContractBinding``, which supplies the shared entry
request, assignment and return forms.

Credit is each binding's own projection and is never bounded, clamped or
rescaled. Every return form carries ``credit`` (number, the binding's own
credit) and ``finding`` (record, its report).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType

from episode_runtime import Commission, DeclaredField, Field, RecordForm
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

REPORT = MappingProxyType({
    'decision': 'Use the child finding in the parent cycle',
    'measurements': {'credit': "The child's own credit on its own scale"},
    'information': {'finding': 'What the child established, with its record references'},
})

RETURN_FORM = RecordForm({
    'credit': Field('number', "This episode's own credit on its own scale; never clamped or rescaled"),
    'finding': Field('record', 'What this episode established, with its record references'),
})

# Every A103 binding below the head is commissioned by its A103 parent with the subject scope and the
# parent's typed role assignment for it.
CHILD_ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The subject scope the commissioning parent holds'),
    'role_assignment': Field('record', "The commissioning A103 parent's typed assignment for this role"),
})


@dataclass(frozen=True)
class ContractRecord(ClosedRecord):
    """A closed A103 record (controller input, request message or result)."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(dict(self.value), sort_keys=True, allow_nan=False))


class A103ContractBinding:
    """Contract hooks of an A103 binding below the head; each class declares its own values."""

    grain_name: str
    goal: str
    unit: str
    result: str
    child_slots: Mapping
    required_collaborators = ()
    assignment_form = CHILD_ASSIGNMENT_FORM
    return_form = RETURN_FORM

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping):
            raise ValueError('a103_entry_input_must_be_a_record:' + self.binding_path)
        fields = self.assignment_form.fields
        supplied = {name for name, spec in fields.items() if not isinstance(spec, DeclaredField)}
        if set(entry_input) != supplied:
            raise ValueError('a103_entry_input_requires_exactly:' + self.binding_path + ':' + ','.join(sorted(supplied)))
        assignment = {name: spec.value if isinstance(spec, DeclaredField) else entry_input[name]
                      for name, spec in fields.items()}
        message = ContractRecord({'scope': dict(entry_input['scope'])})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract={'binding_path': self.binding_path})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT)), assignment)

    def restore_controller_input(self, record):
        return ContractRecord(dict(record))
