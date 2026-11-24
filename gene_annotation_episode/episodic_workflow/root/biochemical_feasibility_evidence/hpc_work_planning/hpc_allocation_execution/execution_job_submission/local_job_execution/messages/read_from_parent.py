"""What the parent gives: the practical assignment for the local resource (the old ``practical_assignment``, one
field per property of the old assignment schema, under the same names), and the records the job's inputs name.

This is the only place the assignment is read. The old ``prepare_assignment`` check of the assignment itself
(``validate_assignment``: version, resource kind, workspace, requested job, requirements, completion keys, initial
context, the flux-balance environment selection) is made here and raises. The old checks of the commissioning launch
request against the old runner's ``runtime_episodes`` table (``read_request_binding``, ``_launch``, the immutable
input versions of the launch) are old-runner machinery and are not carried: a wrong commission fails. The old
compact flux-balance assignment (``resource_assignment_schema``, read through the launch's request binding) is not
carried either: the parent passes the materialized practical assignment."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'practical_assignment'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The assigned local resource'),
    'resource_kind': DeclaredField('text', 'The resource kind: local', 'local'),
    'workspace': Field('text', 'The absolute workspace on the resource every command and path stays inside'),
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
    # New fields the final form needs (the old code read them from the commissioning request, not the assignment).
    'record_refs': Field('record_refs', 'Every record the job inputs name (the flux-balance input versions), passed '
                                        'in custody', required=False),
    'scientific_task': Field('record', 'The scientific parent task: its scientific_question and selected_tool_info '
                                       '(old services.scientific_parent_task)', required=False),
})


def read_from_parent(assignment, message):
    """The validated practical assignment as the parent input. The completion target is the credit the commissioned
    requirements can earn: the sum of the credits of every original requirement (each is at least zero), which the
    practical credit (the sum of the satisfied ones) cannot pass."""
    practical = {name: value for name, value in assignment.items() if name not in ('record_refs', 'scientific_task')}
    practical = validate_assignment(practical)
    target = math.fsum(item['credit'] for item in practical['progress_requirements'])
    parent_input = {'assignment': practical, 'completion_target': target,
                    'record_refs': list(assignment.get('record_refs', []))}
    if 'scientific_task' in assignment:
        parent_input['scientific_task'] = assignment['scientific_task']
    return parent_input
