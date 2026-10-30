"""Fresh-process reopen proof for the two closed controlled Workflow examples."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent.parent))


def main():
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.state import Store
    from gene_annotation_episode import literature_binding_model_storage as module
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(BASE):
        raise ValueError('owned_examples_required')
    original = json.loads((directory / 'POPULATED_MODEL_EXAMPLES.json').read_text())
    def forbidden(*_args, **_kwargs):
        raise AssertionError('model_parser_or_calculator_or_original_source_read_forbidden')
    module.read_binding_model = forbidden
    module.populate_binding_model = forbidden
    module.binding_model_operand_keys = forbidden
    reports = []
    for case in original['cases']:
        if not case['ordinary_workflow_executed']:
            continue
        path = directory / case['name'] / 'state'
        with Store(path) as store:
            run_id, = store.db.execute('select run_id from runtime_runs').fetchone()
            repo = module.LiteratureBindingModelRepository(store, run_id)
            returns = EpisodeReturnRecords(store, run_id, failure_prefix='binding_model_reopen_')
            receipts = EpisodeReceipts(store, run_id)
            row, = store.db.execute('select * from literature_binding_model_operations').fetchall()
            outcome = json.loads(row['outcome'])
            source = store.get(outcome['result']['sheet_ref'])
            # Only original committed numerical sheet/request artifacts may be
            # read. Original table, model-input and witness bytes are forbidden.
            allowed = set()
            for record in store.list('source'):
                if record['provider'] in ['literature.experimental.binding_model',
                                          'literature.experimental.binding_parameter']:
                    allowed.update([record['artifact_ref'], record['request_ref']])
            get_artifact = store.get_artifact
            reads = []
            def saved_only(reference):
                assert reference in allowed, 'original_table_or_model_or_witness_read'
                reads.append(reference)
                return get_artifact(reference)
            store.get_artifact = saved_only
            store.db.execute('pragma query_only=ON')
            before = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
            context = returns.context(row['episode_id'])
            context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
            request = json.loads(store.get_artifact(source['request_ref']))
            assert repo.populate(context, request['arguments'], row['operation_key']) == outcome
            cells = repo.project_cells([source['id']], permitted_record_refs=context.received_record_refs,
                components=context.assignment['requested_binding_model_components'])
            attempt, = store.db.execute('select parent_episode_id,decision_index from runtime_report_attempts').fetchall()
            parent = returns.context(attempt['parent_episode_id'])
            child, form, _ = returns._attempt(parent, attempt['decision_index'])
            assert child.episode_id == context.episode_id
            assert canonical(form['measurements']) == canonical(cells)
            assert canonical(repo.received_cells(parent)) == canonical(cells)
            assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == before == 4
            reports.append({'case': case['name'], 'run_id': run_id, 'cells': len(cells),
                'actual_parent_subset_equals_saved_cells': True, 'observations_before_and_after': before,
                'saved_host_artifact_reads': reads})
    result = {'status': 'passed', 'cases': reports, 'original_input_bytes_read': False,
        'parser_calculator_disabled': True, 'replay_SQL_query_only': True,
        'scope': 'Fresh process reopen of closed controlled examples; no live inference/host restart.'}
    (directory / 'REOPEN_MODEL_RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'cases': len(reports), 'original_input_bytes_read': False}))


if __name__ == '__main__':
    main()
