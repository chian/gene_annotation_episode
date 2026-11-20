"""The commission of each child, built by code from the commission this episode holds and from the records its
earlier children returned. Controlled values and record references only; every record a child reads is named in a
``record_refs`` field, and exactly those records pass.

``launch_local`` receives the controlled commission itself (the sequence set by reference, the kind and its
fields, the local resource and the handoff credit unit) and returns its handoff row, the artifact of the plan the
job runs and whether the handoff exists. ``results`` receives the handoff row and that plan (so the job's receipt is
checked against what actually ran), the sequence set, the declared kind and the credit one usable record earns, and
returns the reference of the prepared-data record. A commission a child's form does not admit fails (nothing here
checks it for the child)."""
from episode_runtime import ChildMessage

LAUNCH_SELECTION = ('execution_handoff_refs', 'execution_completed', 'plan_refs')
RESULTS_SELECTION = ('prepared_data_refs',)
OPTIONAL = ('parse_seqids', 'hash_index', 'db_version', 'program', 'output_format', 'window', 'level', 'linker',
            'locut', 'hicut')


def msg_to_child(slot, arguments, summary):
    fields = summary['fields']
    if slot == 'launch_local':
        return ChildMessage(
            objective='Launch the preparation job on the assigned local resource and return its handoff',
            message={},
            assignment={'version': 'blast_preparation_launch_assignment_v1', 'kind': fields['kind'],
                        'molecule': fields['molecule'], 'input_refs': [fields['input_ref']],
                        **{name: fields[name] for name in OPTIONAL if name in fields},
                        'resource_id': summary['resource_id'], 'handoff_unit': summary['handoff_unit']},
            selection=LAUNCH_SELECTION)
    if slot == 'results':
        return ChildMessage(
            objective='Establish the prepared-data record of the launched preparation job',
            message={},
            assignment={'version': 'blast_preparation_results_assignment_v1',
                        'handoff_refs': [summary['handoff_refs'][0]], 'plan_refs': [summary['plan_refs'][0]],
                        'input_refs': [fields['input_ref']], 'kind': fields['kind'],
                        'prepared_unit': summary['prepared_unit']},
            selection=RESULTS_SELECTION)
    raise ValueError('blast_database_preparation_slot_unknown:' + slot)
