"""Selected atac action controls and completed-action authority.

These private records belong to the existing results episode. They contain no
calculator and grant no access merely because a file or a private receipt exists.
Completed-action checks use frozen controls and Store metadata, never scientific bytes.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
from typing import Literal, TypedDict

from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.native_file_capture import NativeFileIdentity, _identity
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_contracts import validate_atac_result_record
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, validate_atac_fact_values
from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_worker import validate_atac_result_worker_plan, validate_atac_result_worker_result
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_capture import validate_atac_native_capture
from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import POLICY, atac_driver_argv, validate_atac_requested_job, validate_atac_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


from gene_annotation_episode.episodic_workflow.root.library.atac_result_receipt_values import AtacDifferentialResultIntent, AtacDifferentialHandoffProof, AtacDifferentialNativeSnapshot, AtacDifferentialOrigin, AtacDifferentialQualifiedFiles, AtacDifferentialFactGroups, AtacDifferentialSheetEvidence, AtacDifferentialResultReceipt, AtacDifferentialResultAction, _finite_json_copy, require, closed, same, artifact_references, decode, directory, regular, read_control, immutable, empty_facts, empty_files, unique, outcome, qualified_files, closure_value, VERSION, _READING, _READ_CACHE, _OUTPUTS, _TRACK_ROLES


class AtacResultScientificReceipts:
    @staticmethod
    def _raw_file(table):
        return {"artifact_ref": table["artifact_ref"], "sha256": table["sha256"],
            "size_bytes": table["byte_count"], "format": table["format"]}

    def _calculated_rows(self, manifest):
        """Read a supplied retained table; this projects and never recalculates."""
        from gene_annotation_episode.native_file_capture import retained_native_file
        kind = {"partitions": "Partition", "components": "Component", "regions": "Region"}[manifest["role"]]
        path = retained_native_file(self.store, manifest["file"])
        count = 0
        with path.open("rb") as stream:
            for line in stream:
                require(line.endswith(b"\n"), "atac_result_unsealed_calculated_row")
                row = validate_atac_result_record(kind, decode(line, newline=True))
                count += 1
                yield row
        require(count == manifest["row_count"], "atac_result_calculated_row_count_conflict")
        retained_native_file(self.store, manifest["file"])

    @staticmethod
    def _extent_record(group, report):
        return {"group": group, "binding_key": report["binding_key"],
            "artifact": deepcopy(report["artifact"]), "state": deepcopy(report["state"]),
            "parsed_sha256": report["parsed_sha256"], "parsed_byte_count": report["parsed_byte_count"],
            "data_row_count": report["data_row_count"], "readable_data_row_count": report["readable_data_row_count"],
            "malformed_data_row_count": report["malformed_data_row_count"],
            "reported_numbers": deepcopy(report.get("reported_numbers"))}

    def sheet_evidence(self, action, receipt):
        """Freeze native joins and exact numerical output identities once."""
        from gene_annotation_episode.native_file_capture import retained_native_file
        from gene_annotation_episode.episodic_workflow.root.library.atac_differential_result_views import project_atac_result
        from gene_annotation_episode.episodic_workflow.root.library.native_atac_differential_contracts import producer_ref, validate_atac_command_seal
        self.require_action(action)
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            return None
        path = action.directory / "sheet-evidence.json"
        evidence = read_control(path)
        if evidence is None:
            self.validate_worker(receipt, verify_control_bytes=True)
            sheet = validate_atac_result_record("NativeSheet", decode(retained_native_file(self.store, files["sheet"]).read_bytes()))
            self.file_metadata(files["sheet"], value=sheet)
            requested = receipt["intent"]["target"]["assignment"]["requested_job"]["native_atac_differential"]["request"]
            require(all(same(sheet[key], requested[key]) for key in ("reference", "samples", "conditions")))
            require(sheet["comparison"]["comparison_key"] == requested["comparison_key"])
            saved = receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
            if saved:
                originals = self.origins(self.returns.context(action.intent["episode_id"]), action.intent["assignment"])
                identity = deepcopy(originals[0]["sheet_evidence"]["original_identity"])
                require(all(same(row["sheet_evidence"]["original_identity"], identity) for row in originals))
            else:
                plan = receipt["native"]["original_plan"]
                identity = deepcopy(plan["identity"])
                captured = {row["specification"]["file_key"]: row for row in receipt["capture"]["files"]}
                for ordinal, run in enumerate(sheet["callpeak_bindings"]):
                    step = "callpeak" + str(ordinal + 1)
                    source = captured[step + ".seal"]["retained"]
                    require(run["run_key"] == step and run["producer_ref"] == producer_ref(plan, step))
                    require(run["condition_id"] == requested["conditions"][ordinal]["condition_id"]
                        and run["sample_ids"] == requested["conditions"][ordinal]["sample_ids"]
                        and run["treatment_input_refs"] == [requested["inputs"][ordinal]["file"]["artifact_ref"]]
                        and run["reference_id"] == requested["reference"]["reference_id"])
                    if source is not None and captured[step + ".seal"]["outcome"] == "verified":
                        seal = validate_atac_command_seal(decode(retained_native_file(self.store, source["file"]).read_bytes()),
                            plan=plan, step_key=step)
                        require(run["selected_argv"] == seal["argv"])
                    roles = {"peaks_xls": "peaks_xls", "narrowpeak": "narrowpeak", "summits": "summits",
                        "signal_track": "signal", "background_track": "background"}
                    for role, suffix in roles.items():
                        retained = captured[step + "." + suffix]["retained"]
                        require(run["artifact_roles"][role] == (None if retained is None else retained["file"]["artifact_ref"]))
                require(len(sheet["callpeak_bindings"]) == 2)
            raw_tables = [{"track_key": track["binding"]["track_key"], "table": deepcopy(track["rows"])}
                for track in sheet["tracks"] if type(track["rows"]) is dict]
            qualified_raw = {row["table_key"]: row["file"] for row in files["tables"]}
            for row in raw_tables:
                original = self._raw_file(row["table"])
                if same(qualified_raw.get(row["track_key"]), original):
                    retained_native_file(self.store, original)
                else:
                    require(saved)
            calculations = None
            if files["calculations"] is not None:
                calculations = validate_atac_result_record("Calculations",
                    decode(retained_native_file(self.store, files["calculations"]).read_bytes()))
                self.file_metadata(files["calculations"], value=calculations)
                selected = receipt["intent"]["assignment"]["selector"]
                require(calculations["comparison_key"] == sheet["comparison"]["comparison_key"]
                    and calculations["reference_id"] == sheet["reference"]["reference_id"]
                    and calculations["condition_ids"] == [r["condition_id"] for r in sheet["conditions"]]
                    and same(calculations["parameters"], selected["parameters"])
                    and same(calculations["selected_intervals"], selected["intervals"])
                    and same(calculations["summary"]["depth_selection"], sheet["depth_selection"]))
                manifests = {row["table_key"]: row for row in calculations["tables"]}
                if files["projection"] is not None:
                    kind = selected["projection"]["kind"]
                    kwargs = {}
                    if kind in {"interval_components", "derived_regions"}:
                        key = "components" if kind == "interval_components" else "regions"
                        kwargs["component_rows" if key == "components" else "region_rows"] = (
                            self._calculated_rows(manifests[key]) if key in manifests else None)
                    actual = decode(retained_native_file(self.store, files["projection"]).read_bytes())
                    require(same(project_atac_result(sheet, calculations, selector=selected, **kwargs), actual)
                        and same(actual, receipt["projection"]))
                    self.file_metadata(files["projection"], value=actual)
            else:
                require(receipt["projection"] is None)
            extents = [self._extent_record(group, report) for group in
                ("tracks", "peaks_xls", "narrowpeaks", "summits", "native_differential", "bam_references")
                for report in sheet[group]]
            evidence = {"version": "atac_differential_sheet_evidence_v1", "sheet_file": deepcopy(files["sheet"]),
                "request_sha256": digest(requested), "original_identity": identity,
                **{k: deepcopy(sheet[k]) for k in ("reference", "samples", "conditions", "callpeak_bindings",
                    "comparison", "bam_references", "depth_selection")},
                "parsed_extents": extents, "raw_tables": raw_tables, "calculations": calculations,
                "projection_file": deepcopy(files["projection"]), "native_record_population": False,
                "private_refs": sorted(set(self.store._refs(sheet)) | set(self.store._refs(calculations or {})))}
            evidence["native_record_population"] = self._has_native_population(receipt, evidence)
            self.validate_sheet_evidence(receipt, evidence)
            immutable(path, evidence)
        self.validate_sheet_evidence(receipt, evidence)
        return deepcopy(evidence)

    def validate_sheet_evidence(self, receipt, evidence):
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            require(evidence is None)
            return
        closed(evidence, AtacDifferentialSheetEvidence.__annotations__)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_atac_differential"]["request"]
        require(evidence["version"] == "atac_differential_sheet_evidence_v1"
            and same(evidence["sheet_file"], files["sheet"]) and evidence["request_sha256"] == digest(request)
            and all(same(evidence[key], request[key]) for key in ("reference", "samples", "conditions"))
            and evidence["comparison"]["comparison_key"] == request["comparison_key"])
        self.file_metadata(evidence["sheet_file"])
        saved = receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation"
        identity = evidence["original_identity"]
        require(identity["execution_id"] == receipt["intent"]["target"]["execution_id"]
            and identity["requested_job_sha256"] == receipt["intent"]["target"]["request_sha256"])
        if not saved:
            require(same(identity, receipt["native"]["original_plan"]["identity"]))
        require(type(evidence["raw_tables"]) is list and type(evidence["parsed_extents"]) is list
            and type(evidence["private_refs"]) is list and evidence["private_refs"] == sorted(set(evidence["private_refs"])))
        keys = [row["track_key"] for row in evidence["raw_tables"]]
        track_keys = [evidence["comparison"]["track_keys"][role] for role in _TRACK_ROLES]
        require(len(keys) == len(set(keys)) and keys == [key for key in track_keys if key in keys])
        qualified = {row["table_key"]: row["file"] for row in files["tables"]}
        from gene_annotation_episode.episodic_workflow.root.library.atac_differential_contracts import validate_atac_retained_track_table
        for row in evidence["raw_tables"]:
            closed(row, ("track_key", "table"))
            validate_atac_retained_track_table(row["table"])
            file = self._raw_file(row["table"])
            self.file_metadata(file)
            require(row["track_key"] in qualified)
            if not same(file, qualified[row["track_key"]]):
                # A saved source may disappear or fail its late identity
                # check. Preserve its original manifest; a newly retained
                # corrupt/prefix copy cannot become that source identity.
                calculations = evidence["calculations"]
                require(saved and calculations is not None
                    and any(state["track_key"] == row["track_key"] and not state["exhausted"]
                        for state in calculations["stream_states"])
                    and any(problem["code"] in {"calculation_stream_failed", "saved_attachment_unavailable", "artifact_digest_mismatch"}
                        for problem in calculations["failures"]))
            matching = [record for record in evidence["parsed_extents"] if record["group"] == "tracks"
                and record["binding_key"] == row["track_key"]]
            require(len(matching) == 1 and row["table"]["source_artifact_ref"] == matching[0]["artifact"]["artifact_ref"]
                and row["table"]["row_count"] == matching[0]["readable_data_row_count"])
        calculations = evidence["calculations"]
        require((calculations is None) == (files["calculations"] is None)
            and same(evidence["projection_file"], files["projection"]))
        if calculations is not None:
            validate_atac_result_record("Calculations", calculations)
            self.file_metadata(files["calculations"], value=calculations)
            selector = receipt["intent"]["assignment"]["selector"]
            require(same(calculations["parameters"], selector["parameters"])
                and same(calculations["selected_intervals"], selector["intervals"])
                and calculations["comparison_key"] == selector["comparison_key"]
                and calculations["reference_id"] == evidence["reference"]["reference_id"]
                and calculations["condition_ids"] == [row["condition_id"] for row in evidence["conditions"]]
                and same(calculations["summary"]["depth_selection"], evidence["depth_selection"]))
            captured = {row["table_key"]: row["file"] for row in files["calculated_tables"]}
            require(len({row["table_key"] for row in calculations["tables"]}) == len(calculations["tables"]))
            for table in calculations["tables"]:
                validate_atac_result_record("CalculatedTable", table)
                self.file_metadata(table["file"])
                require(table["table_key"] in captured)
                if captured[table["table_key"]] is not None:
                    require(same(captured[table["table_key"]], table["file"]))
                expected = {"partitions": track_keys,
                    "components": ["partitions"], "regions": ["components"]}[table["role"]]
                require(table["source_table_keys"] == expected)
        require(type(evidence["native_record_population"]) is bool
            and evidence["native_record_population"] == self._has_native_population(receipt, evidence))
        if saved:
            require(same(receipt["intent"]["assignment"]["selector"]["saved_sheet_bundle"], self.evidence_bundle(evidence)))

    @classmethod
    def evidence_bundle(cls, evidence):
        return {"sheet": deepcopy(evidence["sheet_file"]), "tables": [
            {"track_key": row["track_key"], "file": cls._raw_file(row["table"])} for row in evidence["raw_tables"]]}

    def saved_bundle(self, receipt):
        evidence = receipt["sheet_evidence"]
        if evidence is None:
            return None
        self.validate_sheet_evidence(receipt, evidence)
        qualified = {row["table_key"]: row["file"] for row in receipt["qualified_files"]["tables"]}
        bundle = self.evidence_bundle(evidence)
        if any(not same(row["file"], qualified.get(row["track_key"])) for row in bundle["tables"]):
            return None
        return validate_atac_result_record("SavedSheetBundle", bundle)

    def publication(self, receipt, *, originals=None):
        from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import requested_atac_sources
        intent = receipt["intent"]
        context = self.returns.context(intent["episode_id"])
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested, facts = requested_atac_sources(schema), empty_facts()
        projection, bundle = receipt["projection"], self.saved_bundle(receipt)
        issues = list(receipt["host_failures"])
        for capture in (receipt["capture"], receipt["worker_capture"]):
            if capture is not None:
                issues.extend(capture["failures"])
        worker = receipt["worker_capture"]
        if worker is not None and worker["result"] is not None:
            issues.extend(worker["result"]["failures"])
        if projection is not None:
            issues.extend(projection["failures"])
        issues = unique(issues)
        for issue in issues:
            validate_atac_result_record("Failure", issue)
        collecting = intent["tool_name"] == "execution.results.collect"
        if collecting:
            if PROJECTION_SOURCE in requested and projection is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(projection)]
            if SAVED_SOURCE in requested and bundle is not None:
                facts[SAVED_SOURCE] = [bundle]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = deepcopy(issues)
        # Delivery is evaluated against THIS requested result. The original
        # native outcome is preserved; it is not a saved-calculation veto.
        complete = (collecting and projection is not None and receipt["sheet_evidence"] is not None
            and (SAVED_SOURCE not in requested or bundle is not None))
        if complete:
            complete = self.requested_projection_complete(receipt)
        return facts, bool(complete)

    @staticmethod
    def requested_projection_complete(receipt):
        projection = receipt["projection"]
        if projection is None or projection["row_extent"] != "complete":
            return False
        if any(row["code"] in {"requested_field_unavailable", "return_authority_mismatch"}
                for row in projection["failures"]):
            return False
        kind = projection["kind"]
        if kind != "summary":
            total, window = projection["total_rows"], projection["row_window"]
            if total is None or len(projection["rows"]) != min(window["limit"], max(0, total - window["offset"])):
                return False
        evidence = receipt["sheet_evidence"]
        calculations = None if evidence is None else evidence["calculations"]
        if calculations is None:
            return False
        # Native row requests can succeed while an unrelated derived stream
        # failed. Summary/components/regions include those requested streams.
        if kind in {"summary", "interval_components", "derived_regions"}:
            if any(row["code"] == "calculation_stream_failed" for row in calculations["failures"]):
                return False
            if any(not row["exhausted"] for row in calculations["stream_states"]):
                return False
            wanted = {"summary": {"partitions", "components", "regions"},
                "interval_components": {"components"}, "derived_regions": {"regions"}}[kind]
            if any(table["extent"] != "complete" for table in calculations["tables"] if table["role"] in wanted):
                return False
        return True

    @staticmethod
    def _has_native_population(receipt, evidence):
        """Actual native numerical records, or a verified complete empty output."""
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["capture"] is None or receipt["native"] is None or receipt["observation"] is None):
            return False
        observation = receipt["observation"]["native"]
        if not observation["terminal"] or not observation["quiescent"]:
            return False
        files = receipt["capture"]["files"]
        for report in evidence["parsed_extents"]:
            if report["group"] not in {"tracks", "peaks_xls", "narrowpeaks", "summits", "native_differential"}:
                continue
            artifact, state = report["artifact"], report["state"]
            matching = [row for row in files if row["retained"] is not None
                and row["retained"]["file"]["artifact_ref"] == artifact["artifact_ref"]
                and row["specification"]["format"] == artifact["format"]]
            if (state["availability"] != "present" or state["identity"] != "verified"
                    or not any(row["outcome"] == "verified" for row in matching)):
                continue
            if report["readable_data_row_count"] > 0:
                return True
            if report["group"] == "peaks_xls" and report["reported_numbers"] is not None:
                if any(row["state"] == "present" and row["value"] is not None
                        for key, row in report["reported_numbers"].items()
                        if key.startswith("treatment_") and key.endswith(("tags", "fragments"))):
                    return True
            if (report["data_row_count"] == 0 and state["output_extent"] == "complete"
                    and state["format"] == "compatible" and artifact["producer_outcome"] == "succeeded"
                    and artifact["writer_closed"] is True):
                return True
        return False

    def acquisition_population(self, receipt):
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["intent"]["tool_name"] != "execution.results.collect" or receipt["sheet_evidence"] is None):
            return None
        return (digest(receipt["native"]["original_plan"]["identity"])
            if receipt["sheet_evidence"]["native_record_population"] else None)

