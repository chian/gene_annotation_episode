"""Metadata-only construction controls over the genuine original342 journal.

These use an owned SQL/archive clone. No episode loop, model request, tool,
native operation, scientific parser or calculator executes here.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_protein_structure_contracts import POLICY
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_protein_structure_ordinary_workflow import (
    _artifact_inventory, _controllers, _credit, _retained_resource_declarations, _tables,
)


ORIGINAL_DATABASE_SHA256 = 'ef1d21820f9302b8a74ae38af7ef6f10beeee2707c0c54e54eb44b69cbc8a3f1'


def forbidden(*args, **kwargs):
    raise AssertionError('closed construction must not perform work')


class NoWorkProvider:
    complete = forbidden


@pytest.fixture
def retained_construction(tmp_path, monkeypatch):
    supplied = os.environ.get('ORDINARY_PROTEIN_RETAINED_STORE')
    if not supplied:
        pytest.skip('requires the explicitly supported original342 retained Store')
    original = Path(supplied).expanduser().resolve(strict=True)
    database, original_run = original / 'state.sqlite3', original.parent / 'run'
    database_pin = hashlib.sha256(database.read_bytes()).hexdigest()
    assert database_pin == ORIGINAL_DATABASE_SHA256
    artifact_pins, run_pins = _artifact_inventory(original / 'artifacts'), _artifact_inventory(original_run)
    owned_database, owned_run = tmp_path / 'owned.sqlite3', tmp_path / 'run'
    source = sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True)
    target = sqlite3.connect(owned_database)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    shutil.copytree(original_run, owned_run)
    store = Store.__new__(Store)
    store.path = original  # The original authenticated artifact root is read-only.
    store.db = sqlite3.connect(owned_database, isolation_level=None, timeout=30)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    try:
        # Install these before reading declarations or constructing either
        # registry/Workflow: the historical artifact root is never a writer.
        for name in ('artifact', 'put', 'commit_reasoning'):
            monkeypatch.setattr(Store, name, forbidden)
        episodes = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and all(row['state'] == 'yielded' for row in episodes)
        parent_row, child_row = episodes
        run_id, = {row['run_id'] for row in episodes}
        child_request = json.loads(child_row['request'])
        descriptors = [deepcopy(child_request['message']['scientific_process']['mechanics_binding']),
            LiteratureEpisodes(None).as_record()]
        resources, environments, inputs = _retained_resource_declarations(store)
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        tools.configure_protein_structure_resources(resources, environments)
        workflow = Workflow(store, tools, NoWorkProvider(), owned_run, run_id, _controllers, _credit,
            project_child_credit=_credit, episode_binding_descriptors=descriptors,
            episode_record_receipts=True, initial_known_record_refs=inputs)
        parent_request = json.loads(parent_row['request'])
        parent_path = json.loads(parent_row['path'])
        root = workflow.build(*parent_path[0], parent_request['goal']['objective'],
            parent_request['message']['scope'])
        records = EpisodeReturnRecords(store, run_id, failure_prefix='control_')
        parent, child = records.context(parent_row['episode_id']), records.context(child_row['episode_id'])
        action_row = store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? AND decision_index=0',
            (parent.episode_id,)).fetchone()
        selected = json.loads(action_row['action'])
        assert selected['kind'] == 'episode_child' and selected['role'] == 'scientific_process'
        assert json.loads(action_row['result'])['status'] == 'completed'
        _, _, schema = records._attempt(parent, 0)
        invocation = dict(objective=selected['goal'], purpose=selected['purpose'],
            report_schema=schema, initial_report=json.loads(selected['initial_report_json']))
        for module, names in (
            ('gene_annotation_episode.native_lifecycle',
                ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status')),
            ('gene_annotation_episode.protein_structure_tools',
                ('run_cancellable_native', 'prepare_protein_structure_work', 'resolve_protein_structure_operands')),
            ('gene_annotation_episode.protein_structure_calculations',
                ('calculate_protein_structure_components', 'fit_ca_transform')),
            ('gene_annotation_episode.protein_structure_formats', ('parse_pdb_structure', 'parse_mmcif_structure')),
        ):
            for name in names:
                monkeypatch.setattr(module + '.' + name, forbidden)
        monkeypatch.setattr('gene_annotation_episode.acquisition.PublicClients._http', forbidden)
        monkeypatch.setattr('socket.create_connection', forbidden)
        yield dict(store=store, workflow=workflow, root=root, parent=parent, child=child,
            selection=selected, invocation=invocation,
            operation_key=f'{run_id}:{parent.episode_id}:0', run_pins=run_pins, owned_run=owned_run)
    finally:
        store.close()
        assert hashlib.sha256(database.read_bytes()).hexdigest() == database_pin
        assert _artifact_inventory(original / 'artifacts') == artifact_pins
        assert _artifact_inventory(original_run) == run_pins


def prepare(case, **changes):
    selected = case['selection']
    values = dict(parent=case['parent'], role='scientific_process', inputs=deepcopy(selected['assignment']),
        scope=deepcopy(selected['scope']), operation_key=case['operation_key'],
        invocation=deepcopy(case['invocation']), closed_context=case['child'])
    values.update(changes)
    return case['workflow'].scientific_process_binding.prepare_invocation(**values)


def test_completed_original_commission_restores_literal_assignment_without_live_catalog(retained_construction, monkeypatch):
    case = retained_construction
    before = _tables(case['store'])
    binding = case['workflow'].scientific_process_binding
    monkeypatch.setattr(binding, '_information_catalog', forbidden)
    prepared = prepare(case)
    assert prepared['assignment'] == plain(case['child'].assignment)
    assert prepared['scientific_process'] == plain(case['child'].request)['message']['scientific_process']
    assert _tables(case['store']) == before
    assert _artifact_inventory(case['owned_run']) == case['run_pins']


def test_workflow_passes_actual_closed_context_before_materializing_tools(retained_construction, monkeypatch):
    case = retained_construction
    binding = case['workflow'].scientific_process_binding
    original_prepare = binding.prepare_invocation
    before = _tables(case['store'])

    class PreparedOriginal(Exception):
        pass

    def capture(*args, **kwargs):
        assert kwargs['closed_context'].as_record() == case['child'].as_record()
        result = original_prepare(*args, **kwargs)
        assert result['assignment'] == plain(case['child'].assignment)
        raise PreparedOriginal()

    monkeypatch.setattr(binding, '_information_catalog', forbidden)
    monkeypatch.setattr(binding, 'prepare_invocation', capture)
    with pytest.raises(PreparedOriginal):
        case['workflow'].selected(case['root'].source, deepcopy(case['selection']), 0)
    assert _tables(case['store']) == before


@pytest.mark.parametrize('change', ['objective', 'purpose', 'schema', 'scope', 'operation_key',
    'assignment_numeric_bool', 'context_assignment'])
def test_closed_construction_rejects_changed_invocation_or_identity(retained_construction, change):
    case = retained_construction
    changes = {}
    if change in {'objective', 'purpose', 'schema'}:
        value = deepcopy(case['invocation'])
        if change == 'schema':
            value['report_schema']['description'] = 'A different requested contract'
        else:
            value[change] += ' changed'
        changes['invocation'] = value
    elif change == 'scope':
        changes['scope'] = {'subject_refs': []}
    elif change == 'operation_key':
        changes['operation_key'] = case['operation_key'] + '0'
    elif change == 'assignment_numeric_bool':
        value = deepcopy(case['selection']['assignment'])
        assert value['constraints']['target_only'] is True
        value['constraints']['target_only'] = 1
        changes['inputs'] = value
    else:
        value = plain(case['child'].assignment)
        value['context']['condition'] = 'changed'
        changes['closed_context'] = replace(case['child'], assignment=value)
    before = _tables(case['store'])
    with pytest.raises(ValueError):
        prepare(case, **changes)
    assert _tables(case['store']) == before


@pytest.mark.parametrize('missing', ['commission', 'completed_result', 'completed_status',
    'closed_state', 'completion', 'archive', 'closing_form', 'successful_attempt'])
def test_closed_construction_requires_actual_completed_commission_archive_and_form(retained_construction, missing):
    case = retained_construction
    db, parent, child = case['store'].db, case['parent'], case['child']
    if missing == 'commission':
        db.execute('DELETE FROM runtime_actions WHERE episode_id=? AND decision_index=0', (parent.episode_id,))
    elif missing == 'completed_result':
        db.execute('UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=0', (parent.episode_id,))
    elif missing == 'completed_status':
        row = db.execute('SELECT result FROM runtime_actions WHERE episode_id=? AND decision_index=0', (parent.episode_id,)).fetchone()
        value = json.loads(row[0]); value['status'] = 'partial'
        db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=0', (json.dumps(value), parent.episode_id))
    elif missing == 'closed_state':
        db.execute("UPDATE runtime_episodes SET state='active' WHERE episode_id=?", (child.episode_id,))
    elif missing in {'completion', 'archive'}:
        db.execute('UPDATE runtime_episodes SET ' + missing + '=NULL WHERE episode_id=?', (child.episode_id,))
    elif missing == 'closing_form':
        db.execute('UPDATE runtime_forms SET form=NULL WHERE episode_id=?', (child.episode_id,))
    else:
        db.execute('UPDATE runtime_report_attempts SET form=NULL WHERE parent_episode_id=? AND decision_index=0', (parent.episode_id,))
    before = _tables(case['store'])
    with pytest.raises(ValueError):
        prepare(case)
    assert _tables(case['store']) == before


def test_live_invocation_still_rejects_changed_current_tool_contract(retained_construction):
    case = retained_construction
    before = _tables(case['store'])
    with pytest.raises(ValueError, match='scientific_tool_contract_changed:compare_protein_structures:local'):
        prepare(case, operation_key=case['operation_key'] + ':new', closed_context=None)
    assert _tables(case['store']) == before


def test_unrecorded_workflow_invocation_preserves_original_injected_prepare_signature(retained_construction, monkeypatch):
    case = retained_construction
    before = _tables(case['store'])

    class OriginalSignatureReached(Exception):
        pass

    def original_signature(parent, role, inputs, scope, operation_key, *, invocation):
        assert operation_key.endswith(':99')
        raise OriginalSignatureReached()

    monkeypatch.setattr(case['workflow'].scientific_process_binding, 'prepare_invocation', original_signature)
    with pytest.raises(OriginalSignatureReached):
        case['workflow'].selected(case['root'].source, deepcopy(case['selection']), 99)
    assert _tables(case['store']) == before
