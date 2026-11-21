"""What the commissioner gives: the results assignment (``execution_results_assignment_v1``): the handoff of the
launched job and the selector of what to acquire from it.

This is the only place the assignment is read. ``handoff_ref`` is a ``record_refs`` field holding exactly one
reference: the handoff row the job service wrote at the launch (a row of the job ledger), passed in custody. The
selector names paths of result files inside the job's directory (``paths`` or ``path``, an ``offset`` and a
``limit``): each requested path is read from ``offset`` (default 0) for ``limit`` bytes (default: to its end). The
job's directory is in the handoff row, which only held records give: the paths are confined to it, and the job
service's name of each path is computed, where the row is read (``messages/internal_summary.py``).
``resource_kind`` names the kind of the resource the job runs on, which chooses the continuation profile
(``yield_estimator.py``); ``acquired_record_unit`` is the credit of acquiring the whole requested selector. A
wrong commission fails with its error.

A typed selector (``local_file_source_selector_v1``, ``flux_balance_result_selector_v1``) selected the old local
file source and flux balance result adapters (``LocalFileSourceResults``, ``NativeFluxBalanceResults``): no carried
home exists for either, so a typed selector raises here, at the reading of the commission."""
import math

from jsonschema import Draft202012Validator

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

RESULTS_VERSION = 'execution_results_assignment_v1'
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
    'handoff_ref': Field('record_refs', 'The handoff row of the launched job (exactly one), passed in custody: the '
                                        'job the results are acquired from'),
    'selector': Field('record', 'The requested paths inside the job\'s directory and their byte interval: paths or '
                                'path, offset, limit'),
    'resource_kind': ChoiceField('text', 'The kind of the resource the handed-off job runs on (it chooses the '
                                         'continuation profile before any record is read)', KINDS),
    'acquired_record_unit': Field('number', 'The credit of acquiring the whole requested selector (positive)'),
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
    """The validated results assignment as the parent input: the assignment (version, the one handoff reference,
    the selector), the requested windows, the resource kind and the credit unit."""
    if len(assignment['handoff_ref']) != 1:
        raise ValueError('results_assignment_requires_exactly_one_handoff')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    selector = dict(assignment['selector'])
    return {'assignment': {'version': assignment['version'], 'handoff_ref': assignment['handoff_ref'][0],
                           'selector': selector},
            'windows': selector_windows(selector), 'resource_kind': assignment['resource_kind'],
            'acquired_record_unit': unit}
