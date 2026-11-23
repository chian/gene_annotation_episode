"""What the commissioner gives: the results assignment (old ``execution_results_assignment``, the library
``RESULTS_SCHEMA`` that ``from_parent.py`` (``ResultsFromParent.assignment_schema``) extended): the original
handoff of the launched attempt and the selector of what to acquire from it.

Not carried from ``ResultsFromParent`` (README 3b P1, C3): ``prepare_assignment``'s restore of an already admitted
original Results commission (``saved_commission.py``, old-runner machinery), its read of the handoff target
(``job_progress_provider.targets.read_target``: BLOCKED-ON-JOB-SERVICE, the job records are not defined; the tool
reads the handoff, ``task.py``), ``initial_references`` (the handoff ref is the one record the assignment names)
and ``required_return_sources`` (``final_to_parent.py`` declares ``execution_result_refs`` required).

A typed selector (``local_file_source_selector``, ``flux_balance_result_selector``) selected the old local
file source and flux balance result adapters (``LocalFileSourceResults``, ``NativeFluxBalanceResults``): no carried
home exists for either, so a typed selector raises here, at the reading of the commission.

``selector_windows`` is the old ``_windows(selector)`` of the library ``received_result_readers`` (not in
``episode_support/``, and not read): rebuilt from the native selector schema alone (``paths`` or ``path``, an
``offset`` and a ``limit``): each requested path is read from ``offset`` (default 0) for ``limit`` bytes (default:
to its end)."""
import math

from jsonschema import Draft202012Validator

from method_loop import DeclaredField, Field, RecordForm

RESULTS_VERSION = 'execution_results_assignment'
_TEXT = {'type': 'string', 'minLength': 1}
_OFFSET = {'type': 'integer', 'minimum': 0}
_LIMIT = {'type': 'integer', 'minimum': 1}
NATIVE_SELECTOR_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': [],
    'properties': {'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT},
                   'path': _TEXT, 'offset': _OFFSET, 'limit': _LIMIT}}
KINDS = ('local', 'hpc')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', RESULTS_VERSION),
    'handoff_ref': Field('record_refs', 'The practical receipt of the launched attempt (exactly one), the target '
                                        'the results are acquired from'),
    'selector': Field('record', 'The requested paths and byte interval: paths or path, offset, limit'),
    'constraints': Field('record', 'The commission\'s constraints', required=False),
    'resource_kind': Field('text', 'The kind of the handed-off resource, local or hpc (new: the old binding read '
                                   'it from the handoff target)'),
    'acquired_record_unit': Field('number', 'The credit of acquiring the whole requested selector (new: the old '
                                            'binding took it from its configuration; positive)'),
})


def selector_windows(selector):
    """The requested ``(path, start, length)`` windows of a native selector; ``length`` is ``None`` to the end."""
    if 'version' in selector:
        raise NotImplementedError(
            'typed result selector ' + repr(selector['version']) + ' has no carried home: the old '
            'LocalFileSourceResults / NativeFluxBalanceResults adapters are not placed')
    if not Draft202012Validator(NATIVE_SELECTOR_SCHEMA).is_valid(selector):
        raise ValueError('invalid_execution_results_selector')
    if 'paths' in selector and 'path' in selector:
        raise ValueError('execution_results_selector_conflict')
    paths = selector['paths'] if 'paths' in selector else [selector['path']] if 'path' in selector else []
    if not paths:
        raise ValueError('results_original_selector_has_no_requested_bytes')
    return [{'path': path, 'start': selector.get('offset', 0), 'length': selector.get('limit')} for path in paths]


def read_from_parent(assignment, message):
    if len(assignment['handoff_ref']) != 1:
        raise ValueError('results_assignment_requires_exactly_one_handoff')
    if assignment['resource_kind'] not in KINDS:
        raise ValueError('results_assignment_resource_kind_unknown')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    return {'handoff_refs': list(assignment['handoff_ref']), 'handoff_ref': assignment['handoff_ref'][0],
            'selector': dict(assignment['selector']), 'windows': selector_windows(assignment['selector']),
            'constraints': dict(assignment.get('constraints', {})), 'resource_kind': assignment['resource_kind'],
            'acquired_record_unit': unit}
