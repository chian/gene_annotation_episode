from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.fluorescence_execution_common import require
from gene_annotation_episode.episodic_workflow.root.a110.native_fluorescence_contracts import fluorescence_driver_argv, fluorescence_environment, validate_fluorescence_run_plan

def _environment(plan):
    return fluorescence_environment(plan['requested_job']['native_fluorescence']['software'], attempt_directory=plan['attempt_directory'])

def fluorescence_native_request(plan, paths):
    """Build the original native request without I/O or current runtime checks."""
    plan = validate_fluorescence_run_plan(plan)
    require(type(paths) is dict and all((type(paths.get(k)) is str for k in ('ready', 'release', 'result'))), 'fluorescence_original_attempt_mismatch')
    return {'command': fluorescence_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': plan['policy']['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
