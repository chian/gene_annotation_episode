"""Replay retained real grading publications through automatic sheet updates.

No model, acquisition, scientific decision or original trace is executed or
changed. Only scientific state is copied, and source artifacts are copied on
first read. This avoids copying the much larger model/execution journal.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_required_grading import action_schema
from gene_annotation_episode.literature_sheet_updates import current_scoring_sheets
from gene_annotation_episode.state import Store


class CopiedScientificStore(Store):
    def __init__(self, path, original):
        self.original = original
        super().__init__(path)

    def get_artifact(self, ref):
        row = self.db.execute('SELECT sha256 FROM artifacts WHERE id=?', (ref,)).fetchone()
        if row is not None:
            relative = Path('artifacts') / row[0][:2] / row[0]
            destination = self.path / relative
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.original / relative, destination)
        return super().get_artifact(ref)


def replay(original, output, axis):
    with sqlite3.connect(original.joinpath('state.sqlite3').as_uri() + '?mode=ro', uri=True) as source:
        source.row_factory = sqlite3.Row
        with CopiedScientificStore(output / 'state', original) as store:
            base = {'artifacts', 'problem', 'inputs', 'records', 'record_roots',
                'current_revisions', 'proposals', 'reasoning_commits'}
            copied = []
            with store.transaction():
                for table in source.execute("SELECT name,sql FROM sqlite_master WHERE type='table'"):
                    name = table['name']
                    if name not in base and not name.startswith('literature_'):
                        continue
                    if name in {'literature_sheet_dependencies', 'literature_current_scoring_sheets'}:
                        continue
                    if name not in base:
                        store.db.execute(table['sql'])
                    columns = source.execute('PRAGMA table_info("' + name + '")').fetchall()
                    placeholders = ','.join('?' for _ in columns)
                    store.db.executemany('INSERT INTO "' + name + '" VALUES(' + placeholders + ')',
                        source.execute('SELECT * FROM "' + name + '" ORDER BY rowid'))
                    copied.append(name)
            run_id = source.execute('SELECT run_id FROM literature_' +
                ('assay_grading' if axis == 'A105' else 'a108_grading') + '_operations LIMIT 1').fetchone()
            if run_id is None:
                return {'axis': axis, 'retained_gradings': 0, 'copied_tables': copied}
            run_id = run_id[0]
            binding = LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store, run_id=run_id)),
                rate_population=True, assay_grading_population=True, a108_context_evidence=True,
                completion_time_population=True, product_partition_population=True,
                active_site_population=True, parent_depletion_population=True,
                stoichiometric_balance_population=True, compiled_assay_population=True,
                channel_population=True, ion_discrimination_population=True,
                ratio_source_population=True)
            native = binding._assay_grading_repository() if axis == 'A105' else binding._a108_grading_repository()
            schema = action_schema({'type': 'object'}, native.population_schema())
            entry = schema['properties']['evidence_processing']['anyOf'][0]['properties']['gradings']['items']
            assert set(entry['properties']) == {'arguments'}
            originals = list(store.db.execute('SELECT * FROM ' + native.operations_table + ' ORDER BY rowid'))
            results = []
            contexts = {}
            for original_operation in originals:
                outcome = json.loads(original_operation['outcome'])
                ref = outcome['result']['sheet_ref']
                saved = native.read(ref)
                request = json.loads(store.get_artifact(store.get(ref)['request_ref']))
                previous = contexts.get(request['episode_id'])
                refs = list(dict.fromkeys([*(previous.received_record_refs if previous else ()),
                    *saved['direct_record_refs']]))
                context = BindingContext(run_id, request['episode_id'], 'literature',
                    (('annotation', 'retained_root'), ('literature', 'retained_source')),
                    request['scope'], {native.requested: list(native.components)}, {}, tuple(refs))
                updated = native.populate(context, saved['selection'],
                    'retained_publication_replay:' + request['operation_key'])
                after = native.read(updated['result']['sheet_ref'])
                before_cells, after_cells = saved['sheet']['cells'], after['sheet']['cells']
                changes = [name for name in before_cells
                    if canonical(before_cells[name]) != canonical(after_cells[name])]
                regressed = [name for name in before_cells
                    if before_cells[name]['value'] is not None
                    and canonical(before_cells[name]['value']) != canonical(after_cells[name]['value'])]
                assert not regressed, {'source_sheet': ref, 'regressed': regressed}
                context = replace(context, received_record_refs=tuple(dict.fromkeys([
                    *context.received_record_refs, *updated['record_refs']])))
                contexts[context.episode_id] = context
                current = current_scoring_sheets(store, context)
                assert any(sheet['axis'] == axis for sheet in current)
                results.append({'source_sheet_ref': ref,
                    'saved_sheet_ref': updated['result']['sheet_ref'],
                    'changed_cells': changes, 'automatic_main_sheets': [
                        sheet['sheet_ref'] for sheet in current if sheet['axis'] == axis],
                    'original_requested_components': request['requested_components'],
                    'original_record_refs': outcome['record_refs'],
                    'updated_record_refs': updated['record_refs']})
            report = {'axis': axis, 'retained_gradings': len(originals), 'replayed': len(results),
                'numerical_value_regressions': 0, 'results': results,
                'current_scoring_sheets': [sheet for context in contexts.values()
                    for sheet in current_scoring_sheets(store, context)],
                'copied_tables': copied,
                'scope': 'retained_native_publication_replay_not_autonomous_workflow_validation'}
            (output / 'replay.json').write_text(json.dumps(report, indent=2) + '\n')
            return {'axis': axis, 'retained_gradings': len(originals),
                'replayed': len(results), 'numerical_value_regressions': 0,
                'automatic_main_sheet_count': store.db.execute('SELECT count(*) FROM ' +
                    ('literature_a105_aggregation_operations' if axis == 'A105'
                     else 'literature_a108_aggregation_operations')).fetchone()[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--a105-state', type=Path, required=True)
    parser.add_argument('--a108-state', type=Path, required=True)
    args = parser.parse_args()
    summary = []
    for axis, original in (('A105', args.a105_state), ('A108', args.a108_state)):
        output = args.output / axis
        output.mkdir(parents=True)
        summary.append(replay(original.resolve(), output, axis))
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
