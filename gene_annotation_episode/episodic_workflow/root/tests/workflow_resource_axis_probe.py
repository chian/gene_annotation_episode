"""Real constructor diagnostics under the canonical workflow launcher.

This is an observation helper, not a simulated owner or a native workload.
Run as a module after promotion to root/tests. A complete report can contain
failed application boundaries; its process exit code is not a passing test count.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode import workflow_budget as canonical


AXES = ('a102', 'a103', 'a104', 'a107', 'a110')
CONSUMERS = ('local_jobs', 'local_resources', 'native_lifecycle', 'providers',
             'runtime', 'terminal_execution')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value):
    cls = type(value)
    return cls.__module__ + '.' + cls.__qualname__


def source(module):
    path = Path(module.__file__).resolve()
    return {'path': str(path), 'sha256': digest(path)}


def diagnostic(directory, axes=AXES):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    report = {'version': 'canonical_workflow_resource_constructor_diagnostic_v1',
              'axes': {}, 'diagnostic_complete': False, 'boundaries': [],
              'scope': 'real owner/policy/resources/Store/ToolRegistry; no action or native execution',
              'canonical_source': source(canonical),
              'helper_source': {'path': str(Path(__file__).resolve()), 'sha256': digest(__file__)},
              'forbidden_operations': []}

    def save():
        (directory / 'probe.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')

    def observe(name, callback, serialize=lambda value: value):
        row = {'name': name, 'status': 'entered'}
        report['boundaries'].append(row)
        save()
        try:
            value = callback()
            row.update(status='returned', value=serialize(value))
            return value
        except Exception as error:
            row.update(status='raised', error={'type': identity(error), 'message': str(error)})
            return None
        finally:
            save()

    def forbidden(name):
        def reject(*args, **kwargs):
            report['forbidden_operations'].append(name)
            save()
            raise AssertionError('probe_forbids_' + name)
        return reject

    save()
    # Authenticate before any Store or registry writes. The owner/environment
    # implementation and /proc/cgroup observations are never patched.
    owner = observe('canonical.active_budget', canonical.active_budget)
    if owner is None:
        return report
    if not directory.is_relative_to(Path(owner['run_directory']).resolve()):
        raise ValueError('probe_output_must_be_inside_actual_workflow_run')
    if os.environ.get('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY'):
        raise ValueError('default_resource_probe_requires_unoverridden_resource_directory')
    report['workflow_receipt_sha256'] = digest(os.environ[canonical.ENV])
    report['actual_owner'] = owner
    with ExitStack() as ports:
        ports.enter_context(patch.object(subprocess, 'Popen', forbidden('subprocess')))
        ports.enter_context(patch.object(os, 'system', forbidden('os_system')))
        for name in ('fork', 'forkpty', 'posix_spawn', 'posix_spawnp'):
            if hasattr(os, name):
                ports.enter_context(patch.object(os, name, forbidden(name)))
        ports.enter_context(patch.object(socket.socket, 'connect', forbidden('socket_connect')))
        ports.enter_context(patch.object(socket.socket, 'connect_ex', forbidden('socket_connect_ex')))
        for axis in axes:
            package = 'gene_annotation_episode.episodic_workflow.root.' + axis
            row = report['axes'][axis] = {'sources': {}}
            def module(name):
                value = importlib.import_module(package + '.' + name)
                row['sources'][name] = source(value)
                return value
            axis_path = Path(importlib.import_module(package).__file__).resolve().parent
            defaults = axis_path / 'defaults.toml'
            row['defaults'] = {'path': str(defaults), 'sha256': digest(defaults)}
            copied = axis_path / 'workflow_budget.py'
            # This is the only intentional historical copy lookup. It is
            # conditional on the file still existing, never an application alias.
            if copied.exists():
                observe(axis + '.copied_checker.active_budget',
                        lambda: module('workflow_budget').active_budget())
            else:
                row['copied_checker'] = 'retired; canonical infrastructure is the owner'
            jobs = observe(axis + '.local_jobs.import', lambda: module('local_jobs'), source)
            resources = observe(axis + '.local_resources.import', lambda: module('local_resources'), source)
            lifecycle = observe(axis + '.native_lifecycle.import', lambda: module('native_lifecycle'), source)
            acquisition = observe(axis + '.acquisition.import', lambda: module('acquisition'), source)
            if jobs is not None:
                observe(axis + '.LocalJobPolicy.default', jobs.LocalJobPolicy.from_config,
                        lambda policy: {'type': identity(policy), 'configuration': policy.to_dict()})
            if resources is not None:
                observe(axis + '.LocalResources.default', resources.LocalResources.configured,
                        lambda value: {'type': identity(value), 'record': value.as_record()})
            if lifecycle is not None and jobs is not None and acquisition is not None:
                row['own_type_identity'] = {
                    'policy': lifecycle.LocalJobPolicy is jobs.LocalJobPolicy,
                    'acquisition_error': lifecycle.AcquisitionError is acquisition.AcquisitionError,
                    'policy_module': jobs.LocalJobPolicy.__module__,
                    'exception_module': acquisition.AcquisitionError.__module__}
            state = observe(axis + '.state.import', lambda: module('state'), source)
            tool_module = observe(axis + '.tools.import', lambda: module('tools'), source)
            store = None
            try:
                if state is not None:
                    store = observe(axis + '.Store.construct', lambda: state.Store(directory / axis / 'store'),
                                    lambda value: {'type': identity(value), 'path': str(value.path)})
                if store is not None and tool_module is not None:
                    observe(axis + '.ToolRegistry.default', lambda: tool_module.ToolRegistry(store),
                            lambda value: {'type': identity(value),
                                'policy_type': identity(value.local_job_policy),
                                'policy': value.local_job_policy.to_dict(),
                                'resources_type': identity(value.local_resources),
                                'resources': value.local_resources.as_record(),
                                'store_identity_preserved': value.store is store,
                                'tool_operations_table': store.db.execute(
                                    "SELECT name FROM sqlite_master WHERE name='tool_operations'").fetchone() is not None})
            finally:
                if store is not None:
                    store.close()
            for name in (*CONSUMERS, *(('homology_recovery',) if axis == 'a103' else ())):
                path = axis_path / (name + '.py')
                row['consumer_source_hashes'] = row.get('consumer_source_hashes', {})
                row['consumer_source_hashes'][str(path)] = digest(path)
            save()
    report['diagnostic_complete'] = True
    report['all_observed_boundaries_returned'] = all(
        row['status'] == 'returned' for row in report['boundaries'])
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--axes', nargs='+', choices=AXES, default=list(AXES))
    args = parser.parse_args()
    report = diagnostic(args.directory, args.axes)
    if not report['diagnostic_complete']:
        raise SystemExit(1)
    print(json.dumps({'diagnostic_complete': True,
                      'all_observed_boundaries_returned': report['all_observed_boundaries_returned'],
                      'report': str(args.directory / 'probe.json')}))


if __name__ == '__main__':
    main()
