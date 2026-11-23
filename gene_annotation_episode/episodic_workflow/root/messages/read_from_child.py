"""What the root takes from an axis head's return: controlled data only.

- ``credit``: the credit the head returned (never bounded, clamped or rescaled). What it measures is the head's own
  (``CREDIT_RETURNED``): the axis credit as it stands over every record the head holds, or the rise since the sheet
  the head was given. ``messages/internal_summary.py`` makes the axis credit from it.
- ``sheet_state_refs``: the subscoring-sheet states the head returned (``SHEET_FIELDS``), which go back to it as the
  sheet it is given at its next commission.
- ``finding``: the numbers and flags of the head's finding, under the head's own field names. Text, lists and
  nested records of a finding stay with the head that wrote them and are not read, except the annotation rows below:
  nothing a model wrote reaches the root's summary or the root's model.
- ``annotation_rows``: the score channel. One row per candidate annotation the head scored, read from the head's own
  scoring sheet as it returned it in its finding (``ANNOTATION_ROWS``): which annotation (``vocabulary``, and the
  ``name`` and ``identifier`` its source gives it), the ``status`` of the evidence (``ROW_STATUS``) and its ``score``:
  the one number that head's scoring sheet gives the annotation, on that head's own scale, never bounded, clamped or
  rescaled here (absent when the status is unknown, never written as 0). A head whose sheet keeps support and
  opposition apart returns them too, so conflict stays visible. These rows are what ``messages/internal_summary.py``
  merges into the root's scoring sheet. The score never reads a credit, and the credit never reads a score.
- ``record_refs``: the records the head returned in the fields the root selected (``RECORD_FIELDS``), which the
  root now holds and passes back to that head at its next commission.
- ``outstanding_job_refs``: the records of the jobs the head left outstanding when it ended its turn
  (``JOB_FIELDS``).

Each head's fields are named here against its own ``messages/final_to_parent.py``, read as data."""

# The record-reference fields of each head's return the root reads.
RECORD_FIELDS = {
    'sequence_homology_evidence': ('committed_record_refs', 'execution_handoff_refs'),
    'structural_homology_evidence': ('committed_record_refs',),
    'gene_context_evidence': ('committed_record_refs',),
    'evolutionary_history_evidence': ('committed_record_refs',),
    'experimental_activity_evidence': ('committed_record_refs',),
    'perturbation_evidence': ('committed_record_refs',),
    'partner_presence_evidence': ('committed_record_refs',),
    'sample_context_evidence': ('committed_record_refs',),
    'biochemical_feasibility_evidence': ('committed_record_refs',),
}
# What the credit of each head's return measures, read from its own ``credit.py``. ``standing``: the credit over every
# record the head holds, so with its earlier records passed back it continues from where it stood (A101: the differential
# credit of the held graded sources). ``rise``: the rise since the sheet the head was given, so each return adds to the
# axis credit (A105: the strongest evidence on its latest sheet minus that on the sheet it was given). The heads that
# are not linked yet (``task.CHILD_SLOTS``) stand as the root first assumed them and are to be read when they are linked.
CREDIT_RETURNED = {
    'sequence_homology_evidence': 'standing',
    'structural_homology_evidence': 'standing',
    'gene_context_evidence': 'standing',
    'evolutionary_history_evidence': 'standing',
    'experimental_activity_evidence': 'rise',
    'perturbation_evidence': 'standing',
    'partner_presence_evidence': 'standing',
    'sample_context_evidence': 'standing',
    'biochemical_feasibility_evidence': 'standing',
}
# The fields of a head's return that hold its subscoring-sheet states, for the heads that take them back as a field of
# their own (``sheet_state_refs`` of the A105 assignment).
SHEET_FIELDS = {
    'sequence_homology_evidence': (),
    'structural_homology_evidence': (),
    'gene_context_evidence': (),
    'evolutionary_history_evidence': (),
    'experimental_activity_evidence': ('sheet_state_refs',),
    'perturbation_evidence': (),
    'partner_presence_evidence': (),
    'sample_context_evidence': (),
    'biochemical_feasibility_evidence': (),
}
# Of the record fields, the ones that name the records of jobs a head left outstanding.
JOB_FIELDS = {
    'sequence_homology_evidence': ('execution_handoff_refs',),
    'structural_homology_evidence': (),
    'gene_context_evidence': (),
    'evolutionary_history_evidence': (),
    'experimental_activity_evidence': (),
    'perturbation_evidence': (),
    'partner_presence_evidence': (),
    'sample_context_evidence': (),
    'biochemical_feasibility_evidence': (),
}


# The status of the evidence of a row, as the heads' scoring sheets name it.
ROW_STATUS = ('measured', 'measured_zero', 'unknown')
# The vocabularies of a candidate annotation: the three of the sequence-homology head's candidates (a database search's
# function, a family of a profile database, a sequence record it was compared with) and the proposed annotation (a
# hypothesis record), which is what the experimental-activity head scores.
VOCABULARIES = ('product', 'profile_family', 'reference_sequence', 'proposed_annotation')


def sequence_homology_rows(finding):
    """A101. The finding holds one entry per target of the scope, and the root annotates one subject: one target. Each
    of its candidates (the possible annotations found, each with its annotation score: the sum of its values on the
    head's subscoring sheets, never negative) is a row with that score. This head's sheets hold no evidence against a
    candidate, so its rows have no support and opposition apart from the score."""
    (target,) = finding['targets']
    return [{'vocabulary': candidate['vocabulary'], 'name': candidate['name'],
             **({'identifier': candidate['identifier']} if 'identifier' in candidate else {}),
             'status': 'measured' if candidate['score'] else 'measured_zero', 'score': candidate['score']}
            for candidate in target['candidates']]


def experimental_activity_rows(finding):
    """A105. The finding holds one score per candidate annotation of the head's main scoring sheet: the hypothesis
    record it is about (``assertion_ref``), the status, the summed support and opposition, and the head's one scalar for
    the annotation: ``tanh((support - opposition) / 2)``, between -1 and 1, negative when the evidence says the claim
    does not hold. The scalar is the row's score. The head omits the numbers when the status is unknown."""
    return [{'vocabulary': 'proposed_annotation', 'identifier': score['assertion_ref'], 'status': score['status'],
             **({'score': score['scalar']} if 'scalar' in score else {}),
             **{name: score[name] for name in ('support', 'opposition') if name in score}}
            for score in finding['scores']]


# How the annotation rows of each linked head's return are read from its finding, written against that head's own
# ``messages/final_to_parent.py``. A head is listed here when it is linked (``task.CHILD_SLOTS``).
ANNOTATION_ROWS = {
    'sequence_homology_evidence': sequence_homology_rows,
    'experimental_activity_evidence': experimental_activity_rows,
}


def references(result, fields):
    """The references of the named fields of a return, in order, each once."""
    return list(dict.fromkeys(ref for field in fields for ref in result[field]))


def read_from_child(slot, result, summary, records):
    return {'credit': result['credit'],
            'finding': {name: value for name, value in result['finding'].items()
                        if type(value) in (bool, int, float)},
            'annotation_rows': ANNOTATION_ROWS[slot](result['finding']),
            'record_refs': references(result, (*RECORD_FIELDS[slot], *SHEET_FIELDS[slot])),
            'sheet_state_refs': references(result, SHEET_FIELDS[slot]),
            'outstanding_job_refs': references(result, JOB_FIELDS[slot])}
