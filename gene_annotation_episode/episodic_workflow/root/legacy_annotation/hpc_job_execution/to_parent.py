"""Original fixed hpc execution to_parent responsibilities; source candidate."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.private_policy_call import invoke as _invoke_private_policy
from gene_annotation_episode.episodic_workflow.root.library.report_fact_assembly import facts as _private_report_facts
from ...communication import validate_form
from ...terminal_execution import digest


from .report_fields import HPCReportFields
from .report_references import HPCReportReferences


class HPCToParent(HPCReportFields, HPCReportReferences):
    def facts(self,context,completion_snapshot):
        state=self.state(context);references=[]
        if self.store is not None:
            from ...practical_receipt_information import PracticalReceiptInformation
            information=PracticalReceiptInformation(self.store,context.run_id)
            references=[information.publish(context,receipt) for receipt in state.receipts()]
        return {'practical_completed':state.completion_proof() is not None,
            'practical_receipt_digests':[digest(receipt) for receipt in state.receipts()],
            'practical_receipt_refs':references}

    def validate_report(self,context,form,original_schema):
        validate_form(form,original_schema,lambda reference,namespace:self.resolve(context,reference,namespace))
        facts=self.facts(context,{})
        for name,node in original_schema.get('properties',{}).items():
            source=node.get('x-source')
            if source in facts and form[name]!=facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')



import json
from ...task_values import Record, _json
from ...communication import form_with_facts


class HPCTaskReport:
    async def finish(self, record):
        if self.request.report_contract is None:
            result = {"credit": self.workflow.source_credit_view(self)["credit"],
                'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(
                self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row("runtime_forms", self.episode_id)
        if saved and saved["form"] is not None:
            form = json.loads(saved["form"])
        else:
            facts = _invoke_private_policy(self.workflow.facts, _private_report_facts, self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save("runtime_forms", {"episode_id": self.episode_id,
                "facts": _json({**facts, "interpretations": self.report_values}), "form": _json(form)})
        # This is the recorded candidate, not an admitted parent report.
        # The parent's separate report projection/admission can fail without
        # undoing completed science or losing the child's acquisition trace.
        await self.workflow.release(self.episode_id)
        return Record({"form": form})

