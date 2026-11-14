"""Private portfolio state for A103 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.root.a103 import hpc_queue
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain
from gene_annotation_episode.episodic_workflow.root.a103.library import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.a103.domain import validate_schema




class PortfolioState:
    def state(self, context):
        validate_schema(plain(context.assignment), self.assignment_schema(context.role))
        commission = self._commission(context.assignment, context.scope)
        owner = context.assignment['owner_episode_id']
        directory = self.directory / 'hpc' / hpc_queue.digest([self.run_id, owner])
        ledger = HPCLedger.open_existing(directory)
        original = ledger.read('owner')
        if original['scope'] != plain(context.scope) or self.commission_identity(original) != self.commission_identity(context.assignment):
            raise ValueError('sister_scope_must_equal_original_parent_scope')
        return ledger

    def initialize(self, context):
        ledger = self.state(context)
        prior = prediction.prior_model(ledger.commission['model'])
        ledger.put('model', prior, identity='reference_model')
        if self.memory is not None:
            imported = ledger.once('shared_history_entry', 'shared_history', lambda: self._shared_history(ledger))
            if imported['observations'] and (not ledger.records('model_choice')):
                model = prediction.fit(ledger.commission['model'], imported['observations'])
                reference = ledger.put('model', model)
                ledger.put('model_choice', {'model_ref': reference, 'origin': 'shared_history_entry'}, identity='shared_history_initial_model')

    @staticmethod
    def _current_model(ledger):
        records = ledger.records('model_choice')
        return records[-1]['body']['model_ref'] if records else 'reference_model'
