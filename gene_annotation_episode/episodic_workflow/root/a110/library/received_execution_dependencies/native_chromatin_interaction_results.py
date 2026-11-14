from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.chromatin_interaction_contracts import validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.chromatin_interaction_result_receipts import ChromatinInteractionResultReceipts, decode, empty_facts, require, same, unique
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.chromatin_interaction_return_views import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, requested_chromatin_sources, validate_chromatin_fact_values
from gene_annotation_episode.episodic_workflow.root.a110.native_file_capture import retained_native_file
ORIGIN = {'content_location': 'retained_complete_producer_bundle', 'attempt_output_version': 'original_producer_manifest_and_verified_file_digests', 'window_consistency': 'complete_files_matched_to_original_manifest', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}

def _bundle_files(bundle):
    yield bundle['sheet']
    yield from bundle['tables']

class NativeChromatinInteractionResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = ChromatinInteractionResultReceipts(owner)

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == 'chromatin_interaction_result_selector_v1'

    def retained_target(self, context, assignment, scope):
        assignment, scope = (plain(assignment), plain(scope))
        validate_chromatin_record('ResultSelector', assignment['selector'])
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
            for role in ('sheet', 'components', 'projection'):
                retained_native_file(self.store, files[role])
            for row in files['tables']:
                if row['file'] is not None:
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
        validate_chromatin_fact_values(SAVED_SOURCE, [bundle])
        return tuple(({'episode_id': receipt['intent']['episode_id'], 'operation_key': receipt['intent']['operation_key']} for receipt in self.receipts.completed_receipts(context) if any((same(bundle, row) for row in receipt['facts'][SAVED_SOURCE]))))

    def facts(self, context):
        receipts = self.receipts.completed_receipts(context)
        schema = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {'properties': {}})
        requested = requested_chromatin_sources(schema)
        groups = empty_facts()
        for receipt in receipts:
            for source in requested:
                groups[source].extend(receipt['facts'][source])
        return {**{source: unique(rows) for source, rows in groups.items()}, 'execution_handoff_refs': [], 'execution_result_refs': [], 'execution_blast_hsps': [], 'execution_completed': any((row['delivery_complete'] for row in receipts)), 'execution_result_origin': deepcopy(ORIGIN) if any((row['delivery_complete'] and row['intent']['assignment']['selector']['mode'] == 'native_result' for row in receipts)) else None}


    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, 'artifact'}:
            return False
        return any((file['artifact_ref'] == reference for bundle in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE] for file in _bundle_files(bundle)))

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)
