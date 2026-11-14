"""A107 original fluorescence terminal files; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a107.fluorescence_execution_common import require
from gene_annotation_episode.episodic_workflow.root.a107.native_fluorescence_contracts import validate_fluorescence_run_plan

def validate_terminal_fluorescence_files(capture, *, original_plan, command_proof):
    """Match retained results to the original completed command's file version."""
    from gene_annotation_episode.episodic_workflow.root.a107.terminal_scientific_evidence import terminal_file_identity
    plan = validate_fluorescence_run_plan(original_plan)
    require(command_proof['original_plan'] == plan, 'fluorescence_terminal_capture_plan_mismatch')
    snapshots = {row['path']: row for row in command_proof['output_snapshots']}
    for row in capture['files']:
        snapshot = snapshots.get(str(Path(plan['attempt_directory']) / row['relative_path']))
        expected = terminal_file_identity(snapshot, row['format']) if snapshot is not None and snapshot.get('available') else None
        actual = row['retained']['file'] if row['retained'] is not None else None
        require(actual == expected, 'fluorescence_terminal_capture_file_mismatch')
