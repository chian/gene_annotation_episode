"""Recover receipt after JSON serializer failure; no rerunning any operation.

All four original selected writers completed and closed before the serializer
failed. Contexts below are explicit verification scopes, not recreated runtime
messages; original request, signature, operation and admission remain in SQLite.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.state import Store
from generate_legacy_001 import LiteratureBindingModelRepository, LiteratureTransportRepository, binding_model_cells_schema, transport_response_cells_schema, context_dict

HERE = Path(__file__).resolve().parent
receipt = {}
for path in sorted((HERE / 'legacy').iterdir()):
    binding = path.name.startswith('binding')
    run_id = 'synthetic-model-run' if binding else 'synthetic-transport-run'
    cls = LiteratureBindingModelRepository if binding else LiteratureTransportRepository
    store = Store(path)
    repo = cls(store, run_id)
    row = store.db.execute(f'SELECT * FROM {repo.operations_table}').fetchone()
    outcome = json.loads(row['outcome'])
    args = json.loads(row['signature'])['arguments']
    reference = outcome['result']['sheet_ref']
    permitted = tuple(r['id'] for r in store.list('source'))
    role = 'literature_table' if binding else 'literature'
    owner = BindingContext(run_id, row['episode_id'], role, ((role, 'fixture'),),
                           store.validate_scope(), {}, {}, permitted)
    receiver = replace(owner, episode_id='synthetic-receiver')
    projected = repo.project_cells([reference], permitted_record_refs=permitted)
    received = repo.received_cells(receiver)
    assert received == projected[:2]
    receipt[path.name] = {'kind': 'binding' if binding else 'transport', 'run_id': run_id,
        'context': context_dict(owner), 'receiver': context_dict(receiver), 'arguments': args,
        'outcome': outcome, 'payload': repo.read(reference), 'projected': projected,
        'received_subset': received,
        'schema': binding_model_cells_schema() if binding else transport_response_cells_schema(),
        'context_provenance': 'verification-only context; original selected request/signature/outcome retained in SQLite'}
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    store.close()
(HERE / 'LEGACY_RECEIPT_001.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
hashes = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in sorted((HERE / 'legacy').rglob('*')) if path.is_file()}
(HERE / 'LEGACY_HASHES_001.json').write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n')
