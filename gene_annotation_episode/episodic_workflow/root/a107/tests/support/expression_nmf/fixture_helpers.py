"""Bounded-check helpers; software inspection is invoked inside that handle."""
from pathlib import Path
import importlib.metadata
import json
import os
import sys

from gene_annotation_episode.expression_nmf_common import MODE, OPERATION, default_nmf_parameters, digest, identity
from gene_annotation_episode.native_expression_nmf_contracts import (expression_nmf_environment,
    requested_job_from_expression_nmf, validate_expression_nmf_software)
from gene_annotation_episode.native_expression_nmf_storage import file_pin


def prepared_software(attempt):
    attempt = Path(attempt)
    source, deps = attempt / 'source_snapshot', attempt / 'dependencies'
    implementations = [source / 'gene_annotation_episode/__init__.py']
    implementations.extend((source / 'gene_annotation_episode').glob('expression_nmf_*.py'))
    implementations.extend((source / 'gene_annotation_episode').glob('native_expression_nmf_*.py'))
    runtime = {}
    for name in ('dependency_pins_before.json', 'stdlib_pins_before.json', 'native_library_pins_before.json'):
        for row in json.loads((attempt / name).read_text()):
            runtime[row['path']] = row
    python = file_pin(sys.executable)
    runtime.pop(python['path'], None)
    result = {'version': 'expression_nmf_software_v1', 'python': python, 'python_version': sys.version,
        'python_home': str(attempt / 'runtime'), 'module_root': str(source),
        'implementation_files': [file_pin(p) for p in sorted(implementations)], 'dependency_roots': [str(deps)],
        'distributions': [{'name': d.metadata['Name'], 'version': d.version, 'requires': d.requires or []}
            for d in importlib.metadata.distributions(path=[str(deps)])], 'runtime_files': list(runtime.values())}
    return validate_expression_nmf_software(result)


def selected_job(software, input_path, *, normalization='none', rank=2, max_iter=1000):
    path = Path(input_path)
    raw = path.read_bytes()
    return {'version': 'native_expression_nmf_job_v1', 'operation': OPERATION, 'mode': MODE,
        'input': {'path': str(path), **identity(raw), 'artifact_ref': 'artifact_' + identity(raw)['sha256'],
            'delimiter': ',', 'metadata': {'units': 'counts'}},
        'parameters': default_nmf_parameters(rank=rank, normalization=normalization, max_iter=max_iter),
        'software': software, 'output_prefix': 'native-output'}


def selected_request(software, input_path, **parameters):
    job = selected_job(software, input_path, **parameters)
    return requested_job_from_expression_nmf(job, environment=expression_nmf_environment(software,
        attempt_directory=str(Path(input_path).parent / 'declared-workspace')))
