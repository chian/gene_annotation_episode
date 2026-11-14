"""Retain original FBA bytes independently; the caller owns execution authority."""
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.flux_balance_native_capture_contracts import CONTROL_FORMATS, _original_plan, _require
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_flux_balance_contracts import OWNER_FILENAME, STARTED_FILENAME, ENVIRONMENT_FILENAME
_CONTROL_PATHS = {'owner': OWNER_FILENAME, 'started': STARTED_FILENAME, 'environment': ENVIRONMENT_FILENAME}

def validate_terminal_flux_balance_files(capture, *, original_plan, command_proof):
    """Match native data and controls to their original executed snapshots."""
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.terminal_scientific_evidence import terminal_file_identity
    plan = _original_plan(original_plan)
    _require(command_proof['original_plan'] == plan, 'terminal_plan_mismatch')
    snapshots = {row['path']: row for row in command_proof['output_snapshots']}
    selected = [(row['relative_path'], row['format'], row['retained']) for row in capture['files']]
    selected.extend(((path, CONTROL_FORMATS[role], capture['controls'][role]) for role, path in _CONTROL_PATHS.items()))
    for relative_path, format_, retained in selected:
        snapshot = snapshots.get(str(Path(plan['attempt_directory']) / relative_path))
        expected = terminal_file_identity(snapshot, format_) if snapshot is not None and snapshot.get('available') else None
        actual = retained['file'] if retained is not None else None
        _require(actual == expected, 'terminal_file_mismatch', relative_path)
