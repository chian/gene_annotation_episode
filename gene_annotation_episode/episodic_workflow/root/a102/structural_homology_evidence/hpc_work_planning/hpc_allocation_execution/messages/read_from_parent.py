"""What the commissioning HPC parent gives (carried from the old ``from_parent.py``).

Old assignment properties, under the same names: ``owner_episode_id`` (required: the ``hpc`` parent episode that owns
the ledger) and exactly one of ``commission_id`` (a statically configured commission) or ``commission_source_ref``
(a commission read from a Store source). The old schema was ``oneOf`` those two; a form cannot say that, so
``read_from_parent`` raises when it is not exactly one.

Fields the old code did not have (each is a "new field" in the carry-over record): ``scope`` (the old code took it
from its request: the subject scope of the original parent, which the owner's ledger must carry) and
``input_refs`` (the records the planned jobs read, passed in custody: the old code re-read them from the parent's own
assignment; the launch child's form requires them).

Not carried from the old ``prepare_assignment``: the check that the commissioning parent has the role ``hpc``, is the
episode named by ``owner_episode_id`` and carries the same commission identity (this function is handed no parent
assignment: a wrong commission fails where the ledger is opened, in ``task.py`` ``open_ledger``), and the check that
the commission carries ``yield_bindings`` (the controller's cost and parameters are this episode's settings now).
``read_from_parent`` is the only place the assignment is read: it returns what ``task.py`` needs to open the owner's
ledger and what ``msg_to_child.py`` passes on."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'owner_episode_id': Field('text', 'The hpc parent episode that owns the ledger'),
    'commission_id': Field('text', 'A statically configured commission (exactly one of commission_id and '
                                   'commission_source_ref)', required=False),
    'commission_source_ref': Field('text', 'The reference of the Store source holding the commission (exactly one of '
                                   'commission_id and commission_source_ref); only its identity is used here, the '
                                   'commission itself is read from the owner ledger', required=False),
    'scope': Field('record', 'The subject scope of the original parent; the owner ledger must carry it (new field)'),
    'input_refs': Field('record_refs', 'The records the planned jobs read, passed in custody (new field)'),
})


def read_from_parent(assignment, message):
    identity = {name: assignment[name] for name in ('commission_id', 'commission_source_ref') if name in assignment}
    if len(identity) != 1:
        raise ValueError('exactly_one_of_commission_id_and_commission_source_ref_required')
    return {'owner_episode_id': assignment['owner_episode_id'], 'commission_identity': identity,
            'scope': assignment['scope'], 'input_refs': list(assignment['input_refs'])}
