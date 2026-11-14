"""Actual A104 reader guards against immutable original049 saved controls.

The producer and decisions belong to the original mixed-owner fixture. These
tests exercise its saved read authority through each current A104 owner; they
do not execute a fluorescence producer or claim an A104 scientific workflow.
"""
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.tests.execution_input_version_probe import PARENTS, CHILDREN
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_native_disposable_store import RetainedCase, unpack_fluorescence as unpack

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
HOMES = tuple('/'.join(part for part in (parent, child) if part) for parent in PARENTS for child in CHILDREN)
OPERATIONS = ('perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells')


@pytest.fixture(scope='module')
def retained_cases(tmp_path_factory):
    cases = unpack(tmp_path_factory.mktemp('original049-fluorescence'))
    yield {case.manifest['operation']: case for case in cases}
    for case in cases:
        case.verify_unchanged()


def historical_reader_resources(case):
    # The original declaration is an already authenticated archive member.
    # Project only the resource identity and currently accepted local fields;
    # producer bindings and obsolete policy fields are not reader capabilities.
    raw = (case.directory / 'fixture-configuration.json').read_bytes()
    assert sha256(raw).hexdigest() == case.allowed['fixture-configuration.json']['sha256']
    factory = json.loads(raw)['factory']
    assert factory['version'] == 'execution_service_factory_v1'
    assert set(factory['resources']) == {'here'}
    resource = factory['resources']['here']
    assert resource['kind'] == 'local'
    assert resource['workspace'] == str(case.logical_root / 'workspace')
    return {'here': {'kind': resource['kind'], 'workspace': resource['workspace'],
        'policy': {name: resource['policy'][name] for name in ('memory_bytes', 'scratch_bytes')}}}


def actual_owner(store, directory, home, case):
    cls = import_module(PREFIX + home.replace('/', '.') + '.episode').ExecutionEpisode
    owner = cls(SimpleNamespace(annotation_task_required=lambda: False), store=store,
        run_id=case.manifest['original_run_id'], directory=directory, resources=historical_reader_resources(case),
        initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
        log_window_bytes=1024, log_roles=('stdout', 'stderr'))
    # Constructors retain original resource identity and the fresh run directory.
    # Historical readers then receive the original logical archive location.
    owner.directory = case.logical_root / 'run'
    case.seal_store(store)
    return owner


