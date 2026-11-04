"""F-wire345 supplied-data checks; no database search or external acquisition."""
from copy import deepcopy
import builtins
import base64
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_blast_database_metadata as legacy
from gene_annotation_episode import native_blast_vdb_function_metadata as module
from gene_annotation_episode import blast_vdb_function_inputs as inputs
from gene_annotation_episode import blast_vdb_inputs as vdb
from gene_annotation_episode import blast_vdb_calculators as measurements
from test_native_blast_database_contracts import job_for

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001"
_RETAINED = []


def evidence_json(value):
    if type(value) is bytes:
        return {"test_evidence_type": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if type(value) is float and not math.isfinite(value):
        return {"test_evidence_type": "nonfinite_float", "literal": repr(value)}
    if type(value) in (list, tuple):
        return [evidence_json(v) for v in value]
    if type(value) is dict:
        return {k: evidence_json(v) for k, v in value.items()}
    return value


@pytest.fixture(autouse=True)
def retain_wire_inputs_and_outcomes(tmp_path, monkeypatch):
    _RETAINED.clear()
    yield
    monkeypatch.undo()
    (tmp_path / "retained-wire-cases.json").write_bytes(encoded(evidence_json(_RETAINED)))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fixture(name="whole_sequence.json"):
    return json.loads((FIXTURES / name).read_text())


def _put(document, pointer):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    for part in parts:
        document = document.setdefault(part, {})


def wire_case(sheet=None, *, assignments=None, dependencies=None, censuses=None, input_key="function-input"):
    sheet = fixture() if sheet is None else deepcopy(sheet)
    key = sheet["base_sheet"]["search"]["search_key"]
    original = dict(search_key=key,
        supplied_assignments=deepcopy(sheet["assignment_records"] if assignments is None else assignments),
        dependency_records=deepcopy(sheet["dependency_records"] if dependencies is None else dependencies),
        census_records=deepcopy(sheet["census_records"] if censuses is None else censuses))
    bodies, keys = {}, {}
    def wire(value, *, raw=False):
        if not raw and type(value) is dict and set(value) == {"source_ref", "pointer"}:
            source = value["source_ref"]
            keys.setdefault(source, "document-" + str(len(keys)))
            _put(bodies.setdefault(source, {}), value["pointer"])
            return dict(source_ref=keys[source], pointer=value["pointer"])
        if not raw and type(value) is dict and set(value) == set(key):
            return dict(output_key="selected-report", **{k: v for k, v in value.items() if k != "artifact_key"})
        if type(value) is dict:
            return {k: wire(v, raw=raw or k == "native_record") for k, v in value.items()}
        if type(value) is list:
            return [wire(v, raw=raw) for v in value]
        return value
    unit = wire(original)
    declarations, documents, retained = [], [], []
    for source, body in bodies.items():
        raw = encoded(body)
        identity = dict(source_ref=source, artifact_ref="artifact:source:" + digest(source.encode()), sha256=digest(raw), size_bytes=len(raw))
        declaration = dict(document_key=keys[source], artifact=dict(kind="received", **identity), format="json")
        declarations.append(declaration)
        documents.append(dict(deepcopy(declaration), artifact_key=None, **identity, contents=raw))
        retained.append(dict(identity, path="/unread/supplied/source"))
    payload = dict(schema=module._SCHEMA_ID, documents=declarations, searches=[unit])
    descriptor = dict(input_key=input_key, consumer="vdb_function", schema_id=module._SCHEMA_ID,
        artifact_ref="artifact:payload:" + input_key, sha256=digest(encoded(payload)), size_bytes=len(encoded(payload)), origin="selected_results_input")
    native = encoded(sheet["base_sheet"]["search"]["native"])
    report = dict(output_key="selected-report", artifact_key=key["artifact_key"], artifact_ref=sheet["base_sheet"]["report_source"]["artifact_ref"],
        source_ref="source:actual-report", sha256=digest(native), size_bytes=len(native), format="json15")
    catalog = dict(descriptor=descriptor, documents=documents, primary_reports=[report],
        bundle_source_ref="source:bundle", bundle_artifact_ref="artifact:bundle")
    artifacts = dict(entries=[dict(report, role="primary_report", path="/unread/report")], retained_sources=retained)
    program = sheet["base_sheet"]["search"]["program_context"]["execution_program"]
    job = job_for(program)
    next(o for o in job["outputs"] if o["role"] == "primary_report")["output_key"] = "selected-report"
    invocation = dict(execution_program=program, request=dict(native_blast_database=job))
    prepared = dict(schema="native_blast_database_prepared_inputs_v1", metadata=[], invocation=invocation)
    base = dict(schema="native_blast_database_sheet_set_v1", vdb=[dict(search_key=key, sheet=sheet["base_sheet"])])
    return dict(sheet=sheet, original=original, payload=payload, descriptor=descriptor, catalog=catalog,
                artifacts=artifacts, job=job, base=base, prepared=prepared)


def validate(case):
    evidence = dict(operation="validate", inputs=deepcopy(case))
    _RETAINED.append(evidence)
    try:
        result = module.validate_native_blast_vdb_function_metadata_payload(case["payload"],
            descriptor=case["descriptor"], document_catalog=case["catalog"], job=case["job"])
    except ValueError as error:
        evidence["error"] = str(error)
        raise
    evidence["result"] = deepcopy(result)
    return result


def populate(case, validations=None):
    prepared = deepcopy(case["prepared"])
    prepared["metadata"] = [validate(case)] if validations is None else validations
    evidence = dict(operation="populate", base_sheet_set=deepcopy(case["base"]),
        prepared_inputs=deepcopy(prepared), artifact_catalog=deepcopy(case["artifacts"]))
    _RETAINED.append(evidence)
    try:
        result = module.populate_native_blast_vdb_function_sheets(case["base"], prepared_inputs=prepared, artifact_catalog=case["artifacts"])
    except ValueError as error:
        evidence["error"] = str(error)
        raise
    evidence["result"] = deepcopy(result)
    return result


def forbidden(*args, **kwargs):
    raise AssertionError("pure F-wire port invoked forbidden operation")


def forbid_io(monkeypatch, *, forbid_population=False, forbid_parsers=True):
    for owner, name in ((builtins, "open"), (Path, "read_bytes"), (Path, "read_text"), (Path, "write_bytes"),
                        (Path, "write_text"), (socket, "socket"), (subprocess, "Popen"),
                        (legacy._Catalog, "read"), (legacy, "prepare_native_blast_database_inputs"),
                        (legacy, "populate_native_blast_database_sheets")):
        monkeypatch.setattr(owner, name, forbidden)
    if forbid_parsers:
        for name in ("parse_ncbi_sra_runinfo", "parse_blast_vdb_member_sequences", "parse_ncbi_gbseq_vdb_metadata", "bind_blast_vdb_metadata"):
            monkeypatch.setattr(vdb, name, forbidden)
    if forbid_population:
        monkeypatch.setattr(inputs, "populate_blast_vdb_function_sheet", forbidden)
        monkeypatch.setattr(measurements, "calculate_blast_vdb_components", forbidden)


def test_closed_dispatch_and_default_helpers_do_not_mutate_registration(monkeypatch):
    case = wire_case(); before = deepcopy(case)
    registry = legacy.metadata_schema_registry()
    forbid_io(monkeypatch, forbid_population=True)
    legacy_catalog = deepcopy(case["catalog"])
    legacy_catalog["descriptor"]["consumer"] = "vdb"
    legacy._validate_catalog(legacy_catalog)
    legacy._validate_catalog(case["catalog"], consumers=("vdb_function",))
    unsupported = dict(case["descriptor"], schema_id="future_unknown_v1")
    old = legacy.validate_native_blast_database_metadata_payload(case["payload"], descriptor=unsupported,
        document_catalog=case["catalog"], job=case["job"])
    assert old["status"] == "unsupported"
    result = validate(case)
    assert result["status"] == "valid" and not result["issues"], [(i["pointer"], i["detail_code"]) for i in result["issues"]]
    assert result["normalized"]["searches"] == [case["original"]]
    assert case == before and legacy.metadata_schema_registry() == registry
    assert set(result) == set("consumer schema_id input_key artifact_ref sha256 status payload normalized normalization_map issues".split())
    result["payload"]["searches"].clear()
    assert case == before


@pytest.mark.parametrize("field,value", [("consumer", "vdb"), ("schema_id", "future_v1")])
def test_wrong_tuple_unsupported_retains_original(field, value):
    case = wire_case(); case["descriptor"][field] = value
    out = validate(case)
    assert out["status"] == "unsupported" and out["payload"] == case["payload"] and out["normalized"] is None


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(extra=1),
    lambda p: p["searches"][0]["supplied_assignments"][0].update(function_ordinal=True),
    lambda p: p["searches"][0]["supplied_assignments"][0].update(function_ordinal=1.0),
    lambda p: p["searches"][0]["supplied_assignments"][0]["target"].update(feature_identifier=dict(namespace="x", value="x", version=None)),
    lambda p: p["searches"][0]["supplied_assignments"][0].pop("scope_source"),
    lambda p: p["searches"][0]["census_records"][0]["datasets"][0].update(sra_mode=1.0),
    lambda p: p["searches"][0]["census_records"][0]["entities"][0]["target_identity"].update(representation="oriented_feature_nt_v1"),
])
def test_closed_nested_fields_and_true_integer_validation(mutation):
    case = wire_case(); mutation(case["payload"])
    out = validate(case)
    assert out["status"] == "invalid" and out["payload"] == case["payload"] and out["normalized"] is None


