"""What the parent takes from a resource child's admitted return: its finding, the execution handoffs it returned
(old ``execution_handoff`` / ``execution_handoffs`` facts; the single ``execution_handoff`` is one of them), the
records that carry them (named under each child's own field) and the child adapter's own facts when it returned
them. The old proof of a received handoff (``received_form_references``) is custody: the child returns the records
and the system writes the ``returned`` receipts."""

# The field of each child's return form that carries its handoff records.
REF_FIELD = {'launch_api': 'execution_handoff_refs', 'launch_local': 'execution_handoff_record_refs',
             'launch_hpc': 'handoff_refs'}


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'finding': result['finding'], 'execution_handoffs': result['execution_handoffs'],
            'handoff_refs': list(result[REF_FIELD[slot]]), 'adapter_facts': result.get('adapter_facts', {})}
