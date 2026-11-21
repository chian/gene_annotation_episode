"""What the parent gives: the handoff of the job and the selector of what to acquire
(``execution_results_assignment_v1``).

This is the only place the assignment is read. ``handoff_ref`` is a ``record_refs`` field holding exactly one
reference: the handoff row the job service wrote at the launch (a row of the job ledger), passed in custody. The
selector names paths of result files inside the job's directory (``paths``, or one ``path`` with ``offset`` and
``limit``). The job's directory is in the handoff row, which only held records give: the paths are confined to it,
and the job service's name of each path is computed, where the row is read (``messages/internal_summary.py``).
``resource_kind`` names the kind of the resource the job runs on, which chooses the continuation profile
(``yield_estimator.py``); ``acquired_record_unit`` is the credit of one fully acquired selector;
``known_result_refs`` passes back what an earlier acquisition of this handoff returned, whose bytes earn nothing.
A wrong commission fails with its error.

Selectors other than native paths (the typed selectors with a ``version``: ``local_file_source_selector_v1``,
``protein_structure_result_selector_v1`` and an API result selector) are not carried: their library has no home in
``episode_support/``. Such a commission raises here."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.execution_contracts import (
    checked, obj)

RESULTS_VERSION = 'execution_results_assignment_v1'
_TEXT = {'type': 'string', 'minLength': 1}
_OFFSET = {'type': 'integer', 'minimum': 0}
_LIMIT = {'type': 'integer', 'minimum': 1}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT},
                              'path': _TEXT, 'offset': _OFFSET, 'limit': _LIMIT}, [])

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The results assignment version', RESULTS_VERSION),
    'handoff_ref': Field('record_refs', 'The handoff row of the job whose results are acquired, passed in custody '
                                        '(exactly one)'),
    'selector': Field('record', 'The requested results: paths of result files inside the job\'s directory (paths, '
                                'or one path with offset and limit)'),
    'acquired_record_unit': Field('number', 'The credit of one fully acquired selector (a positive number)'),
    'resource_kind': ChoiceField('text', 'The kind of the resource the handed-off job runs on (it chooses the '
                                         'continuation profile before any record is read)', ('local', 'hpc')),
    'known_result_refs': Field('record_refs', 'What an earlier acquisition of this handoff returned in '
                               'execution_result_refs and the parent holds: each result record with its '
                               'information artifact. The bytes their windows hold earn no credit',
                               required=False),
})


def windows(selector):
    """The requested byte interval of each path as ``(offset, limit or None)`` (``None``: to the end of the
    file)."""
    values = {path: (0, None) for path in selector.get('paths', [])}
    if 'path' in selector:
        values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
    return values


def native_selector(selector):
    """The validated selector of native paths: a typed selector is not carried; ``offset`` and ``limit`` need a
    single ``path``."""
    if 'version' in selector:
        raise NotImplementedError('result_selector_kind_not_carried:' + str(selector['version']))
    value = checked(selector, NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    return value


def read_from_parent(assignment, message):
    """The validated results assignment as the parent input: the assignment (version, the one handoff reference,
    the selector), the requested byte interval of each path, the known results, the credit unit and the resource
    kind."""
    if len(assignment['handoff_ref']) != 1:
        raise ValueError('execution_results_one_handoff_required')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    selector = native_selector(assignment['selector'])
    return {'assignment': {'version': assignment['version'], 'handoff_ref': assignment['handoff_ref'][0],
                           'selector': selector},
            'requested': {path: list(window) for path, window in windows(selector).items()},
            'known_result_refs': list(assignment.get('known_result_refs', [])),
            'acquired_record_unit': unit,
            'resource_kind': assignment['resource_kind']}
