"""Commission a child episode on the new runner: its assignment, request and requested report form.

Plain functions an episode calls with its own pieces (its own goal text, contract, child slot builder). Nothing
here knows a role, an axis, a prompt or a setting.

* ``fill_assignment`` builds the assignment a child declares (``ChildBuilder.assignment_form``): every
  ``DeclaredField`` is copied from the child's declaration, every other field comes from ``supplied``; a supplied
  ``record`` field may also be checked against a JSON Schema the child itself declares in a ``DeclaredField``
  (``schemas`` maps the supplied field name to that declared field name). It raises ``FormError`` before the child
  is built, so a parent's rejected model selection creates no unit (the child path is never journaled).
* ``commission_child`` builds the ``Commission`` (child goal refining the parent goal, request message, the
  parent's ``ReportContract``, the admitted assignment, optional report form).
* ``commissioned_report_form`` adds the fields a parent requests for one commission to the child's declared
  ``return_form`` (the runner requires every return field to stay unchanged).
"""
from __future__ import annotations

from collections.abc import Mapping

from jsonschema import Draft202012Validator, SchemaError

from method_loop import Commission, FormError, RecordForm
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract


def fill_assignment(form, supplied, *, schemas=None, what='child_assignment'):
    """The child's assignment: declared values copied, the rest from ``supplied``, admitted exactly by ``form``.

    ``schemas`` (optional) maps a supplied field name to the name of a ``DeclaredField`` of ``form`` whose value
    is a JSON Schema; the supplied value is validated against it. A supplied value for a declared field, a
    missing required field, an unknown field or a schema violation raises ``FormError``.
    """
    if not isinstance(form, RecordForm):
        raise TypeError(what + '_form_must_be_a_RecordForm')
    if not isinstance(supplied, Mapping):
        raise FormError(what + '_supplied_values_must_be_a_record')
    declared = form.declared
    clashing = sorted(name for name in supplied if name in declared)
    if clashing:
        raise FormError(what + '_supplies_a_declared_field:' + ','.join(clashing))
    assignment = {**dict(supplied), **dict(declared)}
    admitted = form.admit(assignment, what)
    for name, schema_field in dict(schemas or {}).items():
        if schema_field not in declared:
            raise FormError(what + '_schema_is_not_a_declared_field:' + str(schema_field))
        if name not in form.fields or name in declared:
            raise FormError(what + '_schema_names_no_supplied_field:' + str(name))
        if name not in admitted:
            continue
        try:
            validator = Draft202012Validator(declared[schema_field])
            validator.check_schema(declared[schema_field])
        except SchemaError as error:
            raise FormError(what + '_declared_schema_invalid:' + str(schema_field)) from error
        errors = sorted(validator.iter_errors(admitted[name]), key=lambda error: list(error.absolute_path))
        if errors:
            error = errors[0]
            path = '.'.join([name, *map(str, error.absolute_path)])
            raise FormError(what + '_violates_declared_schema:' + path + ':' + error.message[:200])
    return admitted


def commission_child(parent_request, *, objective, result_contract, message, report_contract, assignment,
                     report_form=None):
    """The ``Commission`` for one child: a child goal of the parent's goal, the message, contract and assignment."""
    if not isinstance(parent_request, EpisodeRequest):
        raise TypeError('commission_child_requires_the_parent_EpisodeRequest')
    if not isinstance(message, ClosedRecord):
        raise TypeError('commission_child_message_must_be_a_ClosedRecord')
    if not isinstance(report_contract, ReportContract):
        raise TypeError('commission_child_requires_a_ReportContract')
    goal = EpisodeGoal.child(parent_request.goal, objective=objective, result_contract=result_contract)
    return Commission(EpisodeRequest(goal, message, report_contract), assignment, report_form)


def commissioned_report_form(return_form, added):
    """The child's ``return_form`` with the parent's ``added`` fields; an added name already returned raises."""
    if not isinstance(return_form, RecordForm):
        raise TypeError('commissioned_report_form_requires_the_child_return_form')
    if not isinstance(added, Mapping) or not added:
        raise ValueError('commissioned_report_form_requires_added_fields')
    overlap = sorted(name for name in added if name in return_form.fields)
    if overlap:
        raise ValueError('commissioned_report_field_is_a_return_field:' + ','.join(overlap))
    return RecordForm({**dict(return_form.fields), **dict(added)})


__all__ = ['commission_child', 'commissioned_report_form', 'fill_assignment']
