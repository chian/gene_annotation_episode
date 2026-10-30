"""Verify the closed controlled primary example without reading source bytes again."""
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
    from gene_annotation_episode import literature_binding_storage as module
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(BASE):
        raise ValueError('owned_controlled_example_required')
    original = json.loads((directory / 'RECEIPT.json').read_text())
    def forbidden(*_args, **_kwargs):
        raise AssertionError('reacquisition_or_recalculation_forbidden')
    module.read_binding_parameter_table = forbidden
    module.populate_binding_contrast = forbidden
    module.Image.open = forbidden
    with Store(directory / 'state') as store:
        run_id = original['run_id']
        repo = module.LiteratureBindingRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix='binding_reopen_')
        receipts = EpisodeReceipts(store, run_id)
        rows = store.db.execute('select * from literature_binding_operations where run_id=?', (run_id,)).fetchall()
        assert len(rows) == 1
        row = rows[0]
        outcome = json.loads(row['outcome'])
        sheet_ref = outcome['result']['sheet_ref']
        sheet_source = store.get(sheet_ref)
        get_artifact = store.get_artifact
        allowed = {sheet_source['artifact_ref'], sheet_source['request_ref']}
        reads = []
        def saved_only(reference):
            assert reference in allowed, 'original_source_artifact_must_not_be_read'
            reads.append(reference)
            return get_artifact(reference)
        store.get_artifact = saved_only
        store.db.execute('pragma query_only=ON')
        before = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
        context = returns.context(row['episode_id'])
        context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
        request = json.loads(store.get_artifact(sheet_source['request_ref']))
        assert repo.populate(context, request['arguments'], row['operation_key']) == outcome
        cells = repo.project_cells([sheet_ref], permitted_record_refs=context.received_record_refs,
            components=context.assignment['requested_binding_components'])
        attempt, = store.db.execute('select parent_episode_id,decision_index from runtime_report_attempts').fetchall()
        parent = returns.context(attempt['parent_episode_id'])
        child, form, schema = returns._attempt(parent, attempt['decision_index'])
        assert child.episode_id == context.episode_id
        assert canonical(form['measurements']) == canonical(cells)
        assert canonical(repo.received_cells(parent)) == canonical(cells)
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == before
    receipt = {'status': 'passed', 'run_id': run_id, 'saved_cells': len(cells),
        'actual_parent_admitted_subset_equal': True, 'original_source_artifacts_read': False,
        'parser_calculator_image_reader_disabled': True, 'replay_SQL_query_only': True,
        'observations_before_and_after': before, 'saved_artifact_reads': reads,
        'scope': 'Fresh process reopens actual controlled primary Workflow records; not live inference or host restart.'}
    (directory / 'REOPEN_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
