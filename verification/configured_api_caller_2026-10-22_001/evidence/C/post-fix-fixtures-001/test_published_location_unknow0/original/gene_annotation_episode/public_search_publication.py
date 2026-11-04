"""No-network publication of exact selected HMMER result captures."""
from __future__ import annotations
import hashlib
import json

from .domain import ContractError, canonical


class PublicSearchResultPublisher:
    def __init__(self, store, tool_registry, *, operations):
        if tool_registry.store is not store or operations.store is not store:
            raise ContractError('unavailable_binding')
        self.store, self.tools, self.operations = store, tool_registry, operations
        with store.transaction():
            store.db.execute('CREATE TABLE IF NOT EXISTS public_search_publications(operation_key TEXT PRIMARY KEY, signature TEXT NOT NULL, data TEXT NOT NULL)')

    def publish(self, receipt_ref: str, *, scope: dict, operation_key: str) -> dict:
        signature = canonical(dict(receipt_ref=receipt_ref, scope=scope,
                                   registry=self.operations.registry))
        with self.store.transaction():
            prior = self.store.db.execute('SELECT signature,data FROM public_search_publications WHERE operation_key=?', (operation_key,)).fetchone()
            if prior:
                if prior['signature'] != signature:
                    raise ContractError('operation_conflict')
                return json.loads(prior['data'])
            receipt = self.operations.read_operation(receipt_ref)
            if receipt['operation'] != 'result' or receipt['outcome'] != 'completed' or not receipt['result_cached']:
                raise ContractError('public_search_result_not_publishable')
            snapshot = self.operations.read_snapshot(receipt_ref)
            request = snapshot.request
            order = self.operations.open_order(receipt['job_ref'])
            original = self.operations.inspect(receipt['job_ref'])['request']
            if (snapshot.transport.get('job_ref') != receipt['job_ref'] or
                    any(request.get(key) != value for key, value in original.items()) or
                    hashlib.sha256(canonical(original).encode()).hexdigest() != receipt['request_sha256'] or
                    receipt['request_sha256'] != order['request_sha256']):
                raise ContractError('identity_conflict')
            page, size = request['page'], request['page_size']
            if type(page) is not int or page < 1 or type(size) is not int or size < 1:
                raise ContractError('invalid_public_search_page_selector')
            imported = self.tools.publish_hmmer_snapshot(snapshot, scope=scope)
            rows = [dict(version='api_search_result_publication_row_v1',
                registry_ref=receipt['registry_ref'], job_ref=receipt['job_ref'],
                request_sha256=receipt['request_sha256'], publication_operation_key=operation_key,
                acquisition_receipt_ref=receipt_ref, source_ref=imported['source_ref'],
                subject_ref=request['subject_ref'], provider='hmmer', page=page, page_size=size, **row)
                for row in imported['publication_rows']]
            selector = dict(version='public_search_result_selector_v1', provider='hmmer',
                            first_page=page, last_page=page, page_size=size)
            body = dict(version='api_search_result_publication_v1', operation_key=operation_key,
                registry_ref=receipt['registry_ref'], job_ref=receipt['job_ref'],
                request_sha256=receipt['request_sha256'], acquisition_receipt_ref=receipt_ref,
                source_ref=imported['source_ref'], subject_ref=request['subject_ref'], selector=selector,
                publication_rows=rows, projection_failures=imported['projection_failures'],
                page=page, page_size=size, page_count=imported['page_count'])
            source = self.store.put('source', dict(provider='episode.api_search_result_publication', accession=None,
                uri=None, artifact_ref=self.store.artifact(canonical(body), 'application/json'), text_ref=None,
                request_ref=None, version='api_search_result_publication_v1', retrieved_at=receipt['observed_at'],
                parent_source_refs=[imported['source_ref']]), origin='tool')
            result = dict(result=dict(publication_ref=source['id'], source_ref=imported['source_ref'],
                acquisition_receipt_ref=receipt_ref, page=page, page_size=size,
                page_count=imported['page_count'], publication_rows=rows,
                projection_failures=imported['projection_failures']),
                record_refs=list(dict.fromkeys([*imported['record_refs'], source['id']])))
            self.store.db.execute('INSERT INTO public_search_publications VALUES(?,?,?)',
                (operation_key, signature, canonical(result)))
            return result
