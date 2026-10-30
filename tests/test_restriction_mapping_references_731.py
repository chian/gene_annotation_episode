"""731 name-authority joins; engineering forms contain no measurements.

Engineering fixtures prove record/selector/receipt behavior, with own catalog
membership explicitly disabled. The separate retained728 case reads its actual
original saved operation and never changes that request into a scientific run.
"""
from copy import deepcopy
from dataclasses import replace
import builtins
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.restriction_mapping_action_records import RestrictionMappingActionRecords
from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
from gene_annotation_episode.restriction_mapping_returns import restriction_mapping_fact_sources
from gene_annotation_episode.state import Store


RUN = "restriction731-engineering"
SOURCE = "restriction_mapping_results"
PREFIX = "restriction_mapping_reference_"
SELECTOR = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_restriction_registry_2026-10-29_728/SAVED_SELECTOR_001.json")
pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def requested(*, names=True, source=False, candidate=False, field="selected"):
    fields = restriction_mapping_fact_sources()[SOURCE]["report_schema"]
    group = fields["items"]["properties"]
    keep = {"selection_policy", "sequence_ref", "namespace", "topology", "data_status",
        "coordinate_unit", "population_scope"}
    if source:
        keep.add("source_ref")
    if names:
        keep.add("enzyme_rows")
        row = group["enzyme_rows"]["items"]
        row["properties"] = {key: value for key, value in row["properties"].items()
            if key in {"catalog_ordinal", "name", "search_state", "position_meaning"}}
        row["required"] = list(row["properties"])
    group = {key: value for key, value in group.items() if key in keep}
    group["selection_policy"] = {"type": "string", "const": "all_own_completed_results"}
    fields["items"]["properties"] = group
    fields["items"]["required"] = list(group)
    properties = {field: fields}
    if candidate:
        properties["candidate"] = {"type": "string", "format": "identifier",
            "x-reference-namespace": "restriction_enzyme"}
    return {"type": "object", "properties": properties, "required": list(properties),
        "additionalProperties": False}


def engineering_rows(case, schema, *, name="EcoRI"):
    """Namespace-only host-form fixture: no counts, positions or source science."""
    fields = next(node for node in schema["properties"].values() if node.get("x-source") == SOURCE)
    group = {"selection_policy": "all_own_completed_results", "sequence_ref": case.sequence,
        "namespace": "subject", "topology": None, "data_status": "unavailable",
        "coordinate_unit": "nt", "population_scope": "full_selected_native_enzyme_population",
        "source_ref": "engineering_source_handle", "enzyme_rows": [{"catalog_ordinal": 0,
            "name": name, "search_state": "not_started", "position_meaning": "unknown"}]}
    return [{key: value for key, value in group.items() if key in fields["items"]["properties"]}]


def saved_context(case, *, parent=None, index=0, role="annotation", schema=None,
        inheritance=True, assignment=None):
    schema = requested() if schema is None else schema
    path = ((role, "root"),) if parent is None else (*parent.path, (role, "child_" + str(index)))
    episode_id = EpisodeRef(RUN, path).episode_id
    manifest = case.receipts.bind(episode_id, None if parent is None else parent.episode_id)
    message = {"scope": deepcopy(case.scope), "episode_assignment": assignment or {}}
    if inheritance:
        message["knowledge_inheritance"] = manifest
    request = {"message": message, "report_contract": {
        "decision": "Use only the requested engineering form", "measurements": {"schema": schema}}}
    context = BindingContext(RUN, episode_id, role, path, case.scope, assignment or {}, request)
    case.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
        "request": canonical(request), "initial_credit": 0., "state": "active"})
    if parent is not None:
        case.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": role, "scope": case.scope,
                "schema_json": canonical(schema), "purpose": request["report_contract"]["decision"]}),
            "result": canonical({"status": "engineering_commission"}), "credit": 0.})
    return context


def frozen(case, context, *, name="EcoRI", form=True, rows=None, candidate="BcgI"):
    schema = plain(context.request)["report_contract"]["measurements"]["schema"]
    rows = engineering_rows(case, schema, name=name) if rows is None else rows
    value = {key: deepcopy(rows) if node.get("x-source") == SOURCE else candidate
        for key, node in schema["properties"].items()}
    case.journal.save("runtime_forms", {"episode_id": context.episode_id,
        "facts": canonical({SOURCE: rows}), "form": canonical(value) if form else None})
    return value


