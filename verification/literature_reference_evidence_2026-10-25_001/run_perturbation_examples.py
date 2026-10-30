"""Retain controlled A106 Workflow returns and independently replay their records.

The selected operands come from the already reviewed fixture definitions. This
script does not review another paper, run inference, open the live scientific
case, change scoring policy or add a controller observation for extraction.
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
NAMES = ('synthetic_matched_restoration', 'primary_cas2_qualitative')


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def run_case(directory, name):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_literature_perturbation_integration import setup_case, FORM, COMPONENTS
    from test_runtime import FixtureController, ScriptedProvider

    directory.mkdir(parents=True, exist_ok=False)
    primary = name == 'primary_cas2_qualitative'
    store, context, args = setup_case(directory / 'state', primary=primary)
    received = []
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the actual source intervention and endpoint',
            'scope': plain(context.scope), 'purpose': 'Return only requested source components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.perturbation.populate',
            'arguments': args}, 'report_update': {}}

        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert [row['component'] for row in rows] == COMPONENTS
            assert rows[2]['value'] == (None if primary else .4725)
            assert rows[3]['value'] is None
            assert rows[3]['unavailable_reason'] == 'joint_uncertainty_unreported'
            if primary:
                assert all(row['value'] is None for row in rows)
                assert all(row['design'] == 'cas_free_reconstitution' for row in rows)
                assert all(row['measurement_status'] == 'qualitative_only' for row in rows)
                assert all(row['endpoint_unit'] == row['exposure_unit'] == 'unreported' for row in rows)
                assert store.get(rows[0]['recipient_ref'])['label'] == 'BL21-AI'
            else:
                assert rows[0]['value'] == 2 / 3 and rows[1]['value'] == .875
            source = store.get(args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            label = 'Cas2' if primary else 'SyntheticProtein'
            start = raw.index(label.encode())
            commit = {field: [] for field in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'source_subject', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': label, 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
                    'start': start, 'end': start + len(label), 'quote': label}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, action, receive]), run_dir=directory / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial,
                2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        run_id, = store.db.execute('select run_id from runtime_runs').fetchone()
        operation, = store.db.execute('select * from literature_perturbation_operations where run_id=?',
            (run_id,)).fetchall()
        outcome = json.loads(operation['outcome'])
        repo = LiteraturePerturbationRepository(store, run_id)
        payload = repo.read(outcome['result']['sheet_ref'])
        counts = {name: store.db.execute('select count(*) from ' + table).fetchone()[0]
            for name, table in {'observations': 'runtime_observations',
                'population_operations': 'literature_perturbation_operations',
                'parent_receipts': 'literature_perturbation_received'}.items()}
        assert counts == {'observations': 3, 'population_operations': 1, 'parent_receipts': 1}
        assert summary['credit'] == 0 and len(received) == 1
        assert not store.list('observation') and not store.list('assessment')
        source_hashes = {ref: hashlib.sha256(store.get_artifact(store.get(ref)['artifact_ref'])).hexdigest()
            for ref in payload['direct_input_source_refs']}
        receipt = {'status': 'passed', 'case': name, 'run_id': run_id, 'model_backed': False,
            'execution': 'ordinary Workflow with scripted decisions and fixture controller',
            'target_problem': 'isolated short-sequence fixture, no target annotation assertion',
            'source_kind': args['source_kind'], 'outcome': outcome, 'saved_payload': payload,
            'actual_admitted_parent_subset': received[0]['measurements'],
            **counts, 'controller_credit': summary['credit'], 'direct_source_sha256': source_hashes,
            'limits': ['No actual configured-model perturbation interpretation',
                'Primary PCR has no numerical calibration or restoration triple',
                'Point source index is a proposed conditional convention, not annotation credit',
                'Joint uncertainty, necessity counterevidence and cross-experiment aggregation remain unfinished']}
        save(directory / 'RECEIPT.json', receipt)
        return {key: receipt[key] for key in ('case', 'run_id', 'model_backed', 'source_kind',
            'observations', 'population_operations', 'parent_receipts')}
    finally:
        store.close()


def reopen_case(directory):
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.state import Store
    from gene_annotation_episode import literature_perturbation_storage as module
    from gene_annotation_episode import literature_perturbation_inputs, literature_perturbation_calculations

    original = json.loads((directory / 'RECEIPT.json').read_text())

    def forbidden(*args, **kwargs):
        raise AssertionError('reading_recalculation_or_identity_regeneration_forbidden')

    module.read_perturbation_inputs = forbidden
    module.populate_source_restoration = forbidden
    literature_perturbation_inputs.read_perturbation_inputs = forbidden
    literature_perturbation_inputs._measurement_key = forbidden
    literature_perturbation_calculations.populate_source_restoration = forbidden
    with Store(directory / 'state') as store:
        run_id = original['run_id']
        repo = module.LiteraturePerturbationRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix='perturbation_reopen_')
        receipts = EpisodeReceipts(store, run_id)
        operation, = store.db.execute('select * from literature_perturbation_operations where run_id=?',
            (run_id,)).fetchall()
        outcome = json.loads(operation['outcome'])
        sheet_ref = outcome['result']['sheet_ref']
        source = store.get(sheet_ref)
        allowed = {source['artifact_ref'], source['request_ref']}
        get_artifact = store.get_artifact
        reads = []

        def saved_only(reference):
            assert reference in allowed, 'original_source_or_retained_measurement_bytes_must_not_be_read'
            reads.append(reference)
            return get_artifact(reference)

        store.get_artifact = saved_only
        store.db.execute('pragma query_only=ON')
        before = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
        context = returns.context(operation['episode_id'])
        context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
        request = json.loads(store.get_artifact(source['request_ref']))
        assert repo.populate(context, request['arguments'], operation['operation_key']) == outcome
        payload = repo.read(sheet_ref)
        assert canonical(payload) == canonical(original['saved_payload'])
        cells = repo.project_cells([sheet_ref], permitted_record_refs=context.received_record_refs,
            components=context.assignment['requested_perturbation_components'])
        attempt, = store.db.execute('select parent_episode_id,decision_index from runtime_report_attempts').fetchall()
        parent = returns.context(attempt['parent_episode_id'])
        child, form, schema = returns._attempt(parent, attempt['decision_index'])
        assert child.episode_id == context.episode_id
        assert canonical(form['measurements']) == canonical(cells)
        assert canonical(repo.received_cells(parent)) == canonical(cells)
        assert canonical(original['actual_admitted_parent_subset']) == canonical(cells)
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == before == 3
    return {'case': original['case'], 'status': 'passed', 'actual_parent_subset_equals_saved_cells': True,
        'cells': len(cells), 'observations_before_and_after': before, 'original_input_bytes_read': False,
        'parser_calculators_disabled': True, 'measurement_identity_generator_disabled': True,
        'replay_SQL_query_only': True, 'saved_artifact_reads': reads}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--reopen', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    owned = BASE / 'perturbation_examples_001'
    if directory != owned:
        raise ValueError('owned_perturbation_example_directory_required')
    if args.reopen:
        result = {'status': 'passed', 'scope': 'fresh process closed controlled Workflow replay, not live host restart',
            'cases': [reopen_case(directory / name) for name in NAMES]}
        save(directory / 'REOPEN_RECEIPT.json', result)
    else:
        directory.mkdir(parents=True, exist_ok=False)
        result = {'status': 'passed', 'cases': [run_case(directory / name, name) for name in NAMES]}
        save(directory / 'EXAMPLES_RECEIPT.json', result)
    print(json.dumps(result))
