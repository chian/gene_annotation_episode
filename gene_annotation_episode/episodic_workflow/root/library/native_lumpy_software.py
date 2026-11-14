"""Freeze explicitly supplied LUMPY software using original file custody.

This host preparation does not become an imported worker dependency.
"""
from __future__ import annotations
import os
from gene_annotation_episode.local_job_policy import LocalJobPolicy, check_scratch_budget
from .native_atac_file_records import _directory, confined_file
from .retained_file_pin import file_pin
from .native_lumpy_execution import (
    _record, _software, _current_module_sources, _current_driver,
    _verify_native_runtime, require, POLICY,
)


def freeze_lumpy_software_binding(*, module_root, snapshot_directory, native_runtime):
    """Freeze only explicitly supplied software; do not find/probe alternatives."""
    from .native_atac_differential_software import _copy_exact, freeze_driver_runtime
    native_runtime = _record('NativeRuntime', native_runtime)
    policy = LocalJobPolicy(**POLICY);target = _directory(snapshot_directory)
    driver = freeze_driver_runtime(module_root=module_root, snapshot_directory=target,
        driver_modules=sorted(_current_module_sources(module_root)), policy=policy)
    require(_current_driver(driver), 'native_dependency_unavailable')
    root = target / 'native'
    (root / 'lib').mkdir(parents=True, exist_ok=True)
    def copy(pin, relative, executable=False):
        require(file_pin(pin['path']) == pin, 'native_dependency_unavailable')
        check_scratch_budget(target, policy, additional_bytes=pin['size_bytes'])
        destination = confined_file(root, relative)
        result = _copy_exact(pin['path'], destination)
        if executable:
            os.chmod(destination, 0o555)
        return result
    frozen = dict(executable=copy(native_runtime['executable'], 'bin/lumpy', True),
        loader=copy(native_runtime['loader'], 'loader', True), libraries=[dict(name=row['name'],
            file=copy(row['file'], 'lib/' + row['name'])) for row in native_runtime['libraries']],
        reported_version=native_runtime['reported_version'])
    _verify_native_runtime(frozen)
    return _software(dict(driver_runtime=driver, native_runtime=frozen))