def admitted(case, parent, child, *, index=None, name="EcoRI", contract=None, form=None, failure=None):
    index = int(child.path[-1][1][6:]) if index is None else index
    form = frozen(case, child, name=name) if form is None else form
    case.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
        "decision_index": index, "child_episode_id": child.episode_id,
        "delivery_ref": "engineering_delivery_" + child.episode_id,
        "contract": canonical(contract or plain(child.request)["report_contract"]),
        "form": canonical(form), "failure": failure})
    return form


def update_request(case, context, message):
    request = plain(context.request)
    request["message"] = message
    case.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
        (canonical(request), RUN, context.episode_id))
    return replace(context, request=request)


@pytest.fixture
def engineering_case(tmp_path, monkeypatch):
    fasta = tmp_path / "namespace-engineering.fa"
    fasta.write_text(">engineering\nAAAAGAATTCTTTT\n")
    with Store(tmp_path / "engineering-store") as store:
        sequence, = store.create_problem(fasta, molecule="dna")["subject_refs"]
        case = SimpleNamespace(store=store, sequence=sequence, scope=store.validate_scope(),
            journal=Journal(store, RUN), receipts=EpisodeReceipts(store, RUN), own_calls=[])
        case.reader = RestrictionMappingReferences(store, RUN)
        def no_own_catalog(self, context, reference):
            case.own_calls.append((context.episode_id, reference))
            return False
        monkeypatch.setattr(RestrictionMappingActionRecords, "own_enzyme_reference", no_own_catalog)
        yield case


def resolve(case, context, name="EcoRI"):
    return case.reader.resolve(context, name, "restriction_enzyme")


def test_unrelated_namespace_does_not_authenticate_or_lookup():
    reader = RestrictionMappingReferences(SimpleNamespace(db=None), RUN)
    assert reader.resolve(None, "EcoRI", "protein") is None
    assert reader.resolve(None, "EcoRI", None) is None


@pytest.mark.parametrize("name", [None, "", 0, True, [], {}])
def test_malformed_names_do_not_consult_sources(engineering_case, name):
    case = engineering_case
    context = saved_context(case, role="scientific_process")
    assert resolve(case, context, name) is False
    assert case.own_calls == []


@pytest.mark.parametrize("has_form", [True, False])
def test_own_frozen_requested_names_do_not_reconstruct_catalog(engineering_case, monkeypatch, has_form):
    case = engineering_case
    context = saved_context(case, role="scientific_process", schema=requested(candidate=True))
    frozen(case, context, form=has_form)
    def forbidden(*args, **kwargs):
        raise AssertionError("Frozen requested names do not reconstruct current own science")
    monkeypatch.setattr(RestrictionMappingActionRecords, "own_enzyme_reference", forbidden)
    before = case.store.db.total_changes
    assert resolve(case, context) is True
    assert case.store.db.total_changes == before


@pytest.mark.parametrize("name", ["BcgI", "ecori", "ECORI", "unknown"])
def test_candidate_and_case_mismatch_do_not_authorize_names(engineering_case, name):
    case = engineering_case
    context = saved_context(case, role="scientific_process", schema=requested(candidate=True))
    frozen(case, context)
    assert resolve(case, context, name) is False


def test_non_scientific_own_form_is_not_a_source(engineering_case):
    case = engineering_case
    context = saved_context(case)
    frozen(case, context)
    assert resolve(case, context) is False
    assert case.own_calls == []


def test_unrequested_facts_and_interpretation_are_not_sources(engineering_case):
    case = engineering_case
    schema = {"type": "object", "properties": {"candidate": {"type": "string", "format": "identifier",
        "x-reference-namespace": "restriction_enzyme"}},
        "required": ["candidate"], "additionalProperties": False}
    context = saved_context(case, role="scientific_process", schema=schema)
    rows = engineering_rows(case, requested())
    case.journal.save("runtime_forms", {"episode_id": context.episode_id,
        "facts": canonical({SOURCE: rows}), "form": canonical({"candidate": "EcoRI"})})
    assert resolve(case, context) is False


