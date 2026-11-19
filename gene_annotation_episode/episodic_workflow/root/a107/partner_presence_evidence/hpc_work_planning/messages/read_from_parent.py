"""What the commissioner gives, carried from the old ``from_parent.py`` (``HPCAssignment.assignment_schema``,
``commission_identity``, ``_commission``, ``prepare_assignment``, ``_tool_request``).

Old assignment properties, under the same names: exactly one of ``commission_id`` (one of the configured
commissions) or ``commission_source_ref`` (a host commission grant read from the Store), and the optional
``tool_request`` ``{name, resources (api, local or hpc), arguments_json, result_reader, objective}``. A form cannot
say "exactly one of" and has no single-reference type, so ``commission_source_ref`` is a ``record_refs`` field
holding one reference and ``read_from_parent`` raises when it is not exactly one identity (the old ``oneOf``).

Fields the old code did not have (each a "new field" in the carry-over record): ``scope`` (the old
``context.scope``: the subject scope of the original task, which the ledger's owner identity carries),
``received_record_refs`` (the old ``context.received_record_refs``: the records the commissioner passes in custody,
such as received result sources and, for a commission source, the source) and ``input_refs`` (the records the planned
jobs read: the old code re-read them from the parent's own assignment; the launch and allocation children need them
named, because a pass carries only the records named).

Not carried from the old ``prepare_assignment``: the checks that the commission source is among
``parent.received_record_refs`` (custody: the field is a ``record_refs`` field, so the commissioner must hold it), that
a ``tool_request`` resolves against the parent's tool library with an actual result reader and valid arguments (the
parent's tool library is the old ``partner_presence_evidence_binding.tool_library``, which has no home: the use raises
in ``task.py``, ``resolve_tool_request``) and that the commission carries ``yield_bindings`` (the controller's cost and
parameters are this episode's settings now). ``read_from_parent`` is the only place the assignment is read."""
from method_loop import ChoiceField, Field, RecordForm

TOOL_REQUEST_FORM = RecordForm({
    'name': Field('text', 'The tool to run through the HPC template'),
    'resources': ChoiceField('text', 'The resource kind the original callable declares', ('api', 'local', 'hpc')),
    'arguments_json': Field('text', 'The arguments of the tool as JSON object text'),
    'result_reader': Field('text', 'The parent tool that reads the result'),
    'objective': Field('text', 'What the requested computation is for'),
})

ASSIGNMENT_FORM = RecordForm({
    'commission_id': Field('text', 'One of the configured HPC commissions (exactly one of commission_id and '
                                   'commission_source_ref)', required=False),
    'commission_source_ref': Field('record_refs', 'The host commission grant, one record passed in custody '
                                                  '(exactly one of commission_id and commission_source_ref)',
                                   required=False),
    'tool_request': Field('record', 'A scientific tool request to implement exactly through the HPC template',
                          form=TOOL_REQUEST_FORM, required=False),
    'scope': Field('record', 'The subject scope of the original task (the old binding context scope; new field)'),
    'received_record_refs': Field('record_refs', 'Records the commissioner passes in custody, such as received HPC '
                                                 'result sources (the old received_record_refs; new field)',
                                  required=False),
    'input_refs': Field('record_refs', 'The records the planned jobs read, passed in custody (new field)',
                        required=False),
})


def read_from_parent(assignment, message):
    identities = [name for name in ('commission_id', 'commission_source_ref') if name in assignment]
    if len(identities) != 1:
        raise ValueError('hpc_assignment_requires_exactly_one_commission_identity')
    source = assignment.get('commission_source_ref')
    if source is not None and len(source) != 1:
        raise ValueError('hpc_commission_source_ref_requires_exactly_one_reference')
    return {'commission_id': assignment.get('commission_id'),
            'commission_source_ref': None if source is None else source[0],
            'tool_request': assignment.get('tool_request'),
            'scope': assignment['scope'],
            'received_record_refs': list(assignment.get('received_record_refs', [])),
            'input_refs': list(assignment.get('input_refs', [])),
            'launch_instructions': message.get('launch_instructions')}
