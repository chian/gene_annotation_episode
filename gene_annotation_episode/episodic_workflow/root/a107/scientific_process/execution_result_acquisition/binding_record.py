"""Private A107 Results binding_record"""
from __future__ import annotations
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a107 import runtime as axis_runtime
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest
from pathlib import Path
from .binding_roles import VERSION
from copy import deepcopy

class ResultsBindingRecord:

    def as_record(self):
        home = Path(__file__).resolve().parent
        axis = Path(axis_runtime.__file__).resolve().parent
        sources = {str(path.relative_to(axis)): path for path in sorted(home.glob('*.py'))}
        sources.update({name: axis / name for name in ('runtime.py', 'runtime_prompt.py', 'episode_services.py', 'episode_report_acquisition.py', 'providers.py', 'decision_context.py', 'terminal_execution.py', 'library/hpc_prompt.py', 'library/monitor_prompt.py', 'library/scientific_instruction_text.py', 'library/scientific_decision_presentation.py', 'scientific_process/task_decision.py', 'a107_blast_execution.py', 'execution_prompt.py', 'rna_structure_prompt.py', 'rna_structure_comparison_prompt.py', 'rna_structure_comparison_receiver_prompt.py', 'rna_structure_presentation.py', 'rna_structure_comparison_presentation.py', 'infernal_result_presentation.py', 'library/execution_result_contract.py', 'library/received_execution_information/received_result_readers.py', 'library/received_execution_targets.py', 'scientific_process/episode.py', 'to_child_execution_job_submission.py', 'to_child_execution_result_acquisition.py', 'from_child_execution_job_submission.py', 'from_child_execution_result_acquisition.py', 'scientific_process/to_child_execution_job_submission.py', 'scientific_process/to_child_execution_result_acquisition.py', 'scientific_process/from_child_execution_job_submission.py', 'scientific_process/from_child_execution_result_acquisition.py', 'scientific_process/to_child_scientific_process.py', 'child_requests.py', 'continuation.py', 'credit.py', 'decision_waiting.py', 'episode.py', 'from_child_execution_progress_assessment.py', 'from_child_hpc_work_planning.py', 'from_child_published_evidence_assessment.py', 'from_child_scientific_process.py', 'from_parent.py', 'goal.py', 'internal_summary.py', 'library/decision_source_admission.py', 'library/decision_source_exchange.py', 'library/decision_source_outcomes.py', 'library/decision_source_state.py', 'received_outcomes.py', 'task.py', 'task_instructions.py', 'task_outcomes.py', 'task_provider.py', 'task_state.py', 'to_child_execution_progress_assessment.py', 'to_child_hpc_work_planning.py', 'to_child_published_evidence_assessment.py', 'to_child_scientific_process.py', 'library/hpc_handoff_report_contract.py')})
        hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()}
        return {'binding_id': 'scientific_process/execution_result_acquisition', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}, 'implementation_sha256': digest(hashes)}
