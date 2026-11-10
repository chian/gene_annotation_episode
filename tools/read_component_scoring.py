"""Read current A107/A110 parent sheets from real retained episode receipts.

This data reader starts no model, calculation, remote job or replay. It uses
the same scientific projection as the live binding, with the original saved
repositories and the receiving episode's actual receipt inventory.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path

from gene_annotation_episode.component_axis_reports import current_scoring_sheets
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store
from gene_annotation_episode.workflow_budget import active_budget


class SavedScientificReaders:
    """Only the real saved-data repositories needed by the current projection."""

    def __init__(self, store, run_id):
        self.partner = LiteraturePartnerRepository(store, run_id)
        self.reaction = LiteratureReactionRepository(store, run_id)

    def literature_partner_repository(self):
        return self.partner

    def literature_reaction_repository(self):
        return self.reaction


def read_case(directory, output, episode_id=None):
    directory = directory.resolve()
    if not (directory/'state'/'state.sqlite3').is_file():
        raise ValueError('existing_episode_state_required')
    prepared = json.loads((directory/'prepared.json').read_text())
    configuration = json.loads((directory/'configuration.json').read_text())
    run_id = prepared['run_id']
    with Store(directory/'state') as store:
        readers = SavedScientificReaders(store, run_id)
        receipts = EpisodeReceipts(store, run_id)
        # Repository initialization above only installs its ordinary schemas.
        # The actual scientific read below cannot mutate evidence or receipts.
        store.db.execute('PRAGMA query_only=ON')
        if episode_id is None:
            rows = list(store.db.execute('SELECT episode_id FROM runtime_episodes '
                'WHERE run_id=? AND json(path)=json(?)',
                (run_id, json.dumps([['annotation', 'root']]))))
            if len(rows) != 1:
                raise ValueError('one_original_annotation_root_required')
            episode_id = rows[0]['episode_id']
        context = EpisodeReturnRecords(store, run_id,
            failure_prefix='retained_component_scoring_').context(episode_id)
        context = replace(context, received_record_refs=tuple(receipts.known(episode_id)))
        sheets = current_scoring_sheets(store, context=context, services=readers,
            configured_axes=(configuration['axis'],))
        report = {'version': 'retained_parent_scoring_read_v1', 'run_directory': str(directory),
            'run_id': run_id, 'receiving_episode_id': episode_id,
            'scientific_execution': 'retained_original_work; no_new_execution',
            'scoring_sheets': sheets}
        destination = output/(directory.name+'-current-scoring.json')
        destination.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        summary = {'run_id': run_id, 'receiving_episode_id': episode_id,
            'axes': {axis: {'native_results': [
                {'source_ref': row['source_ref'], 'pbs_job_id': row['pbs_job_id'],
                    'scientific_profile': row['scientific_profile'],
                    **({'components': row['native_components']['components']}
                        if 'components' in row['native_components'] else
                        {'component_sections': sorted(row['native_components'])})}
                for row in sheet['native_component_results']],
                'experimental_components': sum(len(row['components'])
                    for row in sheet['numerical_results'])}
                for axis, sheet in sheets.items()}, 'output': str(destination)}
        print(json.dumps(summary, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path, nargs='+')
    parser.add_argument('--episode-id')
    arguments = parser.parse_args()
    if arguments.episode_id is not None and len(arguments.run_directory) != 1:
        raise ValueError('explicit_episode_requires_one_run')
    owner = active_budget()
    output = Path(owner['run_directory'])
    for name in ('tmp', 'cache'):
        (output/name).mkdir(exist_ok=True)
    os.environ.update(TMPDIR=str(output/'tmp'), XDG_CACHE_HOME=str(output/'cache'))
    for directory in arguments.run_directory:
        read_case(directory, output, arguments.episode_id)


if __name__ == '__main__':
    main()
