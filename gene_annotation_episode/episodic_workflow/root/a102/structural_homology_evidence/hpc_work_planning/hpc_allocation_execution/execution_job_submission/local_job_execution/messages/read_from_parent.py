"""What the commissioning submission parent gives: one frozen ``practical_assignment_v1`` for one configured local
resource (one field per property of the old assignment schema, same names), the subject scope, and the records
the job reads, passed in custody.

``read_from_parent`` is the only place the assignment is read. It derives from it what the continuation and the
credit need (the completion target, the yield class, the baseline validations) so that ``yield_estimator.py``
never reads the assignment itself."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    assess_validations, validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'practical_assignment_v1'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The configured local resource the job runs on'),
    'resource_kind': DeclaredField('text', 'The kind of the resource (this episode runs on a local resource)', 'local'),
    'workspace': Field('text', 'The absolute workspace of the job, inside the resource\'s configured workspace'),
    'endpoint': ChoiceField('text', 'What counts as the endpoint of the job', ('usable_handoff', 'completed_job_outputs')),
    'requested_job': Field('record', 'The job to run: the generic job (argv, environment) or a native job form '
                                     'the resource declares (for example native_protein_structure)'),
    'progress_requirements': Field('list', 'The caller-valued requirements (key, credit, predicate) whose '
                                           'satisfaction is the credit of this episode'),
    'completion_keys': Field('list', 'The requirement keys that must all be satisfied for the endpoint'),
    'initial_context': Field('record', 'The starting working directory and environment (revision 0)'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource'),
    'constraints': Field('record', 'The caller\'s constraints'),
    'launch_instructions': Field('record', 'The launch instruction sections the parent selected', required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioning parent (new field: the old episode '
                             'took it from its request)'),
    'input_refs': Field('record_refs', 'The records the job reads, passed in custody (new field: the old episode '
                                       'read them from its parent\'s launch assignment)', required=False),
    'scientific_task': Field('record', 'The ancestor\'s scientific question and selected tool information for a '
                                       'native protein-structure job (new field: the old episode asked a services '
                                       'callback for it)', required=False),
})

ASSIGNMENT_FIELDS = ('version', 'assignment_id', 'resource_id', 'resource_kind', 'workspace', 'endpoint',
                     'requested_job', 'progress_requirements', 'completion_keys', 'initial_context',
                     'inventory_snapshot', 'constraints', 'launch_instructions')
# The baseline validations are assessed with no clock: this instant is the one ``validate_validations`` itself uses.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def request_yield_class(request):
    """Classify the original execution request without generated IDs (the old yield estimator's classifier)."""
    requested = request['requested_job']
    native = sorted(key for key in requested if key.startswith('native_'))
    parts = ['practical', request['resource_kind']]
    parts.extend(native)
    parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
    return '_'.join(parts)


def completion_target(assignment):
    """The total requirement credit the assignment declares: the completion controller's target (the old
    estimator had a proof check and no number)."""
    return math.fsum(item['credit'] for item in assignment['progress_requirements'])


def read_from_parent(assignment, message):
    practical = validate_assignment({name: assignment[name] for name in ASSIGNMENT_FIELDS if name in assignment})
    return {'assignment': practical,
            'scope': assignment['scope'],
            'input_refs': assignment.get('input_refs', []),
            'scientific_task': assignment.get('scientific_task'),
            'initial_validations': assess_validations(practical, {'facts': {}}, practical['initial_context'],
                                                      checked_at=BASELINE_CHECKED_AT),
            'completion_target': completion_target(practical),
            'yield_class': request_yield_class(practical)}
