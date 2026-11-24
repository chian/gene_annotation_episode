"""What the parent gives: the owner of the HPC ledger, the commission identity, the ledger records held in custody
and the yield binding of the commission (``hpc_work_planning`` commissions this episode).

Carried from the old ``from_parent.py`` (``PredictionAssignment.assignment_schema``, ``commission_identity``,
``prepare_assignment``). The assignment is read only here: ``read_from_parent`` returns the parent input that the
summary, the credit, the controller and the tools read.

Old assignment properties, under their own names: ``owner_episode_id`` (required), ``commission_id`` and
``commission_source_ref`` (exactly one of the two; the old schema's ``oneOf``). ``commission_source_ref`` is now a
``record_refs`` field holding the one commission source record (a form has no single-reference type). Two fields
are new (contract_misfits): ``ledger_refs`` (the parent-owned HPC ledger records this episode reads, passed in
custody: the old ledger was a file this episode opened by path) and ``yield_binding`` (the old commission's
``yield_bindings['hpc_prediction']``, ``{cutoff, parameters}``, which ``yield_controller`` needs and is handed no
ledger to read).

Not carried (a check of a commission): the old ``prepare_assignment`` refusal of an assignment that did not come
from an ``hpc`` parent whose episode id is the owner and whose commission identity is the same
(``prediction_or_execution_must_belong_to_its_original_hpc_parent``), and the old ``state`` comparison of the
ledger's owner record with the assignment (``sister_scope_must_equal_original_parent_scope``). A wrong commission
fails where its records are read."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'owner_episode_id': Field('text', 'The hpc parent episode that owns the ledger'),
    'commission_id': Field('text', 'One of the static commissions of the binding (exactly one of this and '
                           'commission_source_ref)', required=False),
    'commission_source_ref': Field('record_refs', 'A Store commission source record, passed in custody (exactly one '
                                   'reference; exactly one of this and commission_id)', required=False),
    'ledger_refs': Field('record_refs', 'The parent-owned HPC ledger records this episode reads, passed in custody'),
    'yield_binding': Field('record', 'The commission yield binding of this episode: cutoff (the continuation cost) '
                           'and parameters'),
})


def commission_identity(assignment):
    """The old ``commission_identity``: whichever of the two commission fields the assignment names."""
    return {key: assignment[key] for key in ('commission_id', 'commission_source_ref') if key in assignment}


def read_from_parent(assignment, message):
    identity = commission_identity(assignment)
    if len(identity) != 1:
        raise ValueError('hpc_prediction_exactly_one_commission_required')
    if 'commission_source_ref' in identity:
        if len(identity['commission_source_ref']) != 1:
            raise ValueError('hpc_prediction_one_commission_source_required')
        identity = {'commission_source_ref': identity['commission_source_ref'][0]}
    binding = assignment['yield_binding']
    return {'owner_episode_id': assignment['owner_episode_id'],
            'commission_identity': identity,
            'ledger_refs': list(assignment['ledger_refs']),
            'yield_binding': {'cutoff': binding['cutoff'], 'parameters': dict(binding['parameters'])},
            'message': dict(message)}
