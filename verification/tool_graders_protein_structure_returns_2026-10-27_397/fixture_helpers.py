"""Synthetic host-port fixtures using actual Store, Journal and frozen receipts.

This deliberately is not the root result host. It persists selected original
actions and immutable authority-view artifacts, and verifies them at the three
approved ports. Native input/scientific values are tiny labeled synthetic cases.
Real sequence.align calls additionally exercise the existing native publisher.
"""
from copy import deepcopy
from functools import lru_cache
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.identities import EpisodeRef
from gene_annotation_episode.alignment_site_native import immutable_record
from gene_annotation_episode.episode_contract_information import expand_fact_form
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_protein_structure_returns import (
    NativeProteinStructureReturns, FACT_SOURCES, SEQUENCE_SOURCE, PROJECTION_SOURCE,
    SAVED_SOURCE, FAILURE_SOURCE,
)
from gene_annotation_episode.protein_structure_result_views import (
    protein_structure_fact_sources, project_protein_structure_results,
)

a = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
b = import_module("verification.tool_graders_protein_structure_calculations_2026-10-27_389.fixture_helpers")


@lru_cache(maxsize=1)
def science_fixture():
    """One explicitly synthetic scientific setup per bounded test process."""
    from gene_annotation_episode.protein_structure_calculations import calculate_protein_structure_components
    sheet = b.make_sheet()
    components = calculate_protein_structure_components(sheet, parameters=sheet["native_request"])
    sheet["native_baseline"] = deepcopy(components)
    native = b.synthetic_native(sheet)
    return sheet, components, native, a.fixture_pdb(role="single")


def schema_for(*sources, names=None):
    registry = protein_structure_fact_sources()
    props = {(names or {}).get(source, "answer_" + str(i)): {**registry[source]["report_schema"], "x-source": source}
             for i, source in enumerate(sources)}
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def reference_schema(source="committed_record_refs", namespace="observation"):
    return {"type": "object", "additionalProperties": False, "required": ["selected"], "properties": {
        "selected": {"type": "array", "x-source": source, "items": {
            "type": "string", "format": "reference", "x-reference-namespace": namespace}}}}


def selection(family, fields, *, artifact=False):
    members = {"kind": "extracted_sequence", "residue_positions": {"kind": "all"}} \
        if family == "extracted_sequence" else {"kind": "transform" if family == "transform" else "comparison"}
    return {"projection_id": "selected", "family": family, "members": members,
            "fields": fields, "window": None, "delivery_kind": "artifact" if artifact else "values"}


class PortHost:
    """Only the three approved ports, backed by persisted original records."""
    def __init__(self, fixture):
        self.f = fixture
        fixture.store.db.execute("CREATE TABLE fixture_protein_authorities(custody_key TEXT PRIMARY KEY, artifact_ref TEXT NOT NULL)")

    def read_result_authority(self, custody, *, scope):
        f = self.f
        row = f.store.db.execute("SELECT artifact_ref FROM fixture_protein_authorities WHERE custody_key=?",
            (custody["result_receipt_key"],)).fetchone()
        if row is None:
            raise ValueError("fixture_original_receipt_missing")
        body = json.loads(f.store.get_artifact(row[0]))
        f.returns._require(f.returns._equal(body["custody"], custody))
        context = f.returns.context(custody["result_episode_id"])
        f.returns._require(f.returns._equal(context.scope, scope))
        f.returns._require(custody["original_request_sha256"] == digest(context.request))
        f.returns._require(f.returns._equal(context.assignment["selector"], body["selector"]))
        selected = f.journal.row("runtime_actions", context.episode_id, 0)
        f.returns._require(json.loads(selected["action"]) == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}})
        outcome = json.loads(selected["result"])
        f.returns._require(outcome == {"status": "completed", "record_refs": [custody["source_ref"]],
                           "result": {"fixture_authority_ref": row[0]}})
        immutable_record(f.store.get(custody["source_ref"]))
        return deepcopy(body)

    def own_fact_groups(self, context, *, verify_artifacts):
        f = self.f
        groups = {source: [] for source in FACT_SOURCES}
        rows = f.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index",
            (f.run_id, context.episode_id))
        for row in rows:
            outcome = json.loads(row[0])
            ref = (outcome.get("result") or {}).get("fixture_authority_ref")
            if ref is None:
                continue
            view = json.loads(f.store.get_artifact(ref))
            view = self.read_result_authority(view["custody"], scope=context.scope)
            for source in FACT_SOURCES:
                groups[source].extend(view["facts"][source])
            if verify_artifacts:
                for projection in view["facts"][PROJECTION_SOURCE]:
                    if projection["delivery"]["kind"] == "artifact":
                        f.store.get_artifact(projection["delivery"]["table_file"]["artifact_ref"])
        return groups

    def owns_reference(self, reference):
        f = self.f
        try:
            record = f.store.get(reference)
        except (ValueError, KeyError):
            return False
        source = record if record["record_type"] == "source" else \
            f.store.get(record["source_ref"]) if record["record_type"] == "reference" else None
        if source is not None and source.get("version") == "native_protein_structure_bundle_v1":
            return True
        for row in f.store.db.execute("SELECT artifact_ref FROM fixture_protein_authorities"):
            view = json.loads(f.store.get_artifact(row[0]))
            if reference in f.store._refs(view):
                return True
        return False


