"""Replay the completed218 Workflow using its actual inward root contract.

The root has no outward report contract. This receiver therefore selects the
exact saved child-admission schema, without adding an outward root assignment.
No acquisition, choices, grading, or episode execution occurs in this check.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from samstat_common import (save, host, action_rows, check_values, check_sheet,
    disable_reexecution, HERE)

def test_completed_workflow_saved_root_receiving_contract(tmp_path, monkeypatch):
    path = Path(os.environ['SAMSTAT_WORKFLOW_REPLAY_INPUT']).resolve()
    replay = json.loads(path.read_text())
    attempts, disabled = disable_reexecution(monkeypatch)
    case = 'workflow_replay'
    save(case, 'original_checkpoint', dict(path=str(path), sha256=digest(replay)))
    with Store(replay['state_path']) as store:
        family = ExecutionEpisodes(None, store=store, directory=Path(replay['directory']), run_id=replay['run_id'],
            resources={'selected-api': replay['config']}, initial_information={},
            tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        api = family.api_execution
        contexts = {name: api.appservice.custody.context(ident) for name, ident in replay['episode_ids'].items()}
        schema, forwarded, body = replay['parent_schema'], replay['forwarded'], replay['body']
        root = contexts['grandparent']
        assert root.request.get('report_contract') is None
        attempt = store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
            'AND child_episode_id=?', (replay['run_id'], root.episode_id, contexts['parent'].episode_id)).fetchone()
        assert attempt['failure'] is None and json.loads(attempt['form']) == forwarded
        assert json.loads(attempt['contract'])['measurements']['schema'] == schema
        assert api.read_result(body['source_ref'], root.scope) == body
        # Explicit inward schema is the original, saved child-return contract.
        facts = api.fastqutils_returns.received_facts(root, schema)
        root_typed = {name: facts[node['x-source']] for name, node in schema['properties'].items()}
        assert root_typed == forwarded
        check_values(host.native_values(root_typed), 'current')
        family.validate_received_report(root, root_typed, schema)
        assert api.fastqutils_returns.received_facts(root, schema) == facts
        assert action_rows(store) == replay['actions']
        observed = [dict(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
        assert len(observed) == sum(row['observations'] for row in replay['counts']) == 14
        for row in replay['counts']:
            assert row['actions'] == row['observations']
        saved = body['publication']['adapter_result']
        sheet = api.appservice.publications.read_content_source(saved['sheet_content']['source_ref'], root.scope)
        components = api.appservice.publications.read_content_source(saved['components_content']['source_ref'], root.scope)
        check_sheet(sheet, components, 'current', (HERE / 'native_inputs/current/mixed.sam.samstat.html').read_bytes())
        proof = api._completion(contexts['owner'])
        assert proof and api.verify_completion(contexts['owner'], proof)
        forged = deepcopy(root_typed)
        forged['facts_0'][0]['value']['records'][0]['payload']['value'] = 900
        rejections = []
        for label, context in contexts.items():
            with pytest.raises(ValueError) as error:
                family.validate_received_report(context, forged, schema)
            rejections.append(dict(boundary=label, code=str(error.value)))
        assert not attempts and action_rows(store) == replay['actions']
        assert [dict(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == observed
        assert api.fastqutils_returns.received_facts(root, schema) == facts
        save(case, 'saved_reconstruction_and_rejections', dict(disabled_entrypoints=disabled,
            forbidden_attempts=attempts, original_child_admission=dict(attempt), returned_facts=root_typed,
            original_actions_sha256=digest(replay['actions']), final_actions_sha256=digest(action_rows(store)),
            observations_sha256=digest(observed), proof=proof, forged_value=900, rejections=rejections))
        summary = dict(passed=True, reconstruction_only=True, original_workflow_actions=14,
            original_workflow_observations=14, new_actions=0, new_observations=0, new_acquisition=0,
            root_inward_contract_verified=True, forged_value_rejections=len(rejections),
            numerical_fractions=[[9,10],[4,10]], forbidden_attempts=0)
        save(case, 'summary', summary)
        print(json.dumps(summary, sort_keys=True), flush=True)
