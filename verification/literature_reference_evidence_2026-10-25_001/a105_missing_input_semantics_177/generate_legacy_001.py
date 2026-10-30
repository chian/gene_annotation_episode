"""Before-change writer receipt; entirely synthetic, no papers or model calls.

Run only against the retained original v1 production bytes. The resulting state
is authentic selected-operation output, never fabricated by changing versions.
"""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path

from gene_annotation_episode.communication import plain
from gene_annotation_episode.literature_binding_model_storage import LiteratureBindingModelRepository, binding_model_cells_schema
from gene_annotation_episode.literature_transport_storage import LiteratureTransportRepository, transport_response_cells_schema

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def context_dict(context):
    return {name: plain(getattr(context, name)) for name in context.__dataclass_fields__}

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tests' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    transport = load('test_literature_transport_storage')
    binding = load('test_literature_binding_model_storage')
    receipt = {}
    for name, kind, supplied in [('transport_missing', 'transport', False),
                                  ('transport_known', 'transport', True),
                                  ('binding_missing', 'binding', False),
                                  ('binding_known', 'binding', True)]:
        path = HERE / 'legacy' / name
        if path.exists():
            raise RuntimeError('refuse to replace an authentic legacy store')
        if kind == 'transport':
            store, context, args, _ = transport.fixture(path, km=supplied, covariance=supplied)
            repo = LiteratureTransportRepository(store, context.run_id)
            schema = transport_response_cells_schema()
            if not supplied:
                args.update(primitives={'substrate_test': None, 'substrate_reference': None},
                    curve_contexts={key: None for key in ('substrate_test', 'substrate_reference', 'km')},
                    observation_model='unknown', model_witnesses=[])
        else:
            store, context, args, _ = binding.fixture(path, model=supplied)
            repo = LiteratureBindingModelRepository(store, context.run_id)
            schema = binding_model_cells_schema()
        assert repo.record_version.endswith('_v1')
        outcome = repo.populate(context, args, 'original-v1-selected')
        reference = outcome['result']['sheet_ref']
        projected = repo.project_cells([reference], permitted_record_refs=[reference])
        owner = replace(context, received_record_refs=(*context.received_record_refs, reference))
        subset = projected[:2]
        receiver = replace(owner, episode_id='synthetic-receiver')
        repo.receive_cells(receiver, subset, 'original-v1-receive')
        assert repo.fact_cells(receiver, [reference], components=repo.components) == subset
        receipt[name] = {'kind': kind, 'run_id': context.run_id, 'context': context_dict(owner),
            'receiver': context_dict(receiver), 'arguments': args, 'outcome': outcome,
            'payload': repo.read(reference), 'projected': projected, 'received_subset': subset,
            'schema': schema}
        store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        store.close()
    (HERE / 'LEGACY_RECEIPT_001.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    hashes = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted((HERE / 'legacy').rglob('*')) if path.is_file()}
    (HERE / 'LEGACY_HASHES_001.json').write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n')

if __name__ == '__main__':
    main()
