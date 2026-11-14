"""Original resource-child FBA input controls, outside selected native work.

Only this host's fixed immutable receiving-context controls are replayed.
Arbitrary supplied receipt JSON is never accepted as historical authority.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.bvbrc_appservice_custody import AppServiceCustody, AppServiceCustodyError
from gene_annotation_episode.episodic_workflow.root.a108.communication import plain
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a108.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_contracts import validate_flux_balance_record
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_operands import bind_flux_balance_job_inputs, validate_flux_balance_input_binding_receipt
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.genomic_overlap_result_receipts import read_control
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_file_capture import retained_native_file
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_flux_balance_storage import read_bytes
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.practical_execution_records import validate_assignment
_FORMAT = 'flux_balance_input_binding_receipt_v1'

def _require(condition, code):
    if not condition:
        raise ValueError('flux_balance_execution_input_' + code)

class FluxBalanceExecutionInputs:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.custody = AppServiceCustody(self.store, owner.run_id)
        self.records = EpisodeReturnRecords(self.store, owner.run_id, failure_prefix='flux_balance_execution_input_')

    def validate_selected(self, context, assignment, *, input_versions):
        """Validate original admission only; freeze nothing and grant nothing."""
        return bind_flux_balance_job_inputs(self.store, context, assignment, input_versions=input_versions, reference_access=self.owner.resolve_received_reference)

    def _original(self, context):
        _require(isinstance(context, BindingContext) and context.run_id == self.owner.run_id and (context.role == 'launch_local') and (len(context.path) > 1) and (context.path[-2][0] == 'launch'), 'original_resource_context_required')
        try:
            self.custody.authenticate(context, allow_unsaved=True)
            saved = self.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()
            parent, _ = self.custody._commission(context, unsaved=saved is None)
        except AppServiceCustodyError as error:
            raise ValueError('flux_balance_execution_input_original_commission_invalid') from error
        _require(parent.role == 'launch', 'original_launch_required')
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.flux_balance_request_binding import is_compact_assignment, materialized_assignment, read_request_binding
        if is_compact_assignment(plain(context.assignment)):
            control = read_request_binding(self.store, context.run_id, context.episode_id)
            return (materialized_assignment(self.store, context), control['requests'][0]['input_versions'])
        assignment = validate_assignment(plain(context.assignment))
        _require('native_flux_balance' in assignment['requested_job'], 'original_fba_assignment_required')
        original = plain(parent.assignment)
        versions = original.get('immutable_input_versions')
        _require(type(versions) is list, 'original_versions_required')
        return (assignment, versions)

    def _directory(self, context):
        return Path(self.owner.directory) / 'execution-inputs' / digest({'run_id': context.run_id, 'episode_id': context.episode_id}) / 'native-flux-balance'

    def _new_control_allowed(self, context):
        practical = Path(self.owner.directory) / 'practical-execution' / digest({'run_id': context.run_id, 'episode_id': context.episode_id})
        return not self._directory(context).exists() and (not practical.exists()) and all((self.store.db.execute(f'SELECT 1 FROM {table} WHERE run_id=? AND episode_id=? LIMIT 1', (context.run_id, context.episode_id)).fetchone() is None for table in ('runtime_actions', 'runtime_model_calls', 'runtime_forms', 'runtime_observations')))

    def _validate(self, context, assignment, versions, receipt, file):
        file = validate_flux_balance_record('File', file)
        raw = canonical(receipt).encode('utf-8')
        sha = hashlib.sha256(raw).hexdigest()
        _require(file['format'] == _FORMAT and file['artifact_ref'] == 'artifact_' + sha and (file['sha256'] == sha) and (file['size_bytes'] == len(raw)), 'control_identity_conflict')
        root = self._directory(context)
        _require(read_bytes(root / 'input-binding.json') == raw, 'control_bytes_conflict')
        _require(read_bytes(retained_native_file(self.store, file)) == raw, 'retained_control_conflict')
        receipt = self._validate_frozen_receipt(context, assignment, versions, receipt)
        return {'receipt': receipt, 'file': file}

    def _validate_frozen_receipt(self, context, assignment, versions, receipt):
        try:
            allowed = {(row['reference'], row['record']['record_type']) for row in receipt['witness_records']}
            binding = receipt['binding']
            allowed.update(((row['file']['artifact_ref'], 'artifact') for row in [binding['model'], *binding['prior_sources']]))
        except (KeyError, TypeError) as error:
            raise ValueError('flux_balance_execution_input_original_control_invalid') from error
        return validate_flux_balance_input_binding_receipt(self.store, receipt, context=context, assignment=assignment, input_versions=versions, reference_access=lambda _context, reference, namespace: (reference, namespace) in allowed)

    def received(self, context, *, required=True):
        """Read this receiving context's original control without rebinding it."""
        _require(type(required) is bool, 'invalid_control_requirement')
        assignment, versions = self._original(context)
        root = self._directory(context)
        receipt = read_control(root / 'input-binding.json')
        file = read_control(root / 'input-binding-file.json')
        if not required and receipt is None and (file is None) and self._new_control_allowed(context):
            return None
        _require(receipt is not None and file is not None, 'original_control_required')
        return deepcopy(self._validate(context, assignment, versions, receipt, file))