@pytest.mark.parametrize("fault", ["run", "episode", "role", "scope", "assignment", "request"])
def test_context_authentication_rejects_forgery(engineering_case, fault):
    case = engineering_case
    context = saved_context(case, role="scientific_process")
    values = {"run": {"run_id": "other"}, "episode": {"episode_id": "other"},
        "role": {"role": "annotation"}, "scope": {"scope": {}},
        "assignment": {"assignment": {"forged": True}}, "request": {"request": {}}}
    if fault == "role":
        # BindingContext itself prevents this mismatch at construction. Bypass
        # that constructor only to exercise this reader's independent check.
        forged = SimpleNamespace(**{key: getattr(context, key) for key in
            ("run_id", "episode_id", "role", "path", "scope", "assignment", "request")})
        forged.role = "annotation"
    else:
        forged = replace(context, **values[fault])
    with pytest.raises(ValueError, match=PREFIX):
        resolve(case, forged)


@pytest.mark.parametrize("fault", ["form", "facts", "selector", "value"])
def test_malformed_frozen_authority_is_a_specific_failure(engineering_case, fault):
    case = engineering_case
    schema = requested()
    if fault == "selector":
        schema["properties"]["selected"]["items"]["properties"]["selection_policy"].pop("const")
    context = saved_context(case, role="scientific_process", schema=schema)
    value = frozen(case, context)
    if fault == "form":
        value["selected"][0]["enzyme_rows"][0]["name"] = "BcgI"
        case.store.db.execute("UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?",
            (canonical(value), RUN, context.episode_id))
    elif fault == "facts":
        case.store.db.execute("UPDATE runtime_forms SET facts='[]' WHERE run_id=? AND episode_id=?",
            (RUN, context.episode_id))
    elif fault == "value":
        value["selected"][0]["enzyme_rows"][0]["catalog_ordinal"] = True
        case.store.db.execute("UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?",
            (canonical(value), canonical({SOURCE: value["selected"]}), RUN, context.episode_id))
    with pytest.raises(ValueError, match=PREFIX):
        resolve(case, context)


@pytest.mark.parametrize("role", ["annotation", "launch", "results", "scientific_process"])
def test_successful_immediate_scientific_child_grants_requested_name(engineering_case, role):
    case = engineering_case
    parent = saved_context(case, role=role)
    child = saved_context(case, parent=parent, role="scientific_process")
    admitted(case, parent, child)
    before = case.store.db.total_changes
    assert resolve(case, parent) is True
    assert resolve(case, parent, "ecori") is False
    assert case.store.db.total_changes == before


@pytest.mark.parametrize("names,source", [(False, False), (False, True)])
def test_requested_handle_without_rows_never_grants_catalog(engineering_case, names, source):
    case = engineering_case
    parent = saved_context(case)
    child = saved_context(case, parent=parent, role="scientific_process",
        schema=requested(names=names, source=source))
    admitted(case, parent, child)
    assert resolve(case, parent) is False


def test_sibling_form_is_not_a_receipt(engineering_case):
    case = engineering_case
    root = saved_context(case)
    sibling = saved_context(case, parent=root, index=0)
    parent = saved_context(case, parent=root, index=1)
    child = saved_context(case, parent=sibling, role="scientific_process")
    admitted(case, sibling, child)
    assert resolve(case, parent) is False


@pytest.mark.parametrize("fault", ["failure", "child_role", "literal_form", "facts", "contract", "scope",
    "purpose", "selected_role", "selected_schema", "child_path", "run"])
