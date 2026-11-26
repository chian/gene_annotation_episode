"""The commission of each head: the nine axis heads, the feature calling head and the organism identification head
(the last two are no evidence axis and are commissioned on the root's scope alone; see their functions). One function
per slot, written against that head's own
``messages/read_from_parent.py`` (its assignment form and what it reads of the message) and
``messages/final_to_parent.py`` (the fields it declares it can return), read as data. Nothing is imported from an
axis folder, and nothing here checks a commission: one the head does not admit, or that names a record the root
does not hold, fails where the head is built.

A commission carries controlled data only. Nothing in it was written by a model:

- the objective, a fixed sentence of this file for each axis;
- the head's selection (its evidence-axis option, thought pattern and tools), which the root's settings give for
  the axis and ``task.action`` put into ``arguments``;
- the scope, as the root was given it; the root has no proposed annotation and passes none. A head that checks claims
  is given the claim it is commissioned on (a hypothesis record the head that found the annotation made from it);
- the whole-axis finding task with the root's credit unit of the axis (``credit.AXIS_CREDIT_UNITS``): the setting
  that makes the nine axis scales comparable; for the heads that take them, the credit units of their
  operational children (``credit.OPERATIONAL_CREDIT_UNITS``);
- records in custody: the records the root was given and every record this axis's own head returned to the root
  earlier. A head measures its credit over the records it holds, so the axis's earlier records go back to it and
  its credit continues from where it stood. The records of a job a head left outstanding are among them: this
  is how the root returns to that head. Records another axis returned are not passed;
- empty constraints (every head's form has the field; the root has none to give).

The return fields the root selects (``SELECTION``) are record references, ``committed_record_refs`` wherever a
head declares it selectable (the biochemical-feasibility head always returns it) and ``execution_handoff_refs``
from the sequence-homology head, the one head whose return form declares a job field today, and three fields of
controlled data from the sequence-homology head: ``candidate_hit_organisms`` (the organisms of the database hits
behind each of its candidates: taxon ids and hit counts) and ``candidate_hit_feature_kinds`` (the feature types of
those hits: types of the fixed list and hit counts) and ``claims`` (the claims it made from its leading candidate
annotations: the root makes none). Credit and finding are always returned.
``messages/read_from_child.py`` reads exactly these fields."""
from episode_runtime import ChildMessage

from ..credit import AXIS_CREDIT_UNITS, OPERATIONAL_CREDIT_UNITS

TASK_VERSION = 'evidence_axis_task'
TASK_KIND = 'whole_axis_findings'

# The selectable fields of each head's return form the root asks for.
SELECTION = {
    'sequence_homology_evidence': ('committed_record_refs', 'execution_handoff_refs', 'candidate_hit_organisms',
                                   'candidate_hit_feature_kinds', 'claims'),
    'structural_homology_evidence': ('committed_record_refs',),
    'gene_context_evidence': ('committed_record_refs',),
    'evolutionary_history_evidence': ('committed_record_refs',),
    'experimental_activity_evidence': ('committed_record_refs', 'sheet_state_refs'),
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
    """A101. The scope records in ``scope_refs``; no proposed annotation (the root has none: this head finds the
    candidate annotations, joins the names that are one function itself and makes the claims of its leading ones); the
    records feature calling returned (its feature records name the proteins this head works on); and the credit units of
    its operational children."""
    slot = 'sequence_homology_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary),
                                summary['features']['record_refs']),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A101')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs'],
        'child_credit_units': dict(OPERATIONAL_CREDIT_UNITS)}
    if arguments.get('organism_candidates'):
        assignment['organism_candidates'] = arguments['organism_candidates']
    return ChildMessage(objective='Find what the sequence-homology evidence shows the assigned subject to be',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def structural_homology_evidence(arguments, summary):
    """A102. The scope records in ``scope_refs``."""
    slot = 'structural_homology_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A102')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs']}
    return ChildMessage(objective='Establish what the structural-homology evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def gene_context_evidence(arguments, summary):
    """A103. The scope records in ``scope_refs``."""
    slot = 'gene_context_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A103')},
        'scope': summary['scope'], 'scope_refs': summary['scope_refs']}
    return ChildMessage(objective='Establish what the gene-context evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def evolutionary_history_evidence(arguments, summary):
    """A104. The scope records and the further records in ``record_refs``. Its ``read_from_parent`` reads ``purpose`` (the kind of the task) and ``initial_report``
    from the message."""
    slot = 'evolutionary_history_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A104')},
        'scope': summary['scope'],
        'record_refs': unique(summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the evolutionary-history evidence shows about the '
                                  'assigned subject',
                        message={'purpose': TASK_KIND, 'initial_report': {}},
                        assignment=assignment, selection=SELECTION[slot])


