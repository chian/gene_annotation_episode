"""Original received FBA witness identity checks; no admission or scientific assessment."""
from ..native_file_capture import NativeFileCaptureError, _metadata


def _require(condition, code, pointer=''):
    if not condition:
        raise ValueError('flux_balance_input_' + code + (':' + pointer if pointer else ''))


def _check_version(store, record, version, pointer):
    _require(record.get('id') == version['reference'], 'record_identity_conflict', pointer)
    _require(version['version'] is None or str(record.get('revision')) == version['version'],
             'version_conflict', pointer)
    if version['content_sha256'] is not None:
        reference = (record['id'] if record['record_type'] == 'artifact'
                     else record.get('sequence_ref', record.get('artifact_ref')))
        try:
            actual = _metadata(store, reference)
        except NativeFileCaptureError as error:
            raise ValueError('flux_balance_input_version_conflict:' + pointer) from error
        _require(actual['sha256'] == version['content_sha256'], 'version_conflict', pointer)
