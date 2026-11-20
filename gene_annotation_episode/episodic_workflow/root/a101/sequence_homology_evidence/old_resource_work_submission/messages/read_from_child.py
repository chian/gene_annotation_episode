"""What the parent takes from a resource child's admitted return (carried from
``from_child_api_resource_work_execution.py``, ``from_child_hpc_resource_work_execution.py`` and
``from_child_local_resource_work_execution.py``, ``receive_report``; the three were identical but for role and
binding path).

The old receiver checked the delivery's role and binding path, passed the admitted form to the progress provider,
asked the adapter for the proof references of every returned handoff
(``resource_information_handoff_proof_missing``), recorded the native timing references and registered everything
as received: old-runner machinery (the system receipts the records a child returns; the old handoff proof is the
child's own custody). What is kept is what the parent's credit and report read: the handoffs the child returned, the
adapter facts, the handoff records it returned in custody and its own finding and credit. The three children
declare their handoff facts in different shapes (a record, with ``{}`` for none, from the API and HPC children; a
list of zero or one handoff from the local child); the report always holds the list ``execution_handoffs``, which
every child returns, and the child's handoff records under whichever required or selected field it declares
(``execution_handoff_refs`` of the API child, ``handoff_refs`` of the HPC child, none from the local child)."""


def read_from_child(slot, result, summary, records):
    refs = result.get('execution_handoff_refs', result.get('handoff_refs', []))
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding'],
            'execution_handoffs': list(result['execution_handoffs']),
            'adapter_facts': dict(result.get('adapter_facts', {})), 'handoff_refs': list(refs)}
