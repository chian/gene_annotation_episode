"""Reserve and authenticate one selected chromatin action without dispatch."""
from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_chromatin_interaction_contracts import POLICY, chromatin_driver_argv, chromatin_environment

def _environment(plan):
    return chromatin_environment(plan['requested_job']['native_chromatin_interactions'], attempt_directory=plan['attempt_directory'], environment=plan['requested_job']['environment'])

def _request(plan, paths):
    return {'command': chromatin_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
