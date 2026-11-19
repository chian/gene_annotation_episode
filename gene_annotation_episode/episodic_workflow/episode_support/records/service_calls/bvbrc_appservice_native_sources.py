"""The retained native source of one BV-BRC AppService response in the run's shared Store.

Each response an AppService operation receives (and the partial response an ``AcquisitionError`` carries) is
retained as one ``source`` record of provider ``bvbrc_appservice.<operation>``:

- ``artifact_ref`` holds the received response bytes unchanged;
- ``request_ref`` holds the native-source record (version ``bvbrc_appservice_native_source_v1``), the canonical
  UTF-8 JSON ``{'version', 'origin', 'snapshot', 'prepared'}``: ``origin`` is the operation's ``ReceiptOrigin``,
  ``prepared`` the ``PreparedOperation`` that was issued (its native operands carry the exact JSON-RPC call), and
  ``snapshot`` the service, URL, native request, retrieval time, media type, transport facts and the
  ``content_ref`` of the retained response bytes.

A submission's native-source record is what the proteome bundle reader
(``bvbrc_proteome_bundle_resolution._submitted_record``) checks against the original task of its handoff before the
submitted parameters are used. This module makes no request and no scientific calculation.
"""
from __future__ import annotations

import json

NATIVE_PROVIDER = 'bvbrc_appservice'
NATIVE_VERSION = 'bvbrc_appservice_native_source_v1'
OPERATION_PREFIX = 'api.bvbrc_appservice.'


def canonical(value):
    """The canonical text the native-source record is retained and read back as."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def native_source_record(snapshot, *, origin, prepared, content_ref):
    """The native-source record of one received response of the prepared operation ``origin`` names."""
    operation = prepared['operation']
    if origin['name'] != operation or origin['arguments_sha256'] != prepared['arguments_sha256']:
        raise ValueError('appservice_native_source_origin_conflict')
    return {'version': NATIVE_VERSION, 'origin': origin, 'prepared': prepared, 'snapshot': {
        'service': snapshot.service, 'url': snapshot.url, 'request': snapshot.request,
        'retrieved_at': snapshot.retrieved_at, 'content_ref': content_ref, 'media_type': snapshot.media_type,
        'transport': snapshot.transport}}


def retain_native_source(store, snapshot, *, origin, prepared):
    """Retain one received native AppService response as a source record; return its snapshot content binding."""
    operation = prepared['operation']
    if not operation.startswith(OPERATION_PREFIX):
        raise ValueError('appservice_native_source_operation_not_appservice:' + operation)
    artifact = store.artifact(snapshot.content, snapshot.media_type)
    record = native_source_record(snapshot, origin=origin, prepared=prepared, content_ref=artifact)
    request = store.artifact(canonical(record), 'application/json')
    source = store.put('source', {
        'provider': NATIVE_PROVIDER + '.' + operation.removeprefix(OPERATION_PREFIX), 'accession': None,
        'uri': snapshot.url, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': request,
        'version': NATIVE_VERSION, 'retrieved_at': snapshot.retrieved_at}, origin='external')['id']
    return {'source_ref': source, 'artifact_field': 'artifact_ref', 'artifact_ref': artifact,
            'sha256': snapshot.sha256, 'byte_count': len(snapshot.content)}


__all__ = ['NATIVE_PROVIDER', 'NATIVE_VERSION', 'OPERATION_PREFIX', 'canonical', 'native_source_record',
           'retain_native_source']