@pytest.mark.parametrize("value", [float("inf"), float("nan"), b"bytes"])
def test_nonfinite_and_non_json_rejected(value):
    case = wire_case(); case["payload"]["searches"][0]["dependency_records"] = [value]
    with pytest.raises(ValueError, match="native_blast_metadata_finite_json_required"):
        validate(case)


@pytest.mark.parametrize("filename", ["whole_sequence.json", "translated_features.json", "translated_siblings.json"])
def test_actual342_exports_reproduce_complete_frozen_sheets(filename, monkeypatch, tmp_path):
    case = wire_case(fixture(filename)); initial = deepcopy(case)
    calls = []; actual = inputs.populate_blast_vdb_function_sheet
    def spy(*args, **kwargs):
        calls.append(deepcopy((args, kwargs)))
        return actual(*args, **kwargs)
    with monkeypatch.context() as pure:
        forbid_io(pure)
        pure.setattr(inputs, "populate_blast_vdb_function_sheet", spy)
        out = populate(case)
    assert not out["issues"] and len(out["sheets"]) == 1
    assert out["sheets"][0]["sheet"] == case["sheet"]
    assert calls[0][0][0] == case["sheet"]["base_sheet"] and len(calls) == 1
    assert case == initial
    (tmp_path / filename).write_bytes(encoded(out))
    with monkeypatch.context() as pure:
        forbid_io(pure, forbid_population=True)
        assert inputs.validate_blast_vdb_function_sheet(out["sheets"][0]["sheet"]) == case["sheet"]


