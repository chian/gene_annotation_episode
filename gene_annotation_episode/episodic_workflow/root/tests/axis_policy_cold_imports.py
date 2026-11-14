"""Fresh-process import observations for actual A102/A103 policy owners.

Each child imports one real entry from an authenticated run snapshot. It never
constructs a workflow, invokes a provider or starts scientific/native work.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

APPLICATION = 'gene_annotation_episode'
APPLICATION_ROOTS = (APPLICATION, 'method_loop')
REPOSITORY = Path('/home/chia/repos/gene_annotation_episode')
PREFIX = APPLICATION + '.episodic_workflow.root.'
ENTRIES = (
    'a103.library.action_contracts',
    'a103.library.report_fact_assembly',
    'a103.library.scientific_child_contracts',
    'a103.library.annotation_report_projection',
    'a103.legacy_improvement.internal_summary',
    'a103.legacy_improvement.to_parent',
    'a102.library.action_contracts',
    'a102.library.report_fact_assembly',
    'a102.library.scientific_child_contracts',
    'a102.task',
    'a102.to_parent',
)
ORIGINAL_ENTRIES = tuple(name for name in ENTRIES if '.library.' not in name)
HISTORICAL_FIXED_ENTRIES = ENTRIES + ('a103.legacy_annotation.commissioning_policy',
    'a103.library.unregistered_child_roles', 'a102.commissioning_policy',
    'a102.library.unregistered_child_roles')
FIXED_ENTRIES = ENTRIES + ('a103.commissioning_policy',
    'a103.library.unregistered_child_roles', 'a102.commissioning_policy',
    'a102.library.unregistered_child_roles')
HISTORICAL_CASES = (tuple(('original', entry) for entry in ORIGINAL_ENTRIES)
    + tuple(('broken', entry) for entry in ENTRIES)
    + tuple(('fixed', entry) for entry in HISTORICAL_FIXED_ENTRIES))
CURRENT_CASES = (tuple(('original', entry) for entry in ORIGINAL_ENTRIES)
    + tuple(('broken', entry) for entry in ENTRIES)
    + tuple(('fixed', entry) for entry in FIXED_ENTRIES))
# Explicit pinned snapshots keep their recorded module identity. The permanent
# default follows A103's actual annotation parent at the axis root.
CASES = HISTORICAL_CASES if 'ROOT_POLICY_COLD_INPUTS' in os.environ else CURRENT_CASES
assert len(CASES) == len(HISTORICAL_CASES) == len(CURRENT_CASES) == 30


def pinned(ref):
    path = Path(ref['path'])
    if not path.is_absolute():
        path = REPOSITORY / path
    assert path.resolve(strict=True) == path and not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ref['sha256']
    return raw


def input_record():
    if 'ROOT_POLICY_COLD_INPUTS' not in os.environ:
        assert 'ROOT_POLICY_COLD_INPUTS_SHA256' not in os.environ
        return None, None
    ref = {'path': os.environ['ROOT_POLICY_COLD_INPUTS'],
           'sha256': os.environ['ROOT_POLICY_COLD_INPUTS_SHA256']}
    value = json.loads(pinned(ref))
    assert value['version'] == 'axis_policy_cold_import_inputs_v1'
    return ref, value


def observe(tmp_path, variant, entry):
    ref, inputs = input_record()
    assert (variant, entry) in (HISTORICAL_CASES if ref is not None else CURRENT_CASES)
    if ref is None:
        assert variant == 'fixed', 'historical variants require explicit evidence inputs'
    task_run = tmp_path.resolve()
    assert task_run.is_relative_to(REPOSITORY / 'runs')
    for name in ('tmp', 'cache', 'config', 'data'):
        (task_run / name).mkdir()
    env = dict(os.environ, TMPDIR=str(task_run / 'tmp'), TMP=str(task_run / 'tmp'),
        TEMP=str(task_run / 'tmp'), XDG_CACHE_HOME=str(task_run / 'cache'),
        XDG_CONFIG_HOME=str(task_run / 'config'), XDG_DATA_HOME=str(task_run / 'data'),
        PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONOPTIMIZE', None)
    report = task_run / 'observation.json'
    command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
        '--variant', variant, '--entry', entry, '--output', str(report)]
    if ref is None:
        # Permanent current checks use their own installed tree, not old run snapshots.
        command += ['--installed-root', str(Path(__file__).resolve().parents[4])]
    else:
        command += ['--inputs', ref['path'], '--inputs-sha256', ref['sha256']]
    process = subprocess.run(command, cwd=task_run, env=env, capture_output=True)
    (task_run / 'stdout.log').write_bytes(process.stdout)
    (task_run / 'stderr.log').write_bytes(process.stderr)
    result = json.loads(report.read_bytes())
    assert result['variant'] == variant and result['entry'] == entry
    assert result['inputs'] == ref and result['origin_guards'] is True
    assert process.returncode == result['import_returncode']
    assert result['application_imports']
    if ref is None:
        root = Path(__file__).resolve().parents[4]
        for row in result['application_imports']:
            path = root / row['target']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
            assert path.stat().st_mode & 0o777 == row['mode']
    return result


def child(args):
    assert (args.variant, args.entry) in (
        CURRENT_CASES if args.installed_root is not None else HISTORICAL_CASES)
    if args.installed_root is not None:
        assert args.variant == 'fixed' and args.inputs is None and args.inputs_sha256 is None
        ref, selected = None, None
        root = Path(args.installed_root)
        assert root.resolve(strict=True) == root == Path(__file__).resolve().parents[4]
        dependency_roots = []
    else:
        assert args.inputs is not None and args.inputs_sha256 is not None
        ref = {'path': args.inputs, 'sha256': args.inputs_sha256}
        inputs = json.loads(pinned(ref))
        assert inputs['version'] == 'axis_policy_cold_import_inputs_v1'
        tree = inputs['trees'][args.variant]
        root = Path(tree['snapshot_root'])
        assert root.resolve(strict=True) == root and root.is_relative_to(REPOSITORY / 'runs')
        selection = json.loads(pinned(tree['source_selection']))
        selected = {row['target']: row for row in selection['rows']}
        assert len(selected) == len(selection['rows'])
        dependency_roots = [Path(value) for value in inputs['dependency_roots']]
        for path in dependency_roots:
            assert path.resolve(strict=True) == path and path.is_relative_to(REPOSITORY / 'runs')
        pinned(inputs['dependency_evidence'])
    assert not any(name == package or name.startswith(package + '.')
        for name in sys.modules for package in APPLICATION_ROOTS)
    sys.path[:0] = [str(path) for path in dependency_roots]
    sys.path.insert(0, str(root))
    requested = PREFIX + args.entry
    frames, identity = [], {}
    try:
        module = importlib.import_module(requested)
        assert module.__name__ == requested
        axis = args.entry.split('.')[0]
        runtime = importlib.import_module(PREFIX + axis + '.runtime')
        if args.variant == 'fixed':
            actions = importlib.import_module(PREFIX + axis + '.library.action_contracts')
            reports = importlib.import_module(PREFIX + axis + '.library.report_fact_assembly')
            identity = {
                'action_method_is_actual_definer': runtime.Workflow.action_schema is actions.action_schema,
                'report_method_is_actual_definer': runtime.Workflow.facts is reports.facts,
                'action_runtime_object_is_original': actions._runtime is runtime,
                'report_runtime_object_is_original': reports._runtime is runtime,
            }
            assert all(identity.values())
        elif args.variant == 'original':
            assert runtime.Workflow.action_schema.__module__ == runtime.__name__
            assert runtime.Workflow.facts.__module__ == runtime.__name__
        outcome = {'status': 'imported', 'module': module.__name__}
        code = 0
    except Exception as error:
        frames = [frame.filename for frame in traceback.extract_tb(error.__traceback__)]
        outcome = {'status': 'raised', 'type': type(error).__name__, 'message': str(error),
                   'traceback': traceback.format_exc()}
        code = 1
    paths = {module.__file__ for name, module in tuple(sys.modules.items())
        if any(name == package or name.startswith(package + '.') for package in APPLICATION_ROOTS)
        and getattr(module, '__file__', None)}
    paths.update(path for path in frames if any(str(root / package) in path for package in APPLICATION_ROOTS))
    actual = []
    for filename in sorted(paths):
        path = Path(filename).resolve(strict=True)
        assert path.is_relative_to(root), filename
        target = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        mode = path.stat().st_mode & 0o777
        if selected is not None:
            row = selected[target]
            assert digest == row['source']['sha256'] and mode == row['mode']
        actual.append({'target': target, 'sha256': digest, 'mode': mode})
    output = Path(args.output)
    assert output.parent.resolve().is_relative_to(REPOSITORY / 'runs')
    with output.open('x') as stream:
        json.dump({'inputs': ref, 'variant': args.variant, 'entry': args.entry,
            'outcome': outcome, 'import_returncode': code, 'identity': identity,
            'application_imports': actual, 'origin_guards': True}, stream, indent=2)
        stream.write('\n')
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs')
    parser.add_argument('--inputs-sha256')
    parser.add_argument('--installed-root')
    parser.add_argument('--variant', required=True)
    parser.add_argument('--entry', required=True)
    parser.add_argument('--output', required=True)
    raise SystemExit(child(parser.parse_args()))
