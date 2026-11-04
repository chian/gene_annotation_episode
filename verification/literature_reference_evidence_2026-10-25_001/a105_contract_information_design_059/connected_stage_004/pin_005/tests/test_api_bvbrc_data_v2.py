"""D6a service/publication checks with no network or model execution.

Historical Solr count/facet bytes stay unchanged. Historical array rows used for
join composition are explicitly reserialized into synthetic Solr envelopes; the
tests do not claim those requests were executed live. Input ResultBindings are
labeled host fixtures over actual Store source/artifact bytes, not host admission
tests. D6 host receipts, communication and prompt insertion are separate work.
"""
from copy import deepcopy
from dataclasses import replace
from email.message import Message
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_bvbrc import (
    BVBRCDataService, DATA_QUERY_OPERATION, DATA_RESULT_OPERATION,
    DEFAULT_BASE_URL, EMPTY_ARGUMENTS, QUERY_OPERATION, RESULT_OPERATION,
)
from gene_annotation_episode.bvbrc_data_calculators import (
    calculate_facet_fractions, calculate_feature_sequence_counts, calculate_page_counts,
)
from gene_annotation_episode.bvbrc_data_fields import COLLECTIONS, FIELD_REGISTRY, MOLECULAR_MEASUREMENT_FIELDS
from gene_annotation_episode.bvbrc_data_publication import requested_projection_failures
from gene_annotation_episode.bvbrc_data_query import encode_native_query
from gene_annotation_episode.bvbrc_data_schema import json_digest
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import digest as host_digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry


EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_bvbrc_data_contract_2026-10-24"
FROZEN = json.loads((EVIDENCE / "CONTRACT_SHAPES.json").read_text())
EXAMPLES = json.loads((EVIDENCE / "FILLED_EXAMPLES.json").read_text())
FEATURE_IDS = ["PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
               "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("service/publication verification attempted network access")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


@pytest.fixture
def service(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        scope = {"subject_refs": problem["subject_refs"]}
        yield BVBRCDataService(ToolRegistry(store)), scope


def request(collection="genome", *, mode="page", fields=None, **kwargs):
    value = {"version": "bvbrc_data_request_v2", "collection": collection,
             "mode": mode, "filters": []}
    if fields is not None:
        value["fields"] = fields
    return {**value, **kwargs}


def selector(projection=None, *, page=None, inputs=None, supplied=None):
    return {"version": "bvbrc_data_result_selector_v2", "page": page,
        "projection": {"family": "query_metadata"} if projection is None else projection,
        "inputs": [] if inputs is None else inputs,
        "supplied_metadata": [] if supplied is None else supplied}


def row_selector(*, rows=(0,), numbers=(), metadata=(), **kwargs):
    return selector({"family": "collection_rows", "row_indices": list(rows),
        "numeric_fields": list(numbers), "metadata_fields": list(metadata)}, **kwargs)


def command(service, query, selection=None, *, operation=DATA_RESULT_OPERATION, scope=None):
    return service.prepare(operation, query, {}, scope=scope, previous_events=[],
        selector=selector() if selection is None and operation == DATA_RESULT_OPERATION else selection)


def envelope(rows, *, total=None, start=0, exact=True, **extra):
    response = {"docs": rows, "start": start, "numFound": len(rows) if total is None else total}
    if exact is not None:
        response["numFoundExact"] = exact
    return json.dumps({"responseHeader": {"status": 0}, "response": response, **extra},
        separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def snapshot(prepared, body, *, headers=(), body_complete=True):
    native = prepared["native_request"]
    return SourceSnapshot("bvbrc_data", native["url"], deepcopy(prepared["effective_request"]),
        "2026-10-24T20:00:00+00:00", body, "application/solr+json", {
            "status": 200, "body_complete": body_complete, "automatic_redirects": False,
            "effective_url": native["url"], "request": {key: deepcopy(native[key])
                for key in ("method", "url", "headers", "body")}, "header_items": list(headers)})


def publication_inputs(prepared, inputs=(), supplied=(), metadata_bindings=()):
    return {"version": "bvbrc_data_publication_inputs_v1", "prepared": deepcopy(prepared),
        "input_results": deepcopy(list(inputs)), "supplied_metadata": deepcopy(list(supplied)),
        "metadata_bindings": deepcopy(list(metadata_bindings))}


def publish(service_scope, query, selection, body, *, inputs=(), metadata_bindings=(), key="fixture",
            body_complete=True):
    service, scope = service_scope
    prepared = command(service, query, selection, scope=scope)["prepared_query"]
    source = snapshot(prepared, body, body_complete=body_complete)
    supplied = publication_inputs(prepared, inputs, selection["supplied_metadata"], metadata_bindings)
    outcome = service.publish(query, selection, source, scope, key, publication_inputs=supplied)
    grading, = source_tool_gradings(service.tools.store, outcome["result"]["source_ref"])
    return outcome, grading, source


def retained_rows(name):
    metadata = json.loads((EVIDENCE / (name + ".meta.json")).read_text())
    raw = (EVIDENCE / (name + ".body")).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == metadata["sha256"]
    return json.loads(raw)


def input_page(service_scope, collection, rows, fields=None):
    """Fixture-only host binding over a real, locally published source."""
    fields = fields or list(dict.fromkeys(field for row in rows for field in row
        if field in FIELD_REGISTRY[collection]["fields"]))
    query, selection = request(collection, fields=fields), selector()
    outcome, grading, _ = publish(service_scope, query, selection, envelope(rows), key="input:" + collection)
    result = outcome["result"]
    return {"binding": {"source_ref": result["source_ref"], "native_artifact_ref": result["raw_artifact_ref"],
        "native_sha256": grading["parse_result"]["retained_native_sha256"],
        "grading_artifact_ref": result["grading_artifact_ref"], "collection": collection,
        "acquisition_assignment_sha256": host_digest({"fixture_assignment": query}),
        "selector_sha256": host_digest(selection)}, "sheet": grading["parse_result"]["sheet"]}


def input_selections(inputs):
    return [{"source_ref": item["binding"]["source_ref"], "collection": item["binding"]["collection"]}
            for item in inputs]


def qualified_fixture(outcome, grading, scope, *, inputs=()):
    """Pure-view TEST fixture; these flags do not assert real host admission."""
    result = outcome["result"]
    return {"version": "bvbrc_data_qualified_result_v1", "service": "bvbrc_data", "binding": {
        "source_ref": result["source_ref"], "native_artifact_ref": result["raw_artifact_ref"],
        "native_sha256": grading["parse_result"]["retained_native_sha256"],
        "grading_artifact_ref": result["grading_artifact_ref"], "collection": result["collection"],
        "acquisition_assignment_sha256": host_digest({"fixture_assignment": grading["prepared"]["original_request"]}),
        "selector_sha256": host_digest(grading["selector"])}, "host_qualification": {
            "run_id": "fixture_run", "source_episode_id": "fixture_results", "receiver_episode_id": "fixture_parent",
            "scope_sha256": host_digest(scope), "receipt_verified": True, "native_bytes_verified": True,
            "grading_custody_verified": True, "original_selection_verified": True, "input_bindings_verified": True,
            "receiver_possession_verified": True, "possession_basis": "admitted_return"},
        "grading": grading, "input_results": list(inputs)}


def corrected_frozen_schema(name):
    """Literal additive correction002, independent of production factoring."""
    definitions = deepcopy(FROZEN["schemas"]["$defs"])
    definitions["CellLocation"]["properties"]["source_level"]["enum"].remove("supplied")
    definitions["SuppliedCellLocation"] = {"type": "object", "properties": {
        "cell_key": {"type": "string"}, "field": {"enum": ["sample_ids", "biological_replicate_ids",
            "technical_replicate_ids", "measurement_units", "normalization_method", "pvalue_correction_method", "contrast"]},
        "source_level": {"const": "supplied"}, "source_ref": {"type": "string", "minLength": 1},
        "record_path": {"type": "string", "pattern": r"^(?:/(?:[^~/]|~[01])*)*(?![\s\S])"}},
        "required": ["cell_key", "field", "source_level", "source_ref", "record_path"], "additionalProperties": False}
    definitions["MolecularMetadata"]["properties"]["cells"]["items"] = {
        "oneOf": [{"$ref": "#/$defs/CellLocation"}, {"$ref": "#/$defs/SuppliedCellLocation"}]}
    return {"$ref": "#/$defs/" + name, "$defs": definitions}


@pytest.mark.parametrize("collection", COLLECTIONS)
def test_all_22_collection_contracts_validate_when_nested_in_host_assignment(collection):
    service = BVBRCDataService(None)
    schema = {"type": "object", "properties": {"request": service.request_schema,
        "selector": service.selector_schema}, "required": ["request", "selector"], "additionalProperties": False}
    assert len(COLLECTIONS) == 22
    assert '"$ref"' not in json.dumps(schema)
    for mode in ("page", "count", "facet"):
        options = {}
        if mode == "facet":
            field = next(name for name, spec in FIELD_REGISTRY[collection]["fields"].items() if spec["facet_supported"])
            options["facet"] = {"field": field, "offset": 0, "limit": 2, "min_count": 1,
                "sort": "index", "include_missing": True}
        query = request(collection, mode=mode, **options)
        Draft202012Validator(schema).validate({"request": query, "selector": selector()})
        assert service.validate_request(query, None) == query
        assert service.launch_catalog(query)[0]["name"] == DATA_QUERY_OPERATION
        assert service.result_catalog(query, selector())[0]["name"] == DATA_RESULT_OPERATION


def test_declarations_work_without_service_construction_and_versions_do_not_cross():
    service = BVBRCDataService.__new__(BVBRCDataService)
    assert [entry["name"] for entry in service.capabilities()] == [QUERY_OPERATION, DATA_QUERY_OPERATION]
    assert [entry["name"] for entry in service.result_capabilities()] == [RESULT_OPERATION, DATA_RESULT_OPERATION]
    assert all(entry["input_schema"] == EMPTY_ARGUMENTS for entry in service.capabilities() + service.result_capabilities())
    service = BVBRCDataService(None)
    for query, operation in [(request(), QUERY_OPERATION), ({"collection": "genome", "filters": []}, DATA_QUERY_OPERATION)]:
        with pytest.raises(ContractError, match="operation_request_version_conflict"):
            command(service, query, operation=operation)
    with pytest.raises(ValueError):
        service.result_catalog(request(mode="count"), selector(page={"offset": 0, "limit": 1}))
    with pytest.raises(ValueError):
        service.result_catalog(request(), row_selector(numbers=["log2_fc"]))
    with pytest.raises(ValueError):
        service.result_catalog(request(), {**selector(), "filters": []})


def test_actual_host_assignment_schema_embeds_both_request_versions():
    from gene_annotation_episode.api_service_execution import APIServiceExecution
    host = APIServiceExecution.__new__(APIServiceExecution)
    host.configuration = {"fixture_api": {"kind": "api", "service": "bvbrc_data"}}
    host.services = {"fixture_api": BVBRCDataService(None)}
    definition = host.assignment_schema("fixture_api")
    for query in [request("bioset_result", fields=["id", "counts"]), {"collection": "genome", "filters": []}]:
        assignment = {"version": "api_service_assignment_v1", "resource_id": "fixture_api", "service": "bvbrc_data",
            "request": query, "endpoint": "usable_handoff", "constraints": {}}
        Draft202012Validator(definition).validate(assignment)
        assert host.validate_assignment(assignment) == assignment


def test_exact_one_get_and_original_cache_ignore_local_projection(monkeypatch, service):
    provider, scope = service
    calls = []
    class Response:
        status = 200
        def __init__(self, url, offset):
            self.url, self.offset = url, offset
            self.headers = Message()
            self.headers["Content-Type"] = "application/solr+json"
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return self.url
        def read(self): return envelope([{"genome_id": "511145.12", "plasmids": 0}], total=8, start=self.offset)
    class Opener:
        def open(self, native, timeout):
            from urllib.parse import parse_qs, urlsplit
            calls.append(native)
            return Response(native.full_url, int(parse_qs(urlsplit(native.full_url).query)["start"][0]))
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.urllib.request.build_opener", lambda handler: Opener())
    query = request(fields=["genome_id", "plasmids"], limit=1)
    launched = command(provider, query, operation=DATA_QUERY_OPERATION, scope=scope)
    assert launched["mutates_remote"] is False
    assert launched["prepared_query"] == encode_native_query(query, base_url=DEFAULT_BASE_URL)
    native = provider.invoke(launched)
    assert len(calls) == 1 and calls[0].get_header("Content-type") == "application/solrquery+x-www-form-urlencoded"
    assert provider.decode(launched, native)["handoff_ready"]
    selected = row_selector(numbers=["plasmids"])
    acquired = command(provider, query, selected, scope=scope)
    assert acquired["cache_original"] is True
    with pytest.raises(ContractError, match="original_response_required"):
        provider.invoke(acquired)
    outcome = provider.publish(query, selected, native, scope, "cached", publication_inputs=publication_inputs(acquired["prepared_query"]))
    assert outcome["status"] == "completed" and len(calls) == 1
    explicit_same = command(provider, query, row_selector(numbers=["plasmids"], page={"offset": 0, "limit": 1}), scope=scope)
    assert explicit_same["cache_original"] is True
    later = command(provider, query, row_selector(numbers=["plasmids"], page={"offset": 2, "limit": 1}), scope=scope)
    assert later["cache_original"] is False
    assert provider.decode(later, provider.invoke(later))["facts"]["page"]["response_start"] == 2
    assert len(calls) == 2
    feature_query = request("genome_feature")
    join = selector({"family": "feature_sequence", "feature_ids": ["f"], "sequence_kind": "AA",
        "feature_metadata_fields": [], "include_sequence_values": False},
        inputs=[{"collection": "feature_sequence", "source_ref": "fixture_explicit_input"}])
    assert command(provider, feature_query, join)["cache_original"] is True


def test_publication_custody_full_grading_single_source_and_repeat_identity(service, monkeypatch):
    provider, scope = service
    store = provider.tools.store
    query = request(fields=["genome_id", "genome_length", "plasmids"])
    selected = row_selector(numbers=["genome_length", "plasmids"])
    prepared = command(provider, query, selected, scope=scope)["prepared_query"]
    raw = envelope([{"genome_id": "511145.12", "genome_length": 4639675, "plasmids": 0,
        "unselected_native_payload": {"complete": [1, 2, 3]}}])
    native = snapshot(prepared, raw)
    initial_sources = len(store.list("source"))
    def no_compile(*args, **kwargs): pytest.fail("publication recompiled saved request")
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.encode_native_query", no_compile)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_data_query.encode_native_query", no_compile)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_data_query._expression", no_compile)
    inputs = publication_inputs(prepared)
    outcome = provider.publish(query, selected, native, scope, "first", publication_inputs=inputs)
    result = outcome["result"]
    assert set(result) == {"source_ref", "raw_artifact_ref", "grading_artifact_ref", "collection", "mode",
        "parse_status", "qualification", "requested_projection_complete", "projection_failures"}
    source = store.get(result["source_ref"])
    assert source["auxiliary_artifact_refs"] == [result["grading_artifact_ref"]]
    assert source["artifact_ref"] == result["raw_artifact_ref"]
    assert store.get_artifact(source["artifact_ref"]) == raw
    provenance = json.loads(store.get_artifact(source["request_ref"]))
    assert provenance["transport"] == native.transport and provenance["request"] == native.request
    assert provenance["prepared"] == prepared and provenance["sha256"] == native.sha256
    grading, = source_tool_gradings(store, source["id"])
    Draft202012Validator(corrected_frozen_schema("PublishedGrading")).validate(grading)
    assert "source_ref" not in grading
    assert grading["page_components"] == {"version": "bvbrc_data_page_components_v1", "native_row_count": 1,
        "valid_row_count": 1, "invalid_row_count": 0, "reported_population_count": 1, "population_exactness": "exact"}
    assert [cell["value"] for cell in grading["parse_result"]["sheet"]["rows"][0]["numerical_cells"]] == [4639675, 0]
    assert outcome["record_refs"] == [source["id"]] == outcome["changed_record_refs"]
    repeated = provider.publish(query, selected, native, scope, "repeat", publication_inputs=inputs)
    assert repeated["record_refs"] == outcome["record_refs"] and repeated["changed_record_refs"] == []
    assert len(store.list("source")) == initial_sources + 1
    for name in ("observation", "assessment", "annotation", "feature"):
        assert not store.list(name)
    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert calculate_page_counts(grading["parse_result"]["sheet"]) == grading["page_components"]
    assert requested_projection_failures(grading, input_results=[]) == []


@pytest.mark.parametrize("mode,filename", [("count", "feature_count_solr"), ("facet", "feature_facet_solr_zero")])
def test_unchanged_retained_native_count_two_and_facet_halves(service, mode, filename):
    query = deepcopy(EXAMPLES["qualified_result_fixture"]["grading"]["prepared"]["original_request"])
    query["mode"] = mode
    if mode == "count": del query["facet"]
    raw = (EVIDENCE / (filename + ".body")).read_bytes()
    outcome, grading, _ = publish(service, query, selector(), raw)
    assert outcome["status"] == "completed"
    assert grading["page_components"]["native_row_count"] == 0
    assert grading["page_components"]["reported_population_count"] == 2
    assert grading["parse_result"]["sheet"]["rows"] == []
    if mode == "facet":
        assert grading["facet_components"] == EXAMPLES["facet_expected_components"]
        assert [r["fraction"] for r in grading["facet_components"]["fractions"]] == [0.5, 0.5, 0.0]
        assert grading["parse_result"]["sheet"]["facets"][0]["buckets"][2]["is_missing_bucket"] is True
        assert calculate_facet_fractions(grading["parse_result"]["sheet"],
            denominator_policy="same_response_exact_document_count") == grading["facet_components"]


def test_native_zero_count_and_empty_population_fraction_are_distinct(service):
    facet = {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1, "sort": "index", "include_missing": True}
    query = request("genome_feature", mode="facet", facet=facet)
    outcome, grading, _ = publish(service, query, selector(), envelope([], facet_counts={"facet_fields": {"annotation": [None, 0]}}))
    assert outcome["status"] == "completed"
    assert grading["parse_result"]["sheet"]["count"]["reported_value"] == 0
    fraction, = grading["facet_components"]["fractions"]
    assert (fraction["numerator"], fraction["denominator"], fraction["fraction"], fraction["reason"]) == (0, 0, None, "empty_population")


@pytest.mark.parametrize("population,pairs", [(2, ["PATRIC", 1, "RefSeq"]), ("invalid", ["PATRIC", 1]), (2, ["PATRIC", 3])])
def test_malformed_facet_or_population_preserves_independent_values(service, population, pairs):
    facet = {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1, "sort": "index", "include_missing": True}
    outcome, grading, _ = publish(service, request("genome_feature", mode="facet", facet=facet), selector(),
        envelope([], total=population, facet_counts={"facet_fields": {"annotation": pairs}}))
    assert outcome["status"] == "partial" and outcome["result"]["projection_failures"]
    first = grading["parse_result"]["sheet"]["facets"][0]["buckets"][0]
    assert first["term"]["string_value"] == "PATRIC" and first["count"] == pairs[1]
    if population == "invalid":
        assert grading["parse_result"]["sheet"]["count"]["reported_value"] is None
    Draft202012Validator(corrected_frozen_schema("PublishedGrading")).validate(grading)


def test_partial_native_fields_only_block_the_requested_projection(service):
    query = request(fields=["genome_id", "genome_length", "gc_content"])
    raw = envelope([{"genome_id": "a", "genome_length": 20, "gc_content": 50.0},
                    {"genome_id": "b", "genome_length": 30, "gc_content": "malformed"}])
    outcome, grading, source = publish(service, query, row_selector(rows=[0, 1], numbers=["genome_length"]), raw)
    assert outcome["status"] == "completed" and outcome["result"]["parse_status"] == "partial"
    assert outcome["result"]["requested_projection_complete"] is True
    assert grading["page_components"]["valid_row_count"] == 1 and grading["page_components"]["invalid_row_count"] == 1
    invalid, retained, _ = publish(service, query, row_selector(rows=[0, 1], numbers=["gc_content"]), raw)
    assert invalid["status"] == "partial" and invalid["result"]["requested_projection_complete"] is False
    assert invalid["result"]["projection_failures"][0]["field"] == "gc_content"
    assert len(retained["parse_result"]["sheet"]["rows"]) == 2
    assert service[0].tools.store.get_artifact(invalid["result"]["raw_artifact_ref"]) == source.content
    metadata_only, _, _ = publish(service, query, selector(), raw)
    assert metadata_only["status"] == "completed"


@pytest.mark.parametrize("kind", ["incomplete", "invalid_json", "wrong_media", "http_error"])
def test_failed_and_partial_native_data_keep_raw_and_grading_artifacts(service, kind):
    provider, scope = service
    query, selected = request(fields=["genome_id", "plasmids"]), row_selector(numbers=["plasmids"])
    prepared = command(provider, query, selected, scope=scope)
    native = snapshot(prepared["prepared_query"], envelope([{"genome_id": "a", "plasmids": 0}]))
    if kind == "incomplete": native.transport["body_complete"] = False
    if kind == "invalid_json": native = replace(native, content=b'{"response":')
    if kind == "wrong_media": native = replace(native, media_type="application/json", content=b"[]")
    if kind == "http_error": native.transport["status"] = 429
    event = provider.decode(prepared, native)
    assert event["result_available"] is True
    if kind != "incomplete":
        assert event["state"] == "failed" and not event["handoff_ready"]
        launch = command(provider, query, operation=DATA_QUERY_OPERATION, scope=scope)
        assert not provider.decode(launch, native)["result_available"]
    outcome = provider.publish(query, selected, native, scope, kind,
        publication_inputs=publication_inputs(prepared["prepared_query"]))
    assert outcome["status"] == "partial" and outcome["result"]["projection_failures"]
    assert provider.tools.store.get_artifact(outcome["result"]["raw_artifact_ref"]) == native.content
    grading, = source_tool_gradings(provider.tools.store, outcome["result"]["source_ref"])
    assert grading["parse_result"]["status"] == ("partial" if kind == "incomplete" else "failed")
    if kind == "incomplete": assert grading["parse_result"]["sheet"]["rows"][0]["numerical_cells"][0]["value"] == 0


def test_missing_unselected_null_zero_and_absent_requested_row_are_valid(service):
    query = request(fields=["genome_id", "plasmids", "gc_content"])
    outcome, grading, _ = publish(service, query,
        row_selector(rows=[0, 2], numbers=["plasmids", "gc_content", "genome_length"]),
        envelope([{"genome_id": "a", "plasmids": 0, "gc_content": None}]))
    assert outcome["status"] == "completed" and outcome["result"]["projection_failures"] == []
    assert [(c["field"], c["value"], c["reason"]) for c in grading["parse_result"]["sheet"]["rows"][0]["numerical_cells"]] == [
        ("plasmids", 0, None), ("gc_content", None, "native_null")]
    query = request(fields=["genome_id"], offset=9, limit=1)
    outcome, grading, _ = publish(service, query, selector(), envelope([], total=2, start=9))
    assert outcome["status"] == "completed"
    assert grading["parse_result"]["sheet"]["page"]["population_coverage"] == "subset"
    assert grading["parse_result"]["sheet"]["page"]["next_offset"] is None


@pytest.mark.parametrize("change", ["missing", "request", "page", "inputs", "metadata", "binding_digest", "binding_collection"])
def test_publication_rejects_mismatched_explicit_inputs_before_writing(service, change):
    provider, scope = service
    seq = input_page(service, "feature_sequence", [{"md5": hashlib.md5(b"MA").hexdigest(), "sequence_type": "AA", "sequence": "MA"}])
    query = request("genome_feature", fields=["feature_id", "aa_sequence_md5", "aa_length"])
    selection = selector({"family": "feature_sequence", "feature_ids": ["f"], "sequence_kind": "AA",
        "feature_metadata_fields": [], "include_sequence_values": False}, inputs=input_selections([seq]))
    prepared = command(provider, query, selection, scope=scope)["prepared_query"]
    native = snapshot(prepared, envelope([{"feature_id": "f", "aa_sequence_md5": hashlib.md5(b"MA").hexdigest(), "aa_length": 2}]))
    supplied = publication_inputs(prepared, [seq])
    if change == "missing": supplied = None
    elif change == "request": supplied["prepared"]["original_request"]["limit"] = 3
    elif change == "page": supplied["prepared"]["page_selector"] = {"offset": 3, "limit": 3}
    elif change == "inputs": supplied["input_results"] = []
    elif change == "metadata": supplied["metadata_bindings"] = [{"source_ref": "source_x", "native_artifact_ref": "artifact_x",
        "native_sha256": "0" * 64, "record_path": "", "metadata_sha256": "0" * 64}]
    elif change == "binding_digest": supplied["input_results"][0]["binding"]["native_sha256"] = "0" * 64
    elif change == "binding_collection": supplied["input_results"][0]["binding"]["collection"] = "genome_feature"
    before = len(provider.tools.store.list("source"))
    with pytest.raises(ValueError):
        provider.publish(query, selection, native, scope, change, publication_inputs=supplied)
    assert len(provider.tools.store.list("source")) == before


def test_native_feature_sequence_composition_preserves_two_features_and_four_relations(service, monkeypatch):
    sequences = input_page(service, "feature_sequence", retained_rows("feature_sequences"))
    features = retained_rows("feature_page")
    fields = list(dict.fromkeys(field for row in features for field in row if field in FIELD_REGISTRY["genome_feature"]["fields"]))
    query = request("genome_feature", fields=fields)
    selection = selector({"family": "feature_sequence", "feature_ids": FEATURE_IDS, "sequence_kind": "both",
        "feature_metadata_fields": ["product", "start", "end", "strand"], "include_sequence_values": True},
        inputs=input_selections([sequences]))
    # The publisher consumes the explicit supplied sheet. It may not reopen
    # the named input source or search Store to discover another page.
    store = service[0].tools.store
    original_get = store.get
    def no_input_lookup(reference):
        assert reference != sequences["binding"]["source_ref"], "publisher looked up supplied input source"
        return original_get(reference)
    with monkeypatch.context() as guard:
        guard.setattr(store, "get", no_input_lookup)
        guard.setattr(store, "list", lambda *args, **kwargs: pytest.fail("publisher searched Store"))
        outcome, grading, _ = publish(service, query, selection, envelope(features), inputs=[sequences])
    assert outcome["status"] == "completed"
    Draft202012Validator(corrected_frozen_schema("PublishedGrading")).validate(grading)
    assert grading["feature_sequence_components"] == EXAMPLES["feature_sequence_expected_components"]
    edges = grading["feature_sequence_sheet"]["edges"]
    assert [(edge["feature_id"], edge["sequence_kind"], edge["sequence_length"]) for edge in edges] == [
        (FEATURE_IDS[0], "AA", 253), (FEATURE_IDS[0], "NA", 762),
        (FEATURE_IDS[1], "AA", 253), (FEATURE_IDS[1], "NA", 762)]
    assert all(edge["raw_md5_match"] is True and edge["length_match"] is True for edge in edges)
    assert calculate_feature_sequence_counts(grading["feature_sequence_sheet"]) == grading["feature_sequence_components"]
    assert grading["input_bindings"] == [sequences["binding"]]
    assert not service[0].tools.store.list("observation")
    from gene_annotation_episode.bvbrc_data_views import project_bvbrc_data_facts
    qualified = qualified_fixture(outcome, grading, service[1], inputs=[sequences])
    facts = project_bvbrc_data_facts([qualified], selector=selection,
        requested_sources=("execution_bvbrc_feature_sequence_rows",))
    assert len(facts["execution_bvbrc_feature_sequence_rows"]) == 4
    assert {row["feature_id"] for row in facts["execution_bvbrc_feature_sequence_rows"]} == set(FEATURE_IDS)


def test_native_molecular_composition_retains_all_seven_fields_and_source_levels(service):
    results = retained_rows("expression_page")
    parents = [input_page(service, collection, retained_rows(name)) for collection, name in
        [("bioset", "bioset_page"), ("experiment", "experiment_page")]]
    fields = list(dict.fromkeys([field for row in results for field in row
        if field in FIELD_REGISTRY["bioset_result"]["fields"]] + list(MOLECULAR_MEASUREMENT_FIELDS)))
    query = request("bioset_result", fields=fields)
    selection = selector({"family": "molecular_experiment", "result_ids": [row["id"] for row in results],
        "measurement_fields": ["log2_fc", "z_score"], "metadata_fields": [
            {"source_level": "bioset", "field": "treatment_duration"},
            {"source_level": "experiment", "field": "measurement_technique"}]}, inputs=input_selections(parents))
    outcome, grading, _ = publish(service, query, selection, envelope(results), inputs=parents)
    assert outcome["status"] == "completed"  # Missing feature pages are explicit unavailable links.
    rows = grading["molecular_sheet"]["rows"]
    assert len(rows) == 2 and [row["result_id"] for row in rows] == [row["id"] for row in results]
    assert [[cell["field"] for cell in row["measurements"]] for row in rows] == [list(MOLECULAR_MEASUREMENT_FIELDS)] * 2
    assert [[cell["value"] for cell in row["measurements"]] for row in rows] == [
        [None, None, None, -0.132, None, -0.544, None], [None, None, None, -0.129, None, -0.556, None]]
    assert all(cell["unit_basis"] == "unknown" and not cell["unit_cell_keys"] for row in rows for cell in row["measurements"])
    assert [row["exp_id"] for row in rows] == ["65769", "30087"]
    assert [row["bioset_id"] for row in rows] == ["53111326", "57692532"]
    assert all(row["experiment"]["status"] == row["bioset"]["status"] == "matched" for row in rows)
    Draft202012Validator(corrected_frozen_schema("PublishedGrading")).validate(grading)


def test_supplied_units_keep_real_source_pointer_and_fractional_signed_values(service):
    provider, _ = service
    data = {"result_id": "r", "bioset_id": "b", "sample_ids": ["s1"],
        "biological_replicate_ids": None, "technical_replicate_ids": [],
        "measurement_units": [{"field": "counts", "unit": "reported intensity µmol"}],
        "normalization_method": None, "pvalue_correction_method": None, "contrast": None}
    store = provider.tools.store
    raw_metadata = json.dumps({"design": [data]}, ensure_ascii=False).encode()
    artifact = store.artifact(raw_metadata, "application/json")
    metadata_source = store.put("source", {"provider": "fixture_metadata", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": None, "request_ref": None, "version": None, "retrieved_at": None}, origin="external")["id"]
    supplied = {**data, "provenance": {"source_ref": metadata_source, "record_path": "/design/0"}}
    binding = {"source_ref": metadata_source, "native_artifact_ref": artifact,
        "native_sha256": hashlib.sha256(raw_metadata).hexdigest(), "record_path": "/design/0", "metadata_sha256": json_digest(data)}
    query = request("bioset_result", fields=["id", "exp_id", "bioset_id", "feature_id", *MOLECULAR_MEASUREMENT_FIELDS])
    selection = selector({"family": "molecular_experiment", "result_ids": ["r"],
        "measurement_fields": ["counts"], "metadata_fields": []}, supplied=[supplied])
    outcome, grading, _ = publish(service, query, selection, envelope([{"id": "r", "exp_id": "e", "bioset_id": "b",
        "feature_id": "f", "counts": -1.25, "fpkm": 0.0, "tpm": 2.5, "log2_fc": -2,
        "p_value": 0.01, "z_score": -3.2, "other_value": 7.1}]), metadata_bindings=[binding])
    assert outcome["status"] == "completed"
    molecular = grading["molecular_sheet"]
    assert molecular["supplied_metadata"] == [supplied] and grading["metadata_bindings"] == [binding]
    measurements = molecular["rows"][0]["measurements"]
    assert [cell["value"] for cell in measurements] == [-1.25, 0.0, 2.5, -2, 0.01, -3.2, 7.1]
    count = measurements[0]
    assert count["unit_code"] is None and count["unit_basis"] == "supplied"
    assert count["unit_cell_keys"] == ["supplied/" + metadata_source + "/design/0/measurement_units/0/unit"]
    locations = next(m for m in molecular["rows"][0]["metadata"] if m["source_level"] == "supplied" and m["field"] == "measurement_units")["cells"]
    assert all(location["source_ref"] == metadata_source and "native_sha256" not in location and "collection" not in location for location in locations)
    Draft202012Validator(corrected_frozen_schema("PublishedGrading")).validate(grading)
    from gene_annotation_episode.bvbrc_data_views import (
        FACT_SCHEMAS, materialize_bvbrc_received_values, project_bvbrc_data_facts,
    )
    qualified = qualified_fixture(outcome, grading, service[1])
    facts = project_bvbrc_data_facts([qualified], selector=selection,
        requested_sources=("execution_bvbrc_expression_rows",))
    selected_rows = facts["execution_bvbrc_expression_rows"]
    assert selected_rows[0]["measurements"][0]["value"] == -1.25
    assert selected_rows[0]["measurements"][0]["unit_value_refs"]
    form_schema = {"type": "object", "properties": {"measured": FACT_SCHEMAS["execution_bvbrc_expression_rows"]},
        "required": ["measured"], "additionalProperties": False}
    materialized = materialize_bvbrc_received_values([qualified], admitted_form={"measured": selected_rows}, original_schema=form_schema)
    supplied_cells = [cell for item in materialized for cell in item["cells"] if cell["source_level"] == "supplied"]
    assert len(supplied_cells) == 1 and supplied_cells[0]["source_ref"] == metadata_source
    assert supplied_cells[0]["atoms"][0]["string_value"] == "reported intensity µmol"


def test_requested_join_is_retained_when_current_response_is_unparseable(service):
    selection = selector({"family": "feature_sequence", "feature_ids": ["absent"], "sequence_kind": "AA",
        "feature_metadata_fields": [], "include_sequence_values": False})
    outcome, grading, _ = publish(service, request("genome_feature"), selection, b"malformed")
    assert outcome["status"] == "partial" and grading["parse_result"]["sheet"] is None
    assert grading["feature_sequence_sheet"]["edges"][0]["join_status"] == "missing_feature"
    assert grading["feature_sequence_sheet"]["requirements"][0]["values"] == ["absent"]
    assert grading["feature_sequence_components"]["selected_feature_count"] == 1


def test_invalid_molecular_measurement_is_partial_only_when_requested(service):
    query = request("bioset_result", fields=["id", "exp_id", "bioset_id", "feature_id", "counts", "fpkm"])
    raw = envelope([{"id": "r", "exp_id": "e", "bioset_id": "b", "feature_id": "f", "counts": 1.5, "fpkm": "bad"}])
    def selected(field):
        return selector({"family": "molecular_experiment", "result_ids": ["r"],
            "measurement_fields": [field], "metadata_fields": []})
    valid, grading, _ = publish(service, query, selected("counts"), raw)
    assert valid["status"] == "completed" and grading["parse_result"]["status"] == "partial"
    assert grading["molecular_sheet"]["rows"][0]["measurements"][0]["value"] == 1.5
    invalid, grading, _ = publish(service, query, selected("fpkm"), raw)
    assert invalid["status"] == "partial"
    assert any(issue["field"] == "fpkm" for issue in invalid["result"]["projection_failures"])
    assert len(grading["molecular_sheet"]["rows"][0]["measurements"]) == 7


@pytest.mark.parametrize("family,source", [("query_metadata", "execution_bvbrc_pages"), ("facet", "execution_bvbrc_facets")])
def test_failed_publication_projects_explicit_unavailable_without_native_zero(service, family, source):
    from gene_annotation_episode.bvbrc_data_views import project_bvbrc_data_facts
    query = request() if family == "query_metadata" else request("genome_feature", mode="facet", facet={
        "field": "annotation", "offset": 0, "limit": 2, "min_count": 1, "sort": "index", "include_missing": True})
    selection = selector()
    outcome, grading, _ = publish(service, query, selection, b"malformed")
    assert outcome["status"] == "partial" and not outcome["result"]["requested_projection_complete"]
    qualified = qualified_fixture(outcome, grading, service[1])
    facts = project_bvbrc_data_facts([qualified], selector=selection, requested_sources=(source,))[source]
    assert len(facts) == 1 and facts[0]["status"] == "unavailable"
    if family == "facet":
        assert facts[0]["bucket_ref"] is None and facts[0]["count"] is None
        assert facts[0]["fraction_unavailable_reason"] == "native_value_invalid"
    else:
        assert facts[0]["returned_row_count"] is None and facts[0]["reported_total"] is None
        assert facts[0]["unavailable_reason"] == "native_value_invalid"