def test_explicit_dependency_and_unknown_snapshot_assertion_are_preserved():
    saved = fixture()
    dependency = dict(dependency_key="library-1", relation="same_library", entities=[e["address"] for e in saved["entities"]],
        sources=[dict(source_ref="source:dependence", pointer="/actual~1relation/~0raw")], native_record={"source_ref": "literal", "pointer": "not-a-pointer"})
    case = wire_case(saved, dependencies=[dependency])
    out = populate(case); sheet = out["sheets"][0]["sheet"]
    assert sheet["dependency_records"] == [dependency]
    assert sheet["link_results"][-2]["status"] == "available"
    assert sheet["census_records"] == saved["census_records"]
    assert all(d["sha256"] != saved["census_records"][0]["annotation_snapshot"]["content_sha256"] for d in case["catalog"]["documents"])


@pytest.mark.parametrize("mutation,detail", [
    (lambda c: c["catalog"]["documents"][0].update(contents=b"changed"), "document_bytes_conflict"),
    (lambda c: c["catalog"]["documents"][0]["artifact"].update(sha256="f" * 64), "document_catalog_address_conflict"),
    (lambda c: c["payload"]["searches"][0]["supplied_assignments"][0]["scope_source"].update(pointer="/not-present"), "literal_json_pointer_unresolved"),
    (lambda c: c["payload"]["searches"][0]["supplied_assignments"][0]["scope_source"].update(source_ref="undeclared"), "document_key_undeclared"),
])
def test_wrong_source_bytes_and_addresses_keep_originals(mutation, detail):
    case = wire_case(); mutation(case); out = validate(case)
    assert out["payload"] == case["payload"]
    assert any(i["detail_code"] == detail for i in out["issues"])
    assert not out["normalized"] or not out["normalized"]["searches"]


