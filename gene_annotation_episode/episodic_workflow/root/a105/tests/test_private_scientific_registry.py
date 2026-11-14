"""Actual family registration preserves scientific recursion and parent identity."""
from importlib import import_module
from types import SimpleNamespace

import pytest

from .test_private_binding_restoration import frozen_scientific_binding
from .test_private_literature_bindings import AXIS, HOMES


@pytest.mark.parametrize('restored', [False, True])
def test_actual_scientific_recursion_and_two_literature_parents(tmp_path, restored):
    scientific, directory = frozen_scientific_binding(tmp_path)
    bindings = [scientific, *[
        import_module(AXIS + '.' + home + '.episode').LiteratureEpisode(SimpleNamespace())
        for home in HOMES]]
    if restored:
        store = object()
        composition = import_module(AXIS + '.episode_composition').compose_episode_bindings(
            SimpleNamespace(), store=store,
            journal=SimpleNamespace(store=store, run_id='saved-family'),
            execution_backend=None, descriptors=[binding.as_record() for binding in bindings],
            job_episodes=None, resource_estimator=None, role_credit_bindings={}, directory=directory)
        bindings = list(composition.bindings)
    registry = import_module(AXIS + '.episode_bindings').EpisodeBindingRegistry(bindings)
    scientific = registry.for_binding_path('scientific_process')
    annotation_path = (('annotation', 'saved-annotation'),)
    scientific_path = (*annotation_path, ('scientific_process', 'saved-scientific'))
    assert registry.for_child(annotation_path, 'scientific_process') is scientific
    assert registry.for_child(scientific_path, 'scientific_process') is scientific
    recursive_path = (*scientific_path, ('scientific_process', 'saved-recursion'))
    assert registry.for_path(recursive_path) is scientific
    root_literature = registry.for_child(annotation_path, 'literature')
    scientific_literature = registry.for_child(recursive_path, 'literature')
    assert root_literature.binding_path == 'published_evidence_assessment'
    assert scientific_literature.binding_path == 'scientific_process/published_evidence_assessment'
    assert type(root_literature) is not type(scientific_literature)
    assert registry.for_path((*recursive_path, ('literature', 'saved-child'))) is scientific_literature
