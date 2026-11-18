"""Private scientific report delivery."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.runtime import Record, _json, form_with_facts, json

class ScientificReportDelivery:

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


def _bind_scientific_runtime_providers(namespace):
    from ..library.live_runtime_functions import bind_functions
    names = {'finish': 'ScientificReportDelivery.finish'}
    functions = bind_functions(namespace, {name: ScientificReportDelivery.__dict__[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a106.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.report_delivery')
    for name, function in functions.items():
        setattr(ScientificReportDelivery, name, function)

from .. import runtime as _original_runtime
_bind_scientific_runtime_providers(vars(_original_runtime))
