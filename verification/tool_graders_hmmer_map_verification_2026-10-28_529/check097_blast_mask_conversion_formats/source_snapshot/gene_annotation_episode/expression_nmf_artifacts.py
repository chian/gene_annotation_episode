"""Explicit retained-file loading, separate from pure sheet population.

Each independent valid artifact survives missing or incompatible peers. Exact
manifest filenames, file byte identities, dimensions and factor axes must all
agree before factors become calculation operands. None of these checks grants
episode ownership; the results owner supplies expected_input_identity.
"""
from copy import deepcopy
from pathlib import Path

from .expression_nmf_common import FACTOR_SCHEMA, MODE, digest, identity, issue, require, unique_issues
from .expression_nmf_inputs import parse_expression_matrix
from .native_expression_nmf_contracts import ARTIFACT_FORMATS, ARTIFACT_NAMES
from .native_expression_nmf_storage import confined_file, decode_json, directory, read_json, regular


def load_expression_nmf_artifacts(manifest_path, *, expected_input_identity=None):
    path = Path(manifest_path).absolute()
    require(path.name == ARTIFACT_NAMES['manifest'], 'nmf_manifest_filename_required')
    root = directory(path.parent)
    failures, values, raw_files = [], {}, {}
    manifest = None
    try:
        manifest = read_json(confined_file(root, path.name))
        require(type(manifest) is dict and manifest.get('schema') == ARTIFACT_FORMATS['manifest']
            and manifest.get('mode') == MODE and manifest.get('sealed') is True
            and type(manifest.get('result')) is dict, 'invalid_nmf_manifest')
        rows = manifest['files']
        require(type(rows) is list and [r.get('role') for r in rows] == ['original_input', 'input_data', 'prepared_data', 'factors'],
            'invalid_nmf_manifest_files')
        for row in rows:
            role = row['role']
            require(row['relative_path'] == ARTIFACT_NAMES[role] and row['format'] == ARTIFACT_FORMATS[role]
                and row['state'] in ('present', 'absent'), 'invalid_nmf_manifest_file')
    except (OSError, ValueError, KeyError, TypeError):
        failures.append(issue('manifest_missing_or_malformed', 'artifact_loading', field='manifest'))
        manifest = None
        rows = []
    declarations = {r['role']: r for r in rows}
    for role in ('original_input', 'input_data', 'prepared_data', 'factors'):
        try:
            with regular(confined_file(root, ARTIFACT_NAMES[role])) as stream:
                raw = stream.read()
            declaration = declarations.get(role)
            if declaration is not None:
                require(declaration['state'] == 'present' and identity(raw) == {k: declaration[k] for k in ('sha256', 'size_bytes')},
                    'nmf_artifact_byte_identity_mismatch')
            elif role == 'factors':
                raise ValueError('unbound_nmf_factor_bytes')
            if role == 'original_input' and expected_input_identity is not None:
                require(identity(raw) == expected_input_identity, 'nmf_original_input_identity_mismatch')
            raw_files[role] = raw
            values[role] = raw if role == 'original_input' else decode_json(raw)
            if role != 'original_input':
                require(type(values[role]) is dict and values[role].get('schema') == ARTIFACT_FORMATS[role],
                    'nmf_artifact_schema_mismatch')
        except (OSError, ValueError, KeyError, TypeError) as error:
            values.pop(role, None)
            if declarations.get(role, {}).get('state') != 'absent' or role != 'factors':
                failures.append(issue('artifact_missing_or_incompatible', 'artifact_loading', field=role))
    inp = values.get('input_data', {})
    prep = values.get('prepared_data', {})
    native = deepcopy(manifest.get('result', {}) if manifest else {})
    native.update(W=None, H=None)
    if 'original_input' in values and inp:
        try:
            reparsed = parse_expression_matrix(values['original_input'], delimiter=inp['delimiter'], metadata=inp['metadata'])
            require(digest(reparsed) == digest(inp), 'nmf_input_bytes_parsed_data_conflict')
        except (ValueError, KeyError, TypeError):
            failures.append(issue('original_bytes_input_data_conflict', 'artifact_loading', field='input_data'))
    if expected_input_identity is not None and inp.get('input_identity') != expected_input_identity:
        failures.append(issue('expected_input_identity_mismatch', 'artifact_loading', field='input_data'))
    if manifest:
        if (manifest.get('input_identity') != inp.get('input_identity') or manifest.get('prepared_data_sha256') != digest(prep)
                or manifest.get('shape') != inp.get('shape') or manifest.get('axes') != native.get('axes')):
            failures.append(issue('manifest_operand_relation_mismatch', 'artifact_loading'))
        for role in ('original_input', 'input_data', 'prepared_data'):
            if declarations[role].get('shape') != inp.get('shape'):
                failures.append(issue('manifest_shape_mismatch', 'artifact_loading', field=role))
    factors = values.get('factors')
    if factors:
        try:
            require(factors.get('input_identity') == inp.get('input_identity') and factors.get('prepared_data_sha256') == digest(prep)
                and factors.get('axes') == native.get('axes'), 'nmf_factor_association_mismatch')
            G, S = inp['shape']
            K = native['parameters']['rank']
            require(declarations['factors'].get('shape') == {'W': [G, K], 'H': [K, S]}, 'nmf_factor_declared_shape_mismatch')
            native.update(W=deepcopy(factors.get('W')), H=deepcopy(factors.get('H')))
        except (ValueError, KeyError, TypeError):
            failures.append(issue('factor_association_mismatch', 'artifact_loading', field='factors'))
    native['failures'] = unique_issues(native.get('failures', []), failures)
    return {'input_data': inp, 'prepared_data': prep, 'native_result': native, 'manifest': manifest,
        'failures': failures, 'binding': 'expected_input_checked' if expected_input_identity is not None else 'unbound_component_inspection'}
