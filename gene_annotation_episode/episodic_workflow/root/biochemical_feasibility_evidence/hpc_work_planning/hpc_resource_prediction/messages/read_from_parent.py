"""What the commissioner gives, carried from the old ``from_parent.py`` (``PredictionAssignment.assignment_schema``,
``commission_identity``): ``owner_episode_id`` (required) and exactly one of ``commission_id`` (the old enum of the
configured commissions) or ``commission_source_ref``, under the old names.

New field: ``ledger_refs`` (``record_refs``). The old child opened the parent-owned HPC ledger by its directory
(``<directory>/hpc/<digest(run, owner)>/hpc.sqlite``); a file ledger read by path by another episode does not exist
any more (README 3c). The ledger is the work table ``hpc_evidence`` (declared in ``task.py``), and the parent names
the rows the child reads in this field: the ``commission`` row and the ``owner`` row at least, and any earlier
model, model choice, candidate, queue, plan, measured, closed, result, shared-history, tool-request and credit
rows. A passed row does not bring the rows it names (decision T5), so every row the child will read is named.

The old admission of ``prepare_assignment`` (the owner must be the commissioning hpc episode, the commission
identity equal to the parent's, a commission carrying ``yield_bindings``) judged a commission: it is not carried
(rule 1). The one-of rule of the old schema (``oneOf`` required ``commission_id`` or ``commission_source_ref``) is
the reading of the assignment and is kept here. ``launch_instructions`` is the section selection the old
``decision_inputs`` read from the request message (``episode_assignment.launch_instructions``)."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'owner_episode_id': Field('text', 'The commissioning hpc episode, owner of the ledger'),
    'commission_id': Field('text', 'A configured commission (one of commission_id and commission_source_ref)',
                           required=False),
    'commission_source_ref': Field('text', 'A commission read from a record (one of commission_id and '
                                           'commission_source_ref)', required=False),
    'ledger_refs': Field('record_refs', 'The rows of the parent-owned HPC ledger (work table hpc_evidence) the '
                                        'prediction reads, passed in custody (new field)'),
})


def read_from_parent(assignment, message):
    identity = {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}
    if len(identity) != 1:
        raise ValueError('hpc_prediction_assignment_requires_exactly_one_of_commission_id_or_commission_source_ref')
    return {'owner_episode_id': assignment['owner_episode_id'], **identity,
            'ledger_refs': list(assignment['ledger_refs']),
            'launch_instructions': message.get('launch_instructions')}
