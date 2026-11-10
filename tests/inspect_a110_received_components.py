"""Review actual retained A110 receipts on a disposable copy, without a model.

This is a custody/adapter replay, not an autonomous investigation. Supply the
original state directory, baseline receiver and descendants explicitly. It
never resumes the original run or changes its saved evidence.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-directory', required=True, type=Path)
    parser.add_argument('--run-directory', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--baseline-episode', required=True)
    parser.add_argument('--episode', action='append', required=True)
    parser.add_argument('--sheet-ref', required=True)
    parser.add_argument('--expected-count', required=True, type=int)
    args = parser.parse_args()
    target = args.run_directory.resolve() / 'state'
    shutil.copytree(args.state_directory, target)
    for suffix in ('-wal', '-shm'):
        (target / ('state.sqlite3' + suffix)).unlink(missing_ok=True)
    with sqlite3.connect(args.state_directory.resolve().joinpath('state.sqlite3').as_uri() + '?mode=ro',
            uri=True) as original, sqlite3.connect(target / 'state.sqlite3') as copied:
        original.backup(copied)
    review = {'kind': 'retained_receipt_and_adapter_replay', 'model_executed': False,
        'native_job_executed': False, 'original_state_modified': False, 'contexts': []}
    with Store(target) as store:
        api = EpisodeReturnRecords(store, args.run_id, failure_prefix='review_')
        receipts = EpisodeReceipts(store, args.run_id)
        repository = LiteratureReactionRepository(store, args.run_id)

        def context(episode):
            return replace(api.context(episode), received_record_refs=tuple(receipts.known(episode)))

        baseline = [row for row in repository.received_cells(context(args.baseline_episode))
            if row['sheet_ref'] == args.sheet_ref]
        assert len(baseline) == args.expected_count
        expected = {row['component']: row for row in baseline}
        original_actions = store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
        original_observations = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        for episode in args.episode:
            ctx = context(episode)
            rows = [row for row in repository.received_cells(ctx) if row['sheet_ref'] == args.sheet_ref]
            assert len(rows) == args.expected_count
            assert canonical({row['component']: row for row in rows}) == canonical(expected)
            malformed = deepcopy(plain(ctx.request))
            malformed['message']['knowledge_inheritance']['received_report_prefix']['attempts'] = []
            try:
                repository.received_cells(replace(ctx, request=malformed))
            except ValueError:
                pass
            else:
                raise AssertionError('changed frozen inheritance was accepted')
            review['contexts'].append({'episode_id': episode, 'components': len(rows),
                'all_original_descriptors_identical': True, 'forged_prefix_rejected': True})
        # Exercise the new adapter on the genuinely received source quantities.
        # Its missing biological prerequisites must stay unknown.
        from gene_annotation_episode import a110_experimental_qualification as experiment
        from gene_annotation_episode.a110_qualification import received
        ctx = context(args.episode[0])
        root = next(iter({row['target_ref'] for row in store.coverage(ctx.scope['subject_refs'][0])}))
        arguments = {'target_ref': root, 'sheet_ref': args.sheet_ref, 'components': ['ratio_mean'],
            'reaction_ref': None, 'assessment_ref': None, 'actual_ref': None,
            'target_subject_ref': root, 'source_alignment_ref': None, 'alignment_ref': None,
            'positions': None}
        known = set(ctx.received_record_refs)
        request = experiment.request(store, arguments, context=ctx, known=known)
        qualified, needs = experiment.refresh(store, ctx, known | {request})
        assert len(qualified) == 1 and needs
        result = experiment.read(store, qualified[0], qualified=True)
        assert result['result']['state'] == 'per_use_application_unresolved'
        assert result['result']['selected_components'] == [expected['ratio_mean']]
        assert result['scientific_credit'] is None
        admitted = received(store, qualified, ctx.scope, known=known | set(qualified))
        assert len(admitted) == 1
        assert admitted[0]['result']['selected_components'] == [expected['ratio_mean']]
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == original_actions
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == original_observations
        review['experimental_adapter'] = {'qualified_ref': qualified[0],
            'selected_components_identical': True, 'state': result['result']['state'],
            'missing': result['result']['missing'], 'automatic_grading_authenticated': True,
            'existing_A110_qualified_return_reader_accepts_result': True,
            'new_iterator_observations': 0, 'combined_scientific_score': None}
    (args.run_directory / 'receipt-review.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
