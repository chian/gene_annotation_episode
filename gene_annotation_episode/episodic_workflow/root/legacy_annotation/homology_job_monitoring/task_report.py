from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.library.report_fact_assembly import facts as _private_report_facts
import json
from gene_annotation_episode.episodic_workflow.root.task_values import _json
from gene_annotation_episode.episodic_workflow.root.task_values import Record, _json
from gene_annotation_episode.episodic_workflow.root.task_values import Record, _json
from gene_annotation_episode.episodic_workflow.root.communication import form_with_facts
from gene_annotation_episode.episodic_workflow.root.task_values import _json
from gene_annotation_episode.episodic_workflow.root.communication import form_with_facts

class LegacyHomologyMonitoringTaskReport:

    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = json.loads(saved['form'])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _json({**facts, 'interpretations': self.report_values}), 'form': _json(form)})
        await self.workflow.release(self.episode_id)
        return Record({'form': form})
