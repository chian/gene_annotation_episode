"""A107 original molecular deployment contracts; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from __future__ import annotations
from pathlib import Path
import re
DEPLOYMENT_VERSION = 'molecular_sequence_deployment_v1'
SOURCE_SHA256 = 'de47e1dc0013cd6e8d2941d8945835d585f938e486a69bb2ba3333403a3efba4'
GLYCO_SOURCE_SHA256 = 'ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2'
_LIBRARIES = (('pandas', 'pandas'), ('requests', 'requests'), ('Bio', 'biopython'), ('bs4', 'beautifulsoup4'), ('soupsieve', 'soupsieve'), ('typing_extensions', 'typing_extensions'))
_SOURCE_PROFILES = {'molecular': {'sha256': SOURCE_SHA256, 'libraries': _LIBRARIES}, 'glyco': {'sha256': GLYCO_SOURCE_SHA256, 'libraries': ()}}

class _BoundaryError(ValueError):

    def __init__(self, code, path='', **details):
        super().__init__(code + (': ' + path if path else ''))
        self.code, self.path, self.details = (code, path, details)

def _fail(code, path='', **details):
    raise _BoundaryError('molecular_sequence_' + code, path, **details)

def _closed(value, fields, path):
    if type(value) is not dict or set(value) != set(fields):
        _fail('closed_fields_required', path, required_fields=sorted(fields))

def _path(value, path):
    if type(value) is not str or not value or (not Path(value).is_absolute()):
        _fail('absolute_path_required', path)
    return Path(value)

def _pin_schema(value, path):
    _closed(value, ('path', 'sha256', 'size_bytes'), path)
    _path(value['path'], path + '/path')
    if type(value['sha256']) is not str or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None or type(value['size_bytes']) is not int or (value['size_bytes'] < 0):
        _fail('file_pin_required', path)

def _deployment(value, *, version=DEPLOYMENT_VERSION, source_sha256=SOURCE_SHA256):
    _closed(value, ('version', 'runtime', 'module', 'import_roots', 'software_files_ref', 'software_files_file'), '/deployment')
    if value['version'] != version:
        _fail('deployment_version_required', '/deployment/version')
    _closed(value['runtime'], ('executable', 'home'), '/deployment/runtime')
    _pin_schema(value['runtime']['executable'], '/deployment/runtime/executable')
    _path(value['runtime']['home'], '/deployment/runtime/home')
    _pin_schema(value['module'], '/deployment/module')
    _pin_schema(value['software_files_file'], '/deployment/software_files_file')
    reference = value['software_files_ref']
    if type(reference) is not str or re.fullmatch('artifact_[0-9a-f]{64}', reference) is None or reference != 'artifact_' + value['software_files_file']['sha256']:
        _fail('manifest_artifact_identity_mismatch', '/deployment/software_files_ref')
    roots = value['import_roots']
    if type(roots) is not list or not roots:
        _fail('ordered_import_roots_required', '/deployment/import_roots')
    for i, root in enumerate(roots):
        _path(root, '/deployment/import_roots/' + str(i))
    if len(roots) != len(set(roots)):
        _fail('ordered_import_roots_required', '/deployment/import_roots')
    if value['module']['sha256'] != source_sha256:
        _fail('original_source_pin_required', '/deployment/module/sha256')
