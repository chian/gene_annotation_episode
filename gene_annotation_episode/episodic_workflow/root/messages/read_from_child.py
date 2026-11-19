"""What the root takes from an axis head's return: controlled data only.

- ``credit``: the axis credit, as the head returned it (never bounded, clamped or rescaled). It is the signal of
  whether the axis was productive; nothing else restates it.
- ``finding``: the numbers and flags of the head's finding, under the head's own field names. Text, lists and
  nested records of a finding stay with the head that wrote them and are not read: nothing a model wrote reaches
  the root's summary or the root's model.
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
# Of those, the fields that name the records of jobs a head left outstanding.
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


def references(result, fields):
    """The references of the named fields of a return, in order, each once."""
    return list(dict.fromkeys(ref for field in fields for ref in result[field]))


def read_from_child(slot, result, summary, records):
    return {'credit': result['credit'],
            'finding': {name: value for name, value in result['finding'].items()
                        if type(value) in (bool, int, float)},
            'record_refs': references(result, RECORD_FIELDS[slot]),
            'outstanding_job_refs': references(result, JOB_FIELDS[slot])}
