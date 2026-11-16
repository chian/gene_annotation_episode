"""A107 homer binding metadata."""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from pathlib import Path, PurePosixPath
import re
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a107.native_flux_balance_storage import decode_json
OPERATION = 'find_enriched_motifs_with_homer'
VARIANT = 'supplied_fasta_explicit_background_old_v1'
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}
PATCH_NAMES = ('findMotifsGenome.pl', 'findKnownMotifs.pl', 'compareMotifs.pl', 'HomerConfig.pm')
_SHA = re.compile('[0-9a-f]{64}')

def _require(condition, code):
    if not condition:
        raise ValueError('ordinary_homer_' + code)

def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)

def _copy(value):
    return decode_json(canonical(value).encode('utf-8'))

def _text(value):
    return type(value) is str and bool(value) and (not any((ord(c) < 32 for c in value)))

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum

def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None

def _path(value, *, absolute=True):
    _require(_text(value) and '\\' not in value, 'path_invalid')
    path = PurePosixPath(value)
    _require(str(path) == value and value not in ('.', '/') and ('..' not in path.parts) and (path.is_absolute() == absolute), 'path_invalid')
    return Path(value)

def _deployment_member(value):
    """A copied member name is distinct from an interpolated command path.

    The selected ELF closure contains the literal libstdc++ names. These
    members are opened/copied through confined file descriptors, not inserted
    into shell commands. Keep command/workspace/output path policy unchanged.
    """
    path = _path(value, absolute=False)
    _require(re.fullmatch('[A-Za-z0-9_./+\\-]+', value) is not None, 'deployment_member_path_invalid')
    return path

def _pin(value):
    _closed(value, ('path', 'sha256', 'size_bytes'), 'file_pin_invalid')
    _path(value['path'])
    _require(_sha(value['sha256']) and _integer(value['size_bytes']), 'file_pin_invalid')
    return value

def validate_homer_software(value):
    value = _copy(value)
    _closed(value, ('version', 'python', 'python_home', 'python_version', 'import_roots', 'software_files_file'), 'software_fields_invalid')
    _require(value['version'] == 'homer_native_software_v1' and _text(value['python_version']), 'software_invalid')
    _pin(value['python'])
    _pin(value['software_files_file'])
    _path(value['python_home'])
    roots = value['import_roots']
    _require(type(roots) is list and bool(roots) and (len(set(roots)) == len(roots)), 'import_roots_invalid')
    for path in roots:
        _path(path)
    return value

def _deployment(value):
    _closed(value, ('version', 'root', 'files', 'system_files', 'corrections'), 'deployment_fields_invalid')
    _require(value['version'] == 'homer_native_deployment_v1', 'deployment_version_invalid')
    _path(value['root'])
    _require(type(value['files']) is list and bool(value['files']) and (type(value['system_files']) is list), 'deployment_files_invalid')
    paths = []
    for row in value['files']:
        _closed(row, ('relative_path', 'sha256', 'size_bytes', 'mode'), 'deployment_file_invalid')
        path = _deployment_member(row['relative_path'])
        _require(path.parts[0] in ('deployment', 'selected_runtime') and _sha(row['sha256']) and _integer(row['size_bytes']) and _integer(row['mode']) and (row['mode'] <= 511), 'deployment_file_invalid')
        paths.append(str(path))
    _require(len(set(paths)) == len(paths), 'deployment_path_duplicate')
    required = {'deployment/bin/' + n for n in (*PATCH_NAMES, 'homerTools', 'homer2', 'mergePeaks', 'HomerSVGLogo.pm')}
    required.update(('deployment/config.txt', 'selected_runtime/perl/bin/perl', 'selected_runtime/elf/ld-linux-x86-64.so.2'))
    _require(required <= set(paths), 'deployment_required_file_missing')
    for row in value['system_files']:
        _pin(row)
    _require(len({row['path'] for row in value['system_files']}) == len(value['system_files']), 'system_path_duplicate')
    _closed(value['corrections'], ('extractor_build_report', 'svg_repair_record'), 'correction_records_invalid')
    for row in value['corrections'].values():
        _pin(row)
    return value

def validate_homer_bindings(bindings):
    """Validate configured metadata only; never discover or select a binding."""
    bindings = _copy(bindings)
    _require(type(bindings) is list, 'bindings_invalid')
    for value in bindings:
        _closed(value, ('version', 'operation', 'variant', 'deployment', 'software', 'input_staging'), 'binding_fields_invalid')
        _require(value['version'] == 'homer_native_binding_v1' and value['operation'] == OPERATION and (value['variant'] == VARIANT), 'binding_variant_unsupported')
        _deployment(value['deployment'])
        validate_homer_software(value['software'])
        _closed(value['input_staging'], ('mode', 'max_total_bytes'), 'input_staging_invalid')
        _require(value['input_staging']['mode'] == 'verified_copy' and _integer(value['input_staging']['max_total_bytes']) and (value['input_staging']['max_total_bytes'] <= POLICY['scratch_bytes']), 'input_staging_invalid')
    return bindings
