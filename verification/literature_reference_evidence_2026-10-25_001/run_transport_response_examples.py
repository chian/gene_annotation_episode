"""Retain selected transport response examples and verify closed saved replay.

All decisions/controllers are fixtures; the primary case uses unchanged BtsT
HTML. The script never opens cases/gene_001 or the live configured-model run.
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def primary_setup(path):
    from test_literature_transport_quantity_integration import setup_html
    from test_literature_transport_integration import witness, concentration, COMPONENTS
    from gene_annotation_episode.communication import plain
    store, context, quantity = setup_html(path)
    ref = quantity['source_ref']
    raw = store.get_artifact(store.get(ref)['artifact_ref'])
    # Exact source operands were identified by the prior complete parent review.
    # This fixture nominates those spans; it does not supply measurement values.
    def w(text):
        return witness(ref, raw, text)
    whole = {'molecule': w('BtsT'), 'analyte': w('pyruvate'), 'preparation': w('intact cells'),
        'experimental_system': w('Transport measurements with intact cells.'),
        'endpoint': w('pyruvate uptake'), 'curve': w('Transport measurements with intact cells.')}
    vesicle = {**whole, 'preparation': w('proteoliposomes'),
        'experimental_system': w('Transport measurements with proteoliposomes.'),
        'curve': w('Transport measurements with proteoliposomes.')}
    args = {'source_ref': ref, 'source_kind': 'primary_source',
        'primitives': {'substrate_test': concentration(ref, raw, '10 μM'),
                       'substrate_reference': concentration(ref, raw, '40 μM')},
        'km_sheet_ref': None, 'curve_contexts': {'substrate_test': whole, 'substrate_reference': vesicle, 'km': whole},
        'covariance_source_ref': None, 'variance_status': 'unknown', 'observation_model': 'unknown', 'model_witnesses': []}
    assignment = {**plain(context.assignment), 'requested_quantity_components': [], 'requested_transport_components': COMPONENTS}
    return store, replace(context, assignment=assignment), quantity, args


def run_case(directory, name):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_transport_storage import LiteratureTransportRepository
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_literature_transport_integration import setup_synthetic, FORM, COMPONENTS
    from test_runtime import FixtureController, ScriptedProvider
    setup = primary_setup if name == 'primary_different_systems' else partial(setup_synthetic, different=name == 'synthetic_different_curves')
    directory.mkdir(parents=True, exist_ok=False)
    store, context, quantity_args, args = setup(directory / 'state')
    received = []
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the source substrate response and kinetic-curve relationship',
            'scope': plain(context.scope), 'purpose': 'Return requested native quantities, response components and limitations',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        quantity = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate', 'arguments': quantity_args}, 'report_update': {}}
        def transport(inputs):
            first = inputs['last_local_outcome']
            assert first['status'] == 'completed', first
            return {'selection': {'kind': 'tool', 'tool': 'literature.transport.response.populate',
                'arguments': {**args, 'km_sheet_ref': first['result']['sheet_ref']}}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert [row['component'] for row in rows] == COMPONENTS
            assert rows[0]['value'] == (16.5 if name.startswith('primary') else 12.)
            if name == 'synthetic_same_curve':
                assert rows[1]['value'] == .55
            else:
                assert rows[1]['value'] is None and rows[1]['unavailable_reason'] == 'different_kinetic_curves'
            assert rows[3]['value'] is None
            commit = {field: [] for field in store.reasoning_schema()['required']}
            source = store.get(args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            label = 'BtsT' if name.startswith('primary') else 'FixtureTransporter'
            start = raw.index(label.encode())
            commit['source_subjects'] = [{'alias': 'reported_source', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': label, 'anchor': {'source_ref': source['id'],
                    'artifact_ref': source['artifact_ref'], 'start': start, 'end': start+len(label), 'quote': label}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, quantity, transport, receive]), run_dir=directory / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        run_id, = store.db.execute('select run_id from runtime_runs').fetchone()
        operation, = store.db.execute('select * from literature_transport_operations where run_id=?', (run_id,)).fetchall()
        outcome = json.loads(operation['outcome'])
        payload = LiteratureTransportRepository(store, run_id).read(outcome['result']['sheet_ref'])
        assert result['credit'] == 0 and len(received) == 1
        count = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
        assert count == 4
        receipt = {'status': 'passed', 'case': name, 'run_id': run_id, 'model_backed': False,
            'execution': 'ordinary Workflow with scripted decisions and fixture controller',
            'target_problem': 'isolated short-sequence fixture, no target annotation assertion',
            'outcome': outcome, 'saved_payload': payload, 'actual_admitted_parent_subset': received[0]['measurements'],
            'observations': count, 'controller_credit': result['credit'],
            'actual_source_sha256': hashlib.sha256(store.get_artifact(store.get(args['source_ref'])['artifact_ref'])).hexdigest(),
            'source_kind': args['source_kind'],
            'limits': ['No covariance inferred from native Km spread', 'No actual configured-model transport inference',
                       'No cross-system correction, molecular attribution or annotation credit']}
        save(directory / 'RECEIPT.json', receipt)
        return {key: receipt[key] for key in ('case', 'run_id', 'model_backed', 'observations', 'source_kind')}
    finally:
        store.close()


def reopen_case(directory):
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.state import Store
    from gene_annotation_episode import literature_transport_storage as module
    from gene_annotation_episode import literature_transport_inputs, literature_transport_calculations
    from gene_annotation_episode import literature_prose_reader, literature_html_quantity_reader, literature_activity_calculations
    original = json.loads((directory / 'RECEIPT.json').read_text())
    def forbidden(*args, **kwargs):
        raise AssertionError('reading_or_recalculation_forbidden')
    module.read_transport_inputs = forbidden
    module.populate_transport_response = forbidden
    module._quantity_key = forbidden
    literature_transport_inputs.read_transport_inputs = forbidden
    literature_transport_calculations.populate_transport_response = forbidden
    literature_prose_reader.read_jats_quantity = forbidden
    literature_html_quantity_reader.read_html_quantity = forbidden
    literature_activity_calculations.populate_corrected_activity = forbidden
    with Store(directory / 'state') as store:
        run_id = original['run_id']
        repo = module.LiteratureTransportRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix='transport_response_reopen_')
        receipts = EpisodeReceipts(store, run_id)
        operation, = store.db.execute('select * from literature_transport_operations where run_id=?', (run_id,)).fetchall()
        outcome = json.loads(operation['outcome'])
        sheet_ref = outcome['result']['sheet_ref']
        source = store.get(sheet_ref)
        payload = json.loads(store.get_artifact(source['artifact_ref']))
        km_source = store.get(payload['km_sheet_ref'])
        allowed = {source['artifact_ref'], source['request_ref'], km_source['artifact_ref'], km_source['request_ref']}
        get_artifact = store.get_artifact
        reads = []
        def saved_only(reference):
            assert reference in allowed, 'original_source_or_covariance_bytes_must_not_be_read'
            reads.append(reference)
            return get_artifact(reference)
        store.get_artifact = saved_only
        store.db.execute('pragma query_only=ON')
        before = store.db.execute('select count(*) from runtime_observations').fetchone()[0]
        context = returns.context(operation['episode_id'])
        context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
        request = json.loads(store.get_artifact(source['request_ref']))
        assert repo.populate(context, request['arguments'], operation['operation_key']) == outcome
        cells = repo.project_cells([sheet_ref], permitted_record_refs=context.received_record_refs,
            components=context.assignment['requested_transport_components'])
        attempt, = store.db.execute('select parent_episode_id,decision_index from runtime_report_attempts').fetchall()
        parent = returns.context(attempt['parent_episode_id'])
        child, form, schema = returns._attempt(parent, attempt['decision_index'])
        assert child.episode_id == context.episode_id
        assert canonical(form['measurements']) == canonical(cells)
        assert canonical(repo.received_cells(parent)) == canonical(cells)
        assert canonical(original['actual_admitted_parent_subset']) == canonical(cells)
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == before == 4
    return {'case': original['case'], 'status': 'passed', 'actual_parent_subset_equals_saved_cells': True,
        'cells': len(cells), 'observations_before_and_after': before, 'original_input_bytes_read': False,
        'parser_calculators_disabled': True, 'replay_SQL_query_only': True, 'saved_artifact_reads': reads}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--reopen', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory == BASE or not directory.is_relative_to(BASE):
        raise ValueError('owned_new_example_directory_required')
    names = ['synthetic_same_curve', 'synthetic_different_curves', 'primary_different_systems']
    if args.reopen:
        result = {'status': 'passed', 'scope': 'fresh process closed controlled Workflow replay, not live host restart',
            'cases': [reopen_case(directory / name) for name in names]}
        save(directory / 'REOPEN_RECEIPT.json', result)
    else:
        directory.mkdir(parents=True, exist_ok=False)
        result = {'status': 'passed', 'cases': [run_case(directory / name, name) for name in names]}
        save(directory / 'EXAMPLES_RECEIPT.json', result)
    print(json.dumps(result))
