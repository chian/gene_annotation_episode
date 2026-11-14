"""Selected protein result acquisition, qualification and requested publication."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import ORIGIN
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import _require, _problem, _unique, _empty_files, _empty_facts, _outcome
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import FACT_SOURCES, requested_sources
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_acquisition import ProteinStructureResultAcquisition
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_credit import ProteinStructureResultCredit
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_publication import ProteinStructureResultPublication
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_receipts import ProteinResultBody, ProteinResultPublication, ProteinResultReceipts
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_science import ProteinStructureResultScience
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_acquisition import is_native_protein_structure_target
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinFactGroups, ProteinResultAuthorityRecord, ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import ResultCustody, issue, same
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import validate_protein_structure_failure_return
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import validate_protein_structure_result_selector
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import digest


def operation_catalog() -> list[dict]:
    return [
        {"name": "execution.results.status", "description":
         "Read the selected original protein attempt or retained-input status.",
         "input_schema": obj({})},
        {"name": "execution.results.collect", "description":
         "Acquire and qualify the selected original protein result, or recalculate the explicitly received saved sheet, and return the requested fields.",
         "input_schema": obj({})},
    ]


class NativeProteinStructureResults(ProteinStructureResultAcquisition, ProteinStructureResultScience, ProteinStructureResultPublication, ProteinStructureResultCredit):
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.receipts = ProteinResultReceipts(owner)

    @property
    def _returns(self):
        # Construction precedes installation of the owner's returns adapter.
        return self.owner.native_protein_structure_returns

    def applies(self, context) -> bool:
        assignment = plain(context.assignment)
        return (context.role == "results" and isinstance(assignment, dict)
                and isinstance(assignment.get("selector"), dict)
                and assignment["selector"].get("version") == "protein_structure_result_selector_v1")

    async def execute(self, context, target, tool_name, arguments, operation_key) -> dict:
        _require(self.applies(context) and is_native_protein_structure_target(target))
        request = target["assignment"]["requested_job"]["native_protein_structure"]["request"]
        selector = validate_protein_structure_result_selector(plain(context.assignment)["selector"], request=request)
        _require(tool_name in {row["name"] for row in operation_catalog()} and arguments == {})
        async with self.receipts.locked_action(context, target=target, tool_name=tool_name,
                arguments=arguments, operation_key=operation_key) as action:
            staged = self.receipts.read_staged(action)
            if staged is not None:
                return _outcome(staged)
            collecting = tool_name == "execution.results.collect"
            body: ProteinResultBody = {"version": "protein_structure_result_body_v1", "intent": deepcopy(action.intent),
                "handoff_proof": None, "observation": None, "observation_origin": "not_observed",
                "original_custody": None, "capture": None, "bundle": None, "worker": None,
                "qualified_files": _empty_files(), "calculation": None, "issues": [],
                "native_success": False, "capture_complete": False}
            scientific, source_record = None, None
            try:
                operation = self._saved if selector["acquisition"] == "retained_sheet_only" else self._original
                scientific, source_record = await operation(action, context, target, body, collecting=collecting)
            except (ValueError, OSError) as error:
                body["issues"].append(_problem(error))
            publication: ProteinResultPublication = self._publication(body, scientific, source_record, collecting=collecting)
            publication["family_artifact_refs"] = self._family_artifacts(action, body, publication)
            return _outcome(self.receipts.publish(action, body=body, publication=publication))

    def read_result_authority(self, custody: ResultCustody, *, scope: dict) -> ProteinResultAuthorityRecord:
        # The existing return schema validates the complete custody shape and
        # key formula without interpreting or opening its scientific operands.
        try:
            validate_protein_structure_failure_return({"version": "protein_structure_failure_return_v1",
                "custody": custody, "projection_id": None,
                "issue": issue("original_commission_mismatch", stage="authority", field="receipt")})
            _require(custody is not None and custody["run_id"] == self.owner.run_id)
            receipt = self.receipts.read_completed(episode_id=custody["result_episode_id"],
                operation_key=custody["result_operation_key"], scope=plain(scope))
            _require(same(custody, receipt["publication"]["custody"]))
        except (ValueError, TypeError, KeyError) as error:
            raise ProteinStructureOperandError(_problem(error, stage="authority", field="receipt")) from error
        body = receipt["body"]
        job = body["bundle"]["requested_job"]["native_protein_structure"]
        return deepcopy({"custody": custody, "selector": body["intent"]["assignment"]["selector"],
            "request": job["request"], "software": job["software"],
            **body["qualified_files"], "facts": receipt["publication"]["facts"]})

    def own_fact_groups(self, context, *, verify_artifacts: bool) -> ProteinFactGroups:
        _require(type(verify_artifacts) is bool)
        facts = _empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                facts[source].extend(receipt["publication"]["facts"][source])
        return {source: _unique(rows) for source, rows in facts.items()}

    def owns_reference(self, reference: str) -> bool:
        return self.receipts.owns_reference(reference)

    def facts(self, context, *, verify_artifacts: bool = True) -> dict:
        receipts = self.receipts.completed_receipts(context)
        requested = requested_sources(plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {}))
        groups = _empty_facts()
        for receipt in receipts:
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in requested:
                groups[source].extend(receipt["publication"]["facts"][source])
        return {**{source: _unique(rows) for source, rows in groups.items()},
            "execution_handoff_refs": [], "execution_blast_hsps": [],
            "execution_result_refs": list(dict.fromkeys(ref for receipt in receipts for ref in receipt["publication"]["record_refs"])),
            "execution_completed": any(receipt["publication"]["delivery_complete"] for receipt in receipts),
            "execution_result_origin": deepcopy(ORIGIN) if any(
                receipt["publication"]["delivery_complete"] and receipt["body"]["native_success"]
                and receipt["body"]["capture_complete"]
                and receipt["body"]["intent"]["assignment"]["selector"]["acquisition"] == "complete_bound_bundle"
                for receipt in receipts) else None}

    def completion(self, context) -> dict | None:
        for receipt in self.receipts.completed_receipts(context):
            if receipt["publication"]["delivery_complete"]:
                intent = receipt["body"]["intent"]
                saved = intent["assignment"]["selector"]["acquisition"] == "retained_sheet_only"
                return {"version": "practical_completion_v1", "run_id": context.run_id, "episode_id": context.episode_id,
                    "assignment_sha256": digest(plain(context.assignment)), "endpoint": "usable_handoff",
                    "operation_key": intent["operation_key"], "receipt_sha256": digest(receipt),
                    "validation_keys": ["original_protein_result_commission",
                        "retained_original_sheet_custody" if saved else "complete_sealed_bundle_acquisition",
                        "requested_protein_projection_or_explicit_unavailability"]}
        return None

