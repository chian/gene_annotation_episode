"""What the commissioning HPC parent gives: its own episode id and the commission, named either by its configured
id or by a record (passed in custody). This is the only place the assignment is read."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'ledger': Field('text', "The id of the owner's HPC ledger (the scoped-store ledger is found by its id)"),
    'owner_episode_id': Field('text', 'The commissioning HPC parent episode that owns the ledger'),
    'commission_id': Field('text', 'The configured commission, when it is named by id', required=False),
    'commission_source_ref': Field('record_refs', 'The one record that holds the commission, passed in custody, '
                                   'when it is not named by id', required=False),
})


def read_from_parent(assignment, message):
    identity = {}
    if 'commission_id' in assignment:
        identity['commission_id'] = assignment['commission_id']
    if 'commission_source_ref' in assignment:
        refs = assignment['commission_source_ref']
        if len(refs) != 1:
            raise ValueError('hpc_commission_source_ref_must_name_exactly_one_record')
        identity['commission_source_ref'] = refs[0]
    if len(identity) != 1:
        raise ValueError('hpc_commission_must_be_exactly_one_of_commission_id_or_commission_source_ref')
    return {'ledger': assignment['ledger'], 'owner_episode_id': assignment['owner_episode_id'],
            'commission_identity': identity,
            'launch_instructions': message.get('launch_instructions')}
