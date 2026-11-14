import asyncio
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a104.execution_job_submission.api_job_execution.api_service import APIJobService as APIServiceExecution
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_transport_fixture import CONFIG, PREFIX
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.commissioned_records_fixture import SavedRecords
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_input_fixture import Driver, NativeClient

class ProductionDriver(Driver):

    def __init__(self, store, directory):
        self.saved, self.store = (SavedRecords(store), store)
        self.api = APIServiceExecution(store, run_id=self.saved.run_id, directory=directory, configuration={'selected-api': CONFIG}, tool_registry=SimpleNamespace(store=store, clients={}), handoff_unit=2, acquired_record_unit=3)
        self.client = NativeClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = (self.api.appservice.records, self.api.appservice.custody)
        self.last_outcome = None

    def invoke(self, context, suffix, args, key):
        outcome = asyncio.run(self.api.execute(context, PREFIX + suffix, args, key))
        self.last_outcome = outcome
        if outcome['status'] in {'completed', 'partial'}:
            index = int(key.rsplit(':', 1)[1])
            row = self.saved.journal.row('runtime_actions', context.episode_id, index)
            self.saved.journal.save('runtime_actions', {**row, 'result': canonical(outcome), 'credit': 0})
            self.saved.receipts.receive(context.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
        return outcome

    def call(self, suffix, args, *, context=None):
        context, key = self.selection(suffix, args, context=context)
        outcome = self.invoke(context, suffix, args, key)
        assert outcome['status'] in {'completed', 'partial'}, outcome
        ref = outcome['result'].get('handoff_ref') or outcome['result']['support_receipt_ref']
        return self.records.read(ref)
