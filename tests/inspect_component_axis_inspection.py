"""Read-only reconstruction of source reuse in an actual retained decision.

This runs no model, scientific calculator, historical action or new receipt.
Autonomous use and efficiency still require a fresh complete investigation.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.component_axis_source_access import decision_context
from gene_annotation_episode.decision_context import apply_state_frame, state_frame
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.state import Store


def present(request, state):
    frame = state_frame(state)
    for key in ('restored_pending_decision_index', 'restored_public_exchanges'):
        if key in request['context']:
            frame[key] = deepcopy(request['context'][key])
    presenter = _SessionConnection.__new__(_SessionConnection)
    presenter.scientific_prompt_states = {}
    return presenter._presentation(request['episode_id'], request['role'],
                                   request['instructions'], frame)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-directory', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--provider-request', type=Path, required=True)
    parser.add_argument('--run-directory', type=Path, required=True)
    args = parser.parse_args()
    # Skip the Store's write-capable initialization; any accidental write is
    # rejected by SQLite itself. Existing Store readers still restore metadata.
    store = Store.__new__(Store)
    store.path, store._savepoint = args.state_directory.resolve(), 0
    store.db = sqlite3.connect((store.path / 'state.sqlite3').as_uri() + '?mode=ro',
                               uri=True, isolation_level=None)
    store.db.row_factory = store._row
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    try:
        receipts = EpisodeReceipts(store, args.run_id)
        api = EpisodeReturnRecords(store, args.run_id, failure_prefix='inspection_review_')
        workflow = SimpleNamespace(store=store, run_id=args.run_id, receipts=receipts)
        before = {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            for table in ('records', 'runtime_actions', 'runtime_observations', 'runtime_record_receipts')}
        views = {}
        for row in store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=?',
                                   (args.run_id,)).fetchall():
            context = replace(api.context(row[0]), received_record_refs=tuple(receipts.known(row[0])))
            view = decision_context(workflow, context)
            if view is None or 'own_source_inspection' not in view:
                continue
            inspected = view['own_source_inspection']
            own_indices = {r[0] for r in store.db.execute('SELECT decision_index FROM runtime_actions '
                'WHERE run_id=? AND episode_id=?', (args.run_id, context.episode_id))}
            for group in ('read_sources', 'located_passages', 'saved_component_results'):
                for item in inspected[group]:
                    assert set(item['decision_indices']) <= own_indices
            for search in inspected['located_passages']:
                for match in search['matches']:
                    quote = match['witness']
                    artifact = store.get_artifact(match['artifact_ref'])
                    assert artifact[quote['start']:quote['end']] == quote['quote'].encode()
            assert inspected['credit_change'] is inspected['permission_change'] is False
            views[context.episode_id] = view

        request = json.loads(args.provider_request.read_text())
        state = apply_state_frame(None, request['context'])
        original = deepcopy(state)
        compact, compact_instructions = present(request, state)
        old_text = '\n'.join(part['text'] for part in request['input'] if 'text' in part)
        assert compact_instructions == request['model_instructions']
        context = views[request['episode_id']]
        selected = deepcopy(state)
        selected['component_axis_source_access'] = context
        visible, instructions = present(request, selected)
        assert instructions == compact_instructions and state == original
        assert 'Recorded source inspections and access' in visible
        for search in context['own_source_inspection']['located_passages']:
            for match in search['matches']:
                assert match['witness']['quote'] in visible
        populations = context['own_source_inspection']['saved_component_results']
        for result in populations:
            assert result['sheet_ref'] in visible
        assert before == {table: store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                          for table in before}
        assert store.db.total_changes == 0
        report = {'kind': 'retained_state_reconstruction_not_autonomous_execution',
            'model_executed': False, 'native_job_executed': False,
            'original_database_opened_readonly': True, 'original_database_changes': 0,
            'original_action_observation_and_receipt_counts': before,
            'all_located_quotations_match_original_artifact_bytes': True,
            'original_input_characters': len(old_text),
            'focused_same_state_input_characters': len(compact),
            'focused_input_with_retained_inspection_characters': len(visible),
            'source_episode_count': len(views), 'selected_episode_id': request['episode_id'],
            'own_component_results': len(populations), 'per_episode_views': views,
            'scientific_formulas_credit_and_stopping_unchanged': True}
        args.run_directory.joinpath('inspection-review.json').write_text(json.dumps(report, indent=2) + '\n')
        args.run_directory.joinpath('reconstructed-model-input.txt').write_text(visible)
        print(json.dumps({key: value for key, value in report.items() if key != 'per_episode_views'}, indent=2))
    finally:
        store.close()


if __name__ == '__main__':
    main()
