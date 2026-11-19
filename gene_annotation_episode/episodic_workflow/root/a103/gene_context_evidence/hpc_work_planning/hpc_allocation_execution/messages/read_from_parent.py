"""What the commissioning planner gives (carried from ``from_parent.py``: ``HPCAssignment.assignment_schema``,
``commission_identity`` and ``_commission``; the only place the assignment is read).

Old assignment properties, under the same names: ``owner_episode_id`` (required: the planning Episode that owns
the HPC ledger) and exactly one of ``commission_id`` (the old enum of configured commissions) or
``commission_source_ref`` (a Store commission source). ``commission_source_ref`` is now a ``record_refs`` field,
because a record is passed only in custody.

New fields (each is a "new field" in the carry-over record): ``commission`` (the commission the owner holds: the
old code read it from its configuration or from the Store source, and neither ``read_from_parent`` nor the
yield estimator can), ``scope`` (the old ``context.scope``: the scope the sister inherits from its owner) and
``ledger_credit`` (the credit of the owner's ledger when the commission begins: the old ``initial_credit`` was the
ledger's credit view, which the shared ledger already held).

The old admission (``prepare_assignment``: the owner is the commissioning parent, the commission identity equals
the parent's, the commission carries ``yield_bindings``, the scope equals the owner's recorded scope) was the
child checking its commission; a wrong commission fails (rule 1) and none of those checks is carried. The
yield-binding requirement is the estimator's own declaration check."""
import math

from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'ledger': Field('text', "The id of the owner's HPC ledger (the scoped-store ledger is found by its id)"),
    'owner_episode_id': Field('text', 'The planning Episode that owns the HPC ledger of this commission'),
    'commission_id': Field('text', 'The configured commission this execution belongs to (exactly one of '
                                   'commission_id and commission_source_ref)', required=False),
    'commission_source_ref': Field('record_refs', 'The Store commission source this execution belongs to, passed '
                                   'in custody (exactly one of commission_id and commission_source_ref)',
                                   required=False),
    'commission': Field('record', 'The commission as the owner holds it: objective, resource_id, obligations, '
                                  'candidates, model, history, validation_ids, credit, preferences, limits and '
                                  'yield_bindings (new field)'),
    'scope': Field('record', 'The scope this sister inherits exactly from its owner, an empty subject_refs list '
                             'for an operational task (the old context.scope; new field)'),
    'ledger_credit': Field('number', 'The credit of the owner\'s ledger when this commission begins (new field)'),
})


def read_from_parent(assignment, message):
    identity = {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}
    if len(identity) != 1:
        raise ValueError('hpc_assignment_requires_exactly_one_of_commission_id_and_commission_source_ref')
    if 'commission_source_ref' in identity and len(identity['commission_source_ref']) != 1:
        raise ValueError('hpc_assignment_requires_exactly_one_commission_source_ref')
    credit = assignment['ledger_credit']
    if not math.isfinite(credit):
        raise ValueError('finite_hpc_ledger_credit_required')
    return {'ledger': assignment['ledger'], 'owner_episode_id': assignment['owner_episode_id'],
            'commission_identity': identity,
            'commission': dict(assignment['commission']), 'scope': dict(assignment['scope']),
            'ledger_credit': credit, 'launch_instructions': message.get('launch_instructions')}
