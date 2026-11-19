"""What the commissioning parent gives: the original handoff (in custody), the original selector and what the parent
read of the handed-off target. The only place an assignment is read.

Carried from the old ``from_parent.py`` (``ResultsFromParent.assignment_schema``, ``prepare_assignment``), the
selector admission of the old ``result_selection`` (``_selector``, ``_windows``) and the old ``result_state.py``
check of the target. Old assignment properties, under their own names: ``version``, ``handoff_ref``, ``selector``
and ``constraints``. ``handoff_ref`` is a ``record_refs`` field holding the one handoff record (a form has no single
reference type). New fields (contract_misfits): ``resource_kind`` and ``workspace`` (the old code read them from the
target behind the handoff; the continuation profile and the confinement of the requested paths need them before any
record is read), ``acquired_record_unit`` (the old configuration value of that name; credit has no settings),
``initial_result_refs`` and ``initial_result_artifact_refs`` (the old initial known records: each earlier
``episode.execution_result`` source and its artifact, because a passed record does not bring the records it names).

Only the generic native selector (requested paths and byte windows of a local or HPC resource) is carried. A typed
selector (``version`` in the selector: local file sources, masking, BLAST utility, standard or native BLAST database,
RNA structure and comparison, expression NMF, Infernal, HMMER preparation, HMMER, BLAST) and an API target need the
target's own result host and the BLAST grader requirement rebuilt from the original launch request
(BLOCKED-ON-JOB-SERVICE): they raise here. The old restoring of a returned original commission
(``saved_commission.py``) and the old ``required_return_sources`` are machinery or the parent's selection."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.partner_presence_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    obj, validate_schema)

RESULTS_VERSION = 'execution_results_assignment_v1'
_TEXT = {'type': 'string', 'minLength': 1}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT},
                              'path': _TEXT, 'offset': {'type': 'integer', 'minimum': 0},
                              'limit': {'type': 'integer', 'minimum': 1}}, [])

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The results assignment contract version', RESULTS_VERSION),
    'handoff_ref': Field('record_refs', 'The one original handoff record of the job whose results are acquired, '
                         'passed in custody (the old text field, now a record reference)'),
    'selector': Field('record', 'The original selector: the requested paths, or one path with offset and limit'),
    'constraints': Field('record', 'The scientific parent\'s constraints on the work', required=False),
    'resource_kind': ChoiceField('text', 'The kind of the handed-off resource, read by the parent from the handoff '
                                 'target', ('local', 'hpc', 'api')),
    'workspace': Field('text', 'Absolute workspace path the requested paths are confined to, read by the parent '
                       'from the handoff target'),
    'acquired_record_unit': Field('number', 'The credit of a fully acquired original selector (positive)'),
    'initial_result_refs': Field('record_refs', 'Earlier retained result sources of this job already held by the '
                                 'parent; byte positions they cover earn no credit', required=False),
    'initial_result_artifact_refs': Field('record_refs', 'The artifact of each source named in initial_result_refs '
                                          '(a passed record does not bring the records it names)', required=False),
})


def native_windows(selector, workspace):
    """The old ``_selector`` and ``_windows`` for a generic native target: the requested ``{path: [offset, limit or
    None]}``, every path confined to the workspace of the target."""
    value = dict(selector)
    validate_schema(value, NATIVE_SELECTOR_SCHEMA)
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    for path in paths:
        confined(path, workspace)
    windows = {path: [0, None] for path in value.get('paths', [])}
    if 'path' in value:
        windows[value['path']] = [value.get('offset', 0), value.get('limit')]
    return windows


def read_from_parent(assignment, message):
    """The parent input: the original handoff, the selector as requested windows, the target's kind and workspace."""
    selector = assignment['selector']
    kind = assignment['resource_kind']
    if kind == 'api' or 'version' in selector:
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: the result host of a typed or API target (selector version %r, resource kind '
            '%r); wanted call: ctx.services[\'job_access\'].result_host(target).validate_selector(selector)'
            % (selector.get('version'), kind))
    if len(assignment['handoff_ref']) != 1:
        raise ValueError('execution_results_one_handoff_required')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    windows = native_windows(selector, assignment['workspace'])
    return {'assignment': {'version': assignment['version'], 'selector': selector,
                           'constraints': assignment.get('constraints', {}),
                           'resource_kind': kind, 'workspace': assignment['workspace']},
            'handoff_refs': list(assignment['handoff_ref']),
            'initial_result_refs': list(assignment.get('initial_result_refs', [])),
            'initial_result_artifact_refs': list(assignment.get('initial_result_artifact_refs', [])),
            'requested': windows, 'acquired_record_unit': unit,
            'scientific_task': message}
