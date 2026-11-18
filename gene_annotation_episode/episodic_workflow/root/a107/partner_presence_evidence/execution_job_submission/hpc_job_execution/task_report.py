from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.runtime import Record, _json, form_with_facts, json

class NativeTaskReport:


    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return _live_original_runtime.Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = _live_original_runtime.json.loads(saved['form'])
        else:
            facts = self.workflow.facts(self, completion_record=record)
            form = _live_original_runtime.form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _live_original_runtime._json({**facts, 'interpretations': self.report_values}), 'form': _live_original_runtime._json(form)})
        await self.workflow.release(self.episode_id)
        return _live_original_runtime.Record({'form': form})
from gene_annotation_episode.episodic_workflow.root.a107 import runtime as _live_original_runtime
