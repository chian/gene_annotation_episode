"""Selected chromatin action controls and completed-action authority.

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
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_contracts import Failure, NativeFileIdentity, RequestedProjection, _finite_json, validate_chromatin_record
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE, validate_chromatin_fact_values
from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_result_worker import validate_chromatin_result_worker_plan, validate_chromatin_result_worker_result, _validate_capture
from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_capture import validate_chromatin_native_capture
from gene_annotation_episode.episodic_workflow.root.library.native_chromatin_interaction_contracts import POLICY, TABLE_ROLES, TABLE_NAMES, chromatin_driver_argv, validate_chromatin_requested_job, validate_chromatin_run_plan, _dependency_roots
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_receipt
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation


from gene_annotation_episode.episodic_workflow.root.library.chromatin_result_receipt_values import ChromatinInteractionResultIntent, ChromatinInteractionHandoffProof, ChromatinInteractionNativeSnapshot, ChromatinInteractionOrigin, ChromatinInteractionQualifiedFiles, ChromatinInteractionFactGroups, ChromatinInteractionSheetEvidence, ChromatinInteractionResultReceipt, ChromatinInteractionResultAction, _finite_json_copy, require, closed, same, decode, directory, regular, read_control, immutable, empty_facts, empty_files, unique, outcome, qualified_files, closure_value, VERSION, _READING, _READ_CACHE, _OUTPUTS


class ChromatinResultScientificReceipts:
    def sheet_evidence(self, action, receipt):
        """Read actual captured output once, then retain its compact joins."""
        from gene_annotation_episode.native_file_capture import retained_native_file
        from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_result_views import project_chromatin_result, _validate_joins
        self.require_action(action)
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            return None
        path = action.directory / "sheet-evidence.json"
        evidence = read_control(path)
        if evidence is None:
            self.validate_worker(receipt)
            sheet = validate_chromatin_record("ContactSheet", decode(retained_native_file(self.store, files["sheet"]).read_bytes()))
            self.file_metadata(files["sheet"], value=sheet)
            require(same(sheet["request"], receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]))
            evidence = {"version": "chromatin_interaction_sheet_evidence_v1", "sheet_file": deepcopy(files["sheet"]),
                "request_sha256": digest(sheet["request"]), "populations": [
                    {k: deepcopy(v) for k, v in p.items() if k not in ("element_anchor_rows", "pair_rows")}
                    for p in sheet["populations"]], "data_tables": deepcopy(sheet["data_tables"])}
            self.validate_sheet_evidence(receipt, evidence)
            for file in files["tables"]:
                if file["file"] is not None:
                    retained_native_file(self.store, file["file"])
            if files["components"] is not None:
                components = validate_chromatin_record("ChromatinComponents",
                    decode(retained_native_file(self.store, files["components"]).read_bytes()))
                self.file_metadata(files["components"], value=components)
                require(components["source_sheet_sha256"] == files["sheet"]["sha256"]
                    and same(components["table_identities"], [d["file"] for d in sheet["data_tables"] if d["file"] is not None])
                    and same(components["parameters"], action.intent["assignment"]["selector"]["parameters"]))
                # C2 validates all component/population/table/row joins and
                # selects the requested fields. It does not recalculate them.
                _validate_joins(sheet, components, action.intent["assignment"]["selector"])
                if files["projection"] is not None:
                    projected = project_chromatin_result(sheet, components, selector=action.intent["assignment"]["selector"])
                    actual = decode(retained_native_file(self.store, files["projection"]).read_bytes())
                    require(same(actual, projected) and same(actual, receipt["projection"]))
                    self.file_metadata(files["projection"], value=actual)
            else:
                require(files["projection"] is None and receipt["projection"] is None)
            immutable(path, evidence)
        self.validate_sheet_evidence(receipt, evidence)
        return deepcopy(evidence)

    def validate_sheet_evidence(self, receipt, evidence):
        files = receipt["qualified_files"]
        if files["sheet"] is None:
            require(evidence is None)
            return
        closed(evidence, ChromatinInteractionSheetEvidence.__annotations__)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]
        require(evidence["version"] == "chromatin_interaction_sheet_evidence_v1"
            and same(evidence["sheet_file"], files["sheet"]) and evidence["request_sha256"] == digest(request))
        self.file_metadata(evidence["sheet_file"])
        populations, descriptors = evidence["populations"], evidence["data_tables"]
        require(type(populations) is list and type(descriptors) is list
            and [p["selected_region"] for p in populations] == request["populations"])
        keys = [d["table_key"] for d in descriptors]
        require(len(keys) == len(set(keys)) and keys == [r["table_key"] for r in files["tables"]])
        outputs = receipt["worker_capture"]["result"]["outputs"][4:]
        require(len(outputs) == len(descriptors))
        for p in populations:
            validate_chromatin_record("PopulationExtraction", p)
            chosen = [d for d in descriptors if d["population_key"] == p["population_key"]]
            require(p["population_key"] == p["selected_region"]["population_key"]
                and [d["role"] for d in chosen] == list(TABLE_ROLES)
                and p["data_table_keys"] == [d["table_key"] for d in chosen]
                and same(p["normalization"]["specification"], request["normalization"]))
        require(len(descriptors) == 5 * len(populations))
        for d, output, captured in zip(descriptors, outputs, files["tables"]):
            validate_chromatin_record("TableDescriptor", d)
            declaration = output["declaration"]
            ordinal = next(i for i, p in enumerate(populations) if p["population_key"] == d["population_key"])
            require(output["table_key"] == d["table_key"] == captured["table_key"]
                and declaration["format"] == "chromatin_contact_tables_v1:" + d["role"]
                and declaration["relative_path"] == f"tables/p{ordinal}/" + TABLE_NAMES[TABLE_ROLES.index(d["role"])])
            if d["file"] is not None:
                self.file_metadata(d["file"])
                require(d["file"]["format"] == declaration["format"])
                # A saved file lost during a new use is not a smaller bundle.
                if captured["file"] is not None:
                    require(same(d["file"], captured["file"]))
                if declaration["state"] == "present":
                    require(all(declaration[k] == d["file"][k] for k in ("sha256", "size_bytes")))
            else:
                require(captured["file"] is None and declaration["state"] == "absent")
        selector = receipt["intent"]["assignment"]["selector"]
        if selector["mode"] == "saved_sheet_recalculation":
            require(same(selector["saved_sheet_bundle"], self.evidence_bundle(evidence)))

    @staticmethod
    def evidence_bundle(evidence):
        return {"sheet": deepcopy(evidence["sheet_file"]),
            "tables": [deepcopy(d["file"]) for d in evidence["data_tables"] if d["file"] is not None]}

    def saved_bundle(self, receipt):
        evidence = receipt["sheet_evidence"]
        if evidence is None:
            return None
        self.validate_sheet_evidence(receipt, evidence)
        if any(d["file"] is not None and not same(d["file"], r["file"])
                for d, r in zip(evidence["data_tables"], receipt["qualified_files"]["tables"])):
            return None
        return self.evidence_bundle(evidence)

    def publication(self, receipt, *, originals=None):
        from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import requested_chromatin_sources
        intent = receipt["intent"]
        context = self.returns.context(intent["episode_id"])
        schema = plain(context.request).get("report_contract", {}).get("measurements", {}).get("schema", {"properties": {}})
        requested, facts = requested_chromatin_sources(schema), empty_facts()
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
        if intent["tool_name"] == "execution.results.collect":
            if PROJECTION_SOURCE in requested and projection is not None:
                facts[PROJECTION_SOURCE] = [deepcopy(projection)]
            if SAVED_SOURCE in requested and bundle is not None:
                facts[SAVED_SOURCE] = [bundle]
            if FAILURE_SOURCE in requested:
                facts[FAILURE_SOURCE] = self.selected_failures(receipt, issues)
        complete = (intent["tool_name"] == "execution.results.collect" and projection is not None
            and not receipt["host_failures"] and (SAVED_SOURCE not in requested or bundle is not None))
        if intent["assignment"]["selector"]["mode"] == "native_result":
            complete = complete and self.original_acquisition_complete(receipt)
        else:
            originals = self.origins(context, intent["assignment"]) if originals is None else originals
            complete = complete and any(self.original_acquisition_complete(row) for row in originals)
        return facts, bool(complete)

    def selected_failures(self, receipt, issues):
        selector = receipt["intent"]["assignment"]["selector"]
        selected = set(selector["population_keys"])
        selection = selector["projection"].get("selection", {})
        pairs = ({r["pair_key"] for r in receipt["projection"]["rows"] if "pair_key" in r}
            if receipt["projection"] is not None else
            set(selection.get("pair_keys", ())) if selection.get("by") == "keys" else None)
        request = receipt["intent"]["target"]["assignment"]["requested_job"]["native_chromatin_interactions"]["request"]
        files = [] if receipt["capture"] is None else receipt["capture"]["files"]
        result = []
        for issue in unique(issues):
            validate_chromatin_record("Failure", issue)
            if issue["population_key"] is not None and issue["population_key"] not in selected:
                continue
            if pairs is not None and issue["pair_key"] is not None and issue["pair_key"] not in pairs:
                continue
            path = issue["field_path"] or ""
            if path == "/outputs/table" and receipt["sheet_evidence"] is not None and receipt["worker_capture"] is not None:
                populations = {d["table_key"]: d["population_key"] for d in receipt["sheet_evidence"]["data_tables"]}
                affected = [r["table_key"] for r in receipt["worker_capture"]["outputs"] if r["role"] == "table"
                    and r["capture"]["outcome"] not in {"verified", "declared_absent"}]
                if affected and all(key in populations and populations[key] not in selected for key in affected):
                    continue
            match = re.match(r"^/(?:files/)?p([0-9]+)\.", path)
            if match and int(match[1]) < len(request["populations"]) and request["populations"][int(match[1])]["population_key"] not in selected:
                continue
            match = re.match(r"^/(populations|files)/(0|[1-9][0-9]*)(?:/|$)", path)
            if match:
                rows = request["populations"] if match[1] == "populations" else [r["specification"] for r in files]
                if int(match[2]) < len(rows) and rows[int(match[2])].get("population_key") not in (None, *selected):
                    continue
            result.append(issue)
        return result

    def _population_acquired(self, receipt, population, *, complete=False):
        """Actual captured bins/contact rows, or a proved empty sparse read."""
        evidence, capture = receipt["sheet_evidence"], receipt["capture"]
        if evidence is None or capture is None or receipt["native"] is None:
            return False
        obs = receipt["observation"]
        if obs is None or not obs["native"]["terminal"] or not obs["native"]["quiescent"]:
            return False
        key = population["population_key"]
        tables = {d["role"]: d for d in evidence["data_tables"] if d["population_key"] == key}
        for role in ("bins", "contacts"):
            d = tables[role]
            original, = [r for r in capture["files"] if r["specification"]["role"] == role
                and r["specification"]["population_key"] == key]
            current = next(r for r in receipt["qualified_files"]["tables"] if r["table_key"] == d["table_key"])
            if (d["file"] is None or not same(current["file"], d["file"]) or original["retained"] is None
                    or original["capture"] is None or original["capture"]["outcome"] != "verified"
                    or original["declaration_source"] not in ("bundle", "population")
                    or not same(original["retained"]["file"], d["file"])):
                return False
        read = population["read_evidence"]
        full = (population["extent"] == "complete" and all(read[k] == "complete"
            for k in ("axes_extent", "index_extent", "selected_records_extent")) and not read["failed_block_ids"])
        if complete:
            return full
        if population["raw_cell_population"]["validated_observed_row_count"] > 0:
            return population["extent"] in ("complete", "partial")
        return full and read["implicit_zero_semantics"] == "validated_sparse_absence"

    def original_acquisition_complete(self, receipt):
        if receipt["intent"]["assignment"]["selector"]["mode"] == "saved_sheet_recalculation":
            context = self.returns.context(receipt["intent"]["episode_id"])
            return any(self.original_acquisition_complete(row) for row in self.origins(context, receipt["intent"]["assignment"]))
        observation, capture, evidence = receipt["observation"], receipt["capture"], receipt["sheet_evidence"]
        return bool(observation is not None and observation["state"] == "completed" and observation["returncode"] == 0
            and capture is not None and capture["driver_state"] == "sealed_bundle" and capture["bundle"] is not None
            and not capture["failures"] and evidence is not None and evidence["populations"]
            and all(self._population_acquired(receipt, p, complete=True) for p in evidence["populations"]))

    def acquisition_population(self, receipt):
        self.validate_sheet_evidence(receipt, receipt["sheet_evidence"])
        if (receipt["intent"]["assignment"]["selector"]["mode"] != "native_result"
                or receipt["intent"]["tool_name"] != "execution.results.collect" or receipt["sheet_evidence"] is None):
            return None
        return digest(receipt["native"]["original_plan"]["identity"]) if any(
            self._population_acquired(receipt, p) for p in receipt["sheet_evidence"]["populations"]) else None

