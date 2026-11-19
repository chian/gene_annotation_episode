"""Typed record forms: what an Episode type requires as its assignment and what it returns.

Local patch (``LOCAL_PATCHES.json``): the method's typed request/return admission. An Episode type declares an
``assignment_form`` (what its commissioner supplies) and a ``return_form`` (what it returns); the commissioning
boundary is ``Commission``.

A ``RecordForm`` names every field of a closed JSON record and its type. A
``Field`` is filled by whoever supplies the record (the commissioning parent,
or the entry caller). A ``DeclaredField`` carries the value the declaring
binding itself fixes: the supplier
copies it explicitly and admission rejects any other value. Admission is exact:
a missing, unknown or mistyped field raises. Nothing is defaulted.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import json
import math
import re
from types import MappingProxyType

from .episode import ClosedRecord, EpisodeRequest
from .jsonvalue import closed_copy, same_json

_NAME = re.compile(r'^[a-z][a-z0-9_]*$')

# The closed type vocabulary of a field. ``record_refs`` is a list of record references passed between Episodes:
# in an assignment they are the records the commissioner passes to the child, in a return the records the
# episode returns to its parent. Whoever builds the Episodes admits each pass.
FIELD_TYPES = ('text', 'number', 'integer', 'boolean', 'record', 'list', 'record_refs')


class FormError(ValueError):
    """A record does not match its declared form."""


def _json(value, what):
    return closed_copy(value, what, FormError)


def _typed(kind, value, what):
    if kind == 'text':
        ok = type(value) is str and bool(value.strip())
    elif kind == 'number':
        ok = (not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value))
    elif kind == 'integer':
        ok = type(value) is int
    elif kind == 'boolean':
        ok = type(value) is bool
    elif kind == 'record':
        ok = isinstance(value, Mapping)
    elif kind == 'record_refs':
        ok = (isinstance(value, (list, tuple)) and all(type(ref) is str and ref for ref in value)
              and len(set(value)) == len(value))
    else:
        ok = isinstance(value, (list, tuple))
    if not ok:
        raise FormError(what + '_must_be_' + kind + ':' + repr(value)[:120])
    return _json(value, what)


def _check_shape(kind, form, items):
    if form is not None and (kind != 'record' or not isinstance(form, RecordForm)):
        raise ValueError('field_form_requires_type_record_and_a_RecordForm')
    if items is not None and (kind != 'list' or not isinstance(items, RecordForm)):
        raise ValueError('field_items_require_type_list_and_a_RecordForm')


def _shape_record(spec):
    record = {}
    if spec.form is not None:
        record['form'] = spec.form.as_record()
    if spec.items is not None:
        record['items'] = spec.items.as_record()
    return record


def _admit_shape(spec, value, what):
    """Admit a nested record against ``form`` or each list item against ``items``."""
    if spec.form is not None:
        return spec.form.admit(value, what)
    if spec.items is not None:
        return [spec.items.admit(item, what + '[' + str(index) + ']') for index, item in enumerate(value)]
    return value


@dataclass(frozen=True)
class Field:
    """A field the supplier fills.

    ``form`` types a nested record (``type='record'``) and ``items`` types each
    record of a list (``type='list'``); both are ``RecordForm``s admitted like
    the outer form. ``required=False`` lets the supplier omit the field; an
    omitted field stays absent (nothing is defaulted).
    """
    type: str
    meaning: str
    required: bool = True
    form: object = None
    items: object = None

    def __post_init__(self):
        if self.type not in FIELD_TYPES:
            raise ValueError('field_type_unknown:' + repr(self.type))
        if type(self.meaning) is not str or not self.meaning.strip():
            raise ValueError('field_meaning_required')
        if type(self.required) is not bool:
            raise ValueError('field_required_must_be_boolean')
        _check_shape(self.type, self.form, self.items)

    def as_record(self):
        return {'type': self.type, 'meaning': self.meaning, 'required': self.required, **_shape_record(self)}


@dataclass(frozen=True)
class DeclaredField:
    """A field whose value the declaring binding fixes; the supplier copies ``value``."""
    type: str
    meaning: str
    value: object

    def __post_init__(self):
        Field(self.type, self.meaning)
        if self.type == 'record_refs':
            raise ValueError('record_refs_are_passed_in_custody_not_declared')
        object.__setattr__(self, 'value', _typed(self.type, self.value, 'declared_field'))

    required = True
    form = None
    items = None

    def as_record(self):
        return {'type': self.type, 'meaning': self.meaning, 'value': self.value}


@dataclass(frozen=True)
class ChoiceField:
    """A field the supplier fills by choosing one of the ``options`` the declaring binding offers.

    The runner checks only that the supplied value is one of the options; the
    choice itself is the supplier's (for example the commissioning parent's
    model decision per commission).
    """
    type: str
    meaning: str
    options: tuple
    required: bool = True

    def __post_init__(self):
        Field(self.type, self.meaning, self.required)
        if self.type == 'record_refs':
            raise ValueError('record_refs_are_passed_in_custody_not_chosen')
        if not isinstance(self.options, (list, tuple)) or not self.options:
            raise ValueError('choice_field_requires_options')
        options = tuple(_typed(self.type, option, 'choice_option') for option in self.options)
        if len({json.dumps(option, sort_keys=True) for option in options}) != len(options):
            raise ValueError('choice_field_options_must_be_distinct')
        object.__setattr__(self, 'options', options)

    form = None
    items = None

    def admits(self, value):
        return any(same_json(value, option) for option in self.options)

    def as_record(self):
        return {'type': self.type, 'meaning': self.meaning, 'required': self.required, 'options': list(self.options)}


@dataclass(frozen=True)
class SubsetField:
    """A list field the supplier fills by choosing a subset of the ``options`` the declaring binding offers.

    ``type`` is the type of each element. The runner checks only that every element is one of the options and
    that no element repeats; which subset is chosen is the supplier's decision.
    """
    type: str
    meaning: str
    options: tuple
    required: bool = True

    def __post_init__(self):
        object.__setattr__(self, 'options', ChoiceField(self.type, self.meaning, self.options, self.required).options)

    form = None
    items = None

    def admit_elements(self, value, what):
        elements = [_typed(self.type, element, what + '[' + str(index) + ']') for index, element in enumerate(value)]
        for index, element in enumerate(elements):
            if not any(same_json(element, option) for option in self.options):
                raise FormError(what + '_not_an_offered_option:' + str(index))
            if any(same_json(element, other) for other in elements[:index]):
                raise FormError(what + '_repeats_an_option:' + str(index))
        return elements

    def as_record(self):
        return {'type': 'list', 'element_type': self.type, 'meaning': self.meaning, 'required': self.required,
                'options': list(self.options)}


_FIELD_SPECS = (Field, DeclaredField, ChoiceField, SubsetField)


class RecordForm:
    """The exact, typed field set of one closed JSON record."""

    def __init__(self, fields):
        if not isinstance(fields, Mapping):
            raise TypeError('record_form_fields_must_be_a_mapping')
        for name, spec in fields.items():
            if type(name) is not str or not _NAME.fullmatch(name):
                raise ValueError('record_form_field_name_must_be_lowercase_identifier:' + repr(name))
            if not isinstance(spec, _FIELD_SPECS):
                raise TypeError('record_form_field_must_be_Field_DeclaredField_ChoiceField_or_SubsetField:' + name)
        self.fields = MappingProxyType(dict(fields))

    @property
    def declared(self):
        """The values fixed by the declaring binding, by field name."""
        return MappingProxyType({name: spec.value for name, spec in self.fields.items()
                                 if isinstance(spec, DeclaredField)})

    @property
    def choices(self):
        """The options of each choice and subset field, by field name."""
        return MappingProxyType({name: spec.options for name, spec in self.fields.items()
                                 if isinstance(spec, (ChoiceField, SubsetField))})

    def admit(self, value, what):
        """Return a plain JSON copy of ``value``; raise on any missing, unknown or mistyped field."""
        if isinstance(value, ClosedRecord):
            value = value.as_record()
        if not isinstance(value, Mapping):
            raise FormError(what + '_must_be_a_record')
        missing = [name for name, spec in self.fields.items() if spec.required and name not in value]
        if missing:
            raise FormError(what + '_missing_field:' + ','.join(missing))
        unknown = sorted(str(name) for name in value if name not in self.fields)
        if unknown:
            raise FormError(what + '_unknown_field:' + ','.join(unknown))
        admitted = {}
        for name, spec in self.fields.items():
            if name not in value:
                continue
            if isinstance(spec, SubsetField):
                admitted[name] = spec.admit_elements(_typed('list', value[name], what + ':' + name), what + ':' + name)
                continue
            admitted[name] = _admit_shape(spec, _typed(spec.type, value[name], what + ':' + name), what + ':' + name)
            if isinstance(spec, DeclaredField) and admitted[name] != spec.value:
                raise FormError(what + '_differs_from_declared_value:' + name)
            if isinstance(spec, ChoiceField) and not spec.admits(admitted[name]):
                raise FormError(what + '_not_an_offered_option:' + name)
        return admitted

    def select(self, names):
        """The part of this form a commission selects: every required field and the optional fields ``names``.

        An optional field (``required=False``) of a return form is a field its Episode declares it can return when
        asked; a commissioner selects among them, and the selected fields become required. A name that is not an
        optional field of this form raises.
        """
        names = tuple(names)
        for name in names:
            if name not in self.fields or self.fields[name].required:
                raise FormError('selection_not_a_selectable_field:' + str(name))
        return RecordForm({name: (replace(spec, required=True) if name in names and not spec.required else spec)
                           for name, spec in self.fields.items() if spec.required or name in names})

    def record_refs(self, admitted):
        """Every reference in the ``record_refs`` fields of an admitted record (nested forms included), in
        first-seen order without repeats: the records this record passes in custody."""
        found = {}

        def visit(form, value):
            for name, spec in form.fields.items():
                if name not in value:
                    continue
                if spec.type == 'record_refs':
                    found.update(dict.fromkeys(value[name]))
                elif spec.form is not None:
                    visit(spec.form, value[name])
                elif spec.items is not None:
                    for item in value[name]:
                        visit(spec.items, item)
        visit(self, admitted)
        return tuple(found)

    def as_record(self):
        return {name: spec.as_record() for name, spec in self.fields.items()}

    def __eq__(self, other):
        return isinstance(other, RecordForm) and self.as_record() == other.as_record()

    def __hash__(self):
        return hash(json.dumps(self.as_record(), sort_keys=True))

    def __repr__(self):
        return 'RecordForm(' + json.dumps(self.as_record(), sort_keys=True) + ')'


@dataclass(frozen=True)
class Commission:
    """What opens one Episode: its request, the assignment its binding's ``assignment_form`` requires and the
    ``selection`` its commissioner makes among the fields the Episode declares it can return (see
    ``RecordForm.select``). The Episode's result is admitted against the selected part of its own ``return_form``;
    nothing outside the Episode's own declaration can be requested."""
    request: EpisodeRequest
    assignment: Mapping
    selection: tuple

    def __post_init__(self):
        if not isinstance(self.request, EpisodeRequest):
            raise TypeError('commission_requires_an_EpisodeRequest')
        if not isinstance(self.assignment, Mapping):
            raise TypeError('commission_assignment_must_be_a_mapping')
        if (not isinstance(self.selection, (list, tuple)) or any(type(name) is not str for name in self.selection)
                or len(set(self.selection)) != len(self.selection)):
            raise TypeError('commission_selection_must_be_distinct_field_names')
        object.__setattr__(self, 'assignment', MappingProxyType(_json(dict(self.assignment), 'assignment')))
        object.__setattr__(self, 'selection', tuple(self.selection))

    def as_record(self):
        return {'request': self.request.as_record(), 'assignment': _json(dict(self.assignment), 'assignment'),
                'selection': list(self.selection)}


__all__ = ['ChoiceField', 'Commission', 'DeclaredField', 'FIELD_TYPES', 'Field', 'FormError', 'RecordForm',
           'SubsetField']
