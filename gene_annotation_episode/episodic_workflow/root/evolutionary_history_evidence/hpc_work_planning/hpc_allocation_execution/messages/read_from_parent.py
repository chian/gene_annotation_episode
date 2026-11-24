"""What the commissioner gives: the HPC parent's commission (old ``HPCAssignment.assignment_schema``: ``owner_episode_id``
and exactly one of ``commission_id`` or ``commission_source_ref``), under the same names, and the operational values
the old binding took from its configuration or from the commissioning request and the new form needs.

This is the only place the assignment is read. The old ``prepare_assignment`` checks (the commissioning parent is the
HPC episode that owns the commission, the owner id and the commission identity equal the parent's own, the commission
carries its yield binding) are checks of a commission: a wrong commission fails and nothing checks it ahead
(rule 1), so they are not carried. The old ``oneOf`` of the schema (exactly one commission identity) is made here and
raises."""
import math

from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'owner_episode_id': Field('text', 'The HPC parent episode that owns the commission and its ledger'),
    'ledger': Field('text', 'The id of the owner ledger the parent opened (its rows travel in ledger_refs)'),
    'ledger_refs': Field('record_refs', 'The rows of the owner ledger, passed in custody'),
    'commission_id': Field('text', 'The identity of a configured HPC commission (exactly one of this and '
                                   'commission_source_ref)', required=False),
    'commission_source_ref': Field('record_refs', 'The one Store record that holds the HPC commission, passed in '
                                                  'custody (the old text reference; exactly one of this and '
                                                  'commission_id)', required=False),
    # New fields the final form needs: the old code read the scope from the commissioning request and the units
    # from the configuration of the child roles.
    'scope': Field('record', 'The scope the HPC parent was commissioned on; the sisters inherit exactly the '
                             'parent\'s scope (an operational task has an empty subject_refs list)'),
    'handoff_unit': Field('number', 'Operational credit of each new usable handoff, for the launch child '
                                    '(old launch configuration handoff_unit)'),
    'acquired_record_unit': Field('number', 'Operational credit of an acquired record, for the launch and results '
                                            'children (old configuration acquired_record_unit)'),
    'information_unit': Field('number', 'The credit of one newly informative progress snapshot, for the monitor '
                                        'child (old monitor configuration information_unit)'),
})


def _positive(value):
    if value <= 0 or not math.isfinite(value):
        raise ValueError('explicit_positive_operational_credit_units_required')
    return value


def read_from_parent(assignment, message):
    """The commission identity, the scope and the units, as the parent input."""
    given = [name for name in ('commission_id', 'commission_source_ref') if name in assignment]
    if len(given) != 1:
        raise ValueError('hpc_assignment_requires_exactly_one_commission_identity')
    commission = {}
    if 'commission_id' in assignment:
        commission['commission_id'] = assignment['commission_id']
    else:
        if len(assignment['commission_source_ref']) != 1:
            raise ValueError('hpc_assignment_requires_exactly_one_commission_source_ref')
        commission['commission_source_ref'] = assignment['commission_source_ref'][0]
    return {'owner_episode_id': assignment['owner_episode_id'], 'commission': commission,
            'ledger': assignment['ledger'], 'ledger_refs': list(assignment['ledger_refs']),
            'record_refs': list(assignment.get('commission_source_ref', [])), 'scope': assignment['scope'],
            'handoff_unit': _positive(assignment['handoff_unit']),
            'acquired_record_unit': _positive(assignment['acquired_record_unit']),
            'information_unit': _positive(assignment['information_unit'])}
