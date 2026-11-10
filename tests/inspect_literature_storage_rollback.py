"""Replay a retained literature context after cached table creation rolls back.

This diagnostic uses copied original state, real WorkflowServices and the
original literature decision-context builder. It performs no model, source
acquisition, numerical calculation or native job, and never resumes the run.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.state import Store


class RolledBackSelection(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-directory', required=True, type=Path)
    parser.add_argument('--run-directory', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--episode', required=True)
    args = parser.parse_args()
    copied = args.run_directory.resolve() / 'state'
    copied.mkdir()
    with sqlite3.connect(args.state_directory.resolve().joinpath('state.sqlite3').as_uri() + '?mode=ro',
            uri=True) as original, sqlite3.connect(copied / 'state.sqlite3') as target:
        original.backup(target)
    shutil.copytree(args.state_directory / 'artifacts', copied / 'artifacts')
    with Store(copied) as store:
        api = EpisodeReturnRecords(store, args.run_id, failure_prefix='storage_review_')
        context = replace(api.context(args.episode), received_record_refs=tuple(
            EpisodeReceipts(store, args.run_id).known(args.episode)))
        services = WorkflowServices(SimpleNamespace(store=store, run_id=args.run_id))
        tables = ('literature_rate_operations', 'literature_rate_received', 'literature_rate_source_received')

        def installed():
            return [name for name in tables if store.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()]

        # The original failure has no rate tables or rate acquisitions.
        assert installed() == []
        before = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('runtime_actions', 'runtime_observations', 'records')}
        try:
            with store.transaction():
                repository = services.literature_rate_repository()
                projection = repository.source_projection()
                assert set(installed()) == set(tables)
                raise RolledBackSelection()
        except RolledBackSelection:
            pass
        assert installed() == []
        assert services.literature_rate_repository() is repository
        assert repository.source_projection() is projection
        assert set(installed()) == set(tables)
        assert projection.received_cells(context) == []
        binding = LiteratureEpisodes(services, rate_population=True)
        displayed = binding.decision_context(context, {})
        assert displayed['literature_assignment']['requested_reaction_components']
        assert displayed['literature_rate_source_display'] == {'cells': [], 'records': {}}
        assert before == {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in before}
        review = {'kind': 'retained_decision_context_after_rolled_back_storage',
            'episode_id': context.episode_id, 'original_state_modified': False,
            'original_empty_optional_rate_storage_confirmed': True,
            'cached_repository_identity_preserved': True,
            'cached_source_projection_identity_preserved': True,
            'rolled_back_schema_restored': True,
            'actual_literature_decision_context_completed': True,
            'optional_rate_display': displayed['literature_rate_source_display'],
            'scientific_records_actions_observations_unchanged': True,
            'model_executed': False, 'native_job_executed': False}
        (args.run_directory / 'storage-review.json').write_text(json.dumps(review, indent=2) + '\n')
        print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
