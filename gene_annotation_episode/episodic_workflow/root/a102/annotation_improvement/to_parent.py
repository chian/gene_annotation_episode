"""Original private A102 annotation to_parent responsibility."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a102.library.report_fact_assembly import facts as _private_report_facts
from gene_annotation_episode.episodic_workflow.root.a102.library.private_policy_call import invoke as _invoke_private_policy
from .. import runtime as _runtime

class ImprovementReportDelivery:
    async def finish(self, record):
        if self.request.report_contract is None:
            result = {"credit": self.workflow.source_credit_view(self)["credit"],
                'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(
                self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return _runtime.Record(result)
        saved = self.workflow.journal.row("runtime_forms", self.episode_id)
        if saved and saved["form"] is not None:
            form = _runtime.json.loads(saved["form"])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = _runtime.form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save("runtime_forms", {"episode_id": self.episode_id,
                "facts": _runtime._json({**facts, "interpretations": self.report_values}), "form": _runtime._json(form)})
        # This is the recorded candidate, not an admitted parent report.
        # The parent's separate report projection/admission can fail without
        # undoing completed science or losing the child's acquisition trace.
        await self.workflow.release(self.episode_id)
        return _runtime.Record({"form": form})