def test_sparse_original_search_indices_survive_lowering_and_population():
    case = wire_case(); valid = deepcopy(case["payload"]["searches"][0])
    missing = deepcopy(valid); missing["search_key"]["output_key"] = "absent"
    case["payload"]["searches"] = [missing, valid]
    validation = validate(case)
    assert validation["status"] == "valid" and len(validation["normalized"]["searches"]) == 1
    assert dict(normalized_pointer="/searches/0", payload_pointer="/searches/1") in validation["normalization_map"]
    case["base"]["vdb"] = []
    out = populate(case, [validation])
    issue = next(i for i in out["issues"] if i["detail_code"] == "vdb_function_base_search_unavailable")
    assert issue["pointer"] == "/searches/1" and issue["search_address"] == valid["search_key"]


@pytest.mark.parametrize("mutation,reason", [
    (lambda r: r.update(metadata_key="absent"), "assignment_entity_conflict"),
    (lambda r: r.update(function_ordinal=99), "assignment_function_conflict"),
    (lambda r: r["target"]["member_key"].update(dataset_key="other"), "assignment_entity_conflict"),
])
def test_scientific_join_failure_retains_assignment_and_valid_siblings(mutation, reason):
    case = wire_case(); original = case["payload"]["searches"][0]["supplied_assignments"][0]
    mutation(original); out = populate(case); sheet = out["sheets"][0]["sheet"]
    assert sheet["assignment_records"][0]["target"] == original["target"]
    assert sheet["link_results"][0]["reason_code"] == "blast_vdb_function_" + reason
    assert any(o["qualification"] == "available" and o["assignment_key"] == "assignment-2-0" for o in sheet["observations"])


def test_conflicting_assignment_identity_keeps_both_and_never_selects_first():
    case = wire_case(); rows = case["payload"]["searches"][0]["supplied_assignments"]
    conflict = deepcopy(rows[0]); conflict["function"]["value"] = "unrelated"; rows.append(conflict)
    out = populate(case); sheet = out["sheets"][0]["sheet"]
    assert len(sheet["assignment_records"]) == 4
    assert sheet["link_results"][0]["status"] == "incompatible"
    assert not any(o["assignment_key"] == rows[0]["assignment_key"] for o in sheet["observations"])


def test_malformed_envelope_cannot_erase_independent_valid_payload():
    case = wire_case(); invalid = deepcopy(case); invalid["payload"]["unexpected"] = True
    envelopes = [validate(invalid), validate(case)]; saved = deepcopy(envelopes)
    out = populate(case, envelopes)
    assert out["sheets"][0]["sheet"] == case["sheet"] and envelopes == saved
    assert any(i["code"] == "native_blast_metadata_payload_invalid" for i in out["issues"])


@pytest.mark.parametrize("change,detail", [
    (lambda c: c["base"]["vdb"].append(deepcopy(c["base"]["vdb"][0])), "vdb_function_base_search_ambiguous"),
    (lambda c: c["base"]["vdb"][0]["sheet"].update(extra=True), "vdb_function_base_sheet_invalid"),
    (lambda c: c["artifacts"]["entries"][0].update(artifact_ref="wrong"), "vdb_function_artifact_catalog_conflict"),
])
def test_base_and_catalog_failures_are_specific_and_do_not_mutate_inputs(change, detail):
    case = wire_case(); change(case); before = deepcopy(case)
    out = populate(case)
    assert not out["sheets"] and any(i["detail_code"] == detail for i in out["issues"])
    assert case == before


