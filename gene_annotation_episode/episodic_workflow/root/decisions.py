"""The root's decisions: which evidence axis to commission next, chosen by the model.

Each unit asks ``model_provider.complete`` (with ``goal.INSTRUCTIONS``) for one
axis and a value for every choice that axis's assignment offers. The response is
recorded (``axis_selection.<position>.<attempt>``); a response that fails the
output schema creates no unit and the model decides again with that feedback.
The selected axis is commissioned through its child builder with the assignment
it declares, filled from the values the root holds; each returned result is
recorded as ``outcome.<position>`` and enters the controller as an ``AxisReturn``.
"""
from __future__ import annotations

from collections.abc import Mapping

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, ReportContract

from .continuation import AxisReturn
from .goal import AXIS_REPORT_CONTRACT, INSTRUCTIONS, axis_objective
from .report import Record

MODEL_PROVIDER = 'model_provider'
MODEL_ROLE = 'REASONING'

# Values the root holds for a commission, filled into the axis assignment field of the same name.
SCOPE_FIELD = 'scope'  # the admitted subject scope
PROPOSED_FIELD = 'proposed_annotation_ref'  # from the entry input, when supplied
CONSTRAINTS_FIELD = 'constraints'  # from the entry input, when supplied
EVIDENCE_FIELD = 'evidence_refs'  # union of earlier axis findings' evidence_refs
HELD_FIELDS = (SCOPE_FIELD, PROPOSED_FIELD, CONSTRAINTS_FIELD, EVIDENCE_FIELD)


def selection_schema(builders):
    """The model's output form: one axis, and a value for each choice or subset field that axis declares."""
    options = []
    for axis, builder in builders.items():
        choices = {}
        for name, spec in builder.assignment_form.fields.items():
            if isinstance(spec, SubsetField):
                allowed = {'type': 'array', 'items': {'enum': list(spec.options)}, 'description': spec.meaning}
            elif isinstance(spec, ChoiceField):
                allowed = {'enum': list(spec.options), 'description': spec.meaning}
            else:
                continue
            choices[name] = allowed if spec.required else {'anyOf': [allowed, {'type': 'null'}]}
        options.append({'type': 'object', 'additionalProperties': False, 'required': ['axis', 'choices'],
                        'properties': {'axis': {'type': 'string', 'enum': [axis]},
                                       'choices': {'type': 'object', 'additionalProperties': False,
                                                   'required': sorted(choices), 'properties': choices}}})
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': options}}}


def check_axis_return_form(axis, builder):
    """The axis must return a numeric ``credit`` and a text or record ``finding``."""
    fields = builder.return_form.fields
    for name in ('credit', 'finding'):
        if name not in fields:
            raise KeyError('axis_return_form_missing_' + name + ':' + axis)
    if fields['credit'].type != 'number':
        raise TypeError('axis_return_form_credit_must_be_number:' + axis)
    if fields['finding'].type not in ('text', 'record'):
        raise TypeError('axis_return_form_finding_must_be_text_or_record:' + axis)


def axis_assignment(axis, builder, held, choices):
    """The axis's declared assignment, filled from what the root holds and what the model chose.

    A ``DeclaredField`` is copied from the axis's declaration; a choice or subset field takes the model's choice;
    a held field takes the held value. A required field the root cannot fill raises; an optional one stays
    absent. With ``choices=None`` only the fillability of the non-choice fields is checked.
    """
    assignment = {}
    for name, spec in builder.assignment_form.fields.items():
        if isinstance(spec, DeclaredField):
            assignment[name] = spec.value
        elif isinstance(spec, (ChoiceField, SubsetField)):
            if choices is not None and name in choices:
                assignment[name] = choices[name]
            elif choices is not None and spec.required:
                raise KeyError('annotation_choice_required:' + axis + ':' + name)
        elif name in HELD_FIELDS:
            if name in held:
                assignment[name] = held[name]
            elif spec.required:
                raise KeyError('annotation_entry_lacks_required_field:' + axis + ':' + name)
        elif spec.required:
            raise KeyError('annotation_cannot_supply_assignment_field:' + axis + ':' + name)
    return assignment


class RootDecisionSource:
    """Each unit commissions the axis the model selects."""

    def __init__(self, binding, bound, collaborators, child_builders):
        if set(child_builders) != set(binding.child_slots):
            raise KeyError('annotation_child_builders_differ_from_slots')
        self._binding, self._bound = binding, bound
        self._provider = collaborators[MODEL_PROVIDER]
        self._builders = child_builders
        message = bound.request.message.as_record()
        self._subject = message['subject']
        self._entry_held = {name: message[name] for name in (PROPOSED_FIELD, CONSTRAINTS_FIELD) if name in message}
        self._returns, self._feedback = [], None
        for axis, builder in child_builders.items():
            check_axis_return_form(axis, builder)
            axis_assignment(axis, builder, self._held(), None)
        self._schema = selection_schema(child_builders)

    def _held(self):
        evidence = []
        for item in self._returns:
            refs = item['finding'].get(EVIDENCE_FIELD, []) if isinstance(item['finding'], Mapping) else []
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ValueError('annotation_axis_finding_evidence_refs_must_be_text_refs:' + item['axis'])
            evidence.extend(ref for ref in refs if ref not in evidence)
        return {SCOPE_FIELD: self._subject, EVIDENCE_FIELD: evidence, **self._entry_held}

    def _catch_up(self, position):
        """Recall the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while len(self._returns) < position:
            self._returns.append(self._bound.recorder.recall('outcome.' + str(len(self._returns))))

    def _context(self, view):
        state = view.controller_state
        return {'goal': self._bound.request.goal.as_record(), 'subject_scope': self._subject,
                'axis_weights': dict(self._binding.axis_weights), 'current_credit': state.credit,
                'controller': state.as_record(), 'axis_returns': list(self._returns),
                'units_consumed': view.units_consumed, 'feedback': self._feedback}

    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            context = self._context(view)
            response = await self._bound.recorder.recorded_async(
                'axis_selection.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context,
                                                self._schema))
            try:
                Draft202012Validator(self._schema).validate(response)
            except ValidationError as error:
                # Rejected before acquisition: no unit, no observation.
                self._feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': error.message}
                attempt += 1
                continue
            self._feedback = None
            selection = response['selection']
            choices = {name: value for name, value in selection['choices'].items() if value is not None}
            return self._commission(position, selection['axis'], choices)

    def _commission(self, position, axis, choices):
        goal = EpisodeGoal.child(self._bound.request.goal, objective=axis_objective(axis),
                                 result_contract=AXIS_REPORT_CONTRACT)
        message = Record({'subject': self._subject, 'commissioned_by': self._binding.grain_name})
        builder = self._builders[axis]
        assignment = axis_assignment(axis, builder, self._held(), choices)
        child = builder(axis + '_' + str(position),
                        Commission(EpisodeRequest(goal, message, ReportContract(**AXIS_REPORT_CONTRACT)),
                                   assignment))

        def receive(result, completion, request):
            value = builder.admit(result)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'axis': axis, 'credit': value['credit'], 'finding': value['finding']})
            self._returns.append(outcome)
            return AxisReturn(axis, value['credit'], value['finding'],
                              {'progress_time': self._bound.progress.receipt(position)})

        return ChildEpisodeUnit(child, receive,
                                lambda result, completion, request: {'finding': builder.admit(result)['finding']})


__all__ = ['HELD_FIELDS', 'MODEL_PROVIDER', 'RootDecisionSource', 'axis_assignment',
           'check_axis_return_form', 'selection_schema']
