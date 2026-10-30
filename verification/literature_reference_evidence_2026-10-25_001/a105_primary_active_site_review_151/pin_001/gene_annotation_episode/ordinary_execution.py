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

from .execution_recording import NativeStatistics, _sha
from .run_statistics import ExecutionClass, _resource


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
        return {'version': 'ordinary_native_statistics_binding_v2',
                'history_path': str(self.history_path), 'resource_id': self.resource_id,
                'recovery_directory': str(self.recovery_directory),
                'phases': list(PHASE_TO_TOOLS)}

    @staticmethod
    def available_phase(phase, tools):
        return bool(PHASE_TO_TOOLS.get(phase, frozenset()) & set(tools))

    def alignment_class(self, arguments, policy):
        from Bio.Align import _pairwisealigner
        from . import sequence_ops, sequence_worker
        from .native_lifecycle import VERSION as lifecycle_version
        # Bind the same arguments/defaults used by the native operation, rather
        # than maintaining another set of algorithm settings in the recorder.
        bound = inspect.signature(sequence_ops.align_pair).bind(**arguments)
        bound.apply_defaults()
        values = bound.arguments
        implementation = _sha({'biopython_version': version('biopython'),
            'python_version': sys.version,
            'native_lifecycle_version': lifecycle_version,
            'files': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                for name, path in (('sequence_ops', sequence_ops.__file__),
                    ('sequence_worker', sequence_worker.__file__),
                    ('native_pairwise_aligner', _pairwisealigner.__file__))}})
        # Sequence content and gene labels do not cross the shared boundary.
        # This initial exact-size grouping makes no cross-size extrapolation.
        parameters = {key: value for key, value in values.items() if key not in {'query', 'reference'}}
        return ExecutionClass(phase='pairwise_sequence_alignment', backend='local',
            resource_id=self.resource_id, implementation_sha256=implementation,
            parameters_sha256=_sha(parameters), memory_bytes=policy.memory_bytes,
            scratch_bytes=policy.scratch_bytes, wall_seconds=policy.wall_seconds,
            cpu_threads=None, query_residues=len(values['query']),
            reference_residues=len(values['reference']), reference_records=1,
            reference_state='available', duration_measure='systemd_service_wall_seconds')

    def for_alignment(self, arguments, policy):
        return NativeStatistics.pending(self.history_path, self.alignment_class(arguments, policy),
                                        recovery_directory=self.recovery_directory)

    def spreadsheet_class(self, path, operation, arguments, policy):
        from . import spreadsheet_tools, spreadsheet_worker
        from .native_lifecycle import VERSION as lifecycle_version
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
            'adapter_version': spreadsheet_tools.VERSION,
            'files': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in
                (('adapter', spreadsheet_tools.__file__), ('worker', spreadsheet_worker.__file__))}})
        parameters = {'operation': operation, 'input_bytes': Path(path).stat().st_size, 'selection': selection,
                      'compatibility': 'same_input_size_and_technical_selection_features_v1'}
        return ExecutionClass(phase='spreadsheet_selection', backend='local', resource_id=self.resource_id,
            implementation_sha256=implementation, parameters_sha256=_sha(parameters),
            memory_bytes=policy.memory_bytes, scratch_bytes=policy.scratch_bytes, wall_seconds=policy.wall_seconds,
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
        from .execution_recording import recover_native_measurement
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

    def recorded_class(self, store, class_ref):
        """Resolve actual native forecast declarations in existing journals.

        These are the typed statistical inputs supplied to decisions/work, not
        a new proposal ledger or inspection of a child's private reasoning.
        """
        for table, field, forecasts, classes in (
                ('runtime_actions', 'result', '$.resource_tool_estimates',
                 '$.native_execution_expectations.execution_classes'),
                ('runtime_model_calls', 'request', '$.context.resource_tool_estimates',
                 '$.context.native_execution_expectations.execution_classes')):
            row = store.db.execute(f'''SELECT json_extract(records.{field},?) FROM {table} records
                JOIN json_each(records.{field},?) forecasts
                WHERE json_extract(forecasts.value,'$.execution_class_ref')=?
                AND json_type(records.{field},?)='array' LIMIT 1''',
                (classes, forecasts, class_ref, classes)).fetchone()
            if row is not None:
                for value in json.loads(row[0]):
                    scope = ExecutionClass(**value)
                    if (scope.ref == class_ref and scope.phase in PHASE_TO_TOOLS
                            and scope.resource_id == self.resource_id):
                        return scope
        return None
