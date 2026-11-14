"""Reserve and authenticate one selected atac action without dispatch."""
from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_atac_differential_contracts import POLICY, atac_driver_argv, atac_environment

def _environment(plan):
    return atac_environment(plan['requested_job']['native_atac_differential'], attempt_directory=plan['attempt_directory'], environment=plan['requested_job']['environment'])

def _request(plan, paths):
    return {'command': atac_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
