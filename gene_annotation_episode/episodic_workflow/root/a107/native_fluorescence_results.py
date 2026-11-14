"""Selected fluorescence-result operations within the existing results episode.

The native writer, finite numerical worker, return authority and episode
controller retain their separate responsibilities. This host records one
selected operation and publishes its original qualified values.
"""
from __future__ import annotations
from copy import deepcopy
from .communication import plain
from .fluorescence_result_receipts import FluorescenceResultReceipts, empty_facts, require, same, unique
from .fluorescence_return_views import FACT_SOURCES, PROJECTION_SOURCE, CONTEXT_SOURCE, SAVED_SOURCE, requested_fluorescence_sources
from .native_file_capture import retained_native_file
from .native_fluorescence_storage import read_json
ORIGIN = {'content_location': 'retained_selected_producer_artifacts', 'attempt_output_version': 'original_plan_and_verified_file_digests', 'window_consistency': 'independently_authenticated_retained_files', 'completion_basis': 'requested_delivery_for_selected_calculation'}

class NativeFluorescenceResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = FluorescenceResultReceipts(owner)

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == 'fluorescence_result_selector_v1'

    def retained_target(self, context, assignment, scope):
        assignment, scope = (plain(assignment), plain(scope))
        from .fluorescence_result_contracts import validate_fluorescence_selector
        validate_fluorescence_selector(assignment['selector'])
        self.store.validate_scope(scope, parent_scope=plain(context.scope))
        if assignment['selector']['mode'] == 'saved_sheet_recalculation':
            originals = self.receipts.origins(context, assignment)
            target = deepcopy(originals[0]['intent']['target'])
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
            require(same(read_json(retained_native_file(self.store, files['projection'])), receipt['projection']))
        if receipt['facts'][CONTEXT_SOURCE]:
            for role in ('sheet', 'calculations', 'projection', 'context'):
                retained_native_file(self.store, files[role])
            require(same(read_json(retained_native_file(self.store, files['context'])), receipt['context']))
        for file in receipt['facts'][SAVED_SOURCE]:
            retained_native_file(self.store, file)

    def own_fact_groups(self, context, *, verify_artifacts=True):
        require(type(verify_artifacts) is bool)
        groups = empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                groups[source].extend(receipt['facts'][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def facts(self, context):
        receipts = self.receipts.completed_receipts(context)
        schema = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {'properties': {}})
        requested = requested_fluorescence_sources(schema)
        groups = empty_facts()
        for receipt in receipts:
            for source in requested:
                groups[source].extend(receipt['facts'][source])
        return {**{source: unique(rows) for source, rows in groups.items()}, 'execution_handoff_refs': [], 'execution_result_refs': [], 'execution_blast_hsps': [], 'execution_completed': any((row['delivery_complete'] for row in receipts)), 'execution_result_origin': deepcopy(ORIGIN) if any((row['delivery_complete'] and row['intent']['assignment']['selector']['mode'] == 'native_result' for row in receipts)) else None}

    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, 'artifact'}:
            return False
        return any((file['artifact_ref'] == reference for file in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE]))

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)
