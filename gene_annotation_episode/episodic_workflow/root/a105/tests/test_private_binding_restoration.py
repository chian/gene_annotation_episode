"""Reopen literal current private descriptors using authenticated saved libraries."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from .test_private_literature_bindings import AXIS, HOMES


def frozen_scientific_binding(tmp_path):
    module = import_module(AXIS + '.scientific_process_library')
    tool_module = import_module(AXIS + '.scientific_tool_library')
    source = tmp_path / 'fixture-instruction-source'
    source.mkdir()
    (source / 'index.json').write_text(json.dumps({'format': module.SOURCE_FORMAT,
        'status': 'Explicit empty engineering fixture; no scientific options asserted.',
        'slots': [{'slot': slot, 'catalog': slot + '.json', 'count': 0}
                  for slot in module.SLOTS], 'entries': []}))
    (source / 'option_sources.json').write_text(json.dumps({
        'meaning': 'Engineering restoration fixture only.', 'rows': []}))
    run = tmp_path / 'saved-run'
    library = module.ScientificProcessLibrary.freeze(run / 'scientific-process-library', source=source)
    tools = tool_module.ScientificToolLibrary.freeze(run / 'scientific-tool-library', catalog=[])
    cls = import_module(AXIS + '.scientific_process.episode').ScientificProcessEpisode
    return cls(SimpleNamespace(), library=library, tool_library=tools,
               child_roles=('scientific_process', 'literature')), run


def test_reopen_scientific_uses_actual_frozen_library_identity(tmp_path):
    binding, directory = frozen_scientific_binding(tmp_path)
    saved = binding.as_record()
    composition = import_module(AXIS + '.episode_composition')
    restored = composition.reopen_scientific_binding(SimpleNamespace(), descriptor=saved, directory=directory)
    assert type(restored) is type(binding)
    assert restored.as_record() == saved
    assert restored.binding_path == 'scientific_process'


def test_reopen_rejects_changed_frozen_library(tmp_path):
    binding, directory = frozen_scientific_binding(tmp_path)
    saved = binding.as_record()
    path = directory / 'scientific-tool-library/index.json'
    path.write_text(path.read_text().replace(import_module(AXIS + '.scientific_tool_library').INFO_VERSION, 'forged_library'))
    failure = import_module('gene_annotation_episode.episodic_workflow.root.method_loop.durable').DurableExecutionError
    composition = import_module(AXIS + '.episode_composition')
    with pytest.raises(failure):
        composition.reopen_scientific_binding(SimpleNamespace(), descriptor=saved, directory=directory)


@pytest.mark.parametrize('configuration', [{}, {'rate_population': True, 'assay_grading_population': True}])
def test_reopen_both_literal_literature_families_preserves_parent_identity(configuration):
    services = SimpleNamespace()
    originals = [import_module(AXIS + '.' + home + '.episode').LiteratureEpisode(services, **configuration)
                 for home in HOMES]
    saved = [binding.as_record() for binding in originals]
    store = object()
    composition = import_module(AXIS + '.episode_composition').compose_episode_bindings(
        services, store=store, journal=SimpleNamespace(store=store, run_id='original-run'),
        execution_backend=None, descriptors=saved, job_episodes=None, resource_estimator=None,
        role_credit_bindings={})
    assert [type(binding) for binding in composition.bindings] == [type(binding) for binding in originals]
    assert [binding.as_record() for binding in composition.bindings] == saved
    registry = import_module(AXIS + '.episode_bindings').EpisodeBindingRegistry(composition.bindings)
    for original in originals:
        assert type(registry.for_binding_path(original.binding_path)) is type(original)
    with pytest.raises(LookupError):
        registry.for_role('literature_page')
    assert len({binding.binding_path for binding in composition.bindings}) == 14


def test_reopen_rejects_unregistered_private_path():
    module = import_module(AXIS + '.episode_composition')
    failure = import_module('gene_annotation_episode.episodic_workflow.root.method_loop.durable').DurableExecutionError
    binding = import_module(AXIS + '.' + HOMES[0] + '.episode').LiteratureEpisode(SimpleNamespace())
    saved = deepcopy(binding.as_record())
    saved['binding_id'] = '../other_parent/episode'
    store = object()
    with pytest.raises(failure):
        module.compose_episode_bindings(SimpleNamespace(), store=store,
            journal=SimpleNamespace(store=store, run_id='original-run'), execution_backend=None,
            descriptors=[saved], job_episodes=None, resource_estimator=None, role_credit_bindings={})
