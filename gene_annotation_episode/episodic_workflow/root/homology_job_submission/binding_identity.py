"""Identity of all actual private homology responsibilities and task files."""
import hashlib
from pathlib import Path
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _binding

def as_record(self):
    root = Path(__file__).resolve().parents[1]
    paths = ('homology_job_submission/configuration.py', 'homology_job_submission/credit.py', 'homology_job_submission/from_parent.py', 'homology_job_submission/goal.py', 'homology_job_submission/homology_operations.py', 'homology_job_submission/to_parent.py', 'homology_job_submission/episode.py', 'homology_job_submission/binding_identity.py', 'homology_job_submission/task.py', 'homology_job_submission/task_state.py', 'homology_job_submission/task_protocol.py', 'homology_job_submission/task_decision.py', 'homology_job_submission/task_instructions.py', 'homology_job_submission/task_actions.py', 'homology_job_submission/task_report.py', 'library/homology_episode_contracts.py', 'library/homology_custody.py', 'library/homology_custody_configuration.py', 'library/homology_received_records.py', 'library/homology_native_events.py', 'library/homology_episode_family.py', 'library/monitoring_credit.py', 'homology_job_submission/internal_summary.py', 'homology_job_submission/yield.py', 'homology_job_submission/waiting.py', '../../execution_contracts.py', 'execution_recording.py', 'native_measurement.py', 'native_events.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_private_homology_v1', 'binding_id': 'job_launch', 'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(), 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'credit_binding': self.binding_for('job_launch'), 'credit_calculator': _binding(self.monitoring_projector if 'job_launch' == 'job_monitor' else self._job_credit_calculator), 'statistics': None if self.statistics is None else self.statistics.as_record()}
