"""Read and admit an already returned original HPC result; perform no execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.a104_hpc import import_result


def main():
    active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    args = parser.parse_args()
    case = args.case_directory.resolve()
    prepared = json.loads((case/'PREPARED.json').read_text())
    run_id = 'a104-hpc-'+case.parent.name
    with Store(case/'state') as store:
        roots = [row for row in store.db.execute('SELECT episode_id,path,state,completion FROM runtime_episodes WHERE run_id=?', (run_id,))
                 if json.loads(row['path']) == [['hpc', 'root']]]
        if len(roots) != 1 or roots[0]['state'] != 'yielded' or roots[0]['completion'] is None:
            raise ValueError('a104_retained_admission_requires_original_completed_hpc_parent')
        known = set(EpisodeReceipts(store, run_id).known(roots[0]['episode_id']))
        results = sorted(ref for ref in known if store.get(ref).get('provider') == 'episode.hpc_result')
        admitted = [import_result(store, request_ref=prepared['native_request_ref'], hpc_result_ref=reference,
            known_record_refs=known, scope=prepared['scope'], run_id=run_id, workflow_directory=case/'workflow')
            for reference in results]
        summary = {'event': 'a104_original_hpc_result_admitted', 'run_id': run_id,
            'hpc_result_refs': results, 'native_phylogeny_refs': admitted, 'completed_native_admission': bool(admitted),
            'execution': 'original_completed_PBS_job; reader_repair_only; no_resubmission',
            'scientific_credit_status': 'native_received; measurements_and_attribution_follow'}
        (case/'HPC_RESULT.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
