"""What the parent gives: the practical assignment for the local resource (the old ``practical_assignment_v1``,
one field per property of the old assignment schema, under the same names), and the records the job inputs name.

This is the only place the assignment is read. The old ``prepare_assignment`` check of the assignment itself
(``validate_assignment``: version, resource kind, workspace, requested job, requirements, completion keys, initial
context) is made here and raises. The commissioner's own launch contract (``execution_launch_assignment_v1``) was
re-validated from the old runner's ``runtime_episodes`` table (``_check_parent_inputs``); that is old-runner
machinery and is not carried."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'practical_assignment_v1'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The assigned local resource'),
    'resource_kind': DeclaredField('text', 'The resource kind: local', 'local'),
    'workspace': Field('text', 'The absolute workspace on the resource every command and path stays inside'),
    'endpoint': ChoiceField('text', 'The requested endpoint: a usable handoff or the completed job outputs',
                            ('usable_handoff', 'completed_job_outputs')),
    'requested_job': Field('record', 'The requested job: a generic argv and environment, or exactly one native '
                                     'job family'),
    'progress_requirements': Field('list', 'The original requirements, each with a key, a credit and a predicate'),
    'completion_keys': Field('list', 'The requirement keys whose satisfaction completes the assignment'),
    'initial_context': Field('record', 'The working context before any action: revision 0, cwd and environment'),
    'inventory_snapshot': Field('record', 'The recorded inventory of the resource: context, not proof of usability'),
    'constraints': Field('record', "The commissioner's allocation constraints for the resource"),
    'launch_instructions': Field('record', 'The exact launch instruction sections selected for this assignment',
                                 required=False),
    'scientific_manifest': Field('record', 'The native database scientific manifest', required=False),
    # New fields the final form needs (the old code read them from the commissioning request, not the assignment).
    'record_refs': Field('record_refs', 'Every record the job inputs name (masking and utility inputs), passed in '
                                        'custody', required=False),
    'scientific_task': Field('record', 'The scientific parent task: its scientific_question and selected_tool_info '
                                       '(old services.scientific_parent_task)', required=False),
})


def read_from_parent(assignment, message):
    """The validated practical assignment as the parent input, with the credit its completion earns as the target
    of the completion controller."""
    practical = {name: value for name, value in assignment.items() if name not in ('record_refs', 'scientific_task')}
    practical = validate_assignment(practical)
    keys = set(practical['completion_keys'])
    target = math.fsum(item['credit'] for item in practical['progress_requirements'] if item['key'] in keys)
    parent_input = {'assignment': practical, 'completion_target': target,
                    'record_refs': list(assignment.get('record_refs', []))}
    if 'scientific_task' in assignment:
        parent_input['scientific_task'] = assignment['scientific_task']
    return parent_input
