"""Actual direct file port over engineered retained publication SQL identities.

No native producer or scientific outcome is asserted. These controls cover the
original private-only material check separately from context-specific grants.
"""
from importlib import import_module
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('axis', ['a101', 'a105', 'a106', 'a108'])
@pytest.mark.parametrize('provider,version,operation,origin,auxiliary_public', [
    ('analyze_itc_binding_thermodynamics', 'ordinary_itc_result_v1', 'analyze_itc_binding_thermodynamics', 'tool', True),
    ('liftover_coordinates', 'ordinary_liftover_result_v1', 'liftover_coordinates', 'tool', False),
    ('alphafold', None, 'public.alphafold.file', 'external', False),
])
def test_original_material_port_keeps_private_publication_files_closed(
        tmp_path, axis, provider, version, operation, origin, auxiliary_public):
    def module(name):
        return import_module('gene_annotation_episode.episodic_workflow.root.' + axis + '.' + name)
    with module('state').Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        module('tools').ToolRegistry(store, clients=SimpleNamespace())
        raw = store.artifact('engineered retained native metadata', 'application/json')
        control = store.artifact('engineered private request', 'application/json')
        auxiliary = store.artifact('engineered retained auxiliary', 'application/json')
        source = store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': raw, 'text_ref': None, 'request_ref': control, 'version': version,
            'retrieved_at': None, 'auxiliary_artifact_refs': [auxiliary]}, origin=origin)
        key = 'engineered-material-publication:' + provider
        op = module('domain').identity('operation', {'key': key, 'name': operation})
        result = {'status': 'completed', 'operation_ref': op, 'record_refs': [source['id']],
                  'result': {'source_ref': source['id']}, 'feedback': None}
        canonical = module('domain').canonical
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
            (key, op, operation, '{}', canonical(scope), canonical(result)))
        material = module('materials')
        changes = store.db.total_changes
        # Private-only means ordinary raw bytes are left to their existing
        # context-aware authority. Request controls are never made public.
        assert material.artifact_path(store, raw).read_bytes() == b'engineered retained native metadata'
        with pytest.raises(module('domain').ContractError, match='molecular_private_artifact_not_readable'):
            material.artifact_path(store, control)
        if auxiliary_public:
            assert material.artifact_path(store, auxiliary).read_bytes() == b'engineered retained auxiliary'
        else:
            with pytest.raises(module('domain').ContractError, match='molecular_private_artifact_not_readable'):
                material.artifact_path(store, auxiliary)
        assert store.db.total_changes == changes
