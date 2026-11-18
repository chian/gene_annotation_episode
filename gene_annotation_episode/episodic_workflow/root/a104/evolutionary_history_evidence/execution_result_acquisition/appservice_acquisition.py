from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_record_values import *
from gene_annotation_episode.episodic_workflow.root.a104.library.appservice_record_access import AppServiceRecordAccess

class AppServiceAcquisition(AppServiceRecordAccess):

    def __init__(self, execution):
        self.api, self.store, self.run_id = (execution, execution.store, execution.run_id)
        self.records = AppServiceRecords(execution)
        self.custody = AppServiceCustody(self.store, self.run_id, read_original_handoff=self.original_handoff)
        self.inputs = AppServiceInputs(execution, records=self.records, custody=self.custody, read_acquisition=self.read_acquisition)
        from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.appservice_publication import AppServicePublication as AppServicePublications
        self.publications = AppServicePublications(self)

    def _own_receipts(self, context):
        if not self.owns_context(context):
            return []
        self.custody.authenticate(context, allow_unsaved=True)
        rows = []
        for _, outcome in self.api._own_outcomes(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            result = outcome.get('result') or {}
            reference = result.get('handoff_ref') or result.get('support_receipt_ref')
            if reference is not None:
                rows.append(self.records.read(reference))
        return rows

    def facts(self, context):
        rows = self._own_receipts(context)
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        facts = {'execution_handoff_refs': [r['source_ref'] for r in rows if r['contract'] == 'TaskHandoff'], SUPPORT_SOURCE: [r['source_ref'] for r in rows if r['contract'] != 'TaskHandoff'], 'execution_result_refs': self.publications.own_results(context), 'execution_blast_hsps': [], 'execution_completed': self.completion(context) is not None}
        for returns in (self.api.homology_returns, self.api.phylogeny_returns, self.api.proteome_returns):
            supplied = returns.facts(context, schema)
            if set(facts).intersection(supplied):
                raise ValueError('appservice_own_fact_source_conflict')
            facts.update(supplied)
        return facts

    def completion(self, context):
        return self.publications.completion(context)

    def publish_acquisition(self, context, prepared, event, snapshot, *, common_receipt, operation_key):
        return self.publications.publish(context, prepared, event, snapshot, common_receipt=common_receipt, operation_key=operation_key)