def test_empty_supplied_inputs_still_extract_actual_feature_metadata():
    case = wire_case(fixture("translated_features.json"))
    out = populate(case, [])
    assert len(out["sheets"]) == 1
    assert out["sheets"][0]["sheet"]["assignment_records"] == case["sheet"]["assignment_records"]
    assert not out["sheets"][0]["sheet"]["census_records"]


@pytest.mark.parametrize("field", ["census_records", "dependency_records"])
def test_duplicate_strict_record_identity_rejects_both_and_preserves_assignments(field):
    saved = fixture()
    deps = [dict(dependency_key="d", relation="same_library", entities=[e["address"] for e in saved["entities"]],
                 sources=[dict(source_ref="source:dep", pointer="")], native_record={"library": "supplied"})]
    case = wire_case(saved, dependencies=deps)
    validation = validate(case); second = deepcopy(validation)
    second["input_key"] = "another-original-input"
    other = "dependency_records" if field == "census_records" else "census_records"
    second["normalized"]["searches"][0][other] = []
    second["payload"]["searches"][0][other] = []
    out = populate(case, [validation, second]); sheet = out["sheets"][0]["sheet"]
    assert sheet[field] == [] and len(sheet["assignment_records"]) == 3
    failures = [i for i in out["issues"] if i["detail_code"] == "vdb_function_input_records_conflict"]
    assert {i["input_key"] for i in failures} == {validation["input_key"], second["input_key"]}


def test_report_alias_cannot_supply_census_and_uncorrected_assignments_survive():
    case = wire_case(); census = case["payload"]["searches"][0]["census_records"][0]
    key = census["source"]["source_ref"]
    doc = next(d for d in case["catalog"]["documents"] if d["document_key"] == key)
    report = case["catalog"]["primary_reports"][0]
    # Distinct source/handle aliases, identical actual bytes identity.
    report.update(sha256=doc["sha256"], size_bytes=doc["size_bytes"])
    validation = validate(case)
    assert validation["status"] == "valid" and validation["payload"] == case["payload"]
    assert any(i["pointer"].startswith("/searches/0/census_records/0/") for i in validation["issues"])
    out = populate(case, [validation]); sheet = out["sheets"][0]["sheet"]
    assert not sheet["census_records"] and len(sheet["assignment_records"]) == 3
    assert all(o["qualification"] == "available" for o in sheet["observations"])


def test_inspection_schema_is_closed_and_detached():
    schema = module.native_blast_vdb_function_metadata_schema()
    assert schema == module._SCHEMA and schema is not module._SCHEMA
    assert schema["additionalProperties"] is False
    schema["properties"]["searches"]["items"]["properties"]["supplied_assignments"]["items"]["properties"].clear()
    assert module.native_blast_vdb_function_metadata_schema() == module._SCHEMA
    assert validate(wire_case())["status"] == "valid"


@pytest.mark.parametrize("contradiction", [False, True])
def test_snapshot_assertion_identity_is_distinct_from_source_document_digest(contradiction):
    case = wire_case(); census = case["payload"]["searches"][0]["census_records"][0]
    provenance = census["annotation_snapshot"]["source"]
    doc = next(d for d in case["catalog"]["documents"] if d["document_key"] == provenance["source_ref"])
    body = json.loads(doc["contents"])
    assertion = legacy._pointer_get(body, provenance["pointer"])
    assertion["content_sha256"] = "f" * 64 if contradiction else census["annotation_snapshot"]["content_sha256"]
    doc["contents"] = encoded(body)
    identity = dict(sha256=digest(doc["contents"]), size_bytes=len(doc["contents"]))
    doc.update(identity); doc["artifact"].update(identity)
    next(d for d in case["payload"]["documents"] if d["document_key"] == doc["document_key"])["artifact"].update(identity)
    next(r for r in case["artifacts"]["retained_sources"] if r["artifact_ref"] == doc["artifact_ref"]).update(identity)
    assert identity["sha256"] != census["annotation_snapshot"]["content_sha256"]
    out = populate(case); sheet = out["sheets"][0]["sheet"]
    assert bool(sheet["census_records"]) is not contradiction
    assert bool(out["issues"]) is contradiction
    assert len(sheet["assignment_records"]) == 3


