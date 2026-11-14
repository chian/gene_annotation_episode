from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.atac_differential_result_contracts import validate_atac_result_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.atac_differential_result_receipts import AtacDifferentialResultReceipts, decode, empty_facts, require, same, unique
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.atac_differential_return_views import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, requested_atac_sources, validate_atac_fact_values
from gene_annotation_episode.episodic_workflow.root.a110.native_file_capture import retained_native_file
ORIGIN = {'content_location': 'retained_original_producer_files', 'attempt_output_version': 'original_producer_manifest_and_verified_file_digests', 'window_consistency': 'captured_files_matched_to_original_occurrences', 'completion_basis': 'qualified_requested_typed_delivery'}
SAVED_ORIGIN = {'content_location': 'received_retained_sheet_and_track_tables', 'attempt_output_version': 'received_saved_sheet_and_table_file_digests', 'window_consistency': 'saved_sheet_and_tables_matched_to_received_bundle', 'completion_basis': 'qualified_requested_typed_delivery'}

def _bundle_files(bundle):
    yield bundle['sheet']
    yield from (row['file'] for row in bundle['tables'])

class NativeAtacDifferentialResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = AtacDifferentialResultReceipts(owner)

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == 'atac_differential_result_selector_v1'

    def retained_target(self, context, assignment, scope):
        assignment, scope = (plain(assignment), plain(scope))
        validate_atac_result_record('ResultSelector', assignment['selector'])
        self.store.validate_scope(scope, parent_scope=plain(context.scope))
        if assignment['selector']['mode'] == 'saved_sheet_recalculation':
            origins = self.receipts.origins(context, assignment)
            require(bool(origins))
            target = deepcopy(origins[0]['intent']['target'])
            require(all((same(row['intent']['target'], target) for row in origins)))
            self.receipts._target(context, assignment, target)
            self.store.validate_scope(target['scope'], parent_scope=scope)
            return target
        if not self.applies(context):
            self.receipts.returns.authenticate(context, allow_unsaved=True)
            return None
        self.receipts._context(context, allow_unsaved=True)
        require(same(assignment, plain(context.assignment)))
        receipts = self.receipts.completed_receipts(context)
        if not receipts:
            return None
        target = receipts[0]['intent']['target']
        require(all((same(row['intent']['target'], target) for row in receipts)))
        return deepcopy(target)

    def _verify_artifacts(self, receipt):
        files = receipt['qualified_files']
        if receipt['facts'][PROJECTION_SOURCE]:
            for role in ('sheet', 'calculations', 'projection'):
                retained_native_file(self.store, files[role])
            wanted = {'interval_components': 'components', 'derived_regions': 'regions'}.get(receipt['projection']['kind'])
            for row in files['calculated_tables']:
                if row['role'] == wanted and row['file'] is not None:
                    retained_native_file(self.store, row['file'])
            require(same(decode(retained_native_file(self.store, files['projection']).read_bytes()), receipt['projection']))
        for bundle in receipt['facts'][SAVED_SOURCE]:
            for file in _bundle_files(bundle):
                retained_native_file(self.store, file)

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool)
        groups = empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                groups[source].extend(receipt['facts'][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def completed_saved_bundle_origins(self, context, bundle):
        validate_atac_fact_values(SAVED_SOURCE, [bundle])
        return tuple(({'episode_id': receipt['intent']['episode_id'], 'operation_key': receipt['intent']['operation_key']} for receipt in self.receipts.completed_receipts(context) if any((same(bundle, row) for row in receipt['facts'][SAVED_SOURCE]))))

    def facts(self, context):
        receipts = self.receipts.completed_receipts(context)
        schema = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {'properties': {}})
        requested = requested_atac_sources(schema)
        groups = empty_facts()
        for receipt in receipts:
            for source in requested:
                groups[source].extend(receipt['facts'][source])
        qualified = [row for row in receipts if row['delivery_complete'] and row['sheet_evidence'] is not None and (row['projection'] is not None) and all((row['qualified_files'][role] is not None for role in ('sheet', 'calculations', 'projection')))]
        origin = None
        if qualified:
            saved = qualified[-1]['intent']['assignment']['selector']['mode'] == 'saved_sheet_recalculation'
            origin = deepcopy(SAVED_ORIGIN if saved else ORIGIN)
        return {**{source: unique(rows) for source, rows in groups.items()}, 'execution_handoff_refs': [], 'execution_result_refs': [], 'execution_blast_hsps': [], 'execution_completed': any((row['delivery_complete'] for row in receipts)), 'execution_result_origin': origin}


    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, 'artifact'}:
            return False
        return any((file['artifact_ref'] == reference for bundle in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE] for file in _bundle_files(bundle)))

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)
