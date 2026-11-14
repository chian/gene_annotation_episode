from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_genomic_overlap_contracts import POLICY, genomic_overlap_driver_argv, genomic_overlap_environment

def _environment(plan):
    return genomic_overlap_environment(plan['requested_job']['native_genomic_overlap'], attempt_directory=plan['attempt_directory'])

def _request(plan, paths):
    return {'command': genomic_overlap_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
