"""Retain scientific files from the original general command's frozen outputs.

Purpose-specific adapters retain their manifest and scientific validation. This
port changes only where already closed original bytes are obtained; it never
executes work, prepares a job or accepts a later live-path replacement.
"""
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.terminal_scientific_evidence import terminal_file_identity

def validate_execution_file(file, *, original_plan, relative_path, format, command_proof):
    """A non-null retained identity must name this exact executed version."""
    if command_proof['original_plan'] != original_plan:
        raise ValueError('terminal_capture_original_plan_mismatch')
    if file is None:
        return
    path = str(Path(original_plan['attempt_directory']) / relative_path)
    snapshots = [row for row in command_proof['output_snapshots'] if row['path'] == path]
    if len(snapshots) != 1 or not snapshots[0]['available'] or file != terminal_file_identity(snapshots[0], format):
        raise ValueError('terminal_capture_executed_file_mismatch')