def saved_controls(store, owner):
    rows = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
        "AND json_extract(result,'$.result.version')='native_fluorescence_acquired_result_v1' ORDER BY rowid",
        (owner.run_id,)).fetchall()
    values = [json.loads(row['result'])['result'] for row in rows]
    assert len(values) == 3
    for value in values:
        intent = value['intent']
        actual = owner.native_fluorescence_results.receipts.read_completed(
            episode_id=intent['episode_id'], operation_key=intent['operation_key'], scope=intent['scope'])
        assert actual == value
    assert values[0]['delivery_complete'] is True
    assert values[1]['delivery_complete'] is False
    assert values[2]['intent']['assignment']['selector']['mode'] == 'saved_sheet_recalculation'
    return values


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('home', HOMES)
def test_actual_fluorescence_readers_keep_saved_grants_denials_and_reopen(
        tmp_path, monkeypatch, retained_cases, operation, home):
    case = retained_cases[operation]
    with case.control_transport(monkeypatch), case.open_store() as store:
        owner = actual_owner(store, tmp_path / 'constructor', home, case)
        results, returns = owner.native_fluorescence_results, owner.native_fluorescence_returns
        assert type(results) is import_module(PREFIX + 'library.native_fluorescence_results').NativeFluorescenceResults
        assert type(returns) is import_module(PREFIX + 'library.fluorescence_returns').FluorescenceReturns
        receipts = saved_controls(store, owner)
        original, partial, recalculated = receipts
        reference = original['qualified_files']['sheet']['artifact_ref']
        assert original['qualified_files']['sheet']['sha256'] == case.recovered['sha256']
        # The genuine archived producer's scientific payload was withdrawn.
        # Historical authority still reads the complete original control chain.
        with pytest.raises(FileNotFoundError):
            store.get_artifact(reference)
        context = returns.context(original['intent']['episode_id'])
        root = returns.context(case.manifest['original_root_episode_id'])
        candidates = [returns.context(row['episode_id']) for row in store.db.execute(
            'SELECT episode_id FROM runtime_episodes WHERE run_id=?', (owner.run_id,))]
        science, = [value for value in candidates if value.role == 'scientific_process']
        assert results.owns_reference(reference) is True
        assert returns.authenticate_received_saved_sheet(science, original['qualified_files']['sheet']) == (
            original['intent']['episode_id'],)
        for receiving in (context, science):
            assert owner._fluorescence_reference_access(receiving, reference, 'artifact') is True
            assert owner.resolve_received_reference(receiving, reference, 'artifact') is True
            assert owner.resolve(receiving, reference, 'artifact') is True
            assert owner._versions([{'reference': reference, 'version': None, 'content_sha256': None}],
                plain(receiving.scope), context=receiving) is None
        assert owner._fluorescence_reference_access(science, reference, 'execution_handle') is False
        # Original SCI -> annotation returned measurements/context, not sheets.
        # The artifact's presence in the same Store never grants this root.
        assert owner._fluorescence_reference_access(root, reference, 'artifact') is False
        assert owner.resolve_received_reference(root, reference, 'artifact') is False
        assert owner.resolve(root, reference, 'artifact') is False
        with pytest.raises(ValueError, match='fluorescence_input_protected_reference_denied'):
            owner._versions([{'reference': reference, 'version': None, 'content_sha256': None}],
                plain(root.scope), context=root)
        saved_context = returns.context(recalculated['intent']['episode_id'])
        selected_sheet = recalculated['intent']['assignment']['selector']['saved_sheet_file']
        assert selected_sheet == partial['qualified_files']['sheet']
        assert partial['intent']['episode_id'] in returns.authenticate_received_saved_sheet(saved_context, selected_sheet)
        assert owner._fluorescence_reference_access(saved_context, selected_sheet['artifact_ref'], 'artifact') is True
        with pytest.raises(ValueError):
            results.receipts.read_completed(episode_id=original['intent']['episode_id'],
                operation_key=original['intent']['operation_key'], scope={'subject_refs': []})
        baseline = deepcopy(receipts)

    # Recovery restores exact content from the already required047 fixture to
    # a separate test overlay. It changes no049 row, control, fact or grant.
    overlay = case.recovered_overlay(tmp_path / 'recovered-content')
    with case.control_transport(monkeypatch), case.open_store(overlay=overlay) as reopened:
        owner = actual_owner(reopened, tmp_path / 'reopened-constructor', home, case)
        assert saved_controls(reopened, owner) == baseline
        returns = owner.native_fluorescence_returns
        science = next(returns.context(row['episode_id']) for row in reopened.db.execute(
            'SELECT episode_id FROM runtime_episodes WHERE run_id=?', (owner.run_id,))
            if returns.context(row['episode_id']).role == 'scientific_process')
        reference = baseline[0]['qualified_files']['sheet']['artifact_ref']
        assert owner._versions([{'reference': reference, 'version': None,
            'content_sha256': case.recovered['sha256']}], plain(science.scope), context=science) is None
        with pytest.raises(ValueError, match='execution_input_version_conflict'):
            owner._versions([{'reference': reference, 'version': None, 'content_sha256': '0' * 64}],
                plain(science.scope), context=science)
        root = returns.context(case.manifest['original_root_episode_id'])
        assert owner._fluorescence_reference_access(root, reference, 'artifact') is False
        assert owner.resolve_received_reference(root, reference, 'artifact') is False
    assert case.transported_reads


