"""What the commissioning parent gives: the original handoff (in custody), the original selector and constraints, and
what the parent read of the handed-off target. The only place an assignment is read.

Old assignment schema (``RESULTS_SCHEMA``: ``handoff_ref``, ``selector``, ``constraints``). New fields, which the old
code did not have as assignment fields (it read them from its binding configuration, the handoff target and the
receipts of the binding context): ``resource_kind`` and ``workspace`` (read by the parent from the handoff target),
``acquired_record_unit`` (the old configuration value), ``initial_result_refs`` and ``initial_result_artifact_refs``
(the old ``initial_known_record_refs``: earlier retained results of this job that the parent holds). ``handoff_ref``
is a ``record_refs`` field of one record (the old value was text): custody needs a record reference.

Only the generic native selector (requested paths and byte windows of a local or HPC resource) is carried. A typed
selector (masking, BLAST utility, standard or native BLAST database, HMMER preparation, HMMER, BLAST, Infernal,
RNA structure and comparison, expression NMF, API, local file sources) needs the result host of its target, which no
service provides: it raises at this point. The old ``_recorded_results_assignment`` (restoring a returned commission
from the old receipt tables), the old retained NMF / masking / utility target reads and every selected-input check
against the parent's recorded request are old-runner machinery or read another episode's records and are not
carried."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.partner_presence_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    obj, validate_schema)

_TEXT = {'type': 'string', 'minLength': 1}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT},
                              'path': _TEXT, 'offset': {'type': 'integer', 'minimum': 0},
                              'limit': {'type': 'integer', 'minimum': 1}}, [])

ASSIGNMENT_FORM = RecordForm({
    'handoff_ref': Field('record_refs', 'The one original handoff record of the job whose results are acquired, '
                         'passed in custody (the old text field, now a record reference)'),
    'selector': Field('record', 'The original selector: the requested paths, or one path with offset and limit'),
    'constraints': Field('record', 'The original constraints of the commission', required=False),
    'resource_kind': ChoiceField('text', 'The kind of the handed-off resource, read by the parent from the handoff '
                                 'target', ('local', 'hpc', 'api')),
    'workspace': Field('text', 'Absolute workspace path the requested paths are confined to, read by the parent from '
                       'the handoff target'),
    'acquired_record_unit': Field('number', 'The credit of a fully acquired original selector (positive)'),
    'initial_result_refs': Field('record_refs', 'Earlier retained result sources of this job already held by the '
                                 'parent; byte positions they cover earn no credit', required=False),
    'initial_result_artifact_refs': Field('record_refs', 'The artifact of each source named in initial_result_refs '
                                          '(a passed record does not bring the records it names)', required=False),
})


def native_windows(selector, workspace):
    """The requested ``{path: [offset, limit or None]}`` of a generic native selector (the old ``_windows``: a path
    of ``paths`` is requested whole, ``path`` with its offset and limit), every path confined to the workspace of the
    target."""
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
    if unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    windows = native_windows(selector, assignment['workspace'])
    return {'assignment': {'selector': selector, 'constraints': assignment.get('constraints', {}),
                           'resource_kind': kind, 'workspace': assignment['workspace']},
            'handoff_refs': list(assignment['handoff_ref']),
            'initial_result_refs': list(assignment.get('initial_result_refs', [])),
            'initial_result_artifact_refs': list(assignment.get('initial_result_artifact_refs', [])),
            'requested': windows, 'acquired_record_unit': unit,
            'scientific_task': message}
