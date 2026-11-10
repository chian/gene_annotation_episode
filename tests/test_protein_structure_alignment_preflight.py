"""Real service/mother preflight with an explicitly injected authority port.

The retained extraction bytes are produced by the real native adapter. The
received-authority fixture below is NOT proof of frozen typed report delivery;
that complete extraction -> receipt -> new child path belongs to root's tests.
All execution occurs inside the enclosing bounded local_jobs verification job.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import shutil

import pytest

from gene_annotation_episode import protein_structure_operands as operands
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, identity, obj
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_contracts import issue, same
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_protein_structure_operands import native_fixture, ordinary_source
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_episodes import ContractLibrary


POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}


class ReceivedAuthorityFixture:
    """Only the public authority ports, with explicit supplied failure verdicts."""

    def __init__(self, store, context, rows):
        self.store, self.run_id, self.context = store, context.run_id, context
        self.rows = deepcopy(rows)
        self.calls = []
        self.failure = None

    def authenticate(self, context, *, allow_unsaved=False):
        assert context == self.context and allow_unsaved is True
        self.calls.append(("authenticate", context.episode_id))
        if self.failure is not None:
            raise ProteinStructureOperandError(self.failure)
        return context

    def received_sequence_descriptors(self, context, reference_ref):
        assert context == self.context
        self.calls.append(("descriptors", reference_ref))
        return [deepcopy(row["descriptor"]) for row in self.rows
                if row["descriptor"]["reference_ref"] == reference_ref]

    def authenticate_received_sequence(self, context, descriptor, *, required_use):
        assert context == self.context and required_use == "sequence_align"
        self.calls.append(("sequence", descriptor["reference_ref"]))
        for row in self.rows:
            if same(row["descriptor"], descriptor) and required_use in descriptor["allowed_uses"]:
                return deepcopy(row["view"])
        raise ProteinStructureOperandError(issue("sequence_not_received",
            stage="authority", field="descriptor"))


class ResultsOwnerFixture:
    """Registered results owner exposing only the deliberately injected port."""

    roles, entry_roles = ("results",), ()

    def __init__(self, returns):
        self.native_protein_structure_returns = returns

    def as_record(self):
        return {"version": "401_injected_received_authority_fixture"}

    def credit_kind(self, role):
        assert role == "results"
        return "operational"

    def unused(self, *args, **kwargs):
        raise AssertionError("Injected owner must perform no episode work")

    child_roles = assignment_schema = permitted_common_actions = unused
    allowed_children = prepare_assignment = instructions = decision_context = unused
    catalog = execute = fact_sources = facts = resolve = validate_report = credit_view = unused


@pytest.fixture(scope="module")
def retained_extractions(tmp_path_factory):
    root = tmp_path_factory.mktemp("401-native-extractions")
    with Store(root / "store") as store:
        store.create_problem(raw_sequence="AGST", molecule="protein")
        rows = [native_fixture(store, root / label, label, chain=chain)
                for label, chain in (("query", "A"), ("reference", "B"))]
        (root / "rows.json").write_text(json.dumps(rows))
    return root


@pytest.fixture
def case(tmp_path, retained_extractions):
    shutil.copytree(retained_extractions / "store", tmp_path / "store")
    with Store(tmp_path / "store") as store:
        rows = json.loads((retained_extractions / "rows.json").read_text())
        history = tmp_path / "statistics.sqlite"
        RunHistory(history).close()
        statistics = OrdinaryExecutionStatistics(history, "401-fixture", tmp_path / "statistics")
        tools = ToolRegistry(store, job_limits=POLICY, native_statistics=statistics)
        library = ContractLibrary()
        names = ("sequence.align", "execution.estimate", "sequence.inspect")
        available = tools.catalog()
        catalog = {name: available[name] for name in names}
        tool_library = ScientificToolLibrary.freeze(tmp_path / "tool-library", catalog=catalog, tool_info=True)
        def factory(services):
            return ScientificProcessEpisodes(services, library=library,
                tool_library=tool_library, child_roles=("scientific_process",))
        workflow = Workflow(store, tools, ScriptedProvider([]), tmp_path / "run", "synthetic-run",
            lambda path, initial: FixtureController(str(path), initial, 1), lambda *_: 0,
            episode_binding_factories=[factory], episode_record_receipts=True,
            initial_known_record_refs=[], resource_estimator=ResourceToolEstimator())
        scope = store.validate_scope({"subject_refs": store.problem()["subject_refs"]})
        root = workflow.build("annotation", "root", "Exercise the preflight seam", scope)
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Align explicitly supplied sequence operands",
            "scope": scope, "purpose": "Return the selected operation outcome",
            "schema_json": json.dumps(obj({"records": {"type": "array", "items": {
                "type": "string", "format": "reference"}, "x-source": "committed_record_refs"}})),
            "initial_report_json": "{}", "assignment": {"selection": {
                "version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A01"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": name, "resources": "local"} for name in names]},
                "evidence_refs": [], "constraints": {"fixture_authority_only": True}, "context": {}}}
        child = workflow.selected(root.source, commission, 0).child
        context = workflow.binding_context(child.source)
        authority = ReceivedAuthorityFixture(store, context, rows)
        owner = ResultsOwnerFixture(authority)
        workflow.episode_bindings.register(owner)
        value = type("PreflightCase", (), {})()
        value.__dict__.update(store=store, tools=tools, workflow=workflow, services=workflow.services,
            binding=workflow.scientific_process_binding, child=child, context=context, rows=rows,
            authority=authority, owner=owner, scope=scope, directory=tmp_path)
        yield value


def ordinary(case, molecule="protein"):
    sequence = {"dna": "ACGT", "rna": "ACGU", "protein": "AGST"}[molecule]
    source = ordinary_source(case.store)
    return case.store.put("reference", {"reference_type": molecule, "source_ref": source["id"],
        "accession": "structure_sequence_ordinary", "label": "Structure-derived protein sequence",
        "sequence_ref": case.store.artifact(sequence.encode(), "text/plain"), "molecule": molecule,
        "length": len(sequence), "term_refs": [], "context_refs": [], "anchor": None}, origin="caller")["id"]


def alignment_arguments(case, protected="both", molecule="protein", mode="global"):
    ordinary_ref = ordinary(case, molecule)
    return {"query_ref": case.rows[0]["descriptor"]["reference_ref"]
                if protected in ("query", "both") else ordinary_ref,
            "reference_ref": case.rows[1]["descriptor"]["reference_ref"]
                if protected in ("reference", "both") else ordinary_ref,
            "molecule": molecule, "mode": mode}


def selected(arguments, nested):
    return ("execution.estimate", {"tool": "sequence.align", "arguments": arguments}) if nested else (
        "sequence.align", arguments)


def run(case, arguments, nested=False):
    name, supplied = selected(arguments, nested)
    return asyncio.run(case.binding.execute(case.context, name, supplied, "401-selected"))


def state_counts(case):
    return {table: case.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
        for table in ("records", "artifacts", "tool_operations", "runtime_actions", "runtime_observations")}


def deny_downstream(case, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Rejected preflight reached a downstream consumer")
    monkeypatch.setattr(case.services, "execute_tool", forbidden)
    for name in ("execute", "execute_async", "_alignment_arguments", "_sequence",
                 "_prepare_alignment_async", "_estimate_native", "_sequence_worker_async",
                 "_record_native_execution"):
        monkeypatch.setattr(case.tools, name, forbidden)
    monkeypatch.setattr(type(case.tools.native_statistics), "recover_pending_statistics", forbidden)
    monkeypatch.setattr(case.workflow.resource_estimator, "estimate_context", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr(operands, "_bytes", forbidden)


def assert_invalid(outcome, problem):
    assert outcome["status"] == "invalid"
    assert outcome["record_refs"] == outcome["changed_record_refs"] == []
    assert outcome["result"] is None
    assert outcome["feedback"] == {"category": "arguments_or_reference", "code": problem["code"],
        "detail": {"protein_structure_issue": problem}}
    assert not {"native_execution_refs", "native_execution_expectations", "resource_tool_estimates"} & outcome.keys()


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
@pytest.mark.parametrize("protected", ["query", "reference", "both"])
@pytest.mark.parametrize("mode", ["local", "global"])
def test_original_descriptor_and_successful_dispatch_are_unchanged(case, monkeypatch, nested, protected, mode):
    arguments = alignment_arguments(case, protected, mode=mode)
    original = deepcopy(arguments)
    authenticated = case.services.authenticate_structure_alignment_operands(case.context, arguments)
    assert set(authenticated) == {"query", "reference"}
    for index, role in enumerate(("query", "reference")):
        assert authenticated[role] == (case.rows[index]["descriptor"]
            if protected in (role, "both") else None)
    calls = []
    outcome = {"status": "completed", "record_refs": [], "changed_record_refs": [],
        "result": {"fixture": "dispatch-port-only"}, "feedback": None}
    async def dispatch(name, args, *, scope, operation_key):
        calls.append((name, deepcopy(args), plain(scope), operation_key))
        return outcome
    monkeypatch.setattr(case.tools, "execute_async", dispatch)
    assert run(case, arguments, nested) is outcome
    name, supplied = selected(original, nested)
    assert calls == [(name, supplied, case.scope, "401-selected")]
    assert arguments == original
    assert not case.store.list("observation")


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
@pytest.mark.parametrize("molecule", ["dna", "rna", "protein"])
def test_ordinary_inputs_need_no_results_owner_or_descriptor(case, monkeypatch, nested, molecule):
    arguments = alignment_arguments(case, "ordinary", molecule)
    case.workflow.episode_bindings._by_role.pop("results")
    def not_authority(*args, **kwargs):
        raise AssertionError("Ordinary input entered protected authority")
    monkeypatch.setattr(operands, "authenticate_structure_sequence_reference", not_authority)
    assert case.services.authenticate_structure_alignment_operands(case.context, arguments) == {
        "query": None, "reference": None}
    # These ordinary operations run the actual ToolRegistry, native alignment
    # and timing estimate path, preserving the existing four-argument contract.
    outcome = run(case, arguments, nested)
    assert outcome["status"] == "completed", outcome
    assert len(list(case.store.db.execute("SELECT * FROM tool_operations"))) == 1
    if nested:
        assert outcome["result"]["arguments"] == arguments
        assert not case.store.list("observation")
    else:
        assert outcome["result"]["paired_positions"] == 4
        assert outcome["result"]["identity_fraction"] == 1
        assert len(case.store.list("observation")) == 1


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
@pytest.mark.parametrize("protected", ["query", "reference"])
@pytest.mark.parametrize("failure", ["missing_owner", "missing_returns", "no_descriptor", "wrong_use",
    "absent_frozen_receipt", "stale_frozen_receipt", "foreign_authority_run"])
def test_denied_authority_precedes_every_downstream_effect(case, monkeypatch, nested, protected, failure):
    arguments = alignment_arguments(case, protected)
    problem = issue("sequence_not_received", stage="authority", field="descriptor")
    if failure == "missing_owner":
        case.workflow.episode_bindings._by_role.pop("results")
    elif failure == "missing_returns":
        del case.owner.native_protein_structure_returns
    elif failure == "no_descriptor":
        case.authority.rows = []
    elif failure == "wrong_use":
        for row in case.authority.rows:
            row["descriptor"]["allowed_uses"] = ["structure_correspondence"]
    elif failure == "absent_frozen_receipt":
        case.authority.failure = problem
    elif failure == "stale_frozen_receipt":
        problem = issue("original_commission_mismatch", stage="authority", field="receipt")
        case.authority.failure = problem
    else:
        case.authority.run_id = "foreign-run"
        problem = issue("original_commission_mismatch", stage="authority", field="receipt")
    before = state_counts(case)
    deny_downstream(case, monkeypatch)
    assert_invalid(run(case, arguments, nested), problem)
    assert state_counts(case) == before


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
@pytest.mark.parametrize("role", ["query", "reference"])
@pytest.mark.parametrize("failure", ["malformed_parent", "missing_parent", "wrong_parent_kind", "changed_source"])
def test_malformed_typed_ancestry_is_never_ordinary(case, monkeypatch, nested, role, failure):
    arguments = alignment_arguments(case, "ordinary")
    descriptor = case.rows[0]["descriptor"]
    if failure == "changed_source":
        ref = descriptor["reference_ref"]
        source = case.store.get(descriptor["custody"]["source_ref"])
        source["version"] = "pretend_ordinary"
        case.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(source), source["id"]))
    else:
        payload = {"parent_refs": None if failure == "malformed_parent" else [
            "reference_" + "f" * 24 if failure == "missing_parent" else descriptor["custody"]["source_ref"]],
            "molecule": "protein", "sequence_ref": descriptor["sequence_file"]["artifact_ref"],
            "derivation": "extraction", "context_refs": [], "footprint": []}
        ref = identity("product", {"origin": "reasoning", "record": payload})
        record = dict(payload, id=ref, record_type="product", origin="reasoning")
        case.store.db.execute("INSERT INTO records VALUES(?,?,?,?)", (ref, "product", "reasoning", canonical(record)))
    arguments[role + "_ref"] = ref
    before = state_counts(case)
    deny_downstream(case, monkeypatch)
    assert_invalid(run(case, arguments, nested), issue("invalid_schema" if failure == "malformed_parent"
        else "conflicting_identity", stage="authority", field="descriptor"))
    assert state_counts(case) == before


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
@pytest.mark.parametrize("role", ["query", "reference"])
@pytest.mark.parametrize("kind", ["feature", "product"])
def test_original_descriptor_does_not_authorize_derived_operand(case, monkeypatch, nested, role, kind):
    descriptor = case.rows[0]["descriptor"]
    feature = case.store.put("feature", {"subject_ref": descriptor["reference_ref"], "kind": "sequence_region",
        "segments": [{"start": 0, "end": 4}], "strand": "+", "context_refs": []}, origin="reasoning")
    ref = feature["id"]
    if kind == "product":
        ref = case.store.put("product", {"parent_refs": [feature["id"]], "molecule": "protein",
            "sequence_ref": descriptor["sequence_file"]["artifact_ref"], "derivation": "extraction",
            "context_refs": [], "footprint": []}, origin="tool")["id"]
    arguments = alignment_arguments(case, "ordinary")
    arguments[role + "_ref"] = ref
    before = state_counts(case)
    deny_downstream(case, monkeypatch)
    assert_invalid(run(case, arguments, nested), issue("sequence_not_received", stage="authority", field="descriptor"))
    assert state_counts(case) == before


def test_each_call_uses_current_exact_descriptor_without_permission_union_or_cache(case):
    arguments = alignment_arguments(case, "query")
    first, eligible = deepcopy(case.authority.rows[0]), deepcopy(case.authority.rows[0])
    first["descriptor"]["allowed_uses"] = ["structure_correspondence"]
    eligible["descriptor"]["allowed_uses"] = ["sequence_align"]
    case.authority.rows = [first, eligible]
    result = case.services.authenticate_structure_alignment_operands(case.context, arguments)
    assert result["query"] == eligible["descriptor"] and result["reference"] is None
    result["query"]["allowed_uses"].append("structure_correspondence")
    assert case.authority.rows[1]["descriptor"]["allowed_uses"] == ["sequence_align"]
    case.authority.rows = [first]
    with pytest.raises(ProteinStructureOperandError) as failure:
        case.services.authenticate_structure_alignment_operands(case.context, arguments)
    assert failure.value.issue == issue("sequence_not_received", stage="authority", field="descriptor")


def test_same_reference_in_both_positions_is_authenticated_independently(case):
    arguments = alignment_arguments(case)
    arguments["reference_ref"] = arguments["query_ref"]
    result = case.services.authenticate_structure_alignment_operands(case.context, arguments)
    assert result["query"] == result["reference"] == case.rows[0]["descriptor"]
    assert result["query"] is not result["reference"]
    assert case.authority.calls.count(("sequence", arguments["query_ref"])) == 2


def test_foreign_context_rejects_before_store_or_binding_lookup(case, monkeypatch):
    arguments = alignment_arguments(case, "ordinary")
    def forbidden(*args, **kwargs):
        raise AssertionError("Foreign run consulted operands or another binding")
    monkeypatch.setattr(operands, "is_protein_structure_sequence_operand", forbidden)
    monkeypatch.setattr(case.workflow.episode_bindings, "for_role", forbidden)
    with pytest.raises(ProteinStructureOperandError) as failure:
        case.services.authenticate_structure_alignment_operands(replace(case.context, run_id="foreign"), arguments)
    assert failure.value.issue == issue("original_commission_mismatch", stage="authority", field="receipt")


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
def test_exact_selected_schema_validation_precedes_preflight(case, monkeypatch, nested):
    arguments = alignment_arguments(case)
    arguments["unselected_argument"] = True
    def forbidden(*args, **kwargs):
        raise AssertionError("Schema-invalid selection reached preflight")
    monkeypatch.setattr(case.services, "authenticate_structure_alignment_operands", forbidden)
    deny_downstream(case, monkeypatch)
    assert run(case, arguments, nested)["status"] == "invalid"


@pytest.mark.parametrize("nested", [False, True], ids=["align", "estimate"])
def test_runtime_records_rejection_without_completed_observation_or_forecast(case, monkeypatch, nested):
    arguments = alignment_arguments(case)
    case.authority.rows = []
    before = state_counts(case)
    deny_downstream(case, monkeypatch)
    name, supplied = selected(arguments, nested)
    with pytest.raises(ActionFailure) as failure:
        asyncio.run(case.child.source.execute({"kind": "tool", "tool": name, "arguments": supplied}, 0))
    problem = issue("sequence_not_received", stage="authority", field="descriptor")
    assert failure.value.feedback == {"category": "arguments_or_reference", "code": problem["code"],
        "detail": {"protein_structure_issue": problem}}
    after = state_counts(case)
    assert after == {**before, "runtime_actions": before["runtime_actions"] + 1}
    row = case.workflow.journal.row("runtime_actions", case.context.episode_id, 0)
    assert row["credit"] is None
    assert_invalid(json.loads(row["result"]), problem)


@pytest.mark.parametrize("name", ["sequence.inspect", "execution.estimate"])
def test_other_selected_operations_do_not_enter_alignment_preflight(case, monkeypatch, name):
    arguments = ({"subject_ref": case.scope["subject_refs"][0]} if name == "sequence.inspect" else
        {"tool": "source.xlsx.sheets", "arguments": {"source_ref": case.rows[0]["descriptor"]["custody"]["source_ref"]}})
    def forbidden(*args, **kwargs):
        raise AssertionError("Unrelated selected operation entered alignment preflight")
    monkeypatch.setattr(case.services, "authenticate_structure_alignment_operands", forbidden)
    captured = []
    async def dispatch(selected_name, supplied, *, scope, operation_key):
        captured.append((selected_name, supplied))
        return {"status": "completed", "record_refs": [], "changed_record_refs": [], "result": None}
    monkeypatch.setattr(case.tools, "execute_async", dispatch)
    result = asyncio.run(case.binding.execute(case.context, name, arguments, "401-unrelated"))
    assert result["status"] == "completed", result
    assert captured == [(name, arguments)]