def test_admitted_source_requires_original_relationships(engineering_case, fault):
    case = engineering_case
    parent = saved_context(case)
    child = saved_context(case, parent=parent,
        role="results" if fault == "child_role" else "scientific_process")
    form = admitted(case, parent, child, failure="engineering_rejection" if fault == "failure" else None)
    if fault == "literal_form":
        case.store.db.execute("UPDATE runtime_forms SET form='{}' WHERE run_id=? AND episode_id=?", (RUN, child.episode_id))
    elif fault == "facts":
        case.store.db.execute("UPDATE runtime_forms SET facts='{}' WHERE run_id=? AND episode_id=?", (RUN, child.episode_id))
    elif fault == "contract":
        contract = plain(child.request)["report_contract"]
        contract["decision"] = "forged purpose"
        case.store.db.execute("UPDATE runtime_report_attempts SET contract=? WHERE run_id=? AND parent_episode_id=?",
            (canonical(contract), RUN, parent.episode_id))
    elif fault in {"scope", "purpose", "selected_role", "selected_schema"}:
        row = case.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=?",
            (RUN, parent.episode_id)).fetchone()
        action = json.loads(row["action"])
        key = {"scope": "scope", "purpose": "purpose", "selected_role": "role", "selected_schema": "schema_json"}[fault]
        action[key] = {} if key == "scope" else "{}" if key == "schema_json" else "forged"
        case.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=?",
            (canonical(action), RUN, parent.episode_id))
    elif fault == "child_path":
        case.store.db.execute("UPDATE runtime_episodes SET path='[]' WHERE run_id=? AND episode_id=?", (RUN, child.episode_id))
    elif fault == "run":
        case.store.db.execute("UPDATE runtime_report_attempts SET run_id='other' WHERE run_id=? AND parent_episode_id=?",
            (RUN, parent.episode_id))
    if fault in {"failure", "run"}:
        assert resolve(case, parent) is False
    else:
        with pytest.raises(ValueError, match=PREFIX):
            resolve(case, parent)


def redelivery(case, parent, child, *, index=2, field="redelivered"):
    schema = requested(field=field)
    contract = {"decision": "Read the already delivered names", "measurements": {"schema": schema}}
    delivery = "engineering_delivery_" + child.episode_id
    case.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index,
        "purpose": "decision", "request": "{}", "response": canonical({"selection": {
            "kind": "redeliver_report", "delivery_ref": delivery, "schema_json": canonical(schema),
            "purpose": contract["decision"]}})})
    form = {field: engineering_rows(case, schema)}
    admitted(case, parent, child, index=index, contract=contract, form=form)


@pytest.mark.parametrize("same_schema", [True, False])
def test_recorded_redelivery_reuses_original_frozen_source(engineering_case, same_schema):
    case = engineering_case
    parent = saved_context(case)
    child = saved_context(case, parent=parent, role="scientific_process")
    admitted(case, parent, child)
    redelivery(case, parent, child, field="selected" if same_schema else "redelivered")
    # Exercise the redelivery attempt itself, rather than allowing the first
    # original successful receipt alone to satisfy resolve.
    assert case.reader._attempt(parent, 2) == {"EcoRI"}


@pytest.mark.parametrize("fault", ["delivery", "origin", "frozen"])
def test_redelivery_rejects_changed_origin_or_values(engineering_case, fault):
    case = engineering_case
    parent = saved_context(case)
    child = saved_context(case, parent=parent, role="scientific_process")
    admitted(case, parent, child)
    redelivery(case, parent, child)
    if fault == "delivery":
        case.store.db.execute("UPDATE runtime_report_attempts SET delivery_ref='forged' WHERE run_id=? AND decision_index=2", (RUN,))
    elif fault == "origin":
        case.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND decision_index=0", (RUN,))
    else:
        case.store.db.execute("UPDATE runtime_forms SET facts='{}' WHERE run_id=? AND episode_id=?", (RUN, child.episode_id))
    with pytest.raises(ValueError, match=PREFIX):
        case.reader._attempt(parent, 2)


def test_inheritance_uses_frozen_received_prefix_not_decision_order(engineering_case):
    case = engineering_case
    parent = saved_context(case)
    late = saved_context(case, parent=parent, index=1, role="scientific_process")
    early = saved_context(case, parent=parent, index=3, role="scientific_process")
    admitted(case, parent, early, name="EcoRI")
    consumer = saved_context(case, parent=parent, index=5, role="scientific_process")
    admitted(case, parent, late, name="BcgI")
    assert resolve(case, consumer, "EcoRI") is True
    assert resolve(case, consumer, "BcgI") is False
    assert resolve(case, parent, "BcgI") is True


@pytest.mark.parametrize("fault", ["form_digest", "contract_digest", "delivery", "child", "deleted", "failed"])
def test_captured_witness_must_still_match_exact_attempt(engineering_case, fault):
    case = engineering_case
    parent = saved_context(case)
    child = saved_context(case, parent=parent, index=0, role="scientific_process")
    admitted(case, parent, child)
    consumer = saved_context(case, parent=parent, index=2, role="scientific_process")
    if fault == "deleted":
        case.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=?", (RUN,))
    else:
        column, value = {"form_digest": ("form", "{}"), "contract_digest": ("contract", "{}"),
            "delivery": ("delivery_ref", "forged"), "child": ("child_episode_id", "forged"),
            "failed": ("failure", "engineering_failure")}[fault]
        case.store.db.execute("UPDATE runtime_report_attempts SET " + column + "=? WHERE run_id=?", (value, RUN))
    with pytest.raises(ValueError, match=PREFIX + "received_prefix_conflict"):
        resolve(case, consumer)


