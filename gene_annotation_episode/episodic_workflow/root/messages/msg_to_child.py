"""The commission of each of the nine axis heads: one function per slot, written against that head's own
``messages/read_from_parent.py`` (its assignment form and what it reads of the message) and
``messages/final_to_parent.py`` (the fields it declares it can return), read as data. Nothing is imported from an
axis folder, and nothing here checks a commission: one the head does not admit, or that names a record the root
does not hold, fails where the head is built.

A commission carries controlled data only. Nothing in it was written by a model:

- the objective, a fixed sentence of this file for each axis;
- the head's selection (its evidence-axis option, thought pattern and tools), which the root's settings give for
  the axis and ``task.action`` put into ``arguments``;
- the proposed annotation and the scope, as the root was given them;
- the whole-axis finding task with the root's credit unit of the axis (``credit.AXIS_CREDIT_UNITS``): the setting
  that makes the nine axis scales comparable; for the heads that take them, the credit units of their
  operational children (``credit.OPERATIONAL_CREDIT_UNITS``);
- records in custody: the records the root was given and every record this axis's own head returned to the root
  earlier. A head measures its credit over the records it holds, so the axis's earlier records go back to it and
  its credit continues from where it stood. The records of a job a head left outstanding are among them: this
  is how the root returns to that head. Records another axis returned are not passed;
- empty constraints (every head's form has the field; the root has none to give).

The return fields the root selects (``SELECTION``) are record references only: ``committed_record_refs`` wherever a
head declares it selectable (the biochemical-feasibility head always returns it) and ``execution_handoff_refs``
from the sequence-homology head, the one head whose return form declares a job field today. Credit and finding
are always returned. ``messages/read_from_child.py`` reads exactly these fields."""
from episode_runtime import ChildMessage

from ..credit import AXIS_CREDIT_UNITS, OPERATIONAL_CREDIT_UNITS

TASK_VERSION = 'evidence_axis_task'
TASK_KIND = 'whole_axis_findings'

# The selectable fields of each head's return form the root asks for.
SELECTION = {
    'sequence_homology_evidence': ('committed_record_refs', 'execution_handoff_refs'),
    'structural_homology_evidence': ('committed_record_refs',),
    'gene_context_evidence': ('committed_record_refs',),
    'evolutionary_history_evidence': ('committed_record_refs',),
    'experimental_activity_evidence': ('committed_record_refs',),
    'perturbation_evidence': ('committed_record_refs',),
    'partner_presence_evidence': ('committed_record_refs',),
    'sample_context_evidence': ('committed_record_refs',),
    'biochemical_feasibility_evidence': (),
}


def unique(*groups):
    """The references of ``groups`` in order, each once."""
    return list(dict.fromkeys(ref for group in groups for ref in group))


def evidence_task(slot, axis):
    """The whole-axis finding task a head is commissioned with, in the root's credit unit of the axis."""
    return {'version': TASK_VERSION, 'kind': TASK_KIND, 'evidence_axis': axis,
            'credit_unit': AXIS_CREDIT_UNITS[slot]}


def returned(slot, summary):
    """Every record this axis's head returned to the root so far."""
    return summary['axes'][slot]['record_refs']


