"""Retain an ordinary controlled primary-HTML return and reopen it separately.

Uses the same explicit fixture provider/controller as integration checks. It
does not acquire sources, perform live model inference or open the target case.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def run_example(directory):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository
    from gene_annotation_episode.literature_transport_calculations import populate_transport_response
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_literature_transport_quantity_integration import setup_html, FORM, COMPONENTS, PRIMARY
    from test_runtime import FixtureController, ScriptedProvider
    directory.mkdir(parents=True, exist_ok=False)
    store, context, args = setup_html(directory / 'state')
    seen = []
    try:
        child = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Read the reported whole-cell pyruvate Km for BtsT',
            'scope': plain(context.scope), 'purpose': 'Preserve the actual fitted quantity and unspecified spread',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        selected = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate',
                                 'arguments': args}, 'report_update': {}}
        def parent_receives(inputs):
            form, = inputs['child_reports']
            seen.append(form)
            assert [r['component'] for r in form['measurements']] == COMPONENTS
            assert [r['value'] for r in form['measurements']] == [16.5, 6.4, 6.4/16.5, None]
            commit = {name: [] for name in store.reasoning_schema()['required']}
            source = store.get(args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            start = raw.index(b'BtsT')
            commit['source_subjects'] = [{'alias': 'source_name', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': 'BtsT', 'anchor': {'source_ref': source['id'],
                    'artifact_ref': source['artifact_ref'], 'start': start, 'end': start+4, 'quote': 'BtsT'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([child, selected, parent_receives]), run_dir=directory / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=[args['source_ref']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(seen) == 1
        run_id, = store.db.execute('select run_id from runtime_runs').fetchone()
        operations = store.db.execute('select * from literature_quantity_operations where run_id=?', (run_id,)).fetchall()
        assert len(operations) == 1
        outcome = json.loads(operations[0]['outcome'])
        payload = LiteratureQuantityRepository(store, run_id).read(outcome['result']['sheet_ref'])
        assert store.get_artifact(payload['input_artifact_ref']) == PRIMARY.read_bytes()
        observations = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
        assert observations == 3
        quantity = payload['sheet']['extraction']
        response_inputs = {'values': {'substrate_test': 10., 'substrate_reference': 40., 'km': quantity['value']},
            'curve_keys': {'substrate_test': 'whole_cell_curve', 'substrate_reference': 'proteoliposome_curve',
                           'km': 'whole_cell_curve'},
            'measurement_keys': {'substrate_test': 'whole_cell_substrate', 'substrate_reference': 'vesicle_substrate',
                                 'km': 'whole_cell_reported_km'},
            'covariance': None, 'variance_status': 'unknown', 'observation_model': 'michaelis_menten', 'origin': 'derived'}
        actual_context = populate_transport_response(response_inputs)
        assert actual_context['cells']['condition_response']['value'] is None
        assert actual_context['cells']['condition_response']['unavailable_reason'] == 'different_kinetic_curves'
        hypothetical = {**response_inputs, 'curve_keys': dict.fromkeys(response_inputs['curve_keys'], 'illustrative_common_curve'),
                        'origin': 'synthetic'}
        scenario = populate_transport_response(hypothetical)
        save(directory / 'RECEIPT.json', {'run_id': run_id, 'status': 'passed', 'actual_source_sha256':
            hashlib.sha256(PRIMARY.read_bytes()).hexdigest(), 'selected_arguments': args, 'actual_outcome': outcome,
            'saved_payload': payload, 'actual_admitted_parent_subset': seen[0]['measurements'],
            'observations': observations, 'controller_credit': summary['credit'],
            'model_backed': False, 'target_problem': 'synthetic short-sequence fixture in isolated Store',
            'execution': 'ordinary Workflow with scripted decisions and fixture controller',
            'transport_response_examples': {'actual_different_system_context': actual_context,
                'explicitly_hypothetical_same_curve': scenario},
            'response_calculator_execution': 'direct deterministic function, not selected episode integration',
            'limits': ['No raw transport trace/populated WT restoration calculation',
                       'No known covariance inferred from printed ±',
                       'No actual-model binding/transport execution or live host restart']})
        print(json.dumps({'status': 'passed', 'run_id': run_id, 'actual_cells': len(seen[0]['measurements']),
            'observations': observations, 'hypothetical_response': scenario['cells']['condition_response']['value'],
            'actual_cross_system_response': actual_context['cells']['condition_response']['value']}))
    finally:
        store.close()


def reopen_example(directory):
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository
    from gene_annotation_episode import literature_prose_reader, literature_html_quantity_reader, literature_activity_calculations
    original = json.loads((directory / 'RECEIPT.json').read_text())
    def forbidden(*args, **kwargs):
        raise AssertionError('original_reading_or_calculation_forbidden')
    literature_prose_reader.read_jats_quantity = forbidden
    literature_html_quantity_reader.read_html_quantity = forbidden
    literature_activity_calculations.populate_corrected_activity = forbidden
    with Store(directory / 'state') as store:
        run_id = original['run_id']
        repo = LiteratureQuantityRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix='transport_reopen_')
        receipts = EpisodeReceipts(store, run_id)
        row, = store.db.execute('select * from literature_quantity_operations where run_id=?', (run_id,)).fetchall()
        outcome = json.loads(row['outcome'])
        sheet_ref = outcome['result']['sheet_ref']
        sheet_source = store.get(sheet_ref)
        allowed = {sheet_source['artifact_ref'], sheet_source['request_ref']}
        get_artifact = store.get_artifact
        reads = []
        def saved_only(reference):
            assert reference in allowed, 'original_HTML_bytes_must_not_be_read'
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
            components=context.assignment['requested_quantity_components'])
        attempt, = store.db.execute('select parent_episode_id,decision_index from runtime_report_attempts').fetchall()
        parent = returns.context(attempt['parent_episode_id'])
        child, form, schema = returns._attempt(parent, attempt['decision_index'])
        assert child.episode_id == context.episode_id
        assert canonical(form['measurements']) == canonical(cells)
        assert canonical(repo.received_cells(parent)) == canonical(cells)
        assert canonical(original['actual_admitted_parent_subset']) == canonical(cells)
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == before == 3
    receipt = {'status': 'passed', 'run_id': run_id, 'cells': len(cells),
        'actual_parent_subset_equal': True, 'original_source_bytes_read': False,
        'parser_calculator_disabled': True, 'replay_SQL_query_only': True,
        'observations_before_and_after': before, 'saved_artifact_reads': reads,
        'scope': 'Fresh process replay of controlled primary-source example; not actual inference or host restart.'}
    save(directory / 'REOPEN_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--reopen', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory == BASE or not directory.is_relative_to(BASE):
        raise ValueError('new_owned_example_directory_required')
    (reopen_example if args.reopen else run_example)(directory)
