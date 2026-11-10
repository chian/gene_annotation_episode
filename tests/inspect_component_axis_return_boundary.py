"""Inspect original return-fact contexts and source labels on copied run state.

No model or native job executes. This replays the exact failed literature
received-fact boundary for retained episode roles, then uses the actual model
presenter on a retained request. It never resumes or modifies the original run.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.decision_context import apply_state_frame
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.state import Store


def present(request, context):
    presenter = _SessionConnection.__new__(_SessionConnection)
    presenter.scientific_prompt_states = {}
    return presenter._presentation(request['episode_id'], request['role'], request['instructions'], context)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-directory', required=True, type=Path)
    parser.add_argument('--run-directory', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--provider-request', required=True, type=Path)
    args = parser.parse_args()
    copied = args.run_directory.resolve() / 'state'
    copied.mkdir()
    with sqlite3.connect(args.state_directory.resolve().joinpath('state.sqlite3').as_uri() + '?mode=ro',
            uri=True) as original, sqlite3.connect(copied / 'state.sqlite3') as target:
        original.backup(target)
    shutil.copytree(args.state_directory / 'artifacts', copied / 'artifacts')
    review = {'kind': 'original_return_fact_boundary_and_source_metadata_replay',
        'model_executed': False, 'native_job_executed': False, 'original_state_modified': False,
        'return_contexts': []}
    with Store(copied) as store:
        api = EpisodeReturnRecords(store, args.run_id, failure_prefix='boundary_review_')
        receipts = EpisodeReceipts(store, args.run_id)
        services = WorkflowServices(SimpleNamespace(store=store, run_id=args.run_id))
        binding = LiteratureEpisodes(services, rate_population=True)
        before = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('runtime_actions', 'runtime_observations', 'records')}
        assert LiteraturePartnerRepository(store, args.run_id).cells_schema() == partner_cells_schema()
        episodes = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY rowid',
            (args.run_id,)).fetchall()
        for row in episodes:
            context = replace(api.context(row[0]), received_record_refs=tuple(receipts.known(row[0])))
            facts = binding.received_report_facts(context)
            assert not any(facts.values()), 'No original numerical return was admitted before the failure.'
            review['return_contexts'].append({'episode_id': context.episode_id, 'role': context.role,
                'all_literature_received_fact_providers_completed': True,
                'numerical_cells_exposed': 0})
        assert before == {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in before}
    request = json.loads(args.provider_request.read_text())
    original_text = '\n'.join(block['text'] for block in request['input'] if 'text' in block)
    # Authenticate the retained frame first. The comparison is a presentation
    # over its decoded state, not a forged frame with an outdated revision.
    without_metadata = deepcopy(apply_state_frame(None, request['context']))
    without_metadata['working_state']['sources'] = []
    baseline, baseline_instructions = present(request, without_metadata)
    assert baseline == original_text, 'The baseline must reproduce the actual transmitted request exactly.'
    actual, actual_instructions = present(request, request['context'])
    assert actual_instructions == baseline_instructions == request['model_instructions']
    state = request['context']['fields']
    selected = set(state['scientific_process']['assignment'].get('evidence_refs', ())) | set(
        state['working_state'].get('supplied_context_source_refs', ()))
    sources = [row for row in state['working_state']['sources'] if row['id'] in selected]
    for source in sources:
        assert source['id'] in actual
        if source.get('uri') is not None:
            assert source['uri'] in actual
    start = actual.index('Selected source operands (metadata only)')
    # The added identity section precedes the unchanged scientific task.
    end = actual.index('Investigate the supplied target:', start)
    assert actual[:start] + actual[end:] == baseline
    review['source_operand_presentation'] = {'original_request': str(args.provider_request),
        'episode_id': request['episode_id'], 'selected_sources': len(sources),
        'actual_old_prompt_reproduced_exactly': True,
        'all_selected_source_ids_and_uris_visible': True,
        'all_other_task_and_steering_text_unchanged': True,
        'model_instructions_unchanged': True,
        'no_source_contents_acquired_or_added': True}
    (args.run_directory / 'boundary-review.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
