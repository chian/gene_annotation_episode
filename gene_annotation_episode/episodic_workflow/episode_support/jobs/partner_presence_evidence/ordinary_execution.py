"""Caller-bound measurement classes for ordinary native tool calls.

No episode decisions or scores belong here. Shared compatibility contains run
characteristics only; actual sequence identities stay in local tool records.
"""
from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import inspect
import json
from pathlib import Path
import sys

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.execution_recording import NativeStatistics, _sha
from gene_annotation_episode.episodic_workflow.episode_support.calculations.run_statistics import ExecutionClass, _resource


PHASE_TO_TOOLS = {'pairwise_sequence_alignment': frozenset({'sequence.align', 'reads.align'}),
                  'spreadsheet_selection': frozenset({'source.xlsx.sheets', 'source.xlsx.rows'})}


@dataclass(frozen=True)
class OrdinaryExecutionStatistics:
    history_path: Path
    resource_id: str
    recovery_directory: Path

    def __post_init__(self):
        _resource(self.resource_id)
        for name in ('history_path', 'recovery_directory'):
            object.__setattr__(self, name, Path(getattr(self, name)).expanduser().resolve())

    def as_record(self):
        return {'version': 'ordinary_native_statistics_binding',
                'history_path': str(self.history_path), 'resource_id': self.resource_id,
                'recovery_directory': str(self.recovery_directory),
                'phases': list(PHASE_TO_TOOLS)}

    @staticmethod
    def available_phase(phase, tools):
        return bool(PHASE_TO_TOOLS.get(phase, frozenset()) & set(tools))

    def alignment_class(self, arguments, policy):
        from Bio.Align import _pairwisealigner
        from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_operations import sequence_ops
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.native_lifecycle import VERSION as lifecycle_version
        # Bind the same arguments/defaults used by the native operation, rather
        # than maintaining another set of algorithm settings in the recorder.
        bound = inspect.signature(sequence_ops.align_pair).bind(**arguments)
        bound.apply_defaults()
        values = bound.arguments
        implementation = _sha({'biopython_version': version('biopython'),
            'python_version': sys.version,
            'native_lifecycle_version': lifecycle_version,
            'native_pairwise_aligner_sha256': hashlib.sha256(Path(_pairwisealigner.__file__).read_bytes()).hexdigest()})
        # Sequence content and gene labels do not cross the shared boundary.
        # This initial exact-size grouping makes no cross-size extrapolation.
        parameters = {key: value for key, value in values.items() if key not in {'query', 'reference'}}
        return ExecutionClass(phase='pairwise_sequence_alignment', backend='local',
            resource_id=self.resource_id, implementation_sha256=implementation,
            parameters_sha256=_sha(parameters), memory_bytes=policy.memory_bytes,
            scratch_bytes=policy.scratch_bytes,
            cpu_threads=None, query_residues=len(values['query']),
            reference_residues=len(values['reference']), reference_records=1,
            reference_state='available', duration_measure='systemd_service_wall_seconds')

    def for_alignment(self, arguments, policy):
        return NativeStatistics.pending(self.history_path, self.alignment_class(arguments, policy),
                                        recovery_directory=self.recovery_directory)

    def spreadsheet_class(self, path, operation, arguments, policy):
        from gene_annotation_episode.episodic_workflow.episode_support.tools.documents.partner_presence_evidence import spreadsheet_tools
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.native_lifecycle import VERSION as lifecycle_version
        if operation == 'sheets':
            if arguments:
                raise ValueError('spreadsheet_inventory_has_no_selection_arguments')
            selection = {}
        elif operation == 'rows':
            # The native worker's own defaults define the selection. Store only
            # technical workload features, never a biological filter literal,
            # source identity, sheet name or workbook contents in shared stats.
            bound = inspect.signature(spreadsheet_tools.Workbook.rows).bind(None, None, None, **arguments)
            bound.apply_defaults()
            values = bound.arguments
            where = values['where']
            selection = {key: values[key] for key in ('offset', 'limit', 'header_row')}
            selection['sheet_key_utf8_bytes'] = len(values['sheet_key'].encode('utf-8'))
            selection['where'] = (None if where is None else {
                'column': where['column'], 'match': where['match'],
                'case_sensitive': where['case_sensitive'],
                'value_utf8_bytes': len(where['value'].encode('utf-8'))})
        else:
            raise ValueError('unsupported_spreadsheet_statistics_operation')
        implementation = _sha({'python_version': sys.version, 'native_lifecycle_version': lifecycle_version,
            'adapter_version': spreadsheet_tools.VERSION})
        parameters = {'operation': operation, 'input_bytes': Path(path).stat().st_size, 'selection': selection,
                      'compatibility': 'same_input_size_and_technical_selection_features'}
        return ExecutionClass(phase='spreadsheet_selection', backend='local', resource_id=self.resource_id,
            implementation_sha256=implementation, parameters_sha256=_sha(parameters),
            memory_bytes=policy.memory_bytes, scratch_bytes=policy.scratch_bytes,
            cpu_threads=None, query_residues=None, reference_residues=None, reference_records=None,
            reference_state='available', duration_measure='systemd_service_wall_seconds')

    def for_spreadsheet(self, path, operation, arguments, policy):
        return NativeStatistics.pending(self.history_path, self.spreadsheet_class(path, operation, arguments, policy),
                                        recovery_directory=self.recovery_directory)

    def recover_pending_statistics(self):
        """Finish pending receipt exports before a new expectation is captured.

        Each receipt keeps its original destination, physical identity and start
        condition. This never submits native work or rewrites episode history.
        Completed receipt bodies and scientific archives are not materialized.
        """
        from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.execution_recording import recover_native_measurement
        summary = {'scan_state': 'available', 'pending': 0, 'recorded': 0, 'unavailable': 0, 'invalid': 0,
            'failures': {'history_unavailable': 0, 'identity_conflict': 0,
                         'receipt_invalid': 0, 'receipt_unavailable': 0}}
        def receipts():
            try:
                yield from self.recovery_directory.glob('*.measurement.json')
            except OSError:
                summary['scan_state'] = 'unavailable'
                summary['failures']['receipt_unavailable'] += 1
        for path in receipts():
            disposition = path.with_name(path.name.removesuffix('.measurement.json')+'.export.json')
            try:
                if disposition.is_file():
                    saved = json.loads(disposition.read_text())
                    if isinstance(saved, dict) and saved.get('state') == 'recorded':
                        continue
            except (OSError, ValueError):
                # A missing/corrupt derived disposition can be reconstructed
                # from the original typed receipt through the same publisher.
                pass
            summary['pending'] += 1
            try:
                result = recover_native_measurement(path)
                summary['recorded' if result['state'] == 'recorded' else 'unavailable'] += 1
                if result['state'] != 'recorded':
                    reason = {'statistics_history_unavailable': 'history_unavailable',
                              'statistics_identity_conflict': 'identity_conflict'}.get(result.get('code'), 'receipt_invalid')
                    summary['failures'][reason] += 1
                if result.get('recovery_state') == 'unavailable':
                    summary['failures']['receipt_unavailable'] += 1
            except OSError:
                summary['unavailable'] += 1
                summary['failures']['receipt_unavailable'] += 1
            except (ValueError, TypeError, KeyError):
                summary['invalid'] += 1
                summary['failures']['receipt_invalid'] += 1
        return summary
