"""What the commissioner gives: one concrete HPC execution assignment (the old practical assignment), field for
field under the old names. This file is the only place the assignment is read: ``read_from_parent`` validates it
with the practical assignment contract (the old ``prepare_assignment`` check of the request itself) and derives,
for the yield controller, the request class of the original task and the credit the whole assignment is worth."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    ASSIGNMENT_VERSION, validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The practical assignment contract version', ASSIGNMENT_VERSION),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_kind': DeclaredField('text', 'The kind of the assigned resource', 'hpc'),
    'workspace': Field('text', 'The absolute workspace of the job on the assigned resource'),
    'endpoint': ChoiceField('text', 'The endpoint the commission requests', ('usable_handoff',
                                                                              'completed_job_outputs')),
    'requested_job': Field('record', 'The job requested: argv and environment, or a native job request'),
    'progress_requirements': Field('list', 'The requirements (key, credit, predicate) that earn credit when the '
                                           'actual facts satisfy them'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'initial_context': Field('record', 'The working directory and environment the first command starts from'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource, context and not proof of use'),
    'constraints': Field('record', 'The scheduler constraints (account, queue, resources, allocation)'),
    'launch_instructions': Field('record', 'The pinned launch instruction sections the commissioner selected',
                                 required=False),
    'resource_id': Field('text', 'The configured resource the job is assigned to'),
    'scientific_manifest': Field('record', 'The native database run plan the job executes (path, sha256, size, '
                                           'format)', required=False),
})


def _request_yield_class(request):
    """Classify the original execution request without generated identities (old ``_request_yield_class``, the
    ``practical_assignment_v1`` branch: this episode is commissioned only with that assignment)."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def read_from_parent(assignment, message):
    request = validate_assignment(assignment)
    return {'assignment': request, 'yield_class': _request_yield_class(request),
            'completion_target': math.fsum(item['credit'] for item in request['progress_requirements'])}
