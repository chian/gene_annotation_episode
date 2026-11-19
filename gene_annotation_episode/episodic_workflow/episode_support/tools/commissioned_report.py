"""A parent's per-commission typed report form (contract C5) for an A102 binding.

A commissioning parent may ask for a report form that keeps the binding's own
``return_form`` (``credit`` and ``finding``) and adds fields. An A102 binding
fills each added field from its own recorded facts: a declared fact table maps
each fact name to its field type and whether the fact may be unknown. An added
field that is not one of the binding's facts, is not a plain ``Field``, has
another type, or is required while its fact may be unknown raises when the
Episode is built; nothing is defaulted, inferred or substituted. An unknown
fact (``None``) leaves its optional field absent.
"""
from __future__ import annotations

from collections.abc import Mapping

from method_loop import Field


class CommissionedReportError(ValueError):
    """A commissioned report form asks for a field this binding has no fact for."""


def added_fields(report_form, return_form, facts, what):
    """The names the commissioned ``report_form`` adds to ``return_form``, each checked against ``facts``.

    ``facts`` maps each fact name to ``(field_type, may_be_unknown)``.
    """
    names = tuple(sorted(set(report_form.fields) - set(return_form.fields)))
    for name in names:
        if name not in facts:
            raise CommissionedReportError(what + '_commissioned_report_field_has_no_fact:' + name)
        spec = report_form.fields[name]
        kind, may_be_unknown = facts[name]
        if type(spec) is not Field or spec.form is not None or spec.items is not None:
            raise CommissionedReportError(what + '_commissioned_report_field_must_be_a_plain_field:' + name)
        if spec.type != kind:
            raise CommissionedReportError(what + '_commissioned_report_field_type_differs_from_fact:' + name + ':'
                                          + spec.type + ':' + kind)
        if may_be_unknown and spec.required:
            raise CommissionedReportError(what + '_commissioned_report_field_may_be_unknown_must_be_optional:' + name)
    return names


def report_fields(names, finding, what):
    """The added fields' values from the binding's recorded ``finding``; an unknown fact stays absent."""
    if not isinstance(finding, Mapping):
        raise CommissionedReportError(what + '_finding_must_be_a_record')
    missing = [name for name in names if name not in finding]
    if missing:
        raise CommissionedReportError(what + '_finding_lacks_commissioned_fact:' + ','.join(missing))
    return {name: finding[name] for name in names if finding[name] is not None}


__all__ = ['CommissionedReportError', 'added_fields', 'report_fields']
