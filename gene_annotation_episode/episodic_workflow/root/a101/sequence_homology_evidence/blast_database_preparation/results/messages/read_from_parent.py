"""What the parent gives: the job whose results are wanted, passed in custody, and the credit one usable product
earns. ``handoff_refs`` is the one handoff row the launch wrote; ``plan_refs`` the artifact of the plan that job
ran, and ``input_refs`` the sequence set it was built from: the record the prepared-data row names must be held
here, and the plan is what the job's receipt is checked against. ``kind`` is the kind the commission declared: the
acquisition derives the kind again from the plan the job actually ran and fails when the two differ. This is the
only place the assignment is read."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    KINDS)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', 'blast_preparation_results_assignment_v1'),
    'handoff_refs': Field('record_refs', 'The handoff row of the job whose results are wanted: exactly one job '
                                         'ledger row, passed in custody'),
    'plan_refs': Field('record_refs', 'The artifact of the plan that job ran: exactly one, passed in custody'),
    'input_refs': Field('record_refs', 'The sequence set the job was built from: exactly one, passed in custody'),
    'kind': ChoiceField('text', 'The kind the commission declares: what the job prepares', KINDS),
    'prepared_unit': Field('number', 'The credit one usable prepared record earns (positive)'),
})


def read_from_parent(assignment, message):
    (handoff_ref,) = assignment['handoff_refs']
    unit = assignment['prepared_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('blast_preparation_prepared_unit_must_be_positive')
    return {'handoff_ref': handoff_ref, 'declared_kind': assignment['kind'], 'prepared_unit': unit}
