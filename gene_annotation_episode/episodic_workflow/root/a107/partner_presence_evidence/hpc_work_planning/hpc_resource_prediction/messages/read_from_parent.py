"""What the commissioner gives, carried from the old ``from_parent.py`` (``PredictionAssignment``).

The old schema: ``owner_episode_id`` (required) and exactly one of ``commission_id`` (one of the configured
commissions) or ``commission_source_ref`` (a host commission grant read from the Store). A form cannot say "exactly
one of"; ``read_from_parent`` raises when both or neither is given (the old ``oneOf``). ``commission_source_ref``
is a ``record_refs`` field holding one reference (a form has no single-reference type).

The HPC ledger is rows of a work table in custody (``episode_support/jobs/hpc_ledger.py``): ``ledger_row_refs`` are
the rows of the owner's ledger (and the records they name) that the commissioner passes, so that this Episode reads
them. The ledger is named by its commission, so no ledger id is passed: the episode opens the ledger of its
commission and finds the passed rows under it. Without passed rows (an entry Episode) it creates the ledger.

New fields, which the old code took from its binding context and not from the assignment: ``scope`` (the old
``context.scope``) and ``received_record_refs`` (the old ``context.received_record_refs``: the records the
commissioner passes in custody, e.g. the result sources of the sister's allocations).

Not carried: the old ``prepare_assignment`` checks of the commission against the parent (parent role ``hpc``, owner
episode equal to the parent, commission identity equal to the parent's, yield binding present). They were the
parent's check of its own commission, which fails when it is wrong (nothing checks one ahead). The yield binding
is read from the run's settings in ``yield_estimator.py``. ``initial_information``, ``received_api_reports`` and
``received_execution_information`` (selection of declared readers of the old catalog) are not carried."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'owner_episode_id': Field('text', 'The HPC planning episode that owns the ledger this episode works on'),
    'commission_id': Field('text', 'One of the configured HPC commissions (exactly one of commission_id and '
                                   'commission_source_ref)', required=False),
    'commission_source_ref': Field('record_refs', 'The host commission grant, one record passed in custody '
                                                  '(exactly one of commission_id and commission_source_ref)',
                                   required=False),
    'scope': Field('record', 'The scope of the original HPC episode (the old binding context scope)'),
    'ledger_row_refs': Field('record_refs', "The rows of the owner's HPC ledger and the records they name, passed "
                                            'in custody', required=False),
    'received_record_refs': Field('record_refs', 'Records the commissioner passes in custody, such as received '
                                                 'HPC result sources', required=False),
})


def read_from_parent(assignment, message):
    identities = [name for name in ('commission_id', 'commission_source_ref') if name in assignment]
    if len(identities) != 1:
        raise ValueError('hpc_assignment_requires_exactly_one_commission_identity')
    source = assignment.get('commission_source_ref')
    if source is not None and len(source) != 1:
        raise ValueError('hpc_commission_source_ref_requires_exactly_one_reference')
    return {'owner_episode_id': assignment['owner_episode_id'],
            'commission_id': assignment.get('commission_id'),
            'commission_source_ref': None if source is None else source[0],
            'scope': assignment['scope']}
