"""Current saved-owner reconstruction; no provider, job or scientific action."""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source


PACKAGE = __package__.removesuffix('.tests')
AXIS = PACKAGE.rsplit('.', 1)[-1]


def module(name):
    return importlib.import_module(PACKAGE + '.' + name)


def forbidden(*args, **kwargs):
    raise AssertionError('reconstruction_selected_work_or_crossed_external_port')


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)


@pytest.fixture(scope='module')
def current(tmp_path_factory):
    directory = tmp_path_factory.mktemp('private-reconstruction')
    write_instruction_source(directory / 'instruction-source', AXIS)
    library = module('partner_presence_evidence_library').PartnerPresenceEvidenceLibrary
    tools = module('scientific_tool_library').ScientificToolLibrary
    library.freeze(directory / 'scientific-process-library', source=directory / 'instruction-source')
    tools.freeze(directory / 'scientific-tool-library', catalog=[])
    science = module('private_scientific_literature_reconstruction')
    execution = module('private_execution_hpc_reconstruction')
    catalog = {**science.CATALOG, **execution.CATALOG}
    services = SimpleNamespace(bound_role_credit=forbidden)
    backend = SimpleNamespace(load_commission=forbidden)
    with module('state').Store(directory / 'state') as store:
        journal = SimpleNamespace(store=store, run_id='private-reconstruction-control')
        registry = module('tools').ToolRegistry(store)
        owners = {}
        for name, declaration in catalog.items():
            owner_type = getattr(module(name.replace('/', '.') + '.episode'), declaration['owner_class'])
            kind = declaration['owner_class']
            if kind == 'PartnerPresenceEvidenceEpisode':
                owner = owner_type(services, library=library(directory / 'scientific-process-library'),
                    tool_library=tools(directory / 'scientific-tool-library'),
                    child_roles=('partner_presence_evidence', 'launch', 'results', 'hpc', 'monitor', 'literature'))
            elif kind == 'ExecutionEpisode':
                owner = owner_type(services, store=store, directory=directory, run_id=journal.run_id,
                    resources=resources(), initial_information={}, tool_registry=registry,
                    handoff_unit=3, acquired_record_unit=2, log_window_bytes=1024,
                    log_roles=('stdout', 'stderr'))
            elif kind == 'HPCEpisode':
                owner = owner_type(services, store=store, directory=directory, run_id=journal.run_id,
                    resources=resources(), commissions={})
            else:
                assert kind in ('LiteratureEpisode', 'MonitorEpisode')
                owner = owner_type(services, outcome_page_size=7)
            owners[name] = owner
        records = [owner.as_record() for owner in owners.values()]
        yield SimpleNamespace(directory=directory, store=store, journal=journal,
            services=services, registry=registry, backend=backend, owners=owners,
            records=records, catalog=catalog, science=science, execution=execution)


def compose(current, records=None, **overrides):
    options = dict(store=current.store, journal=current.journal,
        execution_backend=current.backend, descriptors=current.records if records is None else records,
        job_episodes=None, resource_estimator=None,
        role_credit_bindings={'monitor': {'definition': {'kind': 'caller_supplied_monitor_control'},
                                         'project': forbidden}},
        directory=current.directory, tool_registry=current.registry)
    options.update(overrides)
    return module('episode_composition').compose_episode_bindings(current.services, **options)


def test_every_current_private_owner_round_trips_with_original_ports(current):
    axis_root = Path(module('episode_composition').__file__).parent
    actual_paths = {str(path.parent.relative_to(axis_root)) for path in axis_root.rglob('episode.py')
                    if 'tests' not in path.parts and path.parent.name != 'method_loop'}
    # The annotation root and annotation_improvement homes hold routing
    # functions only: no binding owner, no saved descriptor to reconstruct.
    function_only_homes = {'.', 'annotation_improvement'}
    assert function_only_homes <= actual_paths
    assert set(current.catalog) == actual_paths - function_only_homes
    # Saved order is not a dependency order; admission sees the whole set.
    result = compose(current, list(reversed(current.records)))
    assert len(result.bindings) == len(current.owners)
    for binding in result.bindings:
        original = current.owners[binding.binding_path]
        assert type(binding) is type(original)
        assert binding.services is current.services
        assert binding.as_record() == original.as_record()
        assert binding.commissioning_parent == original.commissioning_parent
        if hasattr(original, 'store'):
            assert binding.store is current.store
            assert binding.run_id == current.journal.run_id
        if hasattr(original, 'tool_registry'):
            assert binding.tool_registry is current.registry
    assert result.role_credit_projectors['monitor'] is forbidden
    assert result.progress_provider.durable_store is current.backend


@pytest.mark.parametrize('mutation', ['unknown', 'historical_version', 'duplicate',
    'missing_parent', 'extra_field', 'missing_configuration', 'extra_configuration',
    'missing_monitor_projector',
    'missing_monitor_backend'])
def test_malformed_saved_set_rejected_before_construction_or_progress(current, monkeypatch, mutation):
    records = deepcopy(current.records)
    direct = next(row for row in records if row['binding_id'] == 'execution_job_submission')
    options = {}
    if mutation == 'unknown':
        direct['binding_id'] = 'execution_episode'
    elif mutation == 'historical_version':
        next(row for row in records if row['binding_id'] == 'partner_presence_evidence')['version'] = 'partner_presence_evidence_episodes_v8'
    elif mutation == 'duplicate':
        records.append(deepcopy(direct))
    elif mutation == 'missing_parent':
        records = [row for row in records if row['binding_id'] != 'partner_presence_evidence']
    elif mutation == 'extra_field':
        direct['owner_class'] = 'ExecutionEpisode'
    elif mutation == 'missing_configuration':
        del direct['configuration']['resources']
    elif mutation == 'extra_configuration':
        direct['configuration']['invented_authority'] = True
    elif mutation == 'missing_monitor_projector':
        options['role_credit_bindings'] = {}
    else:
        options['execution_backend'] = None
    monkeypatch.setattr(current.science, 'reconstruct', forbidden)
    monkeypatch.setattr(current.execution, 'reconstruct', forbidden)
    monkeypatch.setattr(module('episode_composition'), 'ProgressProvider', forbidden)
    changes = current.store.db.total_changes
    with pytest.raises(module('method_loop.durable').DurableExecutionError):
        compose(current, records, **options)
    assert current.store.db.total_changes == changes


def test_current_scientific_reopen_and_changed_frozen_library_rejection(current):
    record = deepcopy(next(row for row in current.records if row['binding_id'] == 'partner_presence_evidence'))
    reopen = module('episode_composition').reopen_scientific_binding
    owner = reopen(current.services, descriptor=record, directory=current.directory)
    assert owner.as_record() == record and owner.services is current.services
    record['configuration']['library']['invented'] = True
    with pytest.raises(module('method_loop.durable').DurableExecutionError) as observed:
        reopen(current.services, descriptor=record, directory=current.directory)
    assert observed.value.failure['code'] == 'identity_conflict'


def test_actual_owner_parent_identity_is_checked(current, monkeypatch):
    record = next(row for row in current.records if row['binding_id'] == 'execution_job_submission')
    owner_type = type(current.owners[record['binding_id']])
    monkeypatch.setattr(owner_type, 'commissioning_parent', 'partner_presence_evidence')
    with pytest.raises(module('method_loop.durable').DurableExecutionError) as observed:
        compose(current, [record], execution_backend=None, role_credit_bindings={})
    assert observed.value.failure['code'] == 'identity_conflict'
