"""Actual configured C1 factory reconstructs the original opt-in declaration.

All model transport is forbidden by a fixture; no episode work is launched.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json

import pytest

from gene_annotation_episode import independent_execution as worker
from gene_annotation_episode.communication import plain
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import Workflow, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_contract_information_custody_059 import COMPACT, commission
from test_contract_information_runtime_059 import PROFILE, PresentedProvider
from test_literature_kinetic_storage import setup


def test_actual_worker_factory_forwards_original_host_declaration_and_reopens_profile(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_episodes import _population_catalog
    original_operations = _population_catalog()
    store, seed, args = setup(tmp_path / 'state')
    directory = tmp_path / 'run'
    binding_factory = partial(LiteratureEpisodes, rate_population=True,
        reference_parent_sources=[args['source_ref']], contract_information_profile=PROFILE)
    provider = PresentedProvider([OSError('Fixture stops before any root action')])
    try:
        with pytest.raises(OSError, match='before any root action'):
            asyncio.run(run_workflow(store, build_tools(store), provider=provider, run_dir=directory,
                initial_known_record_refs=list(seed.received_record_refs),
                episode_binding_factories=(binding_factory,), decision_protocol='decision_exchange_v1'))
        manifest = json.loads((directory / 'run.json').read_text())
        run_id = manifest.pop('run_id')
        settings = manifest
        original_binding = worker.make_runtime_binding(store, directory)
        options = worker._standard_bindings(store, directory, settings)
        worker._check_bindings(options, settings)
        chosen = commission(seed, args, COMPACT)
        chooser = PresentedProvider([chosen])
        value = assemble_workflow(store, build_tools(store), chooser, directory, run_id, settings,
            episode_binding_descriptors=settings['episode_bindings'],
            **{key: val for key, val in options.items() if key != 'binding_definitions'})
        value.configure_execution(original_binding)
        root = value.build('annotation', 'root', settings['goal'], plain(seed.scope))
        # The first root request was deliberately interrupted. The fixture
        # explicitly prepares a separate decision without rewriting that row.
        root.source.calls = 1
        response, index, context, schema = asyncio.run(root.source.call({
            'goal': root.goal.as_record(), 'scope': plain(seed.scope),
            'visible_record_refs': list(seed.received_record_refs),
            'tools': value.catalog(seed.scope, source=root.source)}, value.action_schema(root.source)))
        unit = root.source.apply_response(response, index, context, schema)
        assert unit is not None and index == 1
        spec, = value.commissions.recover_selected(root.source.episode_id)
        value.execution_backend.commission(spec)
        assert spec['child']['request']['message']['report_contract_declaration']['submitted_schema_json'] == chosen['response']['selection']['schema_json']
        original = deepcopy(spec)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()

    connections = []
    class ForbiddenModel(PresentedProvider):
        def __init__(self, *_a, **_kw):
            super().__init__([])
            self.entered = self.exited = False
            connections.append(self)
        async def __aenter__(self):
            self.entered = True
            return self
        async def __aexit__(self, *_args):
            self.exited = True
        async def complete(self, *_a, **_kw):
            raise AssertionError('Reconstruction must not invoke a model')
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection', ForbiddenModel)
    async def inspect():
        async with worker.open_commission(spec) as opened:
            episode = opened['episode']
            value = episode.source.workflow
            assert episode.request.as_record() == original['child']['request']
            assert value.contract_information_profile(episode.source) == PROFILE
            assert value.episode_bindings.as_record() == settings['episode_bindings']
            assert value.execution_binding == original_binding
            assert value.execution_backend.load_commission(spec['handle']) == original
            assert value.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
            actual_operations = [{key: row[key] for key in ('name', 'description', 'input_schema')}
                for row in value.catalog(episode.source.scope, source=episode.source)
                if row['name'].startswith('literature.')]
            assert actual_operations == original_operations
    asyncio.run(inspect())
    assert len(connections) == 1 and connections[0].entered and connections[0].exited
    assert not connections[0].contexts and spec == original


def test_owned_caller_rejects_incompatible_profile_before_provider_entry(tmp_path, monkeypatch):
    from gene_annotation_episode.episode_contract_information import ContractInformationError
    from gene_annotation_episode.providers import ModelConnection
    store, seed, args = setup(tmp_path / 'state')
    entered = []
    async def forbidden_entry(_connection):
        entered.append(True)
        raise AssertionError('Invalid explicit configuration must be rejected before model transport')
    monkeypatch.setattr(ModelConnection, '__aenter__', forbidden_entry)
    try:
        with pytest.raises(ContractInformationError) as error:
            asyncio.run(run_workflow(store, build_tools(store), run_dir=tmp_path / 'run',
                initial_known_record_refs=list(seed.received_record_refs),
                episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                    reference_parent_sources=[args['source_ref']], contract_information_profile=PROFILE),),
                decision_protocol=None))
        assert error.value.code == 'contract_information_requires_pending_decision_protocol'
        assert error.value.field == 'decision_protocol' and not entered
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()
