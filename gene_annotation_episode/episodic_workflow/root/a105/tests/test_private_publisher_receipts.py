"""Prospective publisher metadata through real scientific population and cold read.

Controlled repository tests reuse the original synthetic scientific operands;
they do not assert autonomous workflow or typed-finding grading coverage.
"""
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import hashlib
import json
from types import SimpleNamespace

import pytest

from .test_private_binding_restoration import frozen_scientific_binding
from .test_private_literature_bindings import AXIS, HOMES


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.mark.parametrize('home', HOMES)
def test_each_private_factory_supplies_its_actual_registry(home):
    registry = module('episode_bindings').EpisodeBindingRegistry([])
    host = SimpleNamespace(store=object(), run_id='factory-only', episode_bindings=registry)
    binding = module(home + '.episode').LiteratureEpisode(SimpleNamespace(workflow=host))
    for factory in ('_concentration_window_repository', '_measurement_comparison_repository'):
        repository = getattr(binding, factory)()
        assert repository.binding_registry is registry
        assert repository.store is host.store and repository.run_id == host.run_id


@pytest.mark.parametrize('pilot', [False, True])
@pytest.mark.parametrize('family', ['concentration_window', 'measurement_comparison'])
def test_actual_scientific_population_keeps_original_owner_on_cold_read(tmp_path, pilot, family):
    fixture = module('tests.test_literature_' + family + ('_binding_281' if family == 'concentration_window' else '_binding_268'))
    directory = tmp_path / 'state'
    store, original, arguments, original_binding, _ = fixture.setup(directory)
    try:
        host = original_binding.services.workflow
        scientific, _ = frozen_scientific_binding(tmp_path)
        bindings = [scientific, *[module(home + '.episode').LiteratureEpisode(module('episode_services').WorkflowServices(host), rate_population=True, reference_parent_sources=original.received_record_refs) for home in HOMES]]
        registry = module('episode_bindings').EpisodeBindingRegistry(bindings)
        host.episode_bindings = registry
        home = ('scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination' if pilot else 'published_evidence_assessment')
        path = [('annotation', 'original-parent')]
        parts = home.split('.')
        for index in range(len(parts)):
            binding = registry.for_binding_path('/'.join(parts[:index + 1]))
            path.append((binding.roles[0], 'original-' + str(index)))
        path = tuple(path)
        publisher = registry.for_path(path)
        assignment = deepcopy(dict(original.assignment))
        if pilot:
            # Keep the original source and all requested scientific operands.
            # The page owner authenticates its existing assigned-source lineage.
            assignment['source_ref'] = arguments['selection']['source_ref']
        request = {'message': {'scope': dict(original.scope), 'episode_assignment': assignment}}
        context = replace(original, episode_id=module('method_loop.identities').EpisodeRef(original.run_id, path).episode_id, path=path, role=path[-1][0], assignment=assignment, request=request)
        store.db.execute('CREATE TABLE runtime_runs(run_id TEXT,settings TEXT)')
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
        store.db.execute('INSERT INTO runtime_runs VALUES(?,?)', (context.run_id, json.dumps({'episode_bindings': [binding.as_record() for binding in bindings]})))
        store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)', (context.run_id, context.episode_id, json.dumps(path), json.dumps(request)))
        repository = getattr(publisher, '_' + family + '_repository')()
        outcome = repository.populate(context, arguments, 'original-scientific-population')
        assert outcome['status'] == 'completed'
        ref = outcome['result']['sheet_ref']
        saved = repository.read(ref)
        receipt = saved['original_implementation']
        expected_version = ('concentration_window_original_implementation_v2' if family == 'concentration_window' else 'measurement_comparison_original_implementation_v4')
        assert receipt['version'] == expected_version
        assert receipt['bound_descriptor'] == publisher.as_record()
        assert receipt['publisher_binding']['episode_id'] == context.episode_id
        assert receipt['publisher_binding']['descriptor'] == receipt['bound_descriptor']
        implementation = import_module(type(repository).__module__)
        assert all(value == hashlib.sha256(implementation.source_file(name).read_bytes()).hexdigest() for name, value in receipt['files'].items())
        source = store.get(ref)
        source_bytes = store.get_artifact(source['artifact_ref'])
        request_bytes = store.get_artifact(source['request_ref'])
        assert repository.populate(context, arguments, 'original-scientific-population') == outcome
        repository_class = type(repository)
        store.db.commit()
    finally:
        store.close()
    with module('state').Store(directory) as cold:
        reader = repository_class(cold, context.run_id)
        before = cold.db.total_changes
        assert reader.read(ref) == saved
        assert cold.get_artifact(source['artifact_ref']) == source_bytes
        assert cold.get_artifact(source['request_ref']) == request_bytes
        assert cold.db.total_changes == before
        # A new content-addressed source with a different owner header cannot
        # replace the operation's exact original publication.
        altered = json.loads(source_bytes)
        altered['original_implementation']['publisher_binding']['path'][-1][1] = 'substituted-publisher'
        artifact = cold.artifact(json.dumps(altered, sort_keys=True, separators=(',', ':')).encode())
        record = {key: value for key, value in source.items() if key not in ('id', 'origin', 'record_type')}
        record.update(artifact_ref=artifact, text_ref=artifact)
        substituted = cold.put('source', record, origin=source['origin'])['id']
        with pytest.raises(module('domain').ContractError):
            reader.read(substituted)
        assert reader.read(ref) == saved