def experimental_activity_evidence(arguments, summary):
    """A105. It is commissioned on one claim (``arguments['claim_ref']``): a hypothesis record the head that found a
    candidate annotation made from it and returned, which is what the head evaluates (the head's own form names that field
    ``proposed_annotation_ref``; it is the root's claim, never an input of the root). One custody field,
    ``evidence_refs``, for the scope records, the claim with the records it names, and the evidence; its context is
    exactly the finding task. Once its head has returned a sheet for this claim, the sheet states of that return go back
    as ``sheet_state_refs``: the head continues that sheet and returns the rise of its credit since it
    (``read_from_child.CREDIT_RETURNED``). A sheet belongs to one claim: the states of another claim's sheet are not
    passed as this one's."""
    slot = 'experimental_activity_evidence'
    (claim,) = [made for made in summary['claims'] if made['claim_ref'] == arguments['claim_ref']]
    assignment = {
        'selection': arguments['selection'],
        'proposed_annotation_ref': claim['claim_ref'],
        'evidence_refs': unique(summary['scope_refs'], claim['record_refs'], summary['evidence_refs'],
                                summary['received_record_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A105')},
        'scope': summary['scope']}
    sheets = summary['axes'][slot]['claim_sheets']
    if claim['claim_ref'] in sheets and sheets[claim['claim_ref']]:
        assignment['sheet_state_refs'] = list(sheets[claim['claim_ref']])
    return ChildMessage(objective='Establish what the experimental-activity evidence shows about the claim '
                                  'it is commissioned on',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def perturbation_evidence(arguments, summary):
    """A106. The scope records and the further records
    in ``received_record_refs``."""
    slot = 'perturbation_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A106')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the perturbation evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def partner_presence_evidence(arguments, summary):
    """A107. The scope records and the further records in
    ``received_record_refs``; the finding unit and the credit units of its operational children as fields of the
    assignment."""
    slot = 'partner_presence_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A107')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs']),
        'finding_unit': AXIS_CREDIT_UNITS[slot],
        'handoff_unit': OPERATIONAL_CREDIT_UNITS['handoff_unit'],
        'acquired_record_unit': OPERATIONAL_CREDIT_UNITS['acquired_record_unit'],
        'information_unit': OPERATIONAL_CREDIT_UNITS['information_unit']}
    return ChildMessage(objective='Establish what the partner-presence evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def sample_context_evidence(arguments, summary):
    """A108. The scope records and the further records
    in ``received_record_refs``."""
    slot = 'sample_context_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A108')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the sample-context evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def biochemical_feasibility_evidence(arguments, summary):
    """A110. The scope records and the further records in
    ``received_record_refs``. Its return form requires ``committed_record_refs``, so nothing is selected."""
    slot = 'biochemical_feasibility_evidence'
    assignment = {
        'selection': arguments['selection'],
        'evidence_refs': unique(summary['evidence_refs'], returned(slot, summary)),
        'constraints': {},
        'context': {'evidence_task': evidence_task(slot, 'A110')},
        'scope': summary['scope'],
        'received_record_refs': unique(summary['scope_refs'], summary['received_record_refs'])}
    return ChildMessage(objective='Establish what the biochemical-feasibility evidence shows about the '
                                  'assigned subject',
                        message={}, assignment=assignment, selection=SELECTION[slot])


def feature_calling(arguments, summary):
    """The feature calling head (not an evidence axis): the root's own scope, as every head is commissioned on, with the
    records the scope names in custody (``scope_refs``) and, once it has returned, every record it returned to the root
    earlier (``evidence_refs``: its sources, their gradings and the feature records, which its sheet of feature calls
    reads among the sources it holds, so its credit continues from where it stood). Records another head returned are not
    passed. Its form takes no selection and no credit unit: its tools and databases are its own, and the root scales its
    credit (``credit.FEATURE_CREDIT_SCALE``). Selected: ``record_refs`` (so the root holds its records:
    the feature records, the tests' sources and the taxon claim sources of its searches) and ``held_readings`` (the
    genetic code held); its credit and its finding (the feature calls and the claims that wait for one) are always
    returned."""
    assignment = {'scope': summary['scope'], 'scope_refs': list(summary['scope_refs'])}
    if summary['features']['record_refs']:
        assignment['evidence_refs'] = list(summary['features']['record_refs'])
    return ChildMessage(objective='Find which features the sequence holds', message={}, assignment=assignment,
                        selection=('record_refs', 'held_readings'))


def organism_identification(arguments, summary):
    """The organism identification head (not an evidence axis): the root's own scope, as every head is commissioned on,
    with the records the scope names in custody. Its committed records are selected so the root holds its graded
    classifications, over which it computes the scoring sheet of candidate taxa (``internal_summary.organism_table``)."""
    assignment = {'scope': summary['scope'], 'scope_refs': list(summary['scope_refs'])}
    if summary['organism']['record_refs']:
        assignment['evidence_refs'] = list(summary['organism']['record_refs'])
    return ChildMessage(objective='Find which organism the sequence is from', message={}, assignment=assignment,
                        selection=('record_refs',))


COMMISSIONS = {
    'feature_calling': feature_calling,
    'organism_identification': organism_identification,
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
