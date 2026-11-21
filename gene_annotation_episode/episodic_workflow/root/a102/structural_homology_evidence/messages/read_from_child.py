"""How the A102 head reads each child's return (carried from the ``from_child_*.py`` files at ``97308b94c``; the
literature child is removed).

The old receivers admitted the child's typed form against the report contract (a failed admission became feedback
for ``redeliver_report``), then received the references in it. Here the system admits the result against the
child's own return form (a result that does not fit fails the run) and the receipts of the records the child
returned are the system's. What this function makes is the head's report of the unit: the child's credit and
finding, the names of the fields it returned and, by slot:

* ``structural_homology_evidence`` (the head again): the process results it returned
  (``structural_homology_evidence_results``), which join this head's own in its return;
* ``monitor``: the old ``receive_progress`` read every ``episode_progress`` reference of the form through the
  progress provider before granting the observations. The monitor now returns its controlled finding (whether the
  job was observed, its state, whether its results are available, when) and the check rows it wrote
  (``check_refs``), in custody: the report keeps their references, and the summary reads the rows through its
  records (``outstanding_jobs``).

Every other slot (``execution_launch``, ``resource_launch``, ``execution_results``, ``resource_results``, ``hpc``)
reports credit, finding and the returned field names; their records are held in custody and read where a tool or the
summary names them.
"""
from __future__ import annotations

BASE = ('credit', 'finding')


def read_from_child(slot, result, summary, records):
    report = {'slot': slot, 'child_credit': result['credit'], 'child_finding': result['finding'],
              'returned': sorted(set(result) - set(BASE)), 'process_results': [], 'check_refs': []}
    if slot == 'structural_homology_evidence':
        report['process_results'] = list(result.get('structural_homology_evidence_results', []))
    elif slot == 'monitor':
        report['check_refs'] = list(result['check_refs'])
    return report
