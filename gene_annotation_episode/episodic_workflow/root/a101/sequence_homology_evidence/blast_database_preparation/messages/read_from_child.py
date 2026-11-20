"""What the parent takes from a child's return, all of it controlled data. From ``launch_local``: the handoff
row and plan references it returned (now held by this episode), whether the handoff exists, its credit and its
finding (counts). From ``results``: the reference of the prepared-data record it wrote, its credit and its finding
(the state, whether the product is usable and the checked facts). Both children declare these fields and
``msg_to_child`` selects them."""


def read_from_child(slot, result, summary, records):
    if slot == 'launch_local':
        return {'slot': slot, 'handoff_refs': list(result['execution_handoff_refs']),
                'plan_refs': list(result['plan_refs']), 'completed': result['execution_completed'],
                'credit': result['credit'], 'finding': result['finding']}
    return {'slot': slot, 'prepared_refs': list(result['prepared_data_refs']), 'credit': result['credit'],
            'finding': result['finding']}
