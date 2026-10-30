"""Homology projection and actual Store/typed-return boundary verification.

Numerical examples use retained synthetic native fixtures and the real adapter.
Publication envelopes/download records are controlled test inputs, not evidence
of native acquisition or a Workflow run. Store, Journal, EpisodeReceipts,
original requests, custody and TypedReportContract are real. No network/model/job.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
from gene_annotation_episode.bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from gene_annotation_episode.bvbrc_homology_returns import (
    BVBRCHomologyReturns, FACT_SOURCES, IDENTIFIER_NAMESPACES,
    homology_fact_sources, project_homology_facts, requested_sources,
)
from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, validate_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import TypedReportContract, _object
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords, selector
from test_bvbrc_homology_bundle_adapter import c4_fixture, consume
from test_bvbrc_homology_grader import F, G, program_document


MEASUREMENTS, WEIGHTS, REQUIREMENTS = FACT_SOURCES
SELECTIONS = {
    "hits": {"metric": "reported_hit_count", "report_index": 0},
    "qcov": {"metric": "query_paired_coverage", "report_index": 0, "hit_index": 0},
    "rcov": {"metric": "reference_paired_coverage", "report_index": 0, "hit_index": 0},
    "functions": {"metric": "conditional_function_weights", "report_index": 0},
    "missing": {"metric": "missing_requirements"},
}


def fact_form(*sources):
    properties = {"requested_" + str(i): homology_fact_sources()[source]["report_schema"]
                  for i, source in enumerate(sources)}
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def content(value, name="supplied"):
    raw = canonical(value).encode()
    sha = hashlib.sha256(raw).hexdigest()
    return {"source_ref": "source_" + digest([name, sha])[:24], "artifact_field": "artifact_ref",
            "artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(raw)}


def projection(*, selections=None, fixture=None):
    fixture = c4_fixture() if fixture is None else fixture
    selections = SELECTIONS if selections is None else selections
    result = consume(fixture, selections)
    selected = selector()
    selected.update(endpoint="requested_projection", adapter={"adapter_id": "bvbrc_homology",
        "adapter_version": "1", "parameters": fixture[3]},
        requested_schema=adapter.requested_form_schema(selections))
    bundle = content(fixture[0], "bundle")
    saved = {key: deepcopy(value) for key, value in result.items() if key not in {"sheet", "components"}}
    saved.update(sheet_content=content(result["sheet"], "sheet") if result["sheet"] is not None else None,
                 components_content=content(result["components"], "components") if result["components"] is not None else None)
    return {"version": RESULT_VERSION, "reference": bundle["source_ref"], "source_ref": bundle["source_ref"],
        "record_refs": [bundle["source_ref"]], "publication": {"bundle_content": bundle,
            "result_record_refs": [bundle["source_ref"]], "adapter_result": saved},
        "publication_inputs": {"selector": selected, "adapter": selected["adapter"]}}


def all_facts(body):
    return project_homology_facts(body, requested_sources=FACT_SOURCES)


def numbers(facts):
    return {row["field"]: row["value"] for row in facts[MEASUREMENTS]}


@pytest.fixture(autouse=True)
def no_network_or_jobs(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Homology return verification attempted acquisition or execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)


def test_closed_sources_preserve_actual_saved_numbers_and_conditional_weights():
    body = projection()
    original = deepcopy(body)
    facts = all_facts(body)
    assert numbers(facts) == {"hits": 3, "qcov": .60, "rcov": .75}
    assert type(numbers(facts)["hits"]) is int
    assert facts[WEIGHTS] == [{"source_ref": body["source_ref"], "field": "functions",
        "weights": [{"function": F, "weight": 2 / 3}, {"function": G, "weight": 1 / 3}]}]
    assert facts[REQUIREMENTS] == [{"source_ref": body["source_ref"], "field": "missing", "requirements": []}]
    assert body == original
    schema = validate_closed_schema(fact_form(*FACT_SOURCES))
    values = form_with_facts({}, schema, facts)
    assert validate_form(values, schema, lambda *_: True) == values
    declarations = homology_fact_sources()
    declarations[MEASUREMENTS]["report_schema"]["items"]["properties"]["value"]["type"].append("string")
    assert "string" not in homology_fact_sources()[MEASUREMENTS]["report_schema"]["items"]["properties"]["value"]["type"]


def test_zero_missing_and_partial_are_distinct_saved_cells():
    no_hit = projection(selections={"hits": {"metric": "reported_hit_count", "report_index": 1},
        "functions": {"metric": "conditional_function_weights", "report_index": 1}})
    assert numbers(all_facts(no_hit)) == {"hits": 0}
    assert all_facts(no_hit)[WEIGHTS][0]["weights"] == []
    doc = program_document("blastp")
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    missing = projection(fixture=c4_fixture(doc, extras=False), selections={
        "hits": {"metric": "reported_hit_count", "report_index": 0},
        "functions": {"metric": "conditional_function_weights", "report_index": 0},
        "missing": {"metric": "missing_requirements"}})
    facts = all_facts(missing)
    assert numbers(facts) == {"hits": None}
    assert facts[WEIGHTS][0]["weights"] is None
    assert facts[REQUIREMENTS][0]["requirements"]
    assert missing["publication"]["adapter_result"]["status"] == "partial"
    failed = deepcopy(missing)
    failed["publication"]["adapter_result"].update(status="failed", facts={})
    assert all_facts(failed) == {source: [] for source in FACT_SOURCES}


def test_only_requested_groups_and_saved_fields_cross_without_recalculation(monkeypatch):
    body = projection(selections={"paired query / coverage": SELECTIONS["qcov"],
        "conditional functions": SELECTIONS["functions"]})
    def forbidden(*args, **kwargs):
        raise AssertionError("Reading a saved Homology return invoked a current parser/calculator")
    monkeypatch.setattr(adapter, "consume_bundle", forbidden)
    monkeypatch.setattr(adapter, "calculate_homology_scores", forbidden)
    monkeypatch.setattr(adapter, "read_homology_raw_json", forbidden)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_homology_grader.calculate_homology_scores", forbidden)
    assert project_homology_facts(body, requested_sources=()) == {}
    values = project_homology_facts(body, requested_sources=[MEASUREMENTS])
    assert set(values) == {MEASUREMENTS}
    assert values[MEASUREMENTS] == [{"source_ref": body["source_ref"],
        "field": "paired query / coverage", "value": .6}]
    assert all_facts(body)[REQUIREMENTS] == []
    assert "sheet_content" not in canonical(values) and "components_content" not in canonical(values)
    assert requested_sources(fact_form(WEIGHTS, MEASUREMENTS, WEIGHTS)) == (WEIGHTS, MEASUREMENTS)


@pytest.mark.parametrize("bad", [True, 3.0, "3", float("nan")])
def test_saved_integer_types_are_not_coerced(bad):
    body = projection()
    body["publication"]["adapter_result"]["facts"]["hits"] = bad
    with pytest.raises(ValueError):
        all_facts(body)


@pytest.mark.parametrize("alter", [
    lambda body: body.update(source_ref="source_" + "f" * 24),
    lambda body: body["publication"]["bundle_content"].update(source_ref="source_" + "f" * 24),
    lambda body: body["publication"]["adapter_result"].update(adapter_version="2"),
    lambda body: body["publication_inputs"]["selector"]["adapter"].update(adapter_id="other"),
    lambda body: body["publication"]["adapter_result"]["facts"].update(extra=42),
    lambda body: body["publication"]["adapter_result"]["facts"].pop("qcov"),
    lambda body: body["publication_inputs"]["selector"]["requested_schema"]["properties"]["qcov"].pop("x-homology-fact"),
    lambda body: body["publication"]["adapter_result"]["facts"]["functions"][0].update(weight=True),
    lambda body: body["publication"]["adapter_result"]["facts"]["functions"][0].update(function=G),
])
def test_supplied_projection_rejects_wrong_source_selector_or_fact_shape(alter):
    body = projection()
    alter(body)
    with pytest.raises(ValueError):
        all_facts(body)


def test_requirement_projection_must_equal_original_saved_requirements():
    body = projection()
    body["publication"]["adapter_result"]["facts"]["missing"] = [{"requirement_id": "missing:1",
        "kind": "scientific_metadata", "role": None, "source_refs": [], "reason_code": "missing_population"}]
    with pytest.raises(ValueError, match="saved_requirement_conflict"):
        all_facts(body)


class ControlledPublications:
    """Supplied publication boundary; production hash/native checks are separate."""
    def __init__(self, saved):
        self.saved, self.bodies = saved, {}

    def add(self, context, body, *, index=0):
        body = deepcopy(body)
        binding = self.saved.source(canonical({"body": body, "episode_id": context.episode_id,
            "action_index": index}).encode(), provider=DATA_PROVIDER)
        reference = binding["source_ref"]
        body.update(reference=reference, source_ref=reference, record_refs=[reference],
            run_id=context.run_id, episode_id=context.episode_id,
            scope=plain(context.scope), assignment=plain(context.assignment))
        body["publication"].update(bundle_content=binding, result_record_refs=[reference])
        self.bodies[reference] = body
        self.saved.own(context, reference, index, tool="api.bvbrc_appservice.download")
        return body

    def own_results(self, context):
        self.saved.custody.authenticate(context, allow_unsaved=True)
        rows = self.saved.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND result IS NOT NULL ORDER BY decision_index", (context.run_id, context.episode_id))
        refs = []
        for row in rows:
            result = json.loads(row["result"])
            if result["status"] in {"completed", "partial"}:
                refs.extend(ref for ref in result["record_refs"] if ref in self.bodies)
        return refs

    def read(self, reference, scope, *, episode_id=None):
        body = deepcopy(self.bodies[reference])
        context = self.saved.custody.context(body["episode_id"])
        assert episode_id is None or episode_id == context.episode_id
        self.saved.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        assert reference in self.own_results(context)
        return body


class ReturnFixture:
    def __init__(self, store):
        self.saved = SavedRecords(store)
        self.store = store
        self.publications = ControlledPublications(self.saved)
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id)
        self.api.appservice = SimpleNamespace(publications=self.publications,
            custody=self.saved.custody, resolve=self.resolve_source)
        self.host = BVBRCHomologyReturns(self.api)

    def resolve_source(self, context, reference, namespace):
        if namespace not in {None, "source", "execution_result"}:
            return None
        try:
            self.saved.custody.possession(context, reference)
            if namespace == "execution_result":
                self.publications.read(reference, context.scope)
            return True
        except (KeyError, ValueError):
            return False

    def child(self, parent, role, body, *, index=0, sources=FACT_SOURCES, schema=None):
        assignment = {} if role != "results" else {"version": "execution_results_assignment_v1",
            "handoff_ref": "source_" + "a" * 24, "selector": body["publication_inputs"]["selector"]}
        return self.saved.child(parent, role, assignment, index,
            schema=fact_form(*sources) if schema is None else schema)

    def candidate(self, child, *, extra_facts=None):
        schema = plain(child.request)["report_contract"]["measurements"]["schema"]
        facts = (self.host.facts(child, schema) if child.role == "results" else
                 self.host.received_facts(child, schema))
        facts.update(extra_facts or {})
        form = form_with_facts({}, schema, facts)
        self.saved.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        return form, schema

    def admit(self, parent, child, *, extra_facts=None, receive=True):
        form, schema = self.candidate(child, extra_facts=extra_facts)
        original = plain(child.request)["report_contract"]
        resolve = self.host.resolve_own if child.role == "results" else self.host.resolve_received
        def resolver(reference, namespace):
            value = resolve(child, reference, namespace)
            return self.resolve_source(child, reference, namespace) if value is None else value
        typed = TypedReportContract(original["decision"], schema, resolver,
            lambda value: self.host.validate_received_report(child, value, schema))
        admitted = plain(typed.admit(form, audit_identifiers=(child.episode_id,)).as_record())
        index = int(child.path[-1][1].removeprefix("child_"))
        self.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24],
            "child_episode_id": child.episode_id, "contract": canonical(original),
            "form": canonical(admitted), "failure": None})
        key = f"{parent.run_id}:{parent.episode_id}:{index}:typed_form"
        references = self.host.record_admission(parent, admitted, schema, key)
        if receive:
            self.saved.receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return admitted, schema, key, references


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ReturnFixture(store)


def test_real_typed_admission_and_recursive_forwarding_preserve_exact_values(run):
    body = projection()
    root = run.saved.root
    first = run.child(root, "scientific_process", body)
    second = run.child(first, "scientific_process", body)
    producer = run.child(second, "results", body)
    published = run.publications.add(producer, body)
    schema = fact_form(*FACT_SOURCES)
    expected = run.host.facts(producer, schema)
    assert run.host.received_context(root) == run.host.received_context(first) == run.host.received_context(second) == []
    own_action_count = run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    _, _, _, references = run.admit(second, producer, receive=False)
    assert references == [published["source_ref"]]
    assert run.host.received_facts(second, schema) == expected
    assert published["source_ref"] not in run.saved.receipts.known(second.episode_id)
    assert run.host.received_context(first) == []
    run.saved.receipts.receive(second.episode_id, references, kind="child_form", source_index=0)
    run.admit(first, second)
    assert run.host.received_facts(first, schema) == expected
    assert run.host.received_context(root) == []
    run.admit(root, first)
    assert run.host.received_facts(root, schema) == expected
    assert numbers(expected) == {"hits": 3, "qcov": .6, "rcov": .75}
    assert run.host.resolve_received(root, F, "bvbrc_homology_function")
    assert not run.host.resolve_received(root, "unreceived function", "bvbrc_homology_function")
    assert run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == own_action_count
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_latest_completed_publication_replaces_earlier_partial_in_own_projection(run):
    body = projection()
    early = deepcopy(body)
    early["publication"]["adapter_result"]["facts"]["functions"] = None
    early["publication"]["adapter_result"]["status"] = "partial"
    producer = run.child(run.saved.root, "results", body)
    first = run.publications.add(producer, early)
    before = deepcopy(run.host.facts(producer, fact_form(*FACT_SOURCES)))
    last = run.publications.add(producer, body, index=1)
    after = run.host.facts(producer, fact_form(*FACT_SOURCES))
    assert {row["source_ref"] for rows in after.values() for row in rows} == {last["source_ref"]}
    assert before[WEIGHTS][0]["weights"] is None
    assert after[WEIGHTS][0]["weights"] is not None
    assert run.publications.read(first["source_ref"], producer.scope)["publication"] == first["publication"]
    incomplete = run.publications.add(producer, early, index=2)
    run.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE episode_id=? AND decision_index=2",
        (producer.episode_id,))
    assert run.host.facts(producer, fact_form(*FACT_SOURCES)) == after
    assert incomplete["source_ref"] != last["source_ref"]


@pytest.mark.parametrize("alter", [
    lambda form: form["requested_0"][0].update(value=3.0),
    lambda form: form["requested_0"][0].update(value=True),
    lambda form: form["requested_0"][1].update(field="rcov"),
    lambda form: form["requested_0"][1].update(value=.75),
    lambda form: form["requested_0"][0].update(source_ref="source_" + "e" * 24),
    lambda form: form["requested_1"][0]["weights"][0].update(function=G),
    lambda form: form["requested_1"][0]["weights"][0].update(weight=1 / 3),
    lambda form: form["requested_0"].reverse(),
])
def test_valid_individual_identifiers_cannot_change_whole_saved_row(run, alter):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body)
    form, schema = run.candidate(producer)
    alter(form)
    with pytest.raises(ValueError):
        run.host.validate_received_report(producer, form, schema)


def test_original_form_schema_and_frozen_return_cannot_be_substituted(run):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body)
    form, schema, key, _ = run.admit(run.saved.root, producer)
    changed = deepcopy(schema)
    changed["properties"]["requested_0"]["items"]["properties"]["value"]["type"] = ["integer", "null"]
    with pytest.raises(ValueError, match="admitted_form_conflict"):
        run.host.record_admission(run.saved.root, form, changed, key)
    row = run.saved.journal.row("runtime_forms", producer.episode_id)
    frozen = json.loads(row["form"])
    frozen["requested_0"][0]["value"] = 4
    run.saved.journal.save("runtime_forms", {**row, "form": canonical(frozen)})
    with pytest.raises(ValueError, match="frozen_form_conflict"):
        run.host.received_context(run.saved.root)


def test_unrequested_groups_and_opaque_reference_do_not_deliver_saved_numbers(run):
    body = projection()
    parent = run.child(run.saved.root, "scientific_process", body)
    producer = run.child(parent, "results", body, sources=(MEASUREMENTS,))
    run.publications.add(producer, body)
    run.admit(parent, producer)
    assert run.host.received_facts(parent, fact_form(WEIGHTS)) == {WEIGHTS: []}
    assert not run.host.resolve_received(parent, F, "bvbrc_homology_function")
    opaque = {"type": "object", "properties": {"refs": {"type": "array", "items": {
        "type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
        "x-source": "execution_result_refs"}}, "required": ["refs"], "additionalProperties": False}
    only_ref = run.child(parent, "results", body, index=1, schema=opaque)
    publication = run.publications.add(only_ref, body)
    run.admit(parent, only_ref, extra_facts={"execution_result_refs": [publication["source_ref"]]})
    assert run.host.received_facts(parent, fact_form(WEIGHTS)) == {WEIGHTS: []}
    assert run.host.resolve_received(parent, publication["source_ref"], "execution_result") is True
    run.admit(run.saved.root, parent)
    assert run.host.received_facts(run.saved.root, fact_form(WEIGHTS)) == {WEIGHTS: []}


def test_original_child_dependencies_remain_required_after_parent_forwarding(run):
    body = projection()
    parent = run.child(run.saved.root, "scientific_process", body)
    producer = run.child(parent, "results", body)
    run.publications.add(producer, body)
    run.admit(parent, producer)
    run.admit(run.saved.root, parent)
    before = run.host.received_facts(run.saved.root, fact_form(*FACT_SOURCES))
    assert numbers(before)["hits"] == 3
    run.store.db.execute("DELETE FROM runtime_report_attempts WHERE parent_episode_id=?", (parent.episode_id,))
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        run.host.received_context(run.saved.root)


def test_frozen_child_cannot_be_repriced_from_later_publication(run):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body)
    run.admit(run.saved.root, producer)
    later = deepcopy(body)
    later["publication"]["adapter_result"]["facts"]["hits"] = 4
    run.publications.add(producer, later, index=1)
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        run.host.received_context(run.saved.root)


def test_requirement_identifiers_and_source_dependencies_cross_only_as_requested(run):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    dependency = run.saved.source(b"native evidence dependency")["source_ref"]
    run.saved.own(producer, dependency)
    requirements = [{"requirement_id": "missing taxonomy / supplied group", "kind": "scientific_metadata",
        "role": "linked taxonomy", "source_refs": [dependency], "reason_code": "taxonomy input unavailable"}]
    body["publication"]["adapter_result"].update(status="partial", missing_requirements=requirements)
    body["publication"]["adapter_result"]["facts"]["missing"] = deepcopy(requirements)
    publication = run.publications.add(producer, body, index=1)
    form, _, _, references = run.admit(run.saved.root, producer)
    assert references == [publication["source_ref"], dependency]
    assert form["requested_2"][0]["requirements"] == requirements
    for namespace, field in (("bvbrc_homology_requirement", "requirement_id"),
                             ("bvbrc_homology_role", "role"), ("bvbrc_homology_reason", "reason_code")):
        assert run.host.resolve_received(run.saved.root, requirements[0][field], namespace)
        assert not run.host.resolve_received(run.saved.root, "unreceived", namespace)
    assert run.host.resolve_received(run.saved.root, dependency, "source")
    assert dependency in run.saved.receipts.known(run.saved.root.episode_id)


def test_unpossessed_requirement_source_cannot_be_registered_as_received(run):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    source = run.saved.source(b"exists but was never received")["source_ref"]
    requirements = [{"requirement_id": "missing:taxa", "kind": "scientific_metadata", "role": None,
        "source_refs": [source], "reason_code": "taxa_unavailable"}]
    body["publication"]["adapter_result"].update(status="partial", missing_requirements=requirements)
    body["publication"]["adapter_result"]["facts"]["missing"] = deepcopy(requirements)
    run.publications.add(producer, body)
    with pytest.raises(ValueError, match="input_not_possessed"):
        run.host.facts(producer, fact_form(REQUIREMENTS))
    assert source not in run.saved.receipts.known(run.saved.root.episode_id)


def test_repeated_read_uses_original_receipts_without_current_grader(run, monkeypatch):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body)
    run.admit(run.saved.root, producer)
    expected = run.host.received_context(run.saved.root)
    records = list(run.store.db.iterdump())
    def forbidden(*args, **kwargs):
        raise AssertionError("Saved return attempted a current grading operation")
    monkeypatch.setattr(adapter, "consume_bundle", forbidden)
    monkeypatch.setattr(adapter, "calculate_homology_scores", forbidden)
    fresh = BVBRCHomologyReturns(run.api)
    assert fresh.received_context(run.saved.root) == expected
    assert fresh.received_context(run.saved.root) == expected
    assert list(run.store.db.iterdump()) == records


@pytest.mark.parametrize("schema_conflict", [False, True], ids=["original_schema", "conflicting_schema"])
def test_original_redelivery_adds_no_duplicate_rows_or_completed_action(run, schema_conflict):
    body = projection()
    parent = run.saved.root
    producer = run.child(parent, "results", body)
    publication = run.publications.add(producer, body)
    form, _, _, _ = run.admit(parent, producer)
    before = run.host.received_context(parent)
    prior = run.store.db.execute("SELECT delivery_ref FROM runtime_report_attempts WHERE parent_episode_id=?",
        (parent.episode_id,)).fetchone()
    revised = fact_form(MEASUREMENTS)
    returned = {"requested_0": form["requested_0"]}
    contract = {"decision": "Return only the requested measurements", "measurements": {"schema": revised},
        "information": {"requested_0": "requested_0"}}
    selected = {"kind": "redeliver_report", "delivery_ref": prior["delivery_ref"],
        "schema_json": canonical(revised), "purpose": contract["decision"]}
    # A historical direct decision still saved its original action schema.
    # This is an authored fixture of that frame, not a Workflow-generated call.
    branch = _object({"kind": {"type": "string", "const": "redeliver_report"},
        "delivery_ref": {"type": "string"}, "purpose": {"type": "string"},
        "schema_json": {"type": "string"}})
    if schema_conflict:
        branch["properties"]["purpose"]["const"] = "A different permitted purpose"
    request = {"context": {}, "schema": _object({"selection": {"anyOf": [branch]},
        "report_update": _object({})})}
    run.saved.journal.save("runtime_model_calls", {"episode_id": parent.episode_id,
        "call_index": 1, "purpose": "decision", "request": canonical(request),
        "response": canonical({"selection": selected, "report_update": {}})})
    run.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
        "decision_index": 1, "delivery_ref": prior["delivery_ref"], "child_episode_id": producer.episode_id,
        "contract": canonical(contract), "form": canonical(returned), "failure": None})
    if schema_conflict:
        records = list(run.store.db.iterdump())
        with pytest.raises(ValueError, match="parent_selection_invalid"):
            run.host.record_admission(parent, returned, revised,
                f"{parent.run_id}:{parent.episode_id}:1:typed_form")
        assert list(run.store.db.iterdump()) == records
        return
    assert run.host.record_admission(parent, returned, revised,
        f"{parent.run_id}:{parent.episode_id}:1:typed_form") == [publication["source_ref"]]
    assert run.host.received_context(parent) == before
    assert run.saved.journal.row("runtime_actions", parent.episode_id, 1) is None
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_unsuccessful_report_attempt_does_not_deliver_values(run):
    body = projection()
    parent = run.saved.root
    producer = run.child(parent, "results", body)
    published = run.publications.add(producer, body)
    form, schema = run.candidate(producer)
    run.saved.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
        "decision_index": 0, "delivery_ref": "delivery_failed", "child_episode_id": producer.episode_id,
        "contract": canonical(plain(producer.request)["report_contract"]), "form": canonical(form),
        "failure": canonical({"code": "fixture_rejected_return"})})
    assert run.host.received_facts(parent, schema) == {source: [] for source in FACT_SOURCES}
    assert not run.host.resolve_received(parent, published["source_ref"], "execution_result")
    assert not run.host.resolve_received(parent, "hits", "bvbrc_homology_field")


@pytest.mark.parametrize("field", ["run_id", "episode_id", "assignment", "scope"])
def test_foreign_or_modified_results_context_is_rejected(run, field):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    run.publications.add(producer, body)
    value = "other" if field in {"run_id", "episode_id"} else {}
    with pytest.raises(ValueError):
        run.host.facts(replace(producer, **{field: value}), fact_form(*FACT_SOURCES))


def test_unknown_namespace_and_saved_empty_projection_are_not_scientific_facts(run):
    body = projection()
    producer = run.child(run.saved.root, "results", body)
    assert run.host.facts(producer, fact_form(*FACT_SOURCES)) == {source: [] for source in FACT_SOURCES}
    assert run.host.resolve_own(producer, "unrelated", "not_a_homology_namespace") is None
    assert run.host.resolve_received(run.saved.root, "unrelated", "not_a_homology_namespace") is None
    assert len(IDENTIFIER_NAMESPACES) == 5
