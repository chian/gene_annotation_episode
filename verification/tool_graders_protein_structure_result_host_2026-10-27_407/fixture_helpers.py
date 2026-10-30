"""Actual native launch, runtime commissions and real406/407 host ports.

This host fixture bypasses the outer Workflow chooser. It is not a claim that
the complete selected-tool route, continuation or parent credit ran.
"""
from copy import deepcopy
from importlib import import_module

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_protein_structure_results import NativeProteinStructureResults
from gene_annotation_episode.native_protein_structure_returns import NativeProteinStructureReturns
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources

ReceiptFixture = import_module(
    "verification.tool_graders_protein_structure_result_receipts_2026-10-27_406.fixture_helpers").ReceiptFixture


def schema_for(*sources, include_result_refs=False):
    registry = protein_structure_fact_sources()
    properties = {"answer_" + str(i): {**registry[source]["report_schema"], "x-source": source}
                  for i, source in enumerate(sources)}
    if include_result_refs:
        properties["result_refs"] = {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
            "x-source": "execution_result_refs"}
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


class HostFixture(ReceiptFixture):
    def __init__(self, store, directory, **kwargs):
        super().__init__(store, directory, **kwargs)
        self.owner.resources = {self.assignment["resource_id"]: self.config}
        self.owner.services = None
        self.owner.acquired_record_unit, self.owner.handoff_unit = 3, 2
        self.owner._selection = lambda *args: ExecutionEpisodes._selection(self.owner, *args)
        self.host = self.owner.native_protein_structure_results = NativeProteinStructureResults(self.owner)
        self.returns = self.owner.native_protein_structure_returns = NativeProteinStructureReturns(self.owner)

    async def collect(self, context, *, index=0, commit=True, name="execution.results.collect"):
        key = self.select(context, name, index=index)
        result = await self.host.execute(context, self.target, name, {}, key)
        if commit:
            self.commit(context, result, index=index)
            self.episode_receipts.receive(context.episode_id, result["record_refs"], kind="own_action", source_index=index)
        return result

    def returned(self, child):
        """Record the actual typed form and frozen receipt to the original parent."""
        parent = self.root
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        facts = self.host.own_fact_groups(child, verify_artifacts=False)
        facts.update({key: value for key, value in self.host.facts(child, verify_artifacts=False).items() if key not in facts})
        form = {name: deepcopy(facts[node["x-source"]]) for name, node in schema["properties"].items()}
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        index = int(child.path[-1][1][6:])
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery-" + digest([parent.episode_id, child.episode_id]), "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        references = self.returns.record_admission(parent, form, schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        references += self.returns._explicit_refs(form, schema)
        self.episode_receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return form