@pytest.mark.parametrize("missing", [False, True])
def test_source_catalog_conflict_or_absence_has_exact_original_issue(missing):
    case = wire_case(); validation = validate(case)
    if missing:
        case["artifacts"]["retained_sources"].clear()
    else:
        case["artifacts"]["retained_sources"][0]["sha256"] = "f" * 64
    out = populate(case, [validation])
    issue = next(i for i in out["issues"] if i["pointer"] == "/searches/0")
    assert issue["detail_code"] == "vdb_function_artifact_catalog_conflict"
    assert issue["code"] == "native_blast_metadata_relation_" + ("unresolved" if missing else "conflict")
    assert issue["search_address"] == case["payload"]["searches"][0]["search_key"]
    assert out["sheets"][0]["sheet"]["assignment_records"] == []


@pytest.mark.parametrize("field", ["source_ref", "artifact_ref"])
def test_contradictory_document_identity_is_rejected_without_alias_join(field):
    case = wire_case()
    first, second = case["catalog"]["documents"][:2]
    second[field] = first[field]; second["artifact"][field] = first[field]
    case["payload"]["documents"][1]["artifact"][field] = first[field]
    second["contents"] += b" "
    second.update(sha256=digest(second["contents"]), size_bytes=len(second["contents"]))
    second["artifact"].update(sha256=second["sha256"], size_bytes=second["size_bytes"])
    case["payload"]["documents"][1]["artifact"].update(sha256=second["sha256"], size_bytes=second["size_bytes"])
    out = validate(case)
    assert out["status"] == "invalid" and out["payload"] == case["payload"]
    assert any(i["detail_code"] == "document_source_identity_conflict" for i in out["issues"])


def test_native_locator_without_declared_parse_remains_unavailable(monkeypatch):
    from test_blast_vdb_inputs import GBSEQ
    case = wire_case(); doc = case["catalog"]["documents"][0]
    doc["format"] = case["payload"]["documents"][0]["format"] = "ncbi_gbseq_xml"
    doc["contents"] = GBSEQ
    identity = dict(sha256=digest(GBSEQ), size_bytes=len(GBSEQ))
    doc.update(identity); doc["artifact"].update(identity)
    case["payload"]["documents"][0]["artifact"].update(identity)
    provenance = case["payload"]["searches"][0]["supplied_assignments"][0]["scope_source"]
    provenance.update(source_ref=doc["document_key"], pointer="/records/0")
    forbid_io(monkeypatch, forbid_population=True)
    out = validate(case)
    assert out["payload"] == case["payload"]
    assert any(i["detail_code"] == "source_locator_not_supported" for i in out["issues"])


@pytest.mark.parametrize("same_key", [False, True])
def test_feature_mismatch_retains_failed_assignment_and_other_features(same_key):
    case = wire_case(fixture("translated_features.json"))
    original = case["payload"]["searches"][0]["supplied_assignments"][0]
    if not same_key:
        original["assignment_key"] += "-separate-supplied-declaration"
    original["target"]["feature_identifier"]["value"] = "different-feature"
    out = populate(case); sheet = out["sheets"][0]["sheet"]
    assert any(a["target"] == original["target"] for a in sheet["assignment_records"])
    assert any(link["status"] == "incompatible" for link in sheet["link_results"] if link["record_kind"] == "assignment")
    assert any(o["qualification"] == "available" and o["function"] == {"namespace": "fixture_function", "value": "B"}
               for o in sheet["observations"])


