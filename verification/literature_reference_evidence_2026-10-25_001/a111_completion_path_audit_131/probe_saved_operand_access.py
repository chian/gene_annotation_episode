"""Synthetic engineering probe: saved A111 operands via ordinary source.read.

No paper, remote source or actual model inference is used. All state is created
under this audit directory. The child returns one selected derived component;
the parent then explicitly chooses to read the immutable saved sheet.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_structure_storage import structure_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_structure_storage import fixture
from test_runtime import FixtureController, ScriptedProvider


async def main():
    output = Path(__file__).resolve().parent
    store, context, args, _ = fixture(output / 'synthetic_probe_state_003')
    form = obj({'components': structure_cells_schema()})
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': list(context.received_record_refs),
        'requested_structure_components': ['source_geometry_positive']}
    root_commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': assignment, 'goal': 'Evaluate the declared synthetic atom-group geometry.',
        'scope': plain(context.scope), 'purpose': 'Return only the requested conditional component.',
        'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}
    literature_commission = deepcopy(root_commission)
    literature_commission['selection']['role'] = 'literature_strategy'
    literature_commission['selection']['assignment'] = {
        'version': 'strategy_assignment_v1', 'question_context_refs': [], 'prior_search_refs': [],
        'requested_structure_components': ['source_geometry_positive']}
    populate = {'selection': {'kind': 'tool', 'tool': 'literature.structure.populate', 'arguments': args},
        'report_update': {}}
    observed = {}

    def choose_saved_read(inputs):
        received, = inputs['child_reports']
        rows = received['components']
        assert len(rows) == 1 and rows[0]['component'] == 'source_geometry_positive'
        observed['returned_component_count'] = len(rows)
        observed['returned_geometry_definition'] = rows[0]['geometry_definition'] == args['geometry_panel']
        observed['returned_local_definition'] = rows[0]['local_validation_definition'] == args['local_panel']
        observed['sheet_ref'] = rows[0]['sheet_ref']
        return {'selection': {'kind': 'tool', 'tool': 'source.read', 'arguments': {
            'source_ref': rows[0]['sheet_ref'], 'representation': 'original', 'offset': 0, 'limit': 100000}},
            'report_update': {}}

    def inspect_read(inputs):
        result = inputs['last_local_outcome']['result']
        payload = json.loads(result['text'])
        observed['native_distance_A'] = payload['sheet']['native_geometry'][0]['distance_A']
        observed['all_pair_distances_A'] = payload['sheet']['native_geometry'][0]['all_pair_distances_A']
        observed['native_rscc'] = [row['rscc'] for row in payload['extraction']['native_local']]
        observed['literal_values'] = {name: row['value'] if row else None
            for name, row in payload['extraction']['literals'].items()}
        observed['exact_selected_atom_rows_retained'] = all(
            endpoint['selected_atom_rows'] for member in payload['extraction']['native_geometry']
            for name, endpoint in member.items() if name in ('endpoint_a', 'endpoint_b'))
        assert observed['native_distance_A'] == 3
        assert observed['native_rscc'] == [.8, .9]
        assert observed['literal_values']['molecule'] == 'Molecule'
        assert observed['literal_values']['construct'] == 'Construct'
        commit = {name: [] for name in store.reasoning_schema()['required']}
        source = store.get(args['source_ref'])
        quote = 'Synthetic structural experiment.'
        commit['source_subjects'] = [{'alias': 'synthetic_studied_subject',
            'reference_type': 'assay', 'source_ref': source['id'], 'label': quote,
            'anchor': {'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
                'start': 0, 'end': len(quote), 'quote': quote}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

    with store:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = await run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([root_commission, literature_commission, populate,
                choose_saved_read, inspect_read]),
            run_dir=output / 'synthetic_probe_run_003',
            controller_factory=lambda path, initial: FixtureController(str(path), initial,
                3 if len(path) == 2 else 1), project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()})
        observed.update(origin='synthetic_fixture', provider='ScriptedProvider',
            actual_model_inference=False, primary_paper_read=False,
            runtime_observation_count=store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0],
            structure_operation_count=store.db.execute('SELECT COUNT(*) FROM literature_structure_operations').fetchone()[0],
            structure_received_count=store.db.execute('SELECT COUNT(*) FROM literature_structure_received').fetchone()[0],
            final_credit=summary['credit'])
        assert observed['runtime_observation_count'] == 5
        assert observed['structure_operation_count'] == 1
        assert observed['structure_received_count'] == 2
        assert summary['credit'] == 0
    (output / 'SYNTHETIC_OPERAND_ACCESS.json').write_text(json.dumps(observed, indent=2) + '\n')
    print(json.dumps(observed, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
