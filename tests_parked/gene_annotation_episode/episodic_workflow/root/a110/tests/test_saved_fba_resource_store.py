"""Real retained Store custody and an explicit receiving-only resource port.

Operational units below are declared test inputs, not recovered old factory
authority. Resource declarations come from the original three capsules. The
visibility adapter calls the existing production publication restriction and
never grants a reference or substitutes successful native observations.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110 import native_lifecycle
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_tools import OrdinaryFluxBalanceTools
from gene_annotation_episode.episodic_workflow.root.a110.publication_reference_access import publication_reference_restriction
from gene_annotation_episode.episodic_workflow.root.a110.state import Store
from gene_annotation_episode.episodic_workflow.root.a110.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_configuration import ReceivedExecutionConfiguration
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.saved_fba_resource_declaration import (
    SavedFBAResourceDeclaration, qualify_saved_resource_declaration,
)
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.saved_fba_read_resources import SavedFBAReadResources


DATABASE_SHA256 = '7a3e9d961da978a8bc382539dcf21f6e224f26d4ac786d571fd4d60edfae18ae'


def artifact_inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        assert not path.is_symlink()
        if path.is_dir(): continue
        assert path.is_file()
        result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


@pytest.fixture
def retained_case(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / 'fixtures' / 'genuine_fba360'
    assert hashlib.sha256((fixture / 'store/state.sqlite3').read_bytes()).hexdigest() == DATABASE_SHA256
    destination = tmp_path / 'store'
    shutil.copytree(fixture / 'store', destination)
    def no_execution(*args, **kwargs):
        raise AssertionError('saved_resource_read_attempted_new_native_execution')
    for name in ('prepare_job', 'resume_start', 'run_job'):
        if hasattr(native_lifecycle, name): monkeypatch.setattr(native_lifecycle, name, no_execution)
    with Store(destination) as store:
        records = EpisodeReturnRecords(store, next(iter(store.db.execute(
            'SELECT DISTINCT run_id FROM runtime_episodes')))[0], failure_prefix='saved_resource_test_')
        episodes = list(store.db.execute('SELECT episode_id FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2
        parent, science = [records.context(row['episode_id']) for row in episodes]
        tools = ToolRegistry(store)
        ordinary = OrdinaryFluxBalanceTools(tools)
        tools.ordinary_flux_balance_backend = ordinary
        assert tools._flux_balance_configuration is None
        def reader(context, reference, namespace, *, source_metadata_only):
            assert namespace == 'source' and source_metadata_only is True
            # This is an actual retained-receipt policy verdict, not a constant
            # test grant. Ordinary.read_publication independently checks scope,
            # source identity, action/operation completion and artifact hashes.
            verdict = publication_reference_restriction(store, context, reference, namespace)
            return {'failure': None if verdict is True else {'code': 'source_not_admitted'}}
        rows = list(store.db.execute("SELECT * FROM tool_operations WHERE name='perform_flux_balance_analysis' "
            "AND json_extract(arguments,'$.mode') IN ('inspect','edit','solve') ORDER BY operation_key"))
        assert [json.loads(row['arguments'])['mode'] for row in rows] == ['inspect', 'edit', 'solve']
        refs = tuple(json.loads(row['result'])['result']['source_ref'] for row in rows)
        capsules = [ordinary.read_publication(science, reference, reader=reader)[0] for reference in refs]
        selected = capsules[0]['prepared']['selected']
        assert selected['binding_ordinal_0based'] == 0
        assert all(capsule['prepared']['selected'] == selected for capsule in capsules)
        policy = capsules[2]['prepared']['native']['metadata']['policy']
        assert all(capsule['prepared']['model']['execution']['metadata']['policy'] == policy for capsule in capsules[:2])
        resource_id = selected['resource_id']
        configuration = {'kind': 'local', 'workspace': selected['workspace'],
            'policy': deepcopy(policy), 'native_flux_balance': [deepcopy(selected['binding'])]}
        before = tuple(store.db.iterdump())
        artifacts = artifact_inventory(destination / 'artifacts')
        case = SimpleNamespace(store=store, tools=tools, ordinary=ordinary, parent=parent, science=science,
            reader=reader, refs=refs, rows=rows, resource_id=resource_id, configuration=configuration,
            resources={resource_id: configuration}, directory=tmp_path / 'receiving')
        try:
            yield case
        finally:
            assert tuple(store.db.iterdump()) == before
            assert artifact_inventory(destination / 'artifacts') == artifacts
            assert tools._flux_balance_configuration is None


def declaration(case, *, configuration=None, reader=None):
    return qualify_saved_resource_declaration(case.ordinary, case.science,
        resource_id=case.resource_id,
        configuration=case.configuration if configuration is None else configuration,
        publication_references=case.refs, reader=case.reader if reader is None else reader)


def test_real_publications_qualify_read_declaration_without_live_policy(retained_case):
    case = retained_case
    value = declaration(case)
    assert json.loads(value.configuration_json) == case.configuration
    witness = value.requalify(case.ordinary, case.science, reader=case.reader)
    assert witness['producer'] == 'original_355'
    assert witness['producer_episode_id'] == case.science.episode_id
    assert tuple(row['source_ref'] for row in witness['witnesses']) == case.refs
    assert len(witness['selections']) == 1
    port = SavedFBAReadResources(case.ordinary, case.science, reader=case.reader, declarations=(value,))
    assert port.check(store=case.store, run_id=case.science.run_id, resources=case.resources) == frozenset({case.resource_id})


def test_real_qualified_resource_constructs_receiving_owner_and_preserves_typed_evidence(retained_case):
    case = retained_case
    port = SavedFBAReadResources(case.ordinary, case.science, reader=case.reader,
        declarations=(declaration(case),))
    factory = ExecutionServiceFactory(deepcopy(case.resources), {}, 2., .25, .5)
    original_factory = canonical(plain(factory.as_record()))
    configuration = ReceivedExecutionConfiguration.original_global_factory(factory,
        authority_id='explicit-retained-ordinary-read-test')
    # No factory.__call__ or configure_tool_registry: those are live routes and
    # retain their normal current configuration contracts.
    services = SimpleNamespace(annotation_task_required=lambda: False,
        read_received_molecular_input=case.reader)
    catalog = configuration.construct(store=case.store, run_id=case.science.run_id,
        directory=case.directory, tool_registry=case.tools, services=services,
        saved_read_resources={'explicit-retained-ordinary-read-test': port})
    owner = catalog.configured('@annotation')
    assert canonical(plain(factory.as_record())) == original_factory
    assert owner.resources == case.resources and case.resource_id not in owner._practical
    assert owner.native_flux_balance_returns.ordinary_backend is case.ordinary
    attempt, = list(case.store.db.execute('SELECT form, contract FROM runtime_report_attempts'))
    returned, schema = json.loads(attempt['form']), json.loads(attempt['contract'])['measurements']['schema']
    assert returned['measurements'] and returned['saved_sheets']
    facts = owner.native_flux_balance_returns.received_facts(case.parent, schema)
    for field in ('measurements', 'model_views', 'saved_sheets', 'edited_models', 'failures'):
        assert facts['flux_balance_' + field] == returned[field]
    actual = catalog.received('@annotation', case.science).received_report_facts(case.science)
    for field in ('measurements', 'saved_sheets', 'edited_models'):
        assert actual['flux_balance_' + field] == returned[field]
    assert canonical(plain(factory.as_record())) == original_factory


def test_source_visibility_denial_cannot_qualify_existing_publication(retained_case):
    with pytest.raises(ValueError, match='ordinary_fba_result_source_not_received'):
        declaration(retained_case, reader=lambda *args, **kwargs: {'failure': {'code': 'denied'}})


def test_current_policy_cannot_be_substituted_for_original_declaration(retained_case):
    configuration = deepcopy(retained_case.configuration)
    del configuration['policy']['wall_seconds']
    with pytest.raises(ValueError, match='saved_fba_resource_original_policy_conflict'):
        declaration(retained_case, configuration=configuration)


def test_forged_immutable_declaration_still_reauthenticates_real_capsules(retained_case):
    case = retained_case
    forged = SavedFBAResourceDeclaration(case.resource_id, canonical(case.configuration), case.refs,
        canonical({'producer': 'original_355', 'claimed': 'not-qualified'}))
    with pytest.raises(ValueError, match='saved_fba_resource_publication_changed'):
        SavedFBAReadResources(case.ordinary, case.science, reader=case.reader, declarations=(forged,))


def test_previously_qualified_port_rejects_action_outcome_drift(retained_case):
    case = retained_case
    port = SavedFBAReadResources(case.ordinary, case.science, reader=case.reader, declarations=(declaration(case),))
    # A rollback-scoped negative operand, never an accepted rewritten receipt.
    case.store.db.execute('SAVEPOINT saved_resource_negative')
    try:
        case.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=2',
            (case.science.run_id, case.science.episode_id))
        with pytest.raises(ValueError, match='ordinary_fba_completed_action_required'):
            port.check(store=case.store, run_id=case.science.run_id, resources=case.resources)
    finally:
        case.store.db.execute('ROLLBACK TO saved_resource_negative')
        case.store.db.execute('RELEASE saved_resource_negative')