@pytest.mark.parametrize("fault", ["missing", "changed", "manifest_deleted", "wrong_parent", "cycle"])
def test_declared_ancestor_requires_original_manifest_and_prefix(engineering_case, fault):
    case = engineering_case
    parent = saved_context(case)
    consumer = saved_context(case, parent=parent, index=2, role="scientific_process")
    if fault in {"missing", "changed"}:
        prefix = None if fault == "missing" else canonical({"version": "forged", "attempts": []})
        case.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
            (prefix, RUN, consumer.episode_id))
        if fault == "missing":
            message = plain(consumer.request)["message"]
            message["knowledge_inheritance"].pop("received_report_prefix")
            consumer = update_request(case, consumer, message)
    elif fault == "manifest_deleted":
        case.store.db.execute("DELETE FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?", (RUN, consumer.episode_id))
    else:
        new_parent = consumer.episode_id if fault == "cycle" else "unrelated_episode"
        case.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE run_id=? AND episode_id=?",
            (new_parent, RUN, consumer.episode_id))
        message = plain(consumer.request)["message"]
        message["knowledge_inheritance"]["parent_episode_id"] = new_parent
        consumer = update_request(case, consumer, message)
    with pytest.raises(ValueError, match=PREFIX):
        resolve(case, consumer)


@pytest.mark.parametrize("remove_table", [False, True])
def test_legacy_immediate_forms_do_not_infer_ancestor_receipt(engineering_case, remove_table):
    case = engineering_case
    parent = saved_context(case, inheritance=False)
    producer = saved_context(case, parent=parent, index=0, role="scientific_process", inheritance=False)
    admitted(case, parent, producer)
    consumer = saved_context(case, parent=parent, index=2, role="scientific_process", inheritance=False)
    if remove_table:
        case.store.db.execute("DROP TABLE runtime_receipt_inheritance")
    else:
        case.store.db.execute("DELETE FROM runtime_receipt_inheritance WHERE run_id=?", (RUN,))
    assert resolve(case, parent) is True
    assert resolve(case, consumer) is False


def test_retained_original728_own_catalog_is_read_only_and_needs_no_dispatch(monkeypatch):
    selector_path = Path(os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION731_SELECTOR", str(SELECTOR)))
    selector = json.loads(selector_path.read_text())
    store_path = Path(selector["store_path"])
    # Read the root-authorized original Store. The operation key, run/path/
    # request and result-source identities remain original728; no new owner.
    if not store_path.is_absolute():
        store_path = Path(__file__).resolve().parents[1] / store_path
    original_import = builtins.__import__
    def no_bio(name, *args, **kwargs):
        if name == "Bio" or name.startswith("Bio."):
            raise AssertionError("retained own authority must not import Bio")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_bio)
    import gene_annotation_episode.restriction_mapping_jobs as jobs
    import gene_annotation_episode.restriction_mapping_readers as reader_module
    import gene_annotation_episode.native_lifecycle as lifecycle
    def forbidden(*args, **kwargs):
        raise AssertionError("731 must not dispatch native work or719 calculation")
    monkeypatch.setattr(jobs.RestrictionMappingJobs, "run_async", forbidden)
    monkeypatch.setattr(lifecycle, "resume_start", forbidden)
    monkeypatch.setattr(reader_module, "read_restriction_mapping", forbidden)
    with Store(store_path) as store:
        authority = RestrictionMappingReferences(store, selector["run_id"])
        context = authority.context(selector["episode_id"])
        assert plain(context.request) == selector["request"]
        before = store.db.total_changes
        assert authority.resolve(context, "EcoRI", "restriction_enzyme") is True
        assert authority.resolve(context, "ecori", "restriction_enzyme") is False
        assert authority.resolve(context, "BcgI", "restriction_enzyme") is False
        assert store.db.total_changes == before
