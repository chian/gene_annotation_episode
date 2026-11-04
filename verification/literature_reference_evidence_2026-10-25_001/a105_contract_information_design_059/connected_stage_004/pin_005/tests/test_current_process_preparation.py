"""Current-version revision preparation against the actual W04 publication.

These tests cover original-action provenance and new-child reconstruction only.
They deliberately use an ordinary parent-defined form: current-version
scientific_process_results forwarding remains a separate W07 schema issue.
"""
import asyncio
from copy import deepcopy
import json
import shutil

import pytest

from gene_annotation_episode.scientific_process_records import (
    scientific_digest, scientific_invocation_ref, selector_selection)
from gene_annotation_episode.state import Store
from test_published_axis_workflow import (
    FORM, PROTEIN, PublishedCase, ScriptedDecisions, StopBeforeDecision,
    select, table_count, tool)


@pytest.fixture
def prepared(tmp_path):
    with Store(tmp_path / 'state') as store:
        case = PublishedCase(tmp_path, store)
        commission = case.commission('A104', 'P01')
        arguments = {'thought_pattern': case.library.reference('P02'),
            'child_tool_info': [{'name': 'sequence.inspect', 'resources': 'local'}]}
        provider = ScriptedDecisions([select(commission), tool('process.revise', arguments),
            StopBeforeDecision()])
        workflow = case.workflow(provider)
        root = workflow.build('annotation', 'root', 'Investigate the supplied protein', case.scope)
        with pytest.raises(StopBeforeDecision):
            asyncio.run(root.run_async(workflow.context))
        # Reopen the same immutable child selection without running it again.
        owner = workflow.selected(root.source, commission, 0).child
        row = store.db.execute('SELECT action,result FROM runtime_actions '
            'WHERE episode_id=? AND decision_index=0', (owner.source.episode_id,)).fetchone()
        action, outcome = json.loads(row['action']), json.loads(row['result'])
        assert action == {'kind': 'tool', 'tool': 'process.revise', 'arguments': arguments}
        assert outcome['status'] == 'completed'
        assert table_count(store, 'runtime_observations') == 1
        assert case.controllers[owner.source.path].state().history == (0,)
        assert table_count(store, 'tool_operations') == 0
        yield case, workflow, root, owner, commission, action, outcome


