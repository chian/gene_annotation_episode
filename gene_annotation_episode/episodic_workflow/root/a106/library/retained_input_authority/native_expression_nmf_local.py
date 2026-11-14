"""Reserve/authenticate one selected NMF start with the existing lifecycle."""
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_expression_nmf_contracts import POLICY, expression_nmf_driver_argv, expression_nmf_environment

def _environment(plan):
    return expression_nmf_environment(plan['requested_job']['native_expression_nmf']['software'], attempt_directory=plan['attempt_directory'])

def _request(plan, paths):
    return {'command': expression_nmf_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
