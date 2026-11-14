"""Serial diagnostic baseline of real Launch constructors and HPC registries.

This uses the original real Store, configured resources, bindings and ledgers.
The complete registry has 31 bindings for axes with an API child, 27 for A110.
It never executes native/provider work. Constructor and registry failures are
retained as diagnostic results, never converted into successful assertions.
Only the root orchestrator executes this through tools/one_workflow.sh.
"""
from contextlib import redirect_stderr, redirect_stdout
import gc
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import traceback

RUN = Path(sys.argv[1]).resolve()
ROOT = Path.cwd()
SOURCE = ROOT/'gene_annotation_episode/episodic_workflow/root'
AXES = ('a102', 'a103', 'a104', 'a107', 'a110')
if len(sys.argv) > 2:
    selected_axes = tuple(sys.argv[2:])
    assert len(set(selected_axes)) == len(selected_axes) and set(selected_axes) <= set(AXES)
    AXES = selected_axes
PARENTS = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
assert RUN.is_relative_to(ROOT/'runs') and RUN.is_dir()
original_arguments = list(sys.argv)
source_receipts = []
for axis in AXES:
    files = set()
    for parent in PARENTS:
        files.update((SOURCE/axis/parent/'execution_job_submission').rglob('*.py'))
        files.update((SOURCE/axis/parent).glob('*execution_job_submission.py'))
    files.update(SOURCE/axis/name for name in (
        'runtime.py', 'execution_progress.py', 'episode_bindings.py',
        'materials.py', 'materials_packing.py', 'state.py'))
    for path in sorted(files):
        relative = path.relative_to(SOURCE)
        destination = RUN/'source'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        source_receipts.append({'path': str(relative),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(RUN/'source_manifest.json').write_text(json.dumps(source_receipts, indent=2)+'\n')

constructor_script = SOURCE/'tests/launch_constructor_baseline.py'
registry_script = SOURCE/'tests/launch_registry_probe.py'
results = []
for axis in AXES:
    for name, script in (('constructors', constructor_script), ('registry', registry_script)):
        output = RUN/axis/name
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script, output/'probe_source.py')
        sys.argv = [str(script), str(output)]
        row = {'axis': axis, 'probe': name, 'output': str(output),
            'native_or_provider_execution': False}
        with (output/'stdout.log').open('w') as stdout, (output/'stderr.log').open('w') as stderr:
            try:
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    namespace = runpy.run_path(str(script))
                    # Each original probe reads the exact own-axis source; no
                    # behavior, callback or actual constructor is replaced.
                    globals_ = namespace['main'].__globals__
                    globals_['AXES'] = (axis,)
                    globals_['PREFIX'] = 'gene_annotation_episode.episodic_workflow.root.'+axis+'.'
                    namespace['main']()
                row['status'] = 'diagnostic_completed'
            except Exception as error:
                row.update(status='diagnostic_raised', error_type=type(error).__name__,
                    message=str(error), traceback=traceback.format_exc())
                stderr.write(row['traceback'])
        results.append(row)
        (RUN/'diagnostics.json').write_text(json.dumps(results, indent=2)+'\n')
        print(json.dumps({key: value for key, value in row.items() if key != 'traceback'}), flush=True)
        gc.collect()
sys.argv = original_arguments
