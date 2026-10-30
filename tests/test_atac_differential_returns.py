"""Real Store/runtime/form authority with an explicitly synthetic strict host.

Sheet/table bytes, an empty derived projection and host publication controls
are authored boundary fixtures, not native runs or a full Workflow. The production host and
assembled native path have separate root-owned verification responsibilities.
Execute only through packet471's pinned local_jobs/native_lifecycle runner.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.atac_differential_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    atac_fact_sources, requested_atac_sources,
)
from gene_annotation_episode.atac_differential_result_contracts import validate_atac_result_record
from gene_annotation_episode.atac_differential_returns import AtacDifferentialReturns
from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.native_file_capture import _metadata, retained_native_file
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


PREFIX = "atac_received_report_prefix"


def schema_for(*sources):
    descriptors = atac_fact_sources()
    fields = {"chosen_" + str(index): deepcopy(descriptors[source]["report_schema"])
        for index, source in enumerate(sources)}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def files(bundle):
    return [bundle["sheet"], *(row["file"] for row in bundle["tables"])]


def references(bundle):
    return list(dict.fromkeys(file["artifact_ref"] for file in files(bundle)))


def failure(artifact):
    return {"code": "saved_attachment_unavailable", "stage": "return", "step_key": None,
        "file_key": None, "binding_key": "signal1", "artifact_ref": artifact,
        "locator": None, "field_path": "/supplied/table", "partial_artifact_refs": [artifact],
        "requirement": "complete_saved_bundle"}


class StrictResultsHostDouble:
    """Synthetic selected-publication proof over actual immutable/SQL records.

    This is not the production host. Authored controls must exactly match the
    original context, collect selection, committed outcome and Store metadata.
    Native scientific parsing/publication truth is deliberately not simulated.
    """
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self.originals, self.calls = {}, []

    @staticmethod
    def applies(context):
        return context.role == "results" and context.assignment.get("selector", {}).get(
            "version") == "atac_differential_result_selector_v1"

    def register(self, context, facts, *, index=0, descriptors=(), completed=True):
        operation = f"{self.run_id}:{context.episode_id}:{index}"
        action = {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
        outcome = {"status": "completed", "synthetic_host_facts": deepcopy(facts)}
        control = {"context": plain(context.as_record()), "operation_key": operation,
            "action": action, "outcome": outcome, "synthetic_descriptors": list(descriptors)}
        path = self.store.path / "strict-host-controls" / (digest(operation) + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(canonical(control))
        path.chmod(0o444)
        self.originals[(context.episode_id, index)] = (deepcopy(control), path)
        if completed:
            Journal(self.store, self.run_id).save("runtime_actions", {"episode_id": context.episode_id,
                "decision_index": index, "action": canonical(action), "result": canonical(outcome), "credit": None})
        return {"episode_id": context.episode_id, "operation_key": operation}

    def _qualified(self, context):
        if not self.applies(context):
            raise ValueError("strict_host_original_context_required")
        results = []
        for (episode, index), (original, path) in sorted(self.originals.items(), key=lambda item: item[0][1]):
            if episode != context.episode_id:
                continue
            if plain(context.as_record()) != original["context"]:
                raise ValueError("strict_host_original_context_required")
            if not path.is_file() or json.loads(path.read_bytes()) != original:
                raise ValueError("strict_host_original_control_required")
            row = self.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
                "AND episode_id=? AND decision_index=?", (self.run_id, episode, index)).fetchone()
            if row is None or row["result"] is None:
                raise ValueError("strict_host_completed_result_required")
            if json.loads(row["action"]) != original["action"] or json.loads(row["result"]) != original["outcome"]:
                raise ValueError("strict_host_original_completed_action_conflict")
            for bundle in original["outcome"]["synthetic_host_facts"][SAVED_SOURCE]:
                for file in files(bundle):
                    metadata = _metadata(self.store, file["artifact_ref"])
                    if metadata["sha256"] != file["sha256"] or metadata["size"] != file["size_bytes"]:
                        raise ValueError("strict_host_artifact_metadata_conflict")
            results.append(deepcopy(original))
        return results

    def own_fact_groups(self, context, *, verify_artifacts):
        self.calls.append((context.episode_id, verify_artifacts))
        facts = {source: [] for source in FACT_SOURCES}
        for row in self._qualified(context):
            values = row["outcome"]["synthetic_host_facts"]
            if verify_artifacts:
                for bundle in values[SAVED_SOURCE]:
                    for file in files(bundle):
                        retained_native_file(self.store, file)
            for source in FACT_SOURCES:
                for value in values[source]:
                    if value not in facts[source]:
                        facts[source].append(deepcopy(value))
        return facts

    def completed_saved_bundle_origins(self, context, bundle):
        return tuple({"episode_id": context.episode_id, "operation_key": row["operation_key"]}
            for row in self._qualified(context)
            if bundle in row["outcome"]["synthetic_host_facts"][SAVED_SOURCE])


class RuntimeFixture:
    def __init__(self, store):
        self.store, self.run_id = store, "ATAC-return449"
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]}
        self.host = StrictResultsHostDouble(store, self.run_id)
        self.boundary = AtacDifferentialReturns(SimpleNamespace(store=store, run_id=self.run_id,
            atac_results=self.host))
        self.root = self.context((("annotation", "root"),), {}, None)
        self.bundle, self.descriptors = self.make_bundle("first")
        self.projection = {"version": "atac_differential_projection_v1", "comparison_key": "comparison",
            "reference_id": "reference", "condition_ids": ["condition1", "condition2"],
            "selected_intervals": [{"chromosome": "chrToy", "start": 0, "end": 500}],
            "parameters": {"pseudocount": 0.01, "cutoff_log10_lr": 3,
                "minimum_length_bp": 50, "maximum_gap_bp": 0},
            "kind": "derived_regions", "row_window": {"offset": 0, "limit": 10},
            "total_rows": 0, "row_extent": "complete", "rows": [], "summary": None,
            "qualifications": [], "failures": []}
        self.alternate_projection = deepcopy(self.projection)
        self.alternate_projection["parameters"]["cutoff_log10_lr"] = 20

    def identity(self, raw, format):
        sha = hashlib.sha256(raw).hexdigest()
        return {"artifact_ref": self.store.artifact(raw), "sha256": sha,
            "size_bytes": len(raw), "format": format}

    def make_bundle(self, label):
        # Authored authority controls, never native scientific measurements.
        tables = []
        for role in ("signal1", "background1", "signal2", "background2"):
            content = ("synthetic shared background" if role.startswith("background")
                else f"synthetic {label} {role} bytes").encode()
            tables.append({"track_key": role,
                "file": self.identity(content, "atac_bedgraph_rows_jsonl_v1")})
        raw = canonical({"synthetic_boundary_sheet": label, "tables": tables}).encode()
        return {"sheet": self.identity(raw, "atac_differential_native_sheet_v1"), "tables": tables}, tables

    def context(self, path, assignment, contract, parent=None, *, scope=None, persist=True):
        scope = plain(self.scope if scope is None else scope)
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inheritance = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify exact ATAC typed-return authority", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify exact ATAC typed-return authority", result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({"scope": scope, "initial_report": {},
            "episode_assignment": deepcopy(assignment), "knowledge_inheritance": inheritance}), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, scope, assignment, request)
        if persist:
            self.persist(context)
        return context

    def persist(self, context):
        self.journal.save("runtime_episodes", {"episode_id": context.episode_id, "path": canonical(context.path),
            "request": canonical(plain(context.request)), "initial_credit": 0, "state": "active",
            "completion": None, "archive": None})

    def child(self, parent, schema, *, index=0, role="results", kind="episode_child", saved=None,
            scope=None, persist=True):
        contract = TypedReportContract("Return requested ATAC facts", schema, lambda *_: True)
        selector = {"version": "atac_differential_result_selector_v1",
            "mode": "native_result" if saved is None else "saved_sheet_recalculation",
            "saved_sheet_bundle": deepcopy(saved), "comparison_key": "comparison",
            "intervals": deepcopy(self.projection["selected_intervals"]),
            "parameters": deepcopy(self.projection["parameters"]),
            "projection": {"kind": "derived_regions", "row_window": {"offset": 0, "limit": 10},
                "run_keys": [], "categories": ["condition1", "condition2", "common"]}}
        validate_atac_result_record("ResultSelector", selector)
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": "synthetic-handoff",
            "selector": selector} if role == "results" else {}
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent,
            scope=parent.scope if scope is None else scope, persist=persist)
        if persist:
            self.commission(parent, child, kind=kind)
        return child

    def commission(self, parent, child, *, kind="episode_child"):
        contract = plain(child.request)["report_contract"]
        selected = {"kind": kind, "role": child.role, "assignment": plain(child.assignment),
            "scope": plain(child.scope), "purpose": contract["decision"],
            "schema_json": canonical(contract["measurements"]["schema"])}
        if kind == "tool":
            selected = {"kind": "tool", "tool": "process.revise", "arguments": {}}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id,
            "decision_index": int(child.path[-1][1][6:]), "action": canonical(selected), "result": None, "credit": None})

    def own(self, child, *, projections=None, bundles=None, failures=None, index=0, completed=True):
        requested = requested_atac_sources(plain(child.request)["report_contract"]["measurements"]["schema"])
        private = {PROJECTION_SOURCE: [self.projection] if projections is None else projections,
            SAVED_SOURCE: [self.bundle] if bundles is None else bundles,
            FAILURE_SOURCE: [] if failures is None else failures}
        facts = {source: private[source] if source in requested else [] for source in FACT_SOURCES}
        origin = self.host.register(child, facts, index=index, descriptors=self.descriptors, completed=completed)
        return deepcopy(facts), origin

    def returned(self, parent, child, *, successful=True, receive=True):
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        facts = (self.host.own_fact_groups(child, verify_artifacts=True) if child.role == "results"
            else self.boundary.facts_for_closure(child, schema))
        form = form_with_facts({}, schema, facts)
        self.boundary.validate_received_report(child, form, schema)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        typed = TypedReportContract(contract["decision"], schema, lambda *_: True,
            lambda value: self.boundary.validate_received_report(child, value, schema))
        admitted = typed.admit(form, audit_identifiers=(child.episode_id, plain(child.request)["goal"]["goal_id"])).as_record()
        index = int(child.path[-1][1][6:])
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index]),
            "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(admitted) if successful else None,
            "failure": None if successful else canonical({"kind": "synthetic_delivery_failure"})})
        if successful and receive:
            self.receive(parent, admitted, schema, index)
        return admitted

    def receive(self, parent, form, schema, index, *, redelivery=False):
        refs = self.boundary.record_admission(parent, form, schema, self.operation(parent, index))
        self.receipts.receive(parent.episode_id, refs,
            kind="report_redelivery" if redelivery else "child_form", source_index=index)
        return refs

    def redeliver(self, parent, child, schema, *, index=1):
        original_index = int(child.path[-1][1][6:])
        original = self.store.db.execute("SELECT delivery_ref FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND decision_index=?", (self.run_id, parent.episode_id, original_index)).fetchone()
        contract = TypedReportContract("Return corrected requested ATAC fields", schema, lambda *_: True,
            lambda value: self.boundary.validate_received_report(child, value, schema))
        facts = json.loads(self.journal.row("runtime_forms", child.episode_id)["facts"])
        form = contract.admit(form_with_facts({}, schema, facts),
            audit_identifiers=(child.episode_id, plain(child.request)["goal"]["goal_id"])).as_record()
        selected = {"kind": "redeliver_report", "delivery_ref": original["delivery_ref"],
            "purpose": contract.decision, "schema_json": canonical(schema)}
        self.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index,
            "purpose": "decision", "request": "{}", "response": canonical({"selection": selected})})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": original["delivery_ref"], "child_episode_id": child.episode_id,
            "contract": canonical(contract.as_record()), "form": canonical(form), "failure": None})
        self.receive(parent, form, schema, index, redelivery=True)
        return form

    def operation(self, parent, index=0):
        return f"{self.run_id}:{parent.episode_id}:{index}:typed_form"

    def change_action(self, parent, index, **changes):
        action = json.loads(self.journal.row("runtime_actions", parent.episode_id, index)["action"])
        action.update(changes)
        self.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(action), self.run_id, parent.episode_id, index))

    def snapshot(self):
        return list(self.store.db.iterdump())


@pytest.fixture(autouse=True)
def no_science_network_or_subprocess(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Return authority attempted acquisition or scientific computation")
    for path in ("socket.create_connection", "socket.socket", "subprocess.Popen",
        "gene_annotation_episode.atac_differential_sheet.build_atac_differential_sheet",
        "gene_annotation_episode.atac_differential_result_views.project_atac_result"):
        monkeypatch.setattr(path, forbidden)


@pytest.fixture
def f(tmp_path):
    with Store(tmp_path / "store") as store:
        yield RuntimeFixture(store)
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0


@pytest.mark.parametrize("sources", [FACT_SOURCES, (PROJECTION_SOURCE,), (SAVED_SOURCE,), (FAILURE_SOURCE,)])
def test_b01_requested_immediate_edges_and_no_private_reference_grants(f, sources, tmp_path):
    schema = schema_for(*sources)
    science = f.child(f.root, schema, role="scientific_process")
    child = f.child(science, schema)
    own, origin = f.own(child, failures=[failure(f.bundle["tables"][2]["file"]["artifact_ref"])])
    first = f.returned(science, child)
    forwarded = f.returned(f.root, science)
    assert first == forwarded
    expected = {source: own[source] if source in sources else [] for source in FACT_SOURCES}
    assert f.boundary.facts(f.root, schema_for(*FACT_SOURCES)) == expected
    assert f.boundary.record_admission(f.root, forwarded, schema, f.operation(f.root)) == (
        references(f.bundle) if SAVED_SOURCE in sources else [])
    for file in files(f.bundle):
        assert f.boundary.resolve_received(f.root, file["artifact_ref"], "artifact") == (SAVED_SOURCE in sources)
    if SAVED_SOURCE in sources:
        assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
    else:
        assert list(f.receipts.known(f.root.episode_id)) == []
        with pytest.raises(ValueError, match="saved_bundle_not_received"):
            f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)
    (tmp_path / "ACTUAL_TYPED_RETURN.json").write_text(canonical({
        "evidence": "synthetic471_projection_and_strict_host_real_runtime_forms",
        "received_sources": list(sources), "form": forwarded,
        "admitted_references": references(f.bundle) if SAVED_SOURCE in sources else []}))


@pytest.mark.parametrize("sources", [(PROJECTION_SOURCE,), (FAILURE_SOURCE,)])
def test_b02_b03_hashes_and_failure_locations_do_not_grant_saved_operands(f, sources):
    child = f.child(f.root, schema_for(*sources))
    f.own(child, failures=[failure(f.bundle["sheet"]["artifact_ref"])])
    f.returned(f.root, child)
    # Even ordinary receipts/source access cannot substitute for a saved form.
    f.receipts.receive(f.root.episode_id, references(f.bundle), kind="own_action", source_index=8)
    for ref in references(f.bundle):
        assert not f.boundary.resolve_received(f.root, ref, None)
    with pytest.raises(ValueError, match="saved_bundle_not_received"):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


@pytest.mark.parametrize("alter", ["sheet_only", "missing", "extra", "reorder", "size", "format", "splice"])
def test_b04_entire_ordered_bundle_is_the_authorized_value(f, alter):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    other, _ = f.make_bundle("second")
    f.receipts.receive(f.root.episode_id, references(other), kind="own_action")
    bundle = deepcopy(f.bundle)
    if alter == "sheet_only":
        bundle = bundle["sheet"]
    elif alter == "missing":
        bundle["tables"].pop()
    elif alter == "extra":
        bundle["tables"].append(other["tables"][0])
    elif alter == "reorder":
        bundle["tables"].reverse()
    elif alter == "size":
        bundle["tables"][0]["file"]["size_bytes"] += 1
    elif alter == "format":
        bundle["tables"][0]["file"]["format"] = "ATAC_contact_tables_v1:contacts"
    else:
        bundle["tables"][0] = other["tables"][0]
    with pytest.raises(ValueError):
        f.boundary.authenticate_received_saved_bundle(f.root, bundle)


def test_b05_duplicate_table_bytes_keep_two_distinct_positions(f):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    _, origin = f.own(child)
    returned = f.returned(f.root, child)
    actual = returned["chosen_0"][0]
    assert actual["tables"][1]["file"] == actual["tables"][3]["file"]
    assert len(actual["tables"]) == 4 and len(references(actual)) == 4
    witness = f.host.originals[(child.episode_id, 0)][0]["synthetic_descriptors"]
    duplicate_rows = [row for row in witness if row["file"] == actual["tables"][1]["file"]]
    assert [row["track_key"] for row in duplicate_rows] == ["background1", "background2"]
    assert f.boundary.authenticate_received_saved_bundle(f.root, actual) == (origin,)
    assert len(list(f.receipts.known(f.root.episode_id))) == 4
    actual["tables"].pop(3)
    with pytest.raises(ValueError, match="saved_bundle_not_received"):
        f.boundary.authenticate_received_saved_bundle(f.root, actual)


def test_b06_unrequested_grandchild_private_sibling_and_scope_do_not_grant(f):
    science = f.child(f.root, schema_for(PROJECTION_SOURCE), role="scientific_process")
    grandchild = f.child(science, schema_for(*FACT_SOURCES))
    f.own(grandchild)
    f.returned(science, grandchild)
    f.returned(f.root, science)
    private = f.child(f.root, schema_for(SAVED_SOURCE), index=1)
    f.own(private)
    for ref in references(f.bundle):
        f.store.put("source", {"provider": "synthetic.public-source", "accession": None,
            "uri": None, "artifact_ref": ref, "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
    f.receipts.receive(f.root.episode_id, references(f.bundle), kind="own_action")
    assert f.store.reference_subset(references(f.bundle), plain(f.root.scope)) == references(f.bundle)
    f.host.calls.clear()
    assert f.boundary.facts(f.root, schema_for(SAVED_SOURCE)) == {SAVED_SOURCE: []}
    assert not f.boundary.resolve_received(f.root, f.bundle["sheet"]["artifact_ref"], None)
    with pytest.raises(ValueError, match="saved_bundle_not_received"):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)
    assert not any(episode == private.episode_id for episode, _ in f.host.calls)


@pytest.mark.parametrize("same_episode", [True, False])
def test_b07_b08_every_exact_completed_action_origin_survives_fact_deduplication(f, same_episode):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    first = f.child(science, schema)
    _, origin0 = f.own(first)
    if same_episode:
        _, origin1 = f.own(first, index=3)
        f.returned(science, first)
    else:
        f.returned(science, first)
        second = f.child(science, schema, index=1)
        _, origin1 = f.own(second)
        f.returned(science, second)
    f.returned(f.root, science)
    assert f.boundary.facts(f.root, schema) == {SAVED_SOURCE: [f.bundle]}
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin0, origin1)
    groups, origins, prefix = f.boundary._received(science, (SAVED_SOURCE,))
    assert groups == {SAVED_SOURCE: [f.bundle]}
    assert origins[canonical(f.bundle)] == [origin0, origin1]
    assert prefix["version"] == "frozen_received_report_prefix_v1"
    # A good neighboring identical result cannot repair a changed origin.
    owner = first if same_episode else second
    f.change_action(owner, 3 if same_episode else 0, tool="execution.results.status")
    with pytest.raises(ValueError, match="strict_host_original_completed_action_conflict"):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


def test_b09_later_identical_origin_does_not_expand_frozen_forwarding(f):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    first = f.child(science, schema)
    _, origin0 = f.own(first)
    f.returned(science, first)
    frozen = f.returned(f.root, science)
    before = f.journal.row("runtime_forms", science.episode_id)
    later = f.child(science, schema, index=1)
    _, origin1 = f.own(later)
    f.returned(science, later)
    assert f.boundary.authenticate_received_saved_bundle(science, f.bundle) == (origin0, origin1)
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin0,)
    f.boundary.validate_received_report(science, frozen, schema)
    assert f.boundary.facts_for_closure(science, schema) == json.loads(before["facts"])
    assert f.journal.row("runtime_forms", science.episode_id) == before


def test_b10_receipt_time_prefix_excludes_late_lower_index_return(f):
    schema = schema_for(SAVED_SOURCE)
    delayed = f.child(f.root, schema)
    _, origin = f.own(delayed)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, saved=f.bundle)
    f.returned(f.root, delayed)
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
    with pytest.raises(ValueError, match="saved_bundle_not_received"):
        f.boundary.authenticate_received_saved_bundle(selected, f.bundle)
    newer = f.child(f.root, schema_for(PROJECTION_SOURCE), index=2, saved=f.bundle)
    assert f.boundary.authenticate_received_saved_bundle(newer, f.bundle) == (origin,)
    assert f.boundary.facts(newer, schema) == {SAVED_SOURCE: []}
    assert not f.boundary.resolve_received(newer, f.bundle["sheet"]["artifact_ref"], None)


@pytest.mark.parametrize("change", ["scope", "purpose", "schema_json", "role", "assignment", "kind"])
def test_b11_original_commission_fields_remain_exact(f, change):
    schema = schema_for(*FACT_SOURCES)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    replacements = {"scope": {"subject_refs": []}, "purpose": "Changed decision",
        "schema_json": canonical(schema_for()), "role": "launch", "assignment": {}, "kind": "unselected"}
    f.change_action(f.root, 0, **{change: replacements[change]})
    with pytest.raises(ValueError, match="commission"):
        f.boundary.record_admission(f.root, form, schema, f.operation(f.root))


def test_b11_run_id_path_request_scope_and_parent_are_authenticated(f):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    facts, _ = f.own(child)
    form = form_with_facts({}, schema, facts)
    altered_request = plain(child.request)
    altered_request["message"]["initial_report"] = {"changed": True}
    for altered in (replace(child, run_id="different-run"), replace(child, episode_id="foreign"),
            replace(child, path=(*f.root.path, ("results", "child_99"))),
            replace(child, scope={"subject_refs": []}), replace(child, request=altered_request)):
        with pytest.raises(ValueError, match="context_conflict"):
            f.boundary.validate_received_report(altered, form, schema)
    science = f.child(f.root, schema, index=1, role="scientific_process")
    f.returned(f.root, child)
    f.store.db.execute("UPDATE runtime_report_attempts SET parent_episode_id=? WHERE run_id=? AND parent_episode_id=?",
        (science.episode_id, f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="return_child_contract_conflict"):
        f.boundary.facts(science, schema)


@pytest.mark.parametrize("alter", ["form", "facts", "both"])
def test_b12_frozen_source_arrays_and_original_form_are_not_repaired(f, alter):
    schema = schema_for(PROJECTION_SOURCE)
    child = f.child(f.root, schema)
    f.own(child)
    original = f.returned(f.root, child)
    changed = deepcopy(original)
    changed["chosen_0"] = [f.alternate_projection]
    if alter in {"form", "both"}:
        f.store.db.execute("UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?",
            (canonical(changed), f.run_id, child.episode_id))
    if alter in {"facts", "both"}:
        facts = json.loads(f.journal.row("runtime_forms", child.episode_id)["facts"])
        facts[PROJECTION_SOURCE] = changed["chosen_0"]
        f.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
            (canonical(facts), f.run_id, child.episode_id))
    if alter == "both":
        f.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=?",
            (canonical(changed), f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="frozen_.*conflict|returned_facts_conflict"):
        f.boundary.facts(f.root, schema)


@pytest.mark.parametrize("alter", ["missing", "contract_sha256", "form_sha256", "delivery_ref",
                                  "child_episode_id", "deleted_attempt", "order"])
def test_b12_closure_prefix_witnesses_cannot_change(f, alter):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    for index in (0, 1):
        child = f.child(science, schema, index=index)
        f.own(child)
        f.returned(science, child)
    f.returned(f.root, science)
    facts = json.loads(f.journal.row("runtime_forms", science.episode_id)["facts"])
    if alter == "missing":
        del facts[PREFIX]
    elif alter == "order":
        facts[PREFIX]["attempts"].reverse()
    elif alter == "deleted_attempt":
        f.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
            (f.run_id, science.episode_id))
    else:
        facts[PREFIX]["attempts"][0][alter] = "0" * 64
    f.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
        (canonical(facts), f.run_id, science.episode_id))
    with pytest.raises(ValueError, match="closure_prefix_required|return_prefix_conflict|invalid_received_report_prefix"):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


@pytest.mark.parametrize("alter", [None, "reverse", "duplicate", "new"])
def test_b13_frozen_ordered_subset_survives_later_delivery_only_unchanged(f, alter):
    schema = schema_for(PROJECTION_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    child = f.child(science, schema)
    f.own(child, projections=[f.projection, f.alternate_projection])
    f.returned(science, child)
    original = f.returned(f.root, science)
    new = deepcopy(f.projection)
    new["parameters"]["cutoff_log10_lr"] = 4
    late = f.child(science, schema, index=1)
    f.own(late, projections=[new])
    f.returned(science, late)
    assert f.boundary.facts(science, schema)[PROJECTION_SOURCE] == [f.projection, f.alternate_projection, new]
    if alter is None:
        f.boundary.validate_received_report(science, original, schema)
        assert f.boundary.facts(f.root, schema)[PROJECTION_SOURCE] == [f.projection, f.alternate_projection]
        return
    original["chosen_0"] = (list(reversed(original["chosen_0"])) if alter == "reverse"
        else [f.projection, f.projection] if alter == "duplicate" else [f.projection, new])
    facts = json.loads(f.journal.row("runtime_forms", science.episode_id)["facts"])
    facts[PROJECTION_SOURCE] = original["chosen_0"]
    f.store.db.execute("UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?",
        (canonical(original), canonical(facts), f.run_id, science.episode_id))
    f.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=?",
        (canonical(original), f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        f.boundary.facts(f.root, schema)


@pytest.mark.parametrize("original_success", [True, False])
def test_b14_explicit_redelivery_uses_frozen_facts_without_a_new_action(f, original_success):
    child = f.child(f.root, schema_for(*FACT_SOURCES))
    _, origin = f.own(child)
    f.returned(f.root, child, successful=original_success)
    actions = f.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    first_attempt = dict(f.store.db.execute("SELECT * FROM runtime_report_attempts").fetchone())
    form = f.redeliver(f.root, child, schema_for(SAVED_SOURCE))
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
    assert f.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == actions
    assert dict(f.store.db.execute("SELECT * FROM runtime_report_attempts WHERE decision_index=0").fetchone()) == first_attempt
    f.change_action(f.root, 0, assignment={})
    with pytest.raises(ValueError, match="commission_assignment_conflict"):
        f.boundary.record_admission(f.root, form, schema_for(SAVED_SOURCE), f.operation(f.root, 1))


@pytest.mark.parametrize("alter", ["missing", "uncommitted", "status", "outcome", "control_missing", "control_corrupt"])
def test_b15_b18_private_staged_controls_and_changed_completed_actions_never_authorize(f, alter):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    if alter == "missing":
        f.store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    elif alter == "uncommitted":
        f.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    elif alter == "status":
        f.change_action(child, 0, tool="execution.results.status")
    elif alter == "outcome":
        f.store.db.execute("UPDATE runtime_actions SET result='{}' WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    else:
        path = f.host.originals[(child.episode_id, 0)][1]
        if alter == "control_missing":
            path.unlink()
        else:
            path.chmod(0o644)
            path.write_text("{}")
    with pytest.raises(ValueError, match="strict_host_"):
        f.boundary.record_admission(f.root, form, schema, f.operation(f.root))


def test_b15_never_completed_staged_bundle_is_not_a_publication(f):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    f.own(child, completed=False)
    with pytest.raises(ValueError, match="strict_host_completed_result_required"):
        f.boundary.facts(child, schema)
    assert f.boundary.facts(f.root, schema) == {SAVED_SOURCE: []}


def test_b16_b17_history_survives_byte_loss_new_use_checks_bytes_separately(f, monkeypatch):
    schema = schema_for(*FACT_SOURCES)
    science = f.child(f.root, schema, role="scientific_process")
    child = f.child(science, schema)
    _, origin = f.own(child)
    child_form = f.returned(science, child)
    form = f.returned(f.root, science)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, saved=f.bundle)
    paths = {retained_native_file(f.store, file) for file in files(f.bundle)}
    for path in paths:
        path.unlink()
    before = f.snapshot()
    f.host.calls.clear()
    original_read = Path.read_bytes
    def no_scientific_bytes(path):
        if "artifacts" in path.parts:
            pytest.fail("Historical return opened scientific bytes")
        return original_read(path)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", no_scientific_bytes)
        patch.setattr(f.store, "get_artifact", lambda *_: pytest.fail("Historical return opened scientific bytes"))
        patch.setattr("gene_annotation_episode.materials.artifact_path", lambda *_: pytest.fail("Historical file resolution"))
        assert f.boundary.facts(f.root, schema)[SAVED_SOURCE] == [f.bundle]
        f.boundary.validate_received_report(child, child_form, schema)
        f.boundary.validate_received_report(science, form, schema)
        assert f.boundary.facts_for_closure(science, schema) == json.loads(f.journal.row("runtime_forms", science.episode_id)["facts"])
        assert f.boundary.record_admission(f.root, form, schema, f.operation(f.root)) == references(f.bundle)
        assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
        assert f.boundary.authenticate_received_saved_bundle(selected, f.bundle) == (origin,)
        assert all(f.boundary.resolve_received(f.root, ref, None) for ref in references(f.bundle))
    assert f.host.calls and not any(current for _, current in f.host.calls)
    assert f.snapshot() == before
    # This is only the actual current-file prerequisite, not a selected host
    # computation or a claim that an unavailable calculation was executed.
    for file in files(f.bundle):
        with pytest.raises(ValueError, match="retained_artifact_unavailable"):
            retained_native_file(f.store, file)
    assert f.snapshot() == before


@pytest.mark.parametrize("alter", ["missing", "size", "sha256"])
def test_b18_metadata_loss_is_distinct_from_scientific_byte_availability(f, alter):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    file = f.bundle["tables"][0]["file"]
    assert retained_native_file(f.store, file).is_file()
    if alter == "missing":
        f.store.db.execute("DELETE FROM artifacts WHERE id=?", (file["artifact_ref"],))
    else:
        value = 999 if alter == "size" else "0" * 64
        f.store.db.execute(f"UPDATE artifacts SET {alter}=? WHERE id=?", (value, file["artifact_ref"]))
    with pytest.raises(ValueError):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


@pytest.mark.parametrize("alter", ["leading_zero", "foreign_run", "foreign_parent", "suffix", "missing", "failed", "form"])
def test_b19_exact_admission_identity_and_no_receipt_insertion(f, alter):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child, receive=False)
    operation = f.operation(f.root)
    if alter == "leading_zero":
        operation = operation.replace(":0:", ":00:")
    elif alter == "foreign_run":
        operation = "other-run:" + operation.split(":", 1)[1]
    elif alter == "foreign_parent":
        operation = f.operation(child)
    elif alter == "suffix":
        operation += ":other"
    elif alter == "missing":
        f.store.db.execute("DELETE FROM runtime_report_attempts")
    elif alter == "failed":
        f.store.db.execute("UPDATE runtime_report_attempts SET failure='{}'")
    else:
        form["chosen_0"][0]["tables"].pop()
    before = f.snapshot()
    with pytest.raises(ValueError, match="admission_operation_required|successful_return_required|admitted_form_conflict"):
        with f.store.transaction():
            f.boundary.record_admission(f.root, form, schema, operation)
    assert f.snapshot() == before
    assert list(f.receipts.known(f.root.episode_id)) == []


def test_b20_aliases_namespaces_roles_schema_and_unrelated_sources(f):
    schema = schema_for(PROJECTION_SOURCE, PROJECTION_SOURCE)
    child = f.child(f.root, schema)
    facts, _ = f.own(child)
    form = form_with_facts({}, schema, facts)
    form["chosen_1"] = [f.alternate_projection]
    with pytest.raises(ValueError, match="conflicting_fields"):
        f.boundary.validate_received_report(child, form, schema)
    f.returned(f.root, child)
    for namespace in ("source", "execution_result", "other"):
        assert not f.boundary.resolve_received(f.root, f.bundle["sheet"]["artifact_ref"], namespace)
    launch = f.child(f.root, schema_for(SAVED_SOURCE), index=1, role="launch")
    with pytest.raises(ValueError, match="unsupported_return_owner"):
        f.boundary.facts(launch, schema_for(SAVED_SOURCE))
    assert not f.boundary.resolve_received(launch, f.bundle["sheet"]["artifact_ref"], None)
    changed = schema_for(SAVED_SOURCE)
    changed["properties"]["chosen_0"]["$defs"]["SavedSheetBundle"]["required"] = ["sheet"]
    with pytest.raises(ValueError, match="atac_return_unregistered_field_schema"):
        f.boundary.facts(f.root, changed)
    unknown = schema_for(SAVED_SOURCE)
    unknown["properties"]["chosen_0"]["x-source"] = "atac_differential_unknown"
    with pytest.raises(ValueError, match="unknown_source"):
        f.boundary.facts(f.root, unknown)
    ordinary = {"type": "object", "properties": {"done": {"type": "boolean", "x-source": "execution_completed"}},
        "required": ["done"], "additionalProperties": False}
    before = f.snapshot()
    assert f.boundary.facts(f.root, ordinary) == {}
    assert f.boundary.record_admission(f.root, {"done": False}, ordinary, "unrelated") == []
    assert f.boundary.validate_received_report(f.root, {"done": False}, ordinary) is None
    assert f.snapshot() == before


def test_b21_closure_snapshot_prefix_is_private_and_read_only(f, monkeypatch):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    f.own(child)
    f.returned(f.root, child)
    original = f.store.read_snapshot
    entered = []
    @contextmanager
    def snapshot():
        entered.append(True)
        with original():
            yield
    monkeypatch.setattr(f.store, "read_snapshot", snapshot)
    before = f.snapshot()
    facts = f.boundary.facts_for_closure(f.root, schema)
    assert entered == [True]
    assert set(facts) == {SAVED_SOURCE, PREFIX}
    witness = facts[PREFIX]["attempts"][0]
    assert set(witness) == {"decision_index", "delivery_ref", "child_episode_id", "contract_sha256", "form_sha256"}
    assert witness["child_episode_id"] == child.episode_id
    assert PREFIX not in atac_fact_sources()
    assert form_with_facts({}, schema, facts) == {"chosen_0": [f.bundle]}
    private_schema = schema_for(SAVED_SOURCE)
    private_schema["properties"]["chosen_0"]["x-source"] = PREFIX
    with pytest.raises(ValueError):
        validate_form({"chosen_0": [f.bundle]}, private_schema, lambda *_: True)
    assert f.snapshot() == before
    facts[SAVED_SOURCE][0]["tables"].clear()
    assert f.boundary.facts(f.root, schema)[SAVED_SOURCE] == [f.bundle]


@pytest.mark.parametrize("alter", [None, "saved_without_commission", "prior_action", "prior_form", "wrong_parent"])
def test_b22_unsaved_construction_uses_exact_frozen_manifest(f, alter):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    _, origin = f.own(child)
    f.returned(f.root, child)
    other = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, role="scientific_process")
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=2, saved=f.bundle, persist=False)
    if alter == "saved_without_commission":
        f.persist(selected)
    elif alter == "prior_action":
        f.journal.save("runtime_actions", {"episode_id": selected.episode_id, "decision_index": 0,
            "action": "{}", "result": "{}", "credit": None})
    elif alter == "prior_form":
        f.journal.save("runtime_forms", {"episode_id": selected.episode_id, "facts": "{}", "form": "{}"})
    elif alter == "wrong_parent":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE run_id=? AND episode_id=?",
            (other.episode_id, f.run_id, selected.episode_id))
        request = plain(selected.request)
        request["message"]["knowledge_inheritance"] = f.receipts.manifest(selected.episode_id)
        selected = replace(selected, request=request)
    before = f.snapshot()
    if alter is None:
        assert f.boundary.authenticate_received_saved_bundle(selected, f.bundle) == (origin,)
    else:
        with pytest.raises(ValueError, match="original_commission_required|commission_parent_conflict"):
            f.boundary.authenticate_received_saved_bundle(selected, f.bundle)
    assert f.snapshot() == before


@pytest.mark.parametrize("alter", ["native_mode", "other_bundle", "missing_manifest", "changed_manifest",
                                  "missing_prefix", "cycle", "missing_receipt"])
def test_saved_selection_exact_bundle_manifest_and_each_received_handle_required(f, alter):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1,
        saved=None if alter == "native_mode" else f.bundle)
    bundle = deepcopy(f.bundle)
    if alter == "other_bundle":
        bundle["tables"].pop()
    elif alter in {"missing_manifest", "changed_manifest"}:
        request = plain(selected.request)
        if alter == "missing_manifest":
            del request["message"]["knowledge_inheritance"]
        else:
            request["message"]["knowledge_inheritance"]["through_receipt_index"] = 999
        selected = replace(selected, request=request)
        f.persist(selected)
    elif alter == "missing_prefix":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=NULL WHERE run_id=? AND episode_id=?",
            (f.run_id, selected.episode_id))
    elif alter == "cycle":
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE run_id=? AND episode_id=?",
            (selected.episode_id, f.run_id, selected.episode_id))
        request = plain(selected.request)
        request["message"]["knowledge_inheritance"] = f.receipts.manifest(selected.episode_id)
        selected = replace(selected, request=request)
        f.persist(selected)
    elif alter == "missing_receipt":
        f.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND record_ref=?",
            (f.run_id, f.bundle["tables"][0]["file"]["artifact_ref"]))
    with pytest.raises(ValueError, match="saved_|commission_parent_conflict"):
        f.boundary.authenticate_received_saved_bundle(selected, bundle)


@pytest.mark.parametrize("alter", ["positional", "foreign_episode", "foreign_run", "leading_zero", "suffix", "extra_field", "empty"])
def test_host_origin_records_require_exact_owner_and_operation_grammar(f, alter, monkeypatch):
    child = f.child(f.root, schema_for(SAVED_SOURCE))
    _, origin = f.own(child)
    f.returned(f.root, child)
    bad = deepcopy(origin)
    if alter == "foreign_episode":
        bad["episode_id"] = f.root.episode_id
    elif alter == "foreign_run":
        bad["operation_key"] = "other-run:" + bad["operation_key"].split(":", 1)[1]
    elif alter == "leading_zero":
        bad["operation_key"] += "0"
    elif alter == "suffix":
        bad["operation_key"] += ":typed_form"
    elif alter == "extra_field":
        bad["source_ref"] = "unrequested"
    rows = () if alter == "empty" else ((bad["episode_id"], bad["operation_key"]),) if alter == "positional" else (bad,)
    monkeypatch.setattr(f.host, "completed_saved_bundle_origins", lambda *_: rows)
    with pytest.raises(ValueError, match="completed_bundle_origin"):
        f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


@pytest.mark.parametrize("kind", ["child", "episode_child", "tool"])
def test_existing_scientific_and_process_revision_edges_remain_usable(f, kind):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process", kind=kind)
    child = f.child(science, schema)
    _, origin = f.own(child)
    f.returned(science, child)
    f.returned(f.root, science)
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)


def compact_form_frame(f, parent, child, *, index, schema, selection):
    """Authored decision frame validated by the real frozen-contract reader."""
    from gene_annotation_episode.composition_information import (
        CONTRACT_INFORMATION_PROFILE, CONTRACT_INFORMATION_OPERATIONS)
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.episode_contract_information import expand_fact_form
    compact = deepcopy(schema)
    for name, node in compact['properties'].items():
        compact['properties'][name] = {'$ref': 'episode-fact:' + node['x-source']}
    selection = {**deepcopy(selection), 'schema_json': canonical(compact)}
    facts = {child.role: atac_fact_sources()}
    expanded = expand_fact_form(selection['schema_json'], child_role=child.role,
        facts_by_role=facts, permitted_child_roles=[child.role])
    action_schema = obj({'selection': {'anyOf': [obj({'kind': {'const': selection['kind']}})]},
        'report_update': obj({})})
    lookup = [{'properties': {'view': {'const': 'child_options'}, 'role': {'enum': [None, child.role]}}},
        *[{'properties': {'operation': {'const': name}}} for name in CONTRACT_INFORMATION_OPERATIONS]]
    select = obj({'response_type': {'type': 'string', 'const': 'select_action'}, **action_schema['properties']})
    saved = {'context': {'tools': [], 'contract_information_profile': CONTRACT_INFORMATION_PROFILE},
        'schema': action_schema, 'contract_information': {'version': CONTRACT_INFORMATION_PROFILE,
            'permitted_child_roles': [child.role], 'fact_sources_by_role': facts,
            'fact_sources_sha256': digest(facts), 'catalog_sha256': digest([]),
            'action_schema_sha256': digest(action_schema), 'instructions': 'Synthetic decision contract fixture.',
            'exchange_schema': {'properties': {'response': {'anyOf': [
                {'properties': {'lookup': {'anyOf': lookup}}}, select]}}}}}
    f.journal.save('runtime_model_calls', {'episode_id': parent.episode_id, 'call_index': index,
        'purpose': 'decision', 'request': canonical(saved), 'response': canonical({'selection': selection})})
    return selection, expanded


@pytest.mark.parametrize('tamper', [None, 'declaration', 'frozen_digest', 'missing_frame'])
def test_compact_commission_uses_original_frozen_contract_frame(f, tamper):
    schema = schema_for(SAVED_SOURCE)
    child = f.child(f.root, schema)
    action = json.loads(f.journal.row('runtime_actions', f.root.episode_id, 0)['action'])
    selected, expanded = compact_form_frame(f, f.root, child, index=0, schema=schema, selection=action)
    request = plain(child.request)
    request['message']['report_contract_declaration'] = expanded['declaration']
    child = replace(child, request=request)
    f.persist(child)
    f.change_action(f.root, 0, schema_json=selected['schema_json'])
    f.own(child)
    f.returned(f.root, child)
    if tamper == 'declaration':
        request['message']['report_contract_declaration']['expanded_schema_sha256'] = '0' * 64
        child = replace(child, request=request)
        f.persist(child)
    elif tamper == 'frozen_digest':
        saved = json.loads(f.journal.row('runtime_model_calls', f.root.episode_id, 0)['request'])
        saved['contract_information']['fact_sources_sha256'] = '0' * 64
        f.store.db.execute('UPDATE runtime_model_calls SET request=? WHERE call_index=0', (canonical(saved),))
    elif tamper == 'missing_frame':
        f.store.db.execute('DELETE FROM runtime_model_calls')
    if tamper is None:
        assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)
    else:
        with pytest.raises(ValueError):
            f.boundary.authenticate_received_saved_bundle(f.root, f.bundle)


def test_compact_redelivery_authenticates_its_own_frozen_expansion(f):
    child = f.child(f.root, schema_for(*FACT_SOURCES))
    _, origin = f.own(child)
    f.returned(f.root, child)
    schema = schema_for(SAVED_SOURCE)
    form = f.redeliver(f.root, child, schema, index=1)
    selected = json.loads(f.journal.row('runtime_model_calls', f.root.episode_id, 1)['response'])['selection']
    compact_form_frame(f, f.root, child, index=1, schema=schema, selection=selected)
    before = f.snapshot()
    assert f.boundary.record_admission(f.root, form, schema, f.operation(f.root, 1)) == references(f.bundle)
    assert f.boundary.authenticate_received_saved_bundle(f.root, f.bundle) == (origin,)
    assert f.snapshot() == before
