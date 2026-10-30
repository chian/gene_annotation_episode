"""One selected supplied-event parsing job; no scientific calculations.

The existing native lifecycle owns resource limits and process management.
Each complete parsed envelope is published before the final manifest, allowing
authenticated earlier sources to survive a later process/resource failure.
"""
from datetime import datetime, timezone
import errno
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys

from . import fluorescence_event_contracts as core
from .fluorescence_execution_common import canonical, digest, identity, require, same, unique, validate_failure
from .native_fluorescence_contracts import (OWNER_FILENAME, STARTED_FILENAME, fluorescence_environment,
    unavailable_fluorescence_input, validate_fluorescence_manifest, validate_fluorescence_parsed_batch,
    validate_fluorescence_run_plan, validate_fluorescence_software)
from .native_fluorescence_storage import (confined_file, directory, file_pin, immutable_bytes,
    immutable_json, read_json, regular)


def _now():
    return datetime.now(timezone.utc).isoformat()


def verify_fluorescence_software(software):
    """Authenticate the actual interpreter, imports and installed dependencies."""
    software = validate_fluorescence_software(software)
    require(str(Path(sys.executable).resolve()) == str(Path(software['python']['path']).resolve())
        and sys.version == software['python_version'] and Path(sys.prefix).resolve() == Path(software['python_home']).resolve(),
        'native_software_mismatch')
    pins = [software['python'], *software['implementation_files'], *software['runtime_files']]
    expected_paths = {Path(row['path']).resolve() for row in pins}
    for expected in pins:
        require(same(file_pin(expected['path']), expected), 'native_software_mismatch')
    for row in software['distributions']:
        distribution = importlib.metadata.distribution(row['name'])
        require(distribution.version == row['version'] and (distribution.requires or []) == row['requires'],
            'native_software_mismatch')
        # A source-loaded package without actual installed distribution files
        # cannot satisfy this closure. Bytecode caches are not runtime authority.
        require(distribution.files is not None, 'native_software_mismatch')
        for name in distribution.files:
            relative = Path(str(name))
            if '__pycache__' in relative.parts or relative.suffix == '.pyc':
                continue
            located = Path(distribution.locate_file(name)).resolve()
            require(located in expected_paths, 'native_software_mismatch')
    allowed = [Path(software['module_root']).resolve(), Path(software['python_home']).resolve(),
        *[Path(root).resolve() for root in software['dependency_roots']]]
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename)
        if getattr(getattr(module, '__spec__', None), 'origin', None) in ('built-in', 'frozen'):
            continue
        require(path.is_file(), 'native_software_mismatch')
        if path.suffix == '.pyc':
            try:
                path = Path(importlib.util.source_from_cache(str(path)))
            except ValueError:
                pass
        require(any(path.resolve().is_relative_to(root) for root in allowed)
            and path.resolve() in expected_paths, 'native_software_mismatch')


def _failure(code, stage, *, index=None, role=None):
    return validate_failure({'code': code, 'stage': stage, 'input_index': index, 'role': role})


def _retained_input(row, file, output):
    """Return (raw, failure code). Resource failures deliberately propagate."""
    try:
        with regular(row['path']) as stream:
            before = os.fstat(stream.fileno())
            # Read only the selected expected extent plus one mismatch byte.
            raw = stream.read(file['size_bytes'] + 1)
            after = os.fstat(stream.fileno())
    except OSError as error:
        if error.errno not in (errno.ENOENT, errno.EACCES, errno.EPERM, errno.ENOTDIR, errno.ELOOP):
            raise
        return None, 'input_file_unavailable'
    except ValueError as error:
        if str(error) not in ('fluorescence_non_directory_or_symlink', 'fluorescence_non_regular_file'):
            raise
        return None, 'input_file_unavailable'
    if ((before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino)
            != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino)
            or not same(identity(raw, format=file['format']), file)):
        return None, 'input_identity_mismatch'
    output.parent.mkdir(parents=True, exist_ok=True)
    immutable_bytes(output, raw)
    return raw, None


def _parse(raw, binding):
    request = {k: binding[k] for k in ('source', 'sample', 'channels', 'domain')}
    if binding['parser'] == 'csv':
        from .fluorescence_event_readers import parse_fluorescence_csv
        return parse_fluorescence_csv(raw, **request, format_spec=binding['format_spec'])
    if binding['parser'] == 'table_snapshot':
        from .fluorescence_event_readers import parse_fluorescence_table_snapshot
        return parse_fluorescence_table_snapshot(raw, **request)
    from .fluorescence_fcs_reader import parse_fluorescence_fcs
    return parse_fluorescence_fcs(raw, **request)


