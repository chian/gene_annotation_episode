"""What the parent takes from a resource child's admitted return: its finding, the execution handoffs it returned
(old ``execution_handoff`` / ``execution_handoffs`` facts; the single ``execution_handoff`` is one of them), the
records that carry them and the child adapter's own facts when it returned them. The old proof of a received
handoff (``received_form_references``) is custody: the child returns the records and the system writes the
``returned`` receipts."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'finding': result['finding'], 'execution_handoffs': result['execution_handoffs'],
            'handoff_refs': list(result['execution_handoff_refs']), 'adapter_facts': result.get('adapter_facts', {})}
