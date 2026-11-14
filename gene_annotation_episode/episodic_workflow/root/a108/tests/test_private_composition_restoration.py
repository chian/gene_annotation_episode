"""Reopen actual private descriptors and frozen libraries without running science."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS,HOMES
from gene_annotation_episode.episodic_workflow.root.a108.episode_composition import compose_episode_bindings,reopen_scientific_binding
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionError
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_library import ScientificProcessLibrary,SOURCE_FORMAT
from gene_annotation_episode.episodic_workflow.root.a108.scientific_tool_library import ScientificToolLibrary


def compose(descriptors):
    store=object()
    return compose_episode_bindings(SimpleNamespace(),store=store,journal=SimpleNamespace(store=store,run_id='saved-run'),
        execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})


def test_both_private_literature_families_reopen_exact_saved_paths():
    originals=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace()) for home in HOMES]
    descriptors=[binding.as_record() for binding in originals]
    reopened=compose(deepcopy(descriptors))
    assert [binding.as_record() for binding in reopened.bindings]==descriptors
    assert [type(binding) for binding in reopened.bindings]==[type(binding) for binding in originals]
    assert [binding.binding_path for binding in reopened.bindings]==[binding.binding_path for binding in originals]
    assert reopened.progress_provider is None and reopened.resource_capabilities==()


@pytest.mark.parametrize('changed',['implementation_sha256','binding_id'])
def test_private_reopen_rejects_changed_hash_or_unknown_factory(changed):
    descriptor=import_module(AXIS+'.'+HOMES[0]+'.episode').LiteratureEpisode(SimpleNamespace()).as_record()
    descriptor[changed]='0'*64 if changed=='implementation_sha256' else '../../foreign_factory'
    with pytest.raises(DurableExecutionError):compose([descriptor])


def frozen_binding(directory):
    source=directory/'source';source.mkdir()
    (source/'index.json').write_text(json.dumps({'format':SOURCE_FORMAT,'status':'Synthetic empty engineering fixture',
        'slots':[{'slot':slot,'catalog':slot+'.json','count':0} for slot in ('evidence_axis','thought_pattern')],
        'entries':[]}))
    (source/'option_sources.json').write_text(json.dumps({'meaning':'No scientific claims in this reconstruction fixture','rows':[]}))
    library=ScientificProcessLibrary.freeze(directory/'scientific-process-library',source=source)
    tools=ScientificToolLibrary.freeze(directory/'scientific-tool-library',catalog=[])
    return ScientificProcessEpisode(SimpleNamespace(),library=library,tool_library=tools,
        child_roles=('scientific_process','literature'))


def test_scientific_head_reopens_authenticated_frozen_libraries(tmp_path):
    binding=frozen_binding(tmp_path);descriptor=binding.as_record()
    reopened=reopen_scientific_binding(SimpleNamespace(),descriptor=deepcopy(descriptor),directory=tmp_path)
    assert type(reopened) is type(binding) and reopened.as_record()==descriptor
    assert reopened.library.directory==binding.library.directory
    assert reopened.tool_library.directory==binding.tool_library.directory


def test_scientific_head_rejects_changed_frozen_library_bytes(tmp_path):
    binding=frozen_binding(tmp_path);descriptor=binding.as_record()
    manifest=tmp_path/'scientific-tool-library/index.json';manifest.write_text(manifest.read_text()+' ')
    with pytest.raises(DurableExecutionError):
        reopen_scientific_binding(SimpleNamespace(),descriptor=descriptor,directory=tmp_path)
