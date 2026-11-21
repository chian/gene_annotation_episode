"""What the parent gives: the practical assignment for the local resource (``practical_assignment_v1``, one field
per property of the assignment schema, under the same names).

This is the only place the assignment is read. The check of the assignment itself (``validate_assignment``:
version, resource kind, workspace, requested job, requirements, completion keys, initial context, the flux-balance
environment selection) is made here and raises. The parent input is the assignment and ``handoff_credit``: the
credit the assignment's ``requested_job_handoff`` requirements define, which is what a handoff earns and the target
the Episode ends at."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'practical_assignment_v1'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The assigned local resource'),
    'resource_kind': DeclaredField('text', 'The resource kind: local', 'local'),
    'workspace': Field('text', 'The absolute workspace of the assignment on the resource'),
    'endpoint': ChoiceField('text', 'The requested endpoint: a usable handoff or the completed job outputs',
                            ('usable_handoff', 'completed_job_outputs')),
    'requested_job': Field('record', 'The requested job: a generic argv and environment, or a native flux-balance '
                                     'job'),
    'progress_requirements': Field('list', 'The original requirements, each with a key, a credit and a predicate'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'initial_context': Field('record', 'The working context before any action: revision 0, cwd and environment'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource: context, not proof of usability'),
    'constraints': Field('record', "The commissioner's allocation constraints for the resource"),
    'launch_instructions': Field('record', 'The exact launch instruction sections selected for this assignment',
                                 required=False),
    'native_flux_balance_execution': Field('record', 'The flux-balance environment selection: version and '
                                                     'environment realization', required=False),
})


def read_from_parent(assignment, message):
    """The validated practical assignment, with the credit a handoff earns."""
    practical = validate_assignment(dict(assignment))
    handoff_credit = math.fsum(item['credit'] for item in practical['progress_requirements']
                               if item['predicate']['kind'] == 'requested_job_handoff')
    return {'assignment': practical, 'handoff_credit': handoff_credit}
