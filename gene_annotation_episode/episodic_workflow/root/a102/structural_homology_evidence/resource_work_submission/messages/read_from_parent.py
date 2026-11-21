"""What the commissioner supplies: the work to launch, the resources it permits and what a usable handoff is worth.
This is the only place the assignment is read.

Controlled messaging: the work is a record the commissioner holds (a JSON artifact with ``command``,
``environment`` and ``inputs``) passed by reference in ``work_refs``, with the artifacts it stages in
``input_refs``; this episode never reads the work, it passes both on in custody to the resource child it
commissions. The old open records of the launch assignment (``job_request``, ``constraints``,
``resource_selection``, ``adapter_assignment``) are not fields of the form: the constraints are the permitted
kinds (a subset of a fixed vocabulary) and, when the commissioner fixed one, the resource id. A commissioner that
returns to work it already had launched passes the job's ledger rows back in ``job_refs``; the episode then checks
that handoff and launches nothing twice.

The completion target is split evenly between the two things that make a usable handoff: holding the handoff
record of the launched work, and holding a receiving check that found the job in a known state. The same two units
are what this episode gives the resource child it commissions (``msg_to_child``), so the child's credit and this
episode's credit for what the child returns are the same number."""
from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import LAUNCH_VERSION

KINDS = ('api', 'local', 'hpc')
HANDOFF_SHARE = 0.5

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', LAUNCH_VERSION),
    'work_refs': Field('record_refs', 'One record: the work to launch, a JSON artifact with command, environment '
                                      'and inputs, held by the commissioner'),
    'input_refs': Field('record_refs', 'The artifacts the work stages as its input files, passed in custody'),
    'allowed_kinds': SubsetField('text', 'The kinds of resource the commissioner permits', KINDS),
    'resource_id': Field('text', 'The one resource the commissioner fixed; omitted while the choice is this '
                                 "episode's", required=False),
    'job_refs': Field('record_refs', 'The job ledger rows of this work when it was already launched (its handoff '
                                     'row and check rows), passed back in custody', required=False),
    'completion_target': Field('number', 'The credit a usable execution handoff earns'),
})


def read_from_parent(assignment, message):
    target = assignment['completion_target']
    return {'work_ref': assignment['work_refs'][0], 'input_refs': list(assignment['input_refs']),
            'allowed_kinds': list(assignment['allowed_kinds']),
            'resource_id': assignment['resource_id'] if 'resource_id' in assignment else None,
            'completion_target': target,
            'launch_units': {'handoff_unit': target * HANDOFF_SHARE, 'check_unit': target * (1 - HANDOFF_SHARE)}}
