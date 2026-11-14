"""Retained original unavailable function and current root policy are distinct.

The historical function bytes are promoted with the reusable tests. Only that
original unconditional failure is executed in an isolated namespace; it is not
represented as the installed factory or a saved-tree reconstruction.
"""
import hashlib
from pathlib import Path

HISTORICAL_FUNCTION = "def create_evidence_root_workflow(store, tools, provider, directory, run_id, controller_factory,\n                                  *, initial_known_record_refs, axes=AXES, **options):\n    raise ValueError('combined_root_private_runtime_binding_unavailable')\n"
HISTORICAL_MODULE_SHA='159195372aad1705543441202ba4ec91cb50fcee2fd70582f7ba72bf5b46f93a'
CURRENT_MODULE_SHA='58b5e997b684b1abc213496f2c32eee0719e9da0fb874daa13511cc06db955c1'

def root_trace(v):
    from .resource_task_checks import capture
    from gene_annotation_episode.episodic_workflow.root import evidence_root
    assert hashlib.sha256(Path(evidence_root.__file__).read_bytes()).hexdigest()==CURRENT_MODULE_SHA
    namespace={'AXES':()}
    exec(compile(HISTORICAL_FUNCTION,'<retained-original-unavailable-factory>','exec'),namespace)
    historical=capture(lambda:namespace['create_evidence_root_workflow'](
        v.store,v.tools,None,v.output/'historical-root-not-created',v.journal.run_id,None,
        initial_known_record_refs=[]))
    assert historical=={'status':'raised','type':'builtins.ValueError','message':'combined_root_private_runtime_binding_unavailable'}
    current=capture(lambda:evidence_root.create_evidence_root_workflow(
        v.store,v.tools,None,v.output/'current-root-not-created',v.journal.run_id,None,
        initial_known_record_refs=[],project_credit=object()))
    assert current=={'status':'raised','type':'builtins.ValueError','message':'evidence_root_numeric_binding_is_host_owned'}
    assert not (v.output/'historical-root-not-created').exists()
    assert not (v.output/'current-root-not-created').exists()
    return {'historical_unavailable_function':historical,'historical_module_sha256':HISTORICAL_MODULE_SHA,
        'current_root_policy':current,'current_module_sha256':CURRENT_MODULE_SHA,
        'current_default_constructor_executed':False,'current_saved_tree_restoration_claim':False}
