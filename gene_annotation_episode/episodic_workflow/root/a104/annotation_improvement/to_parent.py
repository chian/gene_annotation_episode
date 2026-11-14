"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

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
        facts = self.workflow.facts(self, completion_record=record)
        form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
        self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _json({**facts, 'interpretations': self.report_values}), 'form': _json(form)})
    await self.workflow.release(self.episode_id)
    return Record({'form': form})

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['finish']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'finish': 'finish'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
