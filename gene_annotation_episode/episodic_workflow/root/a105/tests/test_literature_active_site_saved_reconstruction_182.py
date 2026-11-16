"""Synthetic exact saved reconstruction with scientific computation disabled.

The retained v1 records were written by the actual original implementation
before this correction; they are not relabeled outputs from the new code.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a105.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_composition import compose_episode_bindings
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_active_site_storage import LiteratureActiveSiteRepository, active_site_cells_schema
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories
from gene_annotation_episode.episodic_workflow.root.a105.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_active_site_inputs import TEXT
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_active_site_storage import setup
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import FixtureController, ScriptedProvider
REQUESTED = ['sites_per_total_monomer', 'conditional_nominal_to_active_denominator_factor']
FORM = obj({'amounts': active_site_cells_schema()})

def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}

def readonly(path):
    assert not Path(str(path / 'state.sqlite3') + '-wal').exists()
    store = Store.__new__(Store)
    store.path, store._savepoint = (path, 0)
    store.db = sqlite3.connect((path / 'state.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    store.db.row_factory = sqlite3.Row
    store.db.execute('PRAGMA query_only=ON')
    return store

def forbidden(*_args, **_kwargs):
    raise AssertionError('saved reconstruction must not parse, convert or calculate scientific values')

def disable_science(monkeypatch):
    modules = {'literature_active_site_storage': ('read_active_site_inputs', 'populate_active_site_components'), 'literature_active_site_inputs': ('read_active_site_inputs', 'validate_active_site_extraction', 'unit_scale', '_derived_quantity', '_number', '_fraction_number'), 'literature_active_site_calculations': ('populate_active_site_components', 'validate_active_site_extraction', '_operand', '_reason', '_divide', '_multiply', '_subtract', '_point', '_encode', '_project'), 'literature_rate_domains': ('_divide', '_multiply', '_subtract', '_point', '_encode', '_project'), 'literature_rate_native_inputs': ('_number', '_saved_number', '_plain_unit', '_converted'), 'literature_partner_source_fields': ('read_source_number', 'convert_source_number')}
    for module, names in modules.items():
        for name in names:
            monkeypatch.setattr(f'gene_annotation_episode.episodic_workflow.root.a105.library.{module}.{name}', forbidden)

def saved_artifacts_only(monkeypatch, store):
    allowed = {row[field] for row in store.list('source') if row['origin'] == 'tool' for field in ('artifact_ref', 'request_ref')}
    original = store.get_artifact

    def read(reference):
        assert reference in allowed, 'original scientific artifacts must remain closed'
        return original(reference)
    monkeypatch.setattr(store, 'get_artifact', read)

def services_for(store, run_id):
    host = SimpleNamespace(store=store, run_id=run_id, tools=None)
    return (host, WorkflowServices(host))







def test_genuine_empty_cold_binding_does_not_install_tables(tmp_path, monkeypatch):
    store, context, _ = setup(tmp_path)
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    store.close()
    before = hashes(tmp_path)
    disable_science(monkeypatch)
    with readonly(tmp_path) as store:
        host, services = services_for(store, context.run_id)
        binding = LiteratureEpisode(services, rate_population=True, active_site_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        repo = binding._active_site_repository()
        assert not repo._installed(repo.operations_table)
        assert repo.received_cells(context) == []
        assert repo.project_cells([], permitted_record_refs=[]) == []
        assert store.db.total_changes == 0
    assert hashes(tmp_path) == before

def test_current_selected_shared_loop_then_cold_readonly_factory_without_calculators(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / 'state')
    forms, controllers = ([], [])
    assignment = {**plain(context.assignment), 'requested_active_site_components': REQUESTED}
    child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment, 'goal': "Determine the synthetic preparation's active-site denominator.", 'scope': plain(context.scope), 'purpose': 'Return the specified active-site amount components with their scientific meanings.', 'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
    work = {'selection': {'kind': 'tool', 'tool': 'literature.active_site.populate', 'arguments': args}, 'report_update': {}}

    def integrate(inputs):
        form, = inputs['child_reports']
        forms.append(deepcopy(form))
        assert [row['component'] for row in form['amounts']] == REQUESTED
        commit = {key: [] for key in store.reasoning_schema()['required']}
        source = store.get(args['source_ref'])
        start = TEXT.index('active sites')
        commit['source_subjects'] = [{'alias': 'synthetic_amount', 'reference_type': 'assay', 'source_ref': args['source_ref'], 'label': 'active sites', 'anchor': {'source_ref': args['source_ref'], 'artifact_ref': source['artifact_ref'], 'start': start, 'end': start + len('active sites'), 'quote': 'active sites'}}]
        return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}

    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, integrate]), run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer, initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=literature_binding_factories(rate_population=True, active_site_population=True, reference_parent_sources=[args['source_ref']]), binding_definitions={'credit': scorer.as_record()}))
    assert summary['credit'] == 0 and [c.scores for c in controllers] == [[0, 0], [0]]
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
    assert store.db.execute('SELECT count(*) FROM literature_active_site_operations').fetchone()[0] == 1
    run_id, parent_id = store.db.execute('SELECT run_id,episode_id FROM literature_active_site_received').fetchone()
    descriptors = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?', (run_id,)).fetchone()[0])['episode_bindings']
    receiver = replace(context, run_id=run_id, episode_id=parent_id, role='annotation', path=(('annotation', parent_id),), assignment={}, received_record_refs=tuple((row['sheet_ref'] for row in forms[0]['amounts'])))
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    store.close()
    before = hashes(tmp_path / 'state')
    disable_science(monkeypatch)
    with readonly(tmp_path / 'state') as store:
        saved_artifacts_only(monkeypatch, store)
        host, services = services_for(store, run_id)
        restored = compose_episode_bindings(services, store=store, journal=SimpleNamespace(store=store, run_id=run_id), execution_backend=None, descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
        binding, = restored.bindings
        host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)['literature_active_site_cells'] == forms[0]['amounts']
        repo = binding._active_site_repository()
        assert repo.fact_cells(receiver, receiver.received_record_refs, components=repo.components) == forms[0]['amounts']
        assert store.db.total_changes == 0
    assert before == hashes(tmp_path / 'state')
