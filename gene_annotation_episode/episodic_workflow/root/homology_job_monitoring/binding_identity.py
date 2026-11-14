"""Identity of all actual private homology responsibilities and task files."""
import hashlib
from pathlib import Path
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _binding

def as_record(self):
    root = Path(__file__).resolve().parents[1]
    paths = ('homology_job_monitoring/configuration.py', 'homology_job_monitoring/credit.py', 'homology_job_monitoring/from_parent.py', 'homology_job_monitoring/goal.py', 'homology_job_monitoring/homology_operations.py', 'homology_job_monitoring/to_parent.py', 'homology_job_monitoring/episode.py', 'homology_job_monitoring/binding_identity.py', 'homology_job_monitoring/task.py', 'homology_job_monitoring/task_state.py', 'homology_job_monitoring/task_protocol.py', 'homology_job_monitoring/task_decision.py', 'homology_job_monitoring/task_instructions.py', 'homology_job_monitoring/task_actions.py', 'homology_job_monitoring/task_report.py', 'library/homology_episode_contracts.py', 'library/homology_custody.py', 'library/homology_custody_configuration.py', 'library/homology_received_records.py', 'library/homology_native_events.py', 'library/homology_episode_family.py', 'library/monitoring_credit.py', 'homology_job_monitoring/internal_summary.py', 'homology_job_monitoring/yield_estimator.py', 'homology_job_monitoring/waiting.py', '../../execution_contracts.py', 'execution_recording.py', 'native_measurement.py', 'native_events.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_private_homology_v1', 'binding_id': 'job_monitor', 'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(), 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'credit_binding': self.binding_for('job_monitor'), 'credit_calculator': _binding(self.monitoring_projector if 'job_monitor' == 'job_monitor' else self._job_credit_calculator), 'statistics': None if self.statistics is None else self.statistics.as_record()}
