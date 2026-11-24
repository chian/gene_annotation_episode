"""What the commissioning A110 parent gives (carried from the old ``from_parent.py`` ``HPCAssignment``).

Old assignment properties, under the same names: ``commission_id`` (one of the configured commissions; the old
schema made it an ``enum`` of the construction settings, which a form cannot read, so it is free text here),
``commission_source_ref`` (a host-issued commission read from a Store source: a ``record_refs`` field now, because
the commission is read from the held source; exactly one reference) and the optional ``tool_request`` (name,
resources, arguments_json, result_reader, objective). The old schema was ``oneOf`` the two commission identities; a
form cannot say that, so ``read_from_parent`` raises when it is not exactly one.

Fields the old code did not have (each is a "new field" in the carry-over record): ``scope`` (the old code took it
from the request message: the subject scope fixed by the commissioning parent, which the owner ledger carries and
the sisters must equal) and ``input_refs`` (the records the planned jobs read, passed in custody: the launch child's
form requires them).

Not carried from the old ``prepare_assignment``: the check that a ``commission_source_ref`` was received by the parent
(custody does it: the pass of a ``record_refs`` field requires the commissioner to hold the record), the check that
the commission carries ``yield_bindings`` for a private yield (the controller's cost and parameters are this
episode's settings now) and the resolution of ``tool_request`` against the A110 head's tool library (it happens
where the ledger is opened, in ``task.py``, and raises there: see the carry-over record).

This is the only place the assignment is read."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'commission_id': Field('text', 'A configured commission (exactly one of commission_id and commission_source_ref)',
                           required=False),
    'commission_source_ref': Field('record_refs', 'The host-issued Store source holding the commission (exactly one '
                                   'of commission_id and commission_source_ref; exactly one reference)',
                                   required=False),
    'tool_request': Field('record', 'The scientific tool computation to implement through the HPC template: name, '
                          'resources (api, local or hpc), arguments_json, result_reader and objective',
                          required=False),
    'scope': Field('record', 'The subject scope fixed by the commissioning parent (new field)'),
    'input_refs': Field('record_refs', 'The records the planned jobs read, passed in custody (new field)'),
})

TOOL_REQUEST_KEYS = ('name', 'resources', 'arguments_json', 'result_reader', 'objective')


def read_from_parent(assignment, message):
    identity = {}
    if 'commission_id' in assignment:
        identity['commission_id'] = assignment['commission_id']
    if 'commission_source_ref' in assignment:
        if len(assignment['commission_source_ref']) != 1:
            raise ValueError('hpc_commission_source_ref_must_hold_exactly_one_reference')
        identity['commission_source_ref'] = assignment['commission_source_ref'][0]
    if len(identity) != 1:
        raise ValueError('exactly_one_of_commission_id_and_commission_source_ref_required')
    parent_input = {'commission_identity': identity, 'scope': assignment['scope'],
                    'input_refs': list(assignment['input_refs']), 'message': dict(message)}
    if 'tool_request' in assignment:
        request = assignment['tool_request']
        if set(request) != set(TOOL_REQUEST_KEYS):
            raise ValueError('hpc_tool_request_must_name:' + ','.join(TOOL_REQUEST_KEYS))
        parent_input['tool_request'] = request
    return parent_input
