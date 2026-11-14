"""Connected custody recovery and fresh read-only projection, using scripted work."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episodic_workflow.root.a105.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.a105.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import LiteratureControlledResponseRepository
from gene_annotation_episode.episodic_workflow.root.a105.runtime import TypedReportContract
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionStore
from literature_controlled_response_worker_fixture_095 import make_case, run_case
READONLY = "import json, sqlite3, sys\nfrom pathlib import Path\nfrom types import SimpleNamespace\nfrom PIL import Image\nfrom gene_annotation_episode.episodic_workflow.root.a105.state import Store\nfrom gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import LiteratureControlledResponseRepository\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_v3_inputs as inputs\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_inputs as shared\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_v3_population as population\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_local_calculations as local\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_figure_inputs as graph\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_owner_calculations as owner\nfrom gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_calculations as arithmetic\nfrom gene_annotation_episode import providers\nfixture = json.loads(Path(sys.argv[2]).read_text())\n\ndef forbidden(*a, **kw):\n    raise AssertionError('forbidden source/reader/image/counter/model/population/receive/mutation')\nstore = Store.__new__(Store)\nstore.path = Path(sys.argv[1])\nstore._savepoint = 0\nstore.db = sqlite3.connect(store.path.joinpath('state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)\nstore.db.row_factory = sqlite3.Row\nstore.db.execute('PRAGMA query_only=ON')\nstore.db.create_function('library_scope_record', 2, store._scope_filter_record)\nget = store.get_artifact\nreads = []\n\ndef saved_only(ref):\n    if ref in fixture['banned']:\n        raise AssertionError('original source/image bytes accessed')\n    reads.append(ref)\n    return get(ref)\nstore.get_artifact = saved_only\nfor name in ('artifact', 'put', 'transaction', 'register_material', 'parse_material'):\n    setattr(store, name, forbidden)\ninputs.read_controlled_response_v3_inputs = forbidden\nshared.open_controlled_response_sources = forbidden\nshared._number = forbidden\nshared._unit = forbidden\npopulation.populate_controlled_response_v3 = forbidden\nlocal.populate_controlled_response_local = forbidden\nowner.populate_controlled_response_owner = forbidden\narithmetic.populate_controlled_response = forbidden\ngraph.read_controlled_response_rate_figure = forbidden\ngraph._count_bar_runs = forbidden\ngraph._strict_decode = forbidden\nImage.open = forbidden\nproviders.ModelConnection = forbidden\nrepo = LiteratureControlledResponseRepository(store, fixture['run'], evidence_origin='synthetic_fixture')\nrepo.receive_cells = forbidden\ncontext = SimpleNamespace(run_id=fixture['run'], episode_id=fixture['parent'], role='annotation', assignment={}, path=fixture['path'], scope=fixture['scope'], received_record_refs=fixture['known'])\nassert store.db.total_changes == 0\nactual = repo.fact_cells(context, [fixture['sheet']], components=fixture['keys'])\nassert actual == fixture['admitted']\nassert repo.fact_cells(context, [fixture['sheet']], components=['raw:protein_condition1:primary']) == []\nassert repo.received_cells(context) == actual\nrepo.validate_returned_values(actual, permitted_record_refs=context.received_record_refs)\nbindings = repo.semantic_bindings(actual)\nassert bindings == fixture['bindings']\nassert [list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == fixture['observations']\nassert store.db.total_changes == 0\nprint(json.dumps({'mode': 'ro', 'total_changes': store.db.total_changes, 'first_projection': actual, 'saved_artifact_reads': len(reads), 'observation_count': len(fixture['observations']), 'evidence_class': 'connected scripted095 engineering fixture; no live model'}))\nstore.close()\n"

@pytest.mark.parametrize('interrupt_receive', [False, True])
def test_real_independent_c1_c4_recovery_replay_and_first_readonly(tmp_path, monkeypatch, interrupt_receive):
    store, case = make_case(tmp_path / 'state', unresolved=True)
    directory = tmp_path / 'run'
    original_service = WorkflowServices.literature_controlled_response_repository
    injected = []
    if interrupt_receive:

        def service(self, **kwargs):
            repository = original_service(self, **kwargs)
            if not hasattr(repository, '_fixture_interrupt_installed'):
                repository._fixture_interrupt_installed = True
                original = repository.receive_cells

                def receive(context, rows, key):
                    original(context, rows, key)
                    if context.role == 'annotation' and (not injected):
                        injected.append(key)
                        raise OSError('constructed interruption after actual controlled receive')
                repository.receive_cells = receive
            return repository
        monkeypatch.setattr(WorkflowServices, 'literature_controlled_response_repository', service)
    try:
        if interrupt_receive:
            with pytest.raises(OSError, match='after actual controlled receive'):
                asyncio.run(run_case(store, case, directory, durable=True))
            assert injected
            assert store.db.execute('SELECT count(*) FROM literature_controlled_response_component_received').fetchone()[0] == 0
            assert store.db.execute('SELECT count(*) FROM literature_controlled_response_operations').fetchone()[0] == 1
        _, provider, _ = asyncio.run(run_case(store, case, directory, durable=True, resume=interrupt_receive))
        spec = json.loads(store.db.execute('SELECT spec FROM runtime_commission_intents').fetchone()[0])
        backend = DurableExecutionStore(directory / 'episode-execution')
        returned = backend.load_return(spec['handle'], backend.status(spec['handle'])['return_id'])
        assert returned['outcome'] == 'closed' and returned['failure'] is None and (returned['completion']['units_consumed'] == 2)
        parent, child, run = (spec['parent']['episode_id'], spec['child']['episode_id'], spec['run_id'])
        form, = provider.contexts[-1]['child_reports']
        rows = form['requested_response']
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts')
        assert attempt['failure'] is None and attempt['parent_episode_id'] == parent and (attempt['child_episode_id'] == child)
        assert json.loads(attempt['form']) == returned['form'] == form
        assert json.loads(attempt['contract']) == spec['child']['request']['report_contract']
        assert store.db.execute('SELECT count(*) FROM runtime_commission_intents').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_return_admissions').fetchone()[0] == 1

        def forbidden(*a, **kw):
            raise AssertionError('admission replay called a callback')
        contract = spec['child']['request']['report_contract']
        typed = TypedReportContract(contract['decision'], contract['measurements']['schema'], forbidden)
        receiver = ReceiverBindingV1(store, Journal(store, run), 0, typed, forbidden, forbidden, forbidden, forbidden)
        admission = json.loads(store.db.execute('SELECT admission FROM runtime_return_admissions').fetchone()[0])
        before = store.db.total_changes
        assert admit_return(spec, returned, receiver) == admission and store.db.total_changes == before
        repository = LiteratureControlledResponseRepository(store, run, evidence_origin='synthetic_fixture')
        saved = repository.read(rows[0]['sheet_ref'])
        fixture = {'run': run, 'parent': parent, 'path': spec['parent']['path'], 'scope': case['scope'], 'known': list(EpisodeReceipts(store, run).known(parent)), 'sheet': rows[0]['sheet_ref'], 'keys': [row['component_key'] for row in rows], 'admitted': rows, 'bindings': repository.semantic_bindings(rows), 'banned': [store.get(ref)['artifact_ref'] for ref in saved['input_source_refs']], 'observations': [list(r) for r in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]}
        path = tmp_path / 'readonly.json'
        path.write_text(json.dumps(fixture))
        store.close()
        process = subprocess.run([sys.executable, '-c', READONLY, str(tmp_path / 'state'), str(path)], text=True, capture_output=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(Path(__file__).resolve().parents[5])})
        assert process.returncode == 0, process.stdout + process.stderr
        proof = json.loads(process.stdout)
        assert proof['total_changes'] == 0 and proof['first_projection'] == rows
    finally:
        store.close()

def test_ordinary_reforward_preserves_exact_alternative_and_cannot_expand_private_raw(tmp_path):
    from functools import partial
    from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
    from gene_annotation_episode.episodic_workflow.root.a105.domain import obj
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_controlled_response_storage import controlled_response_cells_schema
    from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
    from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
    from literature_controlled_response_worker_fixture_095 import Provider, scorer
    from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import ScriptedProvider, FixtureController
    store, case = make_case(tmp_path / 'state', unresolved=True)
    form_schema = obj({'numbers': controlled_response_cells_schema()})
    outer = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': case['source_refs'], 'requested_controlled_response_components': ['protein_condition1_response', 'controlled_response_difference', 'local_difference'], 'requested_controlled_response_views': ['native_raw', 'conditional', 'local_difference']}
    inner = {'version': 'strategy_assignment_v1', 'question_context_refs': [], 'prior_search_refs': case['source_refs'], 'requested_controlled_response_components': ['controlled_response_difference'], 'requested_controlled_response_views': ['conditional'], 'requested_controlled_response_component_keys': ['joint:1:controlled_response_difference']}

    def commission(role, assignment):
        return {'selection': {'kind': 'episode_child', 'role': role, 'assignment': assignment, 'goal': 'Evaluate the supplied controlled comparison alternatives', 'scope': plain(case['scope']), 'purpose': 'Return the requested controlled response alternative only', 'schema_json': json.dumps(form_schema), 'initial_report_json': '{}'}, 'report_update': {}}
    received = []

    def use(state):
        actual, = state['child_reports']
        received.append(deepcopy(actual))
        assert [row['component_key'] for row in actual['numbers']] == ['joint:1:controlled_response_difference']
        decision = Provider(store, case).reason()['response']
        return {name: decision[name] for name in ('selection', 'report_update')}
    provider = ScriptedProvider([commission('literature', outer), commission('literature_strategy', inner), {'selection': {'kind': 'tool', 'tool': 'literature.controlled_response.source_v3.populate', 'arguments': case['arguments']}, 'report_update': {}}, use, use])
    try:
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / 'run', controller_factory=lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 3 else 2), project_credit=scorer(), initial_known_record_refs=case['source_refs'], episode_record_receipts=True, episode_binding_factories=(partial(LiteratureEpisode, rate_population=True, controlled_response_population=True, controlled_response_evidence_origin='synthetic_fixture', reference_parent_sources=case['source_refs']),), binding_definitions={'credit': scorer().as_record()}))
        assert result['credit'] == 0 and received[0] == received[1]
        assert store.db.execute('SELECT count(*) FROM literature_controlled_response_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_controlled_response_component_received').fetchone()[0] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
        run = json.loads((tmp_path / 'run/run.json').read_text())['run_id']
        root = store.db.execute('SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()[0]
        from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_controlled_response_episode_integration import actual_context
        context = actual_context(store, case, run, root)
        repository = LiteratureControlledResponseRepository(store, run, evidence_origin='synthetic_fixture')
        assert repository.fact_cells(context, [received[0]['numbers'][0]['sheet_ref']], components=['raw:protein_condition1:primary']) == []
    finally:
        store.close()

def test_actual_runtime_digest_and_complete_alternate_wrapper_cannot_replace_selected_output(tmp_path):
    from dataclasses import replace
    from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical
    from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_controlled_response_episode_integration import actual_context
    store, case = make_case(tmp_path / 'state')
    try:
        asyncio.run(run_case(store, case, tmp_path / 'run'))
        run = json.loads((tmp_path / 'run/run.json').read_text())['run_id']
        action = store.db.execute("SELECT * FROM runtime_actions WHERE json_extract(action,'$.tool')='literature.controlled_response.source_v3.populate'").fetchone()
        context = actual_context(store, case, run, action['episode_id'])
        repository = LiteratureControlledResponseRepository(store, run, evidence_origin='synthetic_fixture')
        operation = store.db.execute('SELECT * FROM literature_controlled_response_operations').fetchone()
        outcome = json.loads(operation['outcome'])
        original_runtime = json.loads(action['result'])
        assert 'pending_work_after_action' in original_runtime
        assert store.db.execute('SELECT count(*) FROM ' + repository.runtime_binding_table).fetchone()[0] == 1
        observations = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations')]
        changed = deepcopy(original_runtime)
        changed['pending_work_after_action'] = {'controlled_fixture_tampering': True}
        try:
            store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?', (canonical(changed), run, context.episode_id, action['decision_index']))
            with pytest.raises(ContractError, match='original_runtime_digest_mismatch'):
                repository.read(outcome['result']['sheet_ref'])
        finally:
            store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?', (action['result'], run, context.episode_id, action['decision_index']))
        arguments = deepcopy(case['arguments'])
        arguments['model_kind'] = {'value': 'none', 'witnesses': []}
        try:
            store.db.execute('DELETE FROM literature_controlled_response_operations WHERE run_id=? AND episode_id=? AND operation_key=?', (run, context.episode_id, operation['operation_key']))
            alternate = repository.populate_v3(context, arguments, operation['operation_key'])
            assert alternate['result']['payload_sha256'] != outcome['result']['payload_sha256']
            with pytest.raises(ContractError, match='original_runtime_mismatch'):
                repository.read(alternate['result']['sheet_ref'])
            with pytest.raises(ContractError, match='original_runtime_mismatch'):
                repository.fact_cells(replace(context, received_record_refs=(*context.received_record_refs, *alternate['record_refs'])), [alternate['result']['sheet_ref']], components=['final:controlled_response_difference'])
        finally:
            store.db.execute('DELETE FROM literature_controlled_response_operations WHERE run_id=? AND episode_id=? AND operation_key=?', (run, context.episode_id, operation['operation_key']))
            store.db.execute('INSERT INTO literature_controlled_response_operations VALUES(?,?,?,?,?)', tuple(operation))
        assert repository.read(outcome['result']['sheet_ref'])
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations')] == observations
        assert store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (run, context.episode_id, action['decision_index'])).fetchone()[0] == action['result']
    finally:
        store.close()
