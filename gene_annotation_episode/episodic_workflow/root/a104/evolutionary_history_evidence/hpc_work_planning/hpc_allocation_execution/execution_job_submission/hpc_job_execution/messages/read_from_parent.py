"""What the parent gives: the practical assignment for the HPC resource (the old ``practical_assignment_v1``, one
field per property of the old assignment schema, under the same names), and the records the job inputs name.

This is the only place the assignment is read. The old ``prepare_assignment`` check of the assignment itself
(``validate_assignment``: version, resource kind, workspace, requested job, requirements, completion keys, initial
context, scientific manifest) is made here and raises. The old checks of the commission against the commissioning
launch request (``_check_parent_inputs``, masking, utility and BLAST database inputs, pinned input versions) and the
launch parent's frozen-request ``enum`` are checks of a commission: a wrong commission fails and nothing checks it
ahead (rule 1), so they are not carried."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    validate_assignment)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'practical_assignment_v1'),
    'assignment_id': Field('text', 'The identity of this assignment'),
    'resource_id': Field('text', 'The assigned HPC resource'),
    'resource_kind': DeclaredField('text', 'The resource kind: hpc', 'hpc'),
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
    'scientific_manifest': Field('record', 'The native database scientific manifest: its path, sha256, size and '
                                           'run-plan format', required=False),
    # New field the final form needs: the old code read the job inputs from the commissioning launch request.
    'record_refs': Field('record_refs', 'Every record the job inputs name (masking and utility inputs, pinned '
                                        'input versions), passed in custody', required=False),
})


def read_from_parent(assignment, message):
    """The validated practical assignment as the parent input, with the credit its completion earns as the target
    of the completion controller."""
    practical = {name: value for name, value in assignment.items() if name != 'record_refs'}
    practical = validate_assignment(practical)
    keys = set(practical['completion_keys'])
    target = math.fsum(item['credit'] for item in practical['progress_requirements'] if item['key'] in keys)
    return {'assignment': practical, 'completion_target': target, 'record_refs': list(assignment.get('record_refs', []))}