def run_fluorescence_driver(plan):
    """Run inside the already selected bounded subprocess; never launch work."""
    plan = validate_fluorescence_run_plan(plan)
    job = plan['requested_job']['native_fluorescence']
    attempt = directory(plan['attempt_directory'])
    attempt.mkdir(parents=True, exist_ok=True)
    require(not confined_file(attempt, STARTED_FILENAME).exists(), 'fluorescence_original_attempt_already_started')
    immutable_json(confined_file(attempt, OWNER_FILENAME), plan)
    immutable_json(confined_file(attempt, STARTED_FILENAME), {'plan': plan, 'started_at': _now()})
    environment = fluorescence_environment(job['software'], attempt_directory=str(attempt))
    # The existing native lifecycle explicitly confines these variables to its
    # monitored working directory before invoking any selected command.
    environment.update({name: str(Path(plan['identity']['execution_id']).parent) for name in ('TMPDIR', 'TMP', 'TEMP')})
    require(all(os.environ.get(k) == v for k, v in environment.items()), 'fluorescence_runtime_environment_mismatch')
    for name in ('tmp', 'cache'):
        directory(attempt / name).mkdir(exist_ok=True)
    verify_fluorescence_software(job['software'])
    outputs = {row['role']: row for row in plan['outputs']}
    failures, inputs, support = [], [], []
    v2 = job['version'] == 'native_fluorescence_job_v2'
    retained, event_records = {}, []

    def publish(role, value):
        raw = core.canonical(value) + b'\n'
        output = confined_file(attempt, outputs[role]['relative_path'])
        output.parent.mkdir(parents=True, exist_ok=True)
        immutable_bytes(output, raw)
        return identity(raw, format=outputs[role]['format'])

    for i, binding in enumerate(job['inputs']):
        original = binding['source']['file']
        role = f'event_input:{i}'
        raw, failure = _retained_input(binding, original, confined_file(attempt, outputs[role]['relative_path']))
        if v2 and raw is not None:
            retained[canonical(original)] = raw
        if failure is not None:
            failures.append(_failure(failure, 'input', index=i, role=role))
            parsed = unavailable_fluorescence_input(binding, code='retained_artifact_mismatch'
                if failure == 'input_identity_mismatch' else 'source_unavailable')
        else:
            try:
                parsed = _parse(raw, binding)
            except core.FluorescenceContractError:
                # A native header may reveal an incompatible caller binding.
                # Preserve other inputs and the actual original bytes.
                failures.append(_failure('parsed_batch_invalid', 'input', index=i, role=f'event_batch:{i}'))
                parsed = unavailable_fluorescence_input(binding, code='source_unavailable')
        verify_fluorescence_software(job['software'])
        batch = validate_fluorescence_parsed_batch({'version': 'fluorescence_parsed_batch_v1',
            'original_plan_sha256': digest(plan), 'input_index': i, 'input_binding_sha256': digest(binding),
            'software_sha256': digest(job['software']), 'parse': parsed}, original_plan=plan, input_index=i)
        batch_file = publish(f'event_batch:{i}', batch)
        inputs.append({'input_index': i, 'source_file': original,
            'batch_file': batch_file, 'extent': parsed['source']['extent']})
        if v2:
            event_records.append((parsed, batch_file))
        print(json.dumps({'stage': 'event_batch_retained', 'input_index': i, 'extent': parsed['source']['extent']}), flush=True)
    for i, row in enumerate(job['support_inputs']):
        role = f'support_input:{i}'
        raw, failure = _retained_input(row, row['file'], confined_file(attempt, outputs[role]['relative_path']))
        if failure is not None:
            failures.append(_failure(failure, 'input', index=i, role=role))
        elif v2:
            retained[canonical(row['file'])] = raw
        support.append({'input_index': i, 'file': row['file'] if raw is not None else None})
    preparations, reports = [], []
    if v2:
        report_raws = []
        for i, row in enumerate(job['report_inputs']):
            role = f'report_input:{i}'
            raw, failure = _retained_input(row, row['file'], confined_file(attempt, outputs[role]['relative_path']))
            if failure is not None:
                failures.append(_failure(failure, 'input', index=i, role=role))
            else:
                retained[canonical(row['file'])] = raw
            report_raws.append(raw)
        if job['preparations'] or job['report_inputs']:
            from .native_fluorescence_prepared_driver import produce_selected
            preparations, reports, selected_failures = produce_selected(plan, event_records=event_records,
                retained=retained, report_raws=report_raws, publish=publish, failure=_failure,
                verify=verify_fluorescence_software)
            failures.extend(selected_failures)
    declarations = []
    for row in plan['outputs'][:-1]:
        path = confined_file(attempt, row['relative_path'])
        pin = file_pin(path) if path.is_file() else None
        declarations.append({'role': row['role'], 'declaration': {
            'relative_path': row['relative_path'], 'format': row['format'], 'state': 'present' if pin else 'absent',
            'sha256': pin['sha256'] if pin else None, 'size_bytes': pin['size_bytes'] if pin else None}})
    manifest = validate_fluorescence_manifest({'version': 'fluorescence_native_manifest_v2' if v2 else 'fluorescence_native_manifest_v1',
        'original_plan_sha256': digest(plan), 'identity': plan['identity'],
        'requested_job_sha256': plan['identity']['requested_job_sha256'], 'operation': job['operation'], 'mode': job['mode'],
        'software_sha256': digest(job['software']), 'outputs': declarations, 'inputs': inputs, 'support': support,
        'failures': unique(failures), **({'preparations': preparations, 'reports': reports} if v2 else {})}, original_plan=plan)
    verify_fluorescence_software(job['software'])
    output = confined_file(attempt, outputs['manifest']['relative_path'])
    output.parent.mkdir(parents=True, exist_ok=True)
    immutable_json(output, manifest)
    return manifest


def main():
    require(len(sys.argv) == 2, 'one_fluorescence_run_plan_required')
    try:
        manifest = run_fluorescence_driver(read_json(Path(sys.argv[1]).absolute()))
        return 0 if (not manifest['failures'] and all(row['extent'] == 'complete' for row in manifest['inputs'])
            and all(row['status'] == 'complete' for row in manifest.get('preparations', []))
            and all(row['extent'] == 'complete' for row in manifest.get('reports', []))) else 2
    except (ValueError, OSError, ImportError, MemoryError) as error:
        print(json.dumps({'stage': 'fluorescence_driver_failed', 'exception_class': type(error).__name__,
            'code': str(error)}), file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
