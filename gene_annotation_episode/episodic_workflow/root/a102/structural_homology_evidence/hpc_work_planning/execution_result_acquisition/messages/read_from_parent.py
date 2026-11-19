"""What the parent gives: the original handoff and the selector of what to acquire (``execution_results_assignment_v1``).

Carried from the old ``from_parent.py`` (``RESULTS_SCHEMA``, ``assignment_schema``, ``prepare_assignment``,
``initial_references``) and the selector admission of ``result_selection.py`` (``_selector``, ``_windows``).
The assignment is read only here: ``read_from_parent`` returns the parent input that the summary, the credit, the
controller and the tools read.

Old assignment properties, under their own names: ``version`` (fixed) and ``handoff_ref`` and ``selector``.
``handoff_ref`` is now a ``record_refs`` field holding the one handoff record (a form has no single reference
type; the pass is the custody of the handoff). Three fields are new (contract_misfits): ``resource_kind`` (the kind of the target the old code read through the
handoff; the continuation profile is chosen by it), ``acquired_record_unit`` (the old configuration value of that name: the credit of one fully acquired selector) and ``known_result_refs`` (the
result records the parent already holds, which the old binding context knew as its initial known records: bytes
they hold earn nothing).

The old admission that needed the handoff's target (the paths inside the target's workspace) is done where the
target is read: in the tools (``task.py``). The old admission of a restored results commission
(``saved_result_commission.py``) is old-runner machinery and is not carried.

Selectors other than native paths (the typed selectors with a ``version``: ``local_file_source_selector_v1``,
``protein_structure_result_selector_v1`` and an API result selector) are not carried: their library
(``native_protein_structure_results``, ``api_service_execution`` and the local file capture operations) has no
home in ``episode_support/``. Such a commission raises here."""
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
    'handoff_ref': Field('record_refs', 'The original execution handoff record, passed in custody (exactly one)'),
    'selector': Field('record', 'What to acquire: native paths (paths, or one path with offset and limit)'),
    'acquired_record_unit': Field('number', 'The credit of one fully acquired selector (a positive number)'),
    'resource_kind': ChoiceField('text', 'The kind of the resource the handoff names (the old target resource_kind, which '
                            'the continuation needs before any record is read)', ('local', 'hpc')),
    'known_result_refs': Field('record_refs', 'Result records this commission already holds, whose bytes earn no '
                               'credit', required=False),
})


def windows(selector):
    """The old ``_windows``: ``{path: (start, length or None)}`` of the requested bytes."""
    values = {path: (0, None) for path in selector.get('paths', [])}
    if 'path' in selector:
        values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
    return values


def native_selector(selector):
    """The old ``_selector`` for a native (local or PBS) target, without the workspace confinement: a typed selector
    is not carried; a native selector names paths, and ``offset``/``limit`` need a single ``path``."""
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
            'resource_kind': assignment['resource_kind'],
            'message': dict(message)}