def test_current_preparation_reconstructs_new_child_from_original_frozen_tool_information(prepared):
    case, workflow, root, owner, commission, action, outcome = prepared
    store = case.store
    original_owner_request = deepcopy(owner.request.as_record())
    owner_context = workflow.binding_context(owner.source)
    reference = outcome['operation_ref']
    selection = original_owner_request['message']['episode_assignment']['selection']
    preparation = workflow.services.scientific_preparation(owner_context, reference)
    assert preparation['arguments'] == action['arguments']
    assert preparation['owner_selection'] == selection
    assert preparation['proposal'] == outcome['result']
    assert outcome['result']['parent_selection_sha256'] == scientific_digest(selection)
    proposed = outcome['result']['selection']
    assert proposed['version'] == selection['version'] == 'scientific_process_selection_v3'
    assert proposed['evidence_axis'] == selection['evidence_axis']
    assert proposed['thought_pattern'] == case.library.reference('P02')
    assert proposed['child_tool_info'] == selection['child_tool_info']
    info, = proposed['child_tool_info']
    assert set(info) == {'name', 'description', 'resources', 'instructions'}
    assert info['instructions']
    assert outcome['record_refs'] == outcome['changed_record_refs'] == []
    assert outcome['revision_origin'] == {
        'version': 'scientific_process_revision_origin_v1',
        'parent_invocation_ref': scientific_invocation_ref(workflow.run_id, owner.source.path),
        'preparation_operation_ref': reference}
    assert table_count(store, 'runtime_episodes') == 2  # Preparation starts no child.
    detached = deepcopy(preparation)
    preparation['proposal']['selection']['child_tool_info'][0]['instructions'] = 'forged instruction'
    assert workflow.services.scientific_preparation(owner_context, reference) == detached

    new_selection = deepcopy(commission)
    new_selection['goal'] = 'Investigate the supplied protein using the separately selected alternative reasoning.'
    new_selection['assignment']['selection'] = selector_selection(proposed)
    new_selection['assignment']['revision_origin'] = deepcopy(outcome['revision_origin'])
    new_child = workflow.selected(owner.source, new_selection, 1).child
    child_context = workflow.binding_context(new_child.source)
    original_child_request = deepcopy(new_child.request.as_record())
    assert original_child_request['report_contract']['measurements']['schema'] == FORM
    assert original_child_request['message']['episode_assignment']['selection'] == proposed
    assert original_child_request['message']['episode_assignment']['context']['supplied_sequence'] == PROTEIN
    assert original_child_request['message']['episode_assignment']['revision_origin'] == outcome['revision_origin']
    assert workflow.services.scientific_preparation(child_context, reference, owner='parent') == detached
    assert workflow.scientific_provenance.resolve(child_context, reference, 'scientific_preparation')
    assert owner.request.as_record() == original_owner_request
    assert table_count(store, 'runtime_episodes') == 3
    assert table_count(store, 'runtime_observations') == 1
    before_counts = {table: table_count(store, table) for table in (
        'runtime_episodes', 'runtime_actions', 'runtime_model_calls', 'runtime_observations', 'tool_operations')}
    old_requests = [tuple(row) for row in store.db.execute(
        'SELECT episode_id,request FROM runtime_episodes ORDER BY episode_id')]
    frozen_tools = (case.directory / 'scientific-tool-library/index.json').read_bytes()
    expected_context = workflow.scientific_process_binding.decision_context(child_context, {})
    shutil.rmtree(case.source)

    restored = case.workflow(ScriptedDecisions([]))
    restored_root = restored.build('annotation', 'root', 'Investigate the supplied protein', case.scope)
    restored_owner = restored.selected(restored_root.source, commission, 0).child
    restored_child = restored.selected(restored_owner.source, new_selection, 1).child
    restored_context = restored.binding_context(restored_child.source)
    assert restored_child.request.as_record() == original_child_request
    assert restored_owner.request.as_record() == original_owner_request
    assert restored.scientific_process_binding.decision_context(restored_context, {}) == expected_context
    assert restored.services.scientific_preparation(restored_context, reference, owner='parent') == detached
    assert restored.scientific_process_binding.as_record() == case.descriptor
    assert (case.directory / 'scientific-tool-library/index.json').read_bytes() == frozen_tools
    assert tuple(restored.receipts.known(restored_child.source.episode_id)) == tuple(
        workflow.receipts.known(new_child.source.episode_id))
    assert [tuple(row) for row in store.db.execute(
        'SELECT episode_id,request FROM runtime_episodes ORDER BY episode_id')] == old_requests
    assert {table: table_count(store, table) for table in before_counts} == before_counts
    assert store.count('observation') == store.count('annotation') == 0
    assert all(field.get('x-source') != 'scientific_process_results' for field in FORM['properties'].values())


@pytest.mark.parametrize('mutation', ['instructions', 'axis', 'resource'])
def test_current_preparation_rejects_recorded_proposal_or_selector_tampering(prepared, mutation):
    case, workflow, _, owner, _, action, outcome = prepared
    original_reference = outcome['operation_ref']
    if mutation == 'instructions':
        outcome['result']['selection']['child_tool_info'][0]['instructions'] += '\nForged.'
    elif mutation == 'axis':
        outcome['result']['selection']['evidence_axis'] = case.library.reference('A105')
    else:
        action['arguments']['child_tool_info'][0]['resources'] = 'hpc'
    case.store.db.execute('UPDATE runtime_actions SET action=?,result=? WHERE episode_id=? AND decision_index=0',
        (json.dumps(action), json.dumps(outcome), owner.source.episode_id))
    context = workflow.binding_context(owner.source)
    with pytest.raises(ValueError):
        workflow.services.scientific_preparation(context, original_reference)
    assert not workflow.scientific_provenance.resolve(context, original_reference, 'scientific_preparation')
    assert table_count(case.store, 'runtime_observations') == 1
    assert table_count(case.store, 'runtime_episodes') == 2
    assert table_count(case.store, 'tool_operations') == 0