class Fixture:
    def __init__(self, store):
        self.store, self.run_id = store, "protein397-synthetic-run"
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="AGST", molecule="protein")["subject_refs"]}
        self.root = self.context((("annotation", "root"),), {}, None)
        self.receipts.receive(self.root.episode_id, self.scope["subject_refs"], kind="initial")
        self.owner = SimpleNamespace(store=store, run_id=self.run_id)
        self.host = self.owner.native_protein_structure_results = PortHost(self)
        self.returns = self.owner.native_protein_structure_returns = NativeProteinStructureReturns(self.owner)

    def context(self, path, assignment, contract, parent=None, *, save=True):
        ident = EpisodeRef(self.run_id, path).episode_id
        manifest = self.receipts.bind(ident, None if parent is None else parent.episode_id)
        request = {"goal": {"goal_id": "synthetic-protein-authority-fixture", "objective": "Verify recorded authority"},
            "message": {"scope": deepcopy(self.scope), "episode_assignment": deepcopy(assignment),
                        "knowledge_inheritance": manifest, "initial_report": {}},
            "report_contract": deepcopy(contract)}
        context = BindingContext(self.run_id, ident, path[-1][0], path, self.scope, assignment, request)
        if save:
            self.journal.save("runtime_episodes", {"episode_id": ident, "path": canonical(path), "request": canonical(request),
                "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, *, parent=None, index=0, role="results", sources=(SEQUENCE_SOURCE,), schema=None,
              projections=(), sequence_uses=("sequence_align", "structure_correspondence"), saved=False, save=True):
        parent = parent or self.root
        schema = schema or schema_for(*sources)
        selector = {"version": "protein_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
            "saved_sheet": None, "parameters": None, "projections": list(projections), "return_saved_sheet": saved,
            "sequence_allowed_uses": [] if saved else list(sequence_uses)}
        assignment = {"version": "execution_results_assignment_v1", "selector": selector} if role == "results" else {}
        contract = {"decision": "Return the selected synthetic facts", "measurements": {"schema": schema}}
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent, save=save)
        action = {"kind": "episode_child", "role": role, "assignment": deepcopy(assignment), "scope": deepcopy(self.scope),
                  "purpose": contract["decision"], "schema_json": canonical(schema),
                  "goal": child.request["goal"]["objective"], "initial_report_json": "{}"}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        return child

    def replace_request(self, context, request):
        self.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), self.run_id, context.episode_id))
        return BindingContext(self.run_id, context.episode_id, context.role, context.path,
            request["message"]["scope"], request["message"].get("episode_assignment", {}), request)

    def compact_commission(self, child, *, parent=None):
        parent = parent or self.root
        request = plain(child.request)
        schema = request["report_contract"]["measurements"]["schema"]
        submitted = {**schema, "properties": {name: {"$ref": "episode-fact:" + node["x-source"]}
                                             for name, node in schema["properties"].items()}}
        text = canonical(submitted)
        expanded = expand_fact_form(text, child_role=child.role,
            facts_by_role={child.role: protein_structure_fact_sources()}, permitted_child_roles=[child.role])
        request["message"]["report_contract_declaration"] = expanded["declaration"]
        request["report_contract"]["measurements"]["schema"] = expanded["expanded_schema"]
        index = int(child.path[-1][1][6:])
        action = json.loads(self.journal.row("runtime_actions", parent.episode_id, index)["action"])
        action["schema_json"] = text
        self.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(action), self.run_id, parent.episode_id, index))
        return self.replace_request(child, request)

    def redeliver(self, child, *, parent=None, index, source=SEQUENCE_SOURCE):
        from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
        parent = parent or self.root
        schema = {"type": "object", "additionalProperties": False, "required": ["revised"],
            "properties": {"revised": {"$ref": "episode-fact:" + source}}}
        facts_by_role = {child.role: protein_structure_fact_sources()}
        text = canonical(schema)
        expanded = expand_fact_form(text, child_role=child.role, facts_by_role=facts_by_role,
                                    permitted_child_roles=[child.role])["expanded_schema"]
        delivery_ref = "delivery-" + digest([parent.episode_id, child.episode_id])
        action = {"kind": "redeliver_report", "delivery_ref": delivery_ref,
                  "purpose": "Return saved selected facts", "schema_json": text}
        contract = {"decision": action["purpose"], "measurements": {"schema": expanded}}
        context, action_schema = {"contract_information_profile": CONTRACT_INFORMATION_PROFILE, "tools": []}, {"type": "object"}
        info = {"version": CONTRACT_INFORMATION_PROFILE, "permitted_child_roles": [child.role],
                "fact_sources_by_role": facts_by_role, "fact_sources_sha256": digest(facts_by_role),
                "catalog_sha256": digest([]), "action_schema_sha256": digest(action_schema),
                "exchange_schema": {}, "instructions": "Synthetic recorded contract fixture."}
        self.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index, "purpose": "decision",
            "request": canonical({"contract_information": info, "context": context, "schema": action_schema}),
            "response": canonical({"selection": action})})
        facts = json.loads(self.journal.row("runtime_forms", child.episode_id)["facts"])
        form = {"revised": facts[source]}
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": delivery_ref, "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        refs = self.returns.record_admission(parent, form, expanded, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        self.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        return form

    def file(self, raw, format):
        descriptor = a.identity(raw, format)
        assert self.store.artifact(raw, "application/json" if format.endswith("_v1") else "application/octet-stream") == descriptor["artifact_ref"]
        return descriptor

    def source(self, label, *, bundle, auxiliaries=(), protein=False):
        return self.store.put("source", {"provider": "episode.execution_result" if protein else "fixture.protein397",
            "accession": label, "uri": None, "artifact_ref": bundle, "text_ref": None, "request_ref": None,
            "version": "native_protein_structure_bundle_v1" if protein else "synthetic_fixture_v1",
            "retrieved_at": "2026-10-27T00:00:00+00:00", "auxiliary_artifact_refs": list(auxiliaries)}, origin="tool")["id"]

    def publish(self, child, *, comparison=False):
        """Persist a synthetic result-port receipt; this is not root execution."""
        from gene_annotation_episode.protein_structure_calculations import calculate_protein_structure_components
        key = f"{self.run_id}:{child.episode_id}:0"
        assignment = plain(child.assignment)
        sheet, components, native, extracted = deepcopy(science_fixture())
        bundle = self.file(canonical({"synthetic_original_attempt": key}).encode(), "native_protein_structure_bundle_v1")
        handoff = self.source("synthetic-handoff-" + digest(key), bundle=bundle["artifact_ref"])
        if comparison:
            sheet_file = self.file(canonical(sheet).encode(), "protein_structure_comparison_sheet_v1")
            components_file = self.file(canonical(components).encode(), "protein_structure_components_v1")
            request, software = native["request"], native["producer"]
            native_file = self.file(canonical(native).encode(), "protein_structure_native_v1")
            sequence_file = residue_map_file = None
            projection_input = {"kind": "comparison", "sheet": sheet, "components": components}
            auxiliaries = [native_file["artifact_ref"], sheet_file["artifact_ref"], components_file["artifact_ref"]]
        else:
            raw, parsed, sequence, metadata = extracted
            structure_file = self.file(raw, "pdb_3x_text")
            sequence_file = self.file(sequence["alignment_sequence"].encode(), "ascii_protein_sequence_v1")
            residue_map_file = self.file(canonical(sequence).encode(), "protein_structure_sequence_v1")
            request = {"version": "protein_structure_extract_request_v1", "operation": "extract_sequence",
                       "selection": sequence["selection"], "supplied_metadata_files": []}
            software = native["producer"]
            native_file = self.file(canonical({"synthetic_sequence": sequence}).encode(), "protein_structure_sequence_native_v1")
            sheet_file = components_file = None
            auxiliaries = [structure_file["artifact_ref"], sequence_file["artifact_ref"], residue_map_file["artifact_ref"], native_file["artifact_ref"]]
        source = self.source("synthetic-native-" + digest(key), bundle=bundle["artifact_ref"], auxiliaries=auxiliaries, protein=True)
        custody = {"run_id": self.run_id, "result_episode_id": child.episode_id, "result_operation_key": key,
            "result_receipt_key": "protein_structure_result_receipt:" + digest({"run_id": self.run_id, "episode_id": child.episode_id, "operation_key": key}),
            "handoff_ref": handoff, "source_ref": source, "bundle_artifact_ref": bundle["artifact_ref"],
            "original_request_sha256": digest(child.request)}
        facts = {name: [] for name in FACT_SOURCES}
        if comparison:
            if assignment["selector"]["return_saved_sheet"]:
                facts[SAVED_SOURCE] = [{"version": "protein_structure_saved_sheet_v1", "custody": custody,
                    "sheet_file": sheet_file, "original_components_file": components_file,
                    "operation": "compare_protein_structures", "original_mode": sheet["scientific_mode"],
                    "allowed_uses": ["recalculate", "select_projection", "use_transform"]}]
        else:
            reference = self.store.put("reference", {"reference_type": "protein", "source_ref": source,
                "accession": "structure_sequence_" + digest(sequence), "label": "Structure-derived protein sequence",
                "sequence_ref": sequence_file["artifact_ref"], "molecule": "protein", "length": sequence["sequence_length"],
                "term_refs": [], "context_refs": [], "anchor": None}, origin="tool")
            descriptor = {"version": "structure_sequence_descriptor_v1", "custody": custody,
                "reference_ref": reference["id"], "sequence_file": sequence_file, "residue_map_file": residue_map_file,
                "structure_file": structure_file, "selection": sequence["selection"], "sequence_length": sequence["sequence_length"],
                "allowed_uses": list(assignment["selector"]["sequence_allowed_uses"])}
            if descriptor["allowed_uses"]:
                facts[SEQUENCE_SOURCE] = [descriptor]
            projection_input = {"kind": "extraction", "sequence": sequence, "metadata": metadata,
                                "descriptor": descriptor if descriptor["allowed_uses"] else None}
        for rows in project_protein_structure_results(projection_input, selection=assignment["selector"]["projections"]):
            projection = {key: deepcopy(value) for key, value in rows.items() if key not in {"rows", "calculation_id"}}
            projection.update(version="protein_structure_projection_v1", custody=custody, calculation=None)
            if comparison:
                projection["calculation"] = {"calculation_id": components["calculation_id"],
                    "input_numerical_sha256": components["input_numerical_sha256"], "components_file": components_file}
            if rows["selection"]["delivery_kind"] == "values":
                projection["delivery"] = {"kind": "values", "rows": rows["rows"]}
            else:
                table = self.file(canonical({"version": "protein_structure_projection_table_v1", "rows": rows["rows"]}).encode(),
                                  "protein_structure_projection_table_v1")
                projection["delivery"] = {"kind": "artifact", "table_file": table, "row_count": rows["returned_count"],
                                          "allowed_use": "read_exact_selected_table"}
            facts[PROJECTION_SOURCE].append(projection)
        view = {"custody": custody, "selector": assignment["selector"], "request": request, "software": software,
                "native_file": native_file, "sequence_file": sequence_file, "residue_map_file": residue_map_file,
                "sheet_file": sheet_file, "original_components_file": components_file, "components_file": components_file, "facts": facts}
        self.persist(child, view)
        return view

    def persist(self, child, view):
        receipt_ref = self.store.artifact(canonical(view), "application/json")
        self.store.db.execute("INSERT OR REPLACE INTO fixture_protein_authorities VALUES(?,?)",
            (view["custody"]["result_receipt_key"], receipt_ref))
        outcome = {"status": "completed", "record_refs": [view["custody"]["source_ref"]], "result": {"fixture_authority_ref": receipt_ref}}
        self.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
            "action": canonical({"kind": "tool", "tool": "execution.results.collect", "arguments": {}}),
            "result": canonical(outcome), "credit": 0})
        self.receipts.receive(child.episode_id, outcome["record_refs"], kind="own_action", source_index=0)

    def returned(self, parent, child, *, facts=None, index=None, schema=None):
        contract = plain(child.request)["report_contract"]
        if schema is not None:
            contract["measurements"]["schema"] = schema
        schema = contract["measurements"]["schema"]
        if facts is None:
            facts = self.host.own_fact_groups(child, verify_artifacts=False) if child.role == "results" else \
                self.returns.received_facts(child, schema)
        form = {name: deepcopy(facts[node["x-source"]] if "x-source" in node else facts["interpretations"][name])
                for name, node in schema["properties"].items()}
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        index = int(child.path[-1][1][6:]) if index is None else index
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery-" + digest([parent.episode_id, child.episode_id]), "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        references = self.returns.record_admission(parent, form, schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        references += self.returns._explicit_refs(form, schema)
        self.receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return form

    def alignment(self, context, query, reference, *, index=0, mode="global"):
        from gene_annotation_episode.tools import ToolRegistry
        registry = ToolRegistry(self.store, job_limits={"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None})
        args = {"query_ref": query, "reference_ref": reference, "molecule": "protein", "mode": mode}
        key = f"{self.run_id}:{context.episode_id}:{index}"
        action = {"kind": "tool", "tool": "sequence.align", "arguments": args}
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        outcome = registry.execute("sequence.align", args, scope=plain(context.scope), operation_key=key)
        assert outcome["status"] == "completed", outcome
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical(action), "result": canonical(outcome), "credit": 0})
        self.receipts.receive(context.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        source = self.store.get(outcome["result"]["source_ref"])
        file = lambda ref, format: a.identity(self.store.get_artifact(ref), format)
        return {"version": "structure_alignment_descriptor_v1", "observation_ref": outcome["result"]["observation_ref"],
            "source_ref": source["id"], "original_operation_key": key, "query_reference_ref": query, "reference_reference_ref": reference,
            "native_file": file(source["artifact_ref"], "biopython_pairwise_json"),
            "grading_file": file(source["auxiliary_artifact_refs"][0], "tool_grading_artifact_v1"), "molecule": "protein", "mode": mode,
            "traceback_selection": "explicit_retained", "producer_traceback_selection": "first_native_optimal_returned", "optimal_alternative_count": None}
