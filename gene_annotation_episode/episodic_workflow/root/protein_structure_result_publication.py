"""Original requested projection publication, custody and artifact family classification."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_publication import publish_structure_sequence_reference
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import _require, _problem, _unique, _empty_facts, _result_key
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_acquisition import decode_protein_structure_json
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import ResultCustody, issue, validate_saved_sheet_descriptor, validate_structure_sequence_descriptor
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_projection_publication import publish_protein_structure_projection
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import project_protein_structure_results, validate_protein_structure_failure_return
from gene_annotation_episode.execution_contracts import digest
from pathlib import Path
import hashlib
import json
import os
import stat


class ProteinStructureResultPublication:
    def _custody(self, body, source_record) -> ResultCustody | None:
        if source_record is None:
            return None
        intent = body["intent"]
        return {"run_id": intent["run_id"], "result_episode_id": intent["episode_id"],
            "result_operation_key": intent["operation_key"], "result_receipt_key": _result_key(intent),
            "handoff_ref": intent["assignment"]["handoff_ref"], "source_ref": source_record["id"],
            "bundle_artifact_ref": body["capture"]["bundle_file"]["artifact_ref"],
            "original_request_sha256": intent["original_request_sha256"]}

    def _publication(self, body, scientific, source_record, *, collecting):
        selector = body["intent"]["assignment"]["selector"]
        saved = selector["acquisition"] == "retained_sheet_only"
        facts, references = _empty_facts(), []
        custody = self._custody(body, source_record)
        accounting = {"projection_ids": [], "failed_projection_ids": [],
            "saved_sheet": "unavailable" if collecting and selector["return_saved_sheet"] else "not_requested",
            "sequence": "unavailable" if collecting and selector["sequence_allowed_uses"] else "not_requested"}
        if collecting and custody is not None and scientific is not None:
            if scientific["kind"] == "extraction" and selector["sequence_allowed_uses"]:
                files, sequence = body["qualified_files"], scientific["sequence"]
                if files["sequence_file"] is not None and files["residue_map_file"] is not None:
                    try:
                        reference = publish_structure_sequence_reference(self.store, source_ref=source_record["id"],
                            sequence=sequence, sequence_file=files["sequence_file"], residue_map_file=files["residue_map_file"])
                        descriptor = validate_structure_sequence_descriptor({"version": "structure_sequence_descriptor_v1",
                            "custody": deepcopy(custody), "reference_ref": reference,
                            "sequence_file": deepcopy(files["sequence_file"]), "residue_map_file": deepcopy(files["residue_map_file"]),
                            "structure_file": deepcopy(sequence["selection"]["file_identity"]),
                            "selection": deepcopy(sequence["selection"]), "sequence_length": sequence["sequence_length"],
                            "allowed_uses": deepcopy(selector["sequence_allowed_uses"])})
                        scientific["descriptor"] = descriptor
                        facts[SEQUENCE_SOURCE].append(descriptor)
                        references.append(self.store.get(reference))
                        accounting["sequence"] = "published"
                    except (ValueError, OSError) as error:
                        body["issues"].append(_problem(error, role="sequence"))
            if scientific["kind"] == "comparison" and selector["return_saved_sheet"]:
                descriptor = (deepcopy(selector["saved_sheet"]) if saved else validate_saved_sheet_descriptor({
                    "version": "protein_structure_saved_sheet_v1", "custody": deepcopy(custody),
                    "sheet_file": deepcopy(body["qualified_files"]["sheet_file"]),
                    "original_components_file": deepcopy(body["qualified_files"]["original_components_file"]),
                    "operation": "compare_protein_structures", "original_mode": scientific["sheet"]["scientific_mode"],
                    "allowed_uses": ["recalculate", "select_projection", "use_transform"]}))
                facts[SAVED_SOURCE].append(descriptor)
                accounting["saved_sheet"] = "published"
        if collecting:
            for name, role in (("saved_sheet", None), ("sequence", "sequence")):
                if accounting[name] == "unavailable":
                    body["issues"].append(issue("selected_field_unavailable", stage="projection", field="descriptor", artifact_role=role))
            operation_issues = _unique(body["issues"])
            # A failure in one requested population cannot discard another.
            for selection in selector["projections"]:
                try:
                    if scientific is None or custody is None:
                        raise ValueError("selected_field_unavailable")
                    rows, = project_protein_structure_results(scientific, selection=[selection])
                    value = publish_protein_structure_projection(self.store, rows=rows,
                        custody=custody, calculation=body["calculation"])
                except (ValueError, OSError) as error:
                    problem = _problem(error, stage="projection", field="projection_fields")
                    body["issues"].append(problem)
                    facts[FAILURE_SOURCE].append(validate_protein_structure_failure_return({
                        "version": "protein_structure_failure_return_v1", "custody": deepcopy(custody),
                        "projection_id": selection["projection_id"], "issue": problem}))
                    accounting["failed_projection_ids"].append(selection["projection_id"])
                else:
                    facts[PROJECTION_SOURCE].append(value)
                    accounting["projection_ids"].append(selection["projection_id"])
            body["issues"] = _unique(body["issues"])
            facts[FAILURE_SOURCE] = [validate_protein_structure_failure_return({
                "version": "protein_structure_failure_return_v1", "custody": deepcopy(custody),
                "projection_id": None, "issue": problem}) for problem in operation_issues] + facts[FAILURE_SOURCE]
        else:
            body["issues"] = _unique(body["issues"])
        worker_result = None if body["worker"] is None else body["worker"]["result"]
        complete = bool(collecting and custody is not None and body["handoff_proof"] is not None
            and worker_result is not None and (scientific is not None and scientific["kind"] == "comparison"
                if saved else body["capture_complete"]))
        return {"version": "protein_structure_result_publication_v1", "body_sha256": digest(body),
            "result_receipt_key": _result_key(body["intent"]), "custody": custody,
            "source_record": deepcopy(source_record), "reference_records": references, "facts": facts,
            "accounting": accounting, "record_refs": [] if source_record is None else [source_record["id"]],
            "family_artifact_refs": [], "delivery_complete": complete}

    def _family_artifacts(self, action, body, publication):
        references = []
        def add(value):
            if value is not None and value not in references:
                self.store._require(value, {"artifact"})
                references.append(value)
        capture = body["capture"]
        if capture is not None:
            if capture["bundle_file"] is not None:
                add(capture["bundle_file"]["artifact_ref"])
            for row in capture["files"]:
                if row["observed"] is not None:
                    add(row["observed"]["artifact_ref"])
        worker = body["worker"]
        if worker is not None:
            prepared, execution = worker["prepared"], worker["execution"]
            for name in ("plan_artifact_ref", "execution_receipt_artifact_ref", "worker_result_artifact_ref"):
                add(prepared[name])
            for row in prepared["diagnostic_files"]:
                add(row["artifact_ref"])
            for name in ("stdout_artifact_ref", "stderr_artifact_ref", "handle_artifact_ref"):
                add(execution[name])
            # 396 already retained these exact controls. Only their existing
            # identities join classification; no implicit artifact acquisition.
            paths = []
            if execution["handle_artifact_ref"] is not None:
                handle = decode_protein_structure_json(self.store.get_artifact(execution["handle_artifact_ref"]), canonical_bytes=False)
                paths.extend(Path(value) for value in handle["paths"].values())
            paths.append(action.worker_directory / "intent.json")
            for path in paths:
                _require(path.parent == action.worker_directory, "invalid_output_path")
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
                except FileNotFoundError:
                    continue
                try:
                    _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
                    with os.fdopen(os.dup(fd), "rb") as stream:
                        raw = stream.read()
                finally:
                    os.close(fd)
                ref = "artifact_" + hashlib.sha256(raw).hexdigest()
                try:
                    self.store._require(ref, {"artifact"})
                except ContractError as error:
                    if str(error) == "unknown_reference":
                        continue
                    raise
                add(ref)
        for file in body["qualified_files"].values():
            if file is not None:
                add(file["artifact_ref"])
        for projection in publication["facts"][PROJECTION_SOURCE]:
            if projection["delivery"]["kind"] == "artifact":
                add(projection["delivery"]["table_file"]["artifact_ref"])
        return references