def sequence_homology_evidence(arguments, summary):
    """A101. The proposed annotation as text and in custody; the scope records in ``scope_refs``; the credit
    units of its operational children."""
    slot = 'sequence_homology_evidence'
    proposed = summary['proposed_annotation_ref']
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': proposed,
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A101')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs'],
        'proposed_annotation_refs': [proposed],
        'child_credit_units': dict(OPERATIONAL_CREDIT_UNITS)}
    return ChildMessage(objective='Establish what the sequence-homology evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def structural_homology_evidence(arguments, summary):
    """A102. The proposed annotation as one reference in custody; the scope records in ``scope_refs``."""
    slot = 'structural_homology_evidence'
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': [summary['proposed_annotation_ref']],
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A102')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs']}
    return ChildMessage(objective='Establish what the structural-homology evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def gene_context_evidence(arguments, summary):
    """A103. The proposed annotation as one reference in custody; the scope records in ``scope_refs``."""
    slot = 'gene_context_evidence'
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': [summary['proposed_annotation_ref']],
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A103')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs']}
    return ChildMessage(objective='Establish what the gene-context evidence shows about the proposed annotation '
                                  'of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def evolutionary_history_evidence(arguments, summary):
    """A104. The proposed annotation as text; the proposed annotation, the scope records and the further records
    in ``record_refs``. Its ``read_from_parent`` reads ``purpose`` (the kind of the task) and ``initial_report``
    from the message."""
    slot = 'evolutionary_history_evidence'
    proposed = summary['proposed_annotation_ref']
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': proposed,
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A104')},
        'scope': summary['scope'],
        'record_refs': unique([proposed], summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the evolutionary-history evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={'purpose': TASK_KIND, 'initial_report': {}},
                        assignment=assignment, selection=SELECTION[slot])


def experimental_activity_evidence(arguments, summary):
    """A105. The proposed annotation as text; one custody field, ``evidence_refs``, for the scope records, the
    proposed annotation and the evidence; its context is exactly the finding task."""
    slot = 'experimental_activity_evidence'
    proposed = summary['proposed_annotation_ref']
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': proposed,
        'evidence_refs': unique(summary['scope_refs'], [proposed], summary['evidence_refs'],
                                summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A105')},
        'scope': summary['scope']}
    return ChildMessage(objective='Establish what the experimental-activity evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def perturbation_evidence(arguments, summary):
    """A106. The proposed annotation as text; the proposed annotation, the scope records and the further records
    in ``received_record_refs``."""
    slot = 'perturbation_evidence'
    proposed = summary['proposed_annotation_ref']
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': proposed,
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A106')},
        'scope': summary['scope'],
        'received_record_refs': unique([proposed], summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the perturbation evidence shows about the proposed annotation '
                                  'of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def partner_presence_evidence(arguments, summary):
    """A107. The proposed annotation as one reference in custody; the scope records and the further records in
    ``received_record_refs``; the finding unit and the credit units of its operational children as fields of the
    assignment."""
    slot = 'partner_presence_evidence'
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': [summary['proposed_annotation_ref']],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A107')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs']),
        'finding_unit': AXIS_CREDIT_UNITS[slot],
        'handoff_unit': OPERATIONAL_CREDIT_UNITS['handoff_unit'],
        'acquired_record_unit': OPERATIONAL_CREDIT_UNITS['acquired_record_unit'],
        'information_unit': OPERATIONAL_CREDIT_UNITS['information_unit']}
    return ChildMessage(objective='Establish what the partner-presence evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def sample_context_evidence(arguments, summary):
    """A108. The proposed annotation as text; the proposed annotation, the scope records and the further records
    in ``received_record_refs``."""
    slot = 'sample_context_evidence'
    proposed = summary['proposed_annotation_ref']
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': proposed,
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A108')},
        'scope': summary['scope'],
        'received_record_refs': unique([proposed], summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the sample-context evidence shows about the proposed annotation '
                                  'of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def biochemical_feasibility_evidence(arguments, summary):
    """A110. The proposed annotation as one reference in custody; the scope records and the further records in
    ``received_record_refs``. Its return form requires ``committed_record_refs``, so nothing is selected."""
    slot = 'biochemical_feasibility_evidence'
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': [summary['proposed_annotation_ref']],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A110')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the biochemical-feasibility evidence shows about the proposed '
                                  'annotation of the assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


COMMISSIONS = {
    'sequence_homology_evidence': sequence_homology_evidence,
    'structural_homology_evidence': structural_homology_evidence,
    'gene_context_evidence': gene_context_evidence,
    'evolutionary_history_evidence': evolutionary_history_evidence,
    'experimental_activity_evidence': experimental_activity_evidence,
    'perturbation_evidence': perturbation_evidence,
    'partner_presence_evidence': partner_presence_evidence,
    'sample_context_evidence': sample_context_evidence,
    'biochemical_feasibility_evidence': biochemical_feasibility_evidence,
}


def msg_to_child(slot, arguments, summary):
    return COMMISSIONS[slot](arguments, summary)