def test_tabular_sparse_native_hsp_indices_and_source_lines_survive_wire(tmp_path, monkeypatch):
    from test_blast_vdb_calculators import table_values
    from test_blast_vdb_function_inputs import explicit
    values = table_values()
    assignment = explicit(values, 0)
    sheet = inputs.populate_blast_vdb_function_sheet(vdb.populate_blast_vdb_sheet(**values),
        supplied_assignments=[assignment], dependency_records=[], census_records=[])
    case = wire_case(sheet)
    case["job"]["outputs"][next(i for i, o in enumerate(case["job"]["outputs"]) if o["role"] == "primary_report")]["format"] = "tabular7"
    case["catalog"]["primary_reports"][0]["format"] = "tabular7"
    case["artifacts"]["entries"][0]["format"] = "tabular7"
    with monkeypatch.context() as pure:
        forbid_io(pure)
        out = populate(case)
    assert not out["issues"] and out["sheets"][0]["sheet"] == sheet
    assigned = [o for o in sheet["observations"] if o["assignment_key"] is not None]
    assert [o["row_key"]["hsp_ordinal"] for o in assigned] == [1]
    assert assigned[0]["source_locator"]["line_numbers"] == [5]
    assert assigned[0]["source_locator"]["data_row_ordinals"] == [1]
    (tmp_path / "tabular-function-sheet.json").write_bytes(encoded(out))


def test_bad_original_search_does_not_erase_independent_valid_search():
    case = wire_case(); original = case["payload"]["searches"][0]
    second = deepcopy(original); second["search_key"]["report_index"] = 1
    case["payload"]["searches"] = [original, second]
    out = populate(case)
    assert out["sheets"][0]["sheet"] == case["sheet"]
    issue = next(i for i in out["issues"] if i["detail_code"] == "vdb_function_base_search_unavailable")
    assert issue["pointer"] == "/searches/1" and issue["search_address"] == second["search_key"]


@pytest.mark.parametrize("change", [
    lambda c: c["base"]["vdb"].append({}),
    lambda c: c["artifacts"]["entries"].append({}),
    lambda c: c["prepared"]["metadata"].append(None),
])
def test_malformed_whole_outer_object_raises_closed_structural_error(change):
    case = wire_case(); change(case)
    with pytest.raises(ValueError, match="^blast_vdb_function_sheet_schema_invalid$"):
        populate(case, case["prepared"]["metadata"])


