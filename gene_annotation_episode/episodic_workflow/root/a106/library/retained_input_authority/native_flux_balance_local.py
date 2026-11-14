"""Reserve the selected FBA start; authenticate its original local controls.

The caller authenticates the received694 input receipt and its File before
calling this adapter. These local joins neither authorize arbitrary JSON nor
grant input references. Preparation never dispatches the reserved command.
"""
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_flux_balance_contracts import POLICY, RUN_PLAN_FILENAME, flux_balance_driver_argv

def _environment(plan):
    return plan['environment_binding']['realized_environment'] if plan['version'] == 'flux_balance_run_plan_v2' else plan['requested_job']['environment']

def _invoke(plan, file):
    request = plan['requested_job']
    return {'cwd': str(Path(plan['identity']['execution_id']).parent), 'argv': request['argv'], 'environment': request['environment'], 'native_flux_balance_plan': RUN_PLAN_FILENAME, 'native_flux_balance_input_binding_file': file}

def _request(plan, paths):
    return {'command': flux_balance_driver_argv(plan), 'cwd': str(Path(plan['identity']['execution_id']).parent), 'file_bytes': POLICY['scratch_bytes'], 'ready_path': paths['ready'], 'release_path': paths['release'], 'result_path': paths['result'], 'stdin_path': None, 'env': _environment(plan)}
