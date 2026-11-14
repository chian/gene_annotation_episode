"""Private binding record for A102 hpc."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import hashlib
from gene_annotation_episode.episodic_workflow.root.a102 import hpc_queue




class HPCBindingRecord:
    def as_record(self):
        home = Path(__file__).resolve().parent
        axis = home.parents[0]
        sources = {str(p.relative_to(axis)): p for p in sorted(home.glob('*.py'))}
        sources.update({name: axis / name for name in ('hpc_campaign.py', 'hpc_ledger.py', 'library/hpc_prediction.py', 'hpc_queue.py', 'hpc_allocation.py', 'hpc_monitoring.py', 'library/hpc_continuation.py', 'execution_memory.py', 'execution_guidance.py', 'hpc_history.py', 'library/hpc_resource_prediction.py', 'terminal_execution.py', 'execution_job_submission/terminal_execution.py', 'execution_job_submission/api_job_execution/terminal_execution.py', 'execution_job_submission/local_job_execution/terminal_execution.py', 'execution_job_submission/hpc_job_execution/terminal_execution.py', 'execution_result_acquisition/terminal_execution.py', 'hpc_work_planning/execution_job_submission/terminal_execution.py', 'hpc_work_planning/execution_job_submission/api_job_execution/terminal_execution.py', 'hpc_work_planning/execution_job_submission/local_job_execution/terminal_execution.py', 'hpc_work_planning/execution_job_submission/hpc_job_execution/terminal_execution.py', 'hpc_work_planning/execution_result_acquisition/terminal_execution.py', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/terminal_execution.py', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution/terminal_execution.py', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution/terminal_execution.py', 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution/terminal_execution.py', 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition/terminal_execution.py', 'hpc_commission_sources.py', 'library/hpc_prompt.py', 'library/hpc_handoff_report_contract.py')})
        hashes = {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in sources.items()}
        return {'version': 'hpc_episode_v1', 'binding_id': 'hpc_work_planning', 'implementation_sha256': hpc_queue.digest(hashes), 'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions), **({'shared_execution_memory': self.memory.as_record()} if self.memory else {}), **({'require_commission_yield': True} if self.private_yield_binding else {})}}