def test_actual_v1_multiple_payload_merge_resolves_final_feature_indices(tmp_path, monkeypatch):
    import test_native_blast_database_metadata as old
    from test_blast_vdb_inputs import inputs as base_inputs, hsp
    from test_blast_vdb_calculators import feature
    symbols = ["CCCATGGCTAAACCCCCC", "AAAATGGCTAAATTTTTT"]
    hits = [dict(len=18, description=[dict(id=f"member{i}", accession=f"member{i}")],
                 hsps=[hsp("MAK", hit_from=4, hit_to=12, hit_frame=1)]) for i in range(2)]
    job, bundle, catalog, _, search = old.vdb_fixture(tmp_path, program="tblastn_vdb", hits=hits, query=b">q\nMAK\n")
    values = base_inputs(search, symbols=symbols, kind="reference", samples=False)
    payloads = []
    for i in range(2):
        feature(values, interval=[3, 12], identifier=f"feature{i}", translation="MAK", genetic_code=1,
                codon_start=1, function=dict(namespace="fixture_function", value="A" if i == 0 else "B"), hit=i)
    for i in range(2):
        payload = old.empty_payload("vdb")
        payload["documents"] = [old.source(tmp_path, catalog, "facts", encoded({"sequence": symbols[i]}))]
        # Separate document handles even though both payload-local keys are facts.
        payload["documents"][0]["artifact"]["source_ref"] += f"-{i}"
        payload["documents"][0]["artifact"]["artifact_ref"] += f"-{i}"
        catalog["retained_sources"][-1].update({k: payload["documents"][0]["artifact"][k] for k in ("source_ref", "artifact_ref")})
        # Retained source files must also remain distinct between payloads.
        new_path = tmp_path / f"merge-facts-{i}.json"
        new_path.write_bytes(encoded({"sequence": symbols[i]})); catalog["retained_sources"][-1]["path"] = str(new_path)
        unit = old.wire_fixture(dict(search_key=search["search_key"], dataset_records=[values["dataset_records"][i]],
            member_bindings=[values["member_bindings"][i]], sequence_identity_bindings=[values["sequence_identity_bindings"][i]],
            feature_bindings=[values["feature_bindings"][i]], reference_metadata=[m for m in values["reference_metadata"] if m["entity"]["dataset_key"] == f"D{i}"],
            sequence_proofs=[], population_records=[], parsed_sources=[], metadata_bindings=[]))
        unit["feature_bindings"][0]["member_binding_index"] = 0
        unit["dataset_records"][0]["selected_input"]["value"] = "target"
        unit["dataset_records"][0]["snapshot"]["manifest_sha256"] = job["databases"][0]["manifest_file"]["sha256"]
        binding = unit["sequence_identity_bindings"][0]["binding"]
        binding.update(source_ref="facts", pointer="", linkage_source_ref="facts", linkage_pointer="")
        unit["sequence_proofs"] = [dict(binding_index=0, document_key="facts", representation="json_sequence", record_ordinal=None,
            sequence_pointer="/sequence", molecule="nt", sha256=digest(symbols[i].encode()), length=18)]
        payload["searches"] = [unit]
        payloads.append(old.metadata(tmp_path, catalog, "vdb", payload, key=f"base-input-{i}"))
    prepared = old.prepared(job, bundle, catalog, payloads)
    base = old.populate(prepared, catalog)
    assert [f["member_binding_index"] for f in base["vdb"][0]["sheet"]["feature_bindings"]] == [0, 1], base["issues"]
    expected = inputs.populate_blast_vdb_function_sheet(base["vdb"][0]["sheet"], supplied_assignments=[], dependency_records=[], census_records=[])
    case = wire_case(expected, censuses=[])
    # Native-extracted assignments also pass the supplied exact-member join.
    validation = validate(case)
    with monkeypatch.context() as pure:
        forbid_io(pure)
        out = populate(case, [validation])
    sheet = out["sheets"][0]["sheet"]
    assert not out["issues"] and sheet == expected
    features = [e for e in sheet["entities"] if e["address"]["assignment_scope"] == "feature"]
    assert [e["member_binding_indices"] for e in features] == [[0], [1]]
    assert {o["function"]["value"] for o in sheet["observations"] if o["function"] and o["qualification"] == "available"} == {"A", "B"}
    (tmp_path / "actual-v1-merge-inputs.json").write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=payloads)))
    (tmp_path / "actual-v1-merge-base.json").write_bytes(encoded(base))
    (tmp_path / "actual-v1-merge-function.json").write_bytes(encoded(out))


def test_actual_native_gbseq_assignment_survives_without_new_native_reader(tmp_path, monkeypatch):
    import test_native_blast_database_metadata as old
    old.test_gbseq_actual_binding_feature_and_forward_codon_map(tmp_path)
    base = json.loads((tmp_path / "gbseq-sheets.json").read_bytes())
    captured = json.loads((tmp_path / "gbseq-inputs.json").read_bytes())
    case = dict(base=base, prepared=base["prepared_inputs"], artifacts=captured["artifact_catalog"])
    with monkeypatch.context() as pure:
        # The unchanged base calculator revalidates already embedded GBSeq XML.
        forbid_io(pure, forbid_parsers=False)
        out = populate(case, case["prepared"]["metadata"])
    sheet = out["sheets"][0]["sheet"]
    assert not out["issues"] and len(sheet["assignment_records"]) == 2
    assert all(a["scope_origin"] == "native_feature_record" for a in sheet["assignment_records"])
    assert [a["function_ordinal"] for a in sheet["assignment_records"]] == [0, 1]
    assert all(o["qualification"] == "available" for o in sheet["observations"] if o["function"])
    assert any(m["native_record"].get("input_text", "").startswith("<GBSet>") for m in sheet["base_sheet"]["reference_metadata"])
    with monkeypatch.context() as pure:
        forbid_io(pure, forbid_population=True)
        assert inputs.validate_blast_vdb_function_sheet(sheet) == sheet
    (tmp_path / "native-gbseq-function-sheet.json").write_bytes(encoded(out))
