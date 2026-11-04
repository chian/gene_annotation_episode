"""HPA gene acquisition contracts over one retained native HTTP entity.

Request association in these controls is engineered over the exact captured
body; these are not live requests or current-episode integration evidence.
Pure receipt references test syntax only. Publication controls use the real
registry operation and request builder with an engineered HTTP snapshot, without
fabricating actions, observations, receipts or receiver grants.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode import molecular_provider_acquisition as provider
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


OPERATION = "public.hpa.gene"
GENE = "ENSG00000141510"
ARGUMENTS = dict(gene_id=GENE, max_bytes=8388608)
SOURCE_SYNTAX = "source_" + "a" * 24
FIXTURES = Path(__file__).parent / "fixtures/hpa"
RAW_SHA256 = "ab75a8987ac2754757cd4f11406b535a1e33c8cae6823c387b9eb63310842146"
METADATA_SHA256 = "aa5dacb230452d1bb4e8fe5531c8cf5b009b768a932ba9645072a254c0185966"


def _forbidden(*args, **kwargs):
    raise AssertionError("HPA retained contract control attempted acquisition")


@pytest.fixture(autouse=True)
def no_acquisition(monkeypatch):
    for name in ("_http", "_skill"):
        monkeypatch.setattr(PublicClients, name, _forbidden)


def _fixture():
    raw = (FIXTURES / "ENSG00000141510.json").read_bytes()
    metadata_raw = (FIXTURES / "CAPTURE.json").read_bytes()
    assert len(metadata_raw) == 2498 and hashlib.sha256(metadata_raw).hexdigest() == METADATA_SHA256
    metadata = json.loads(metadata_raw)
    assert len(raw) == 9225 and hashlib.sha256(raw).hexdigest() == RAW_SHA256
    assert metadata["raw_file"] == dict(name="ENSG00000141510.json", sha256=RAW_SHA256, size_bytes=9225)
    assert metadata["capture"]["request_count"] == 1
    assert metadata["capture"]["proof_sha256"] == "a75e31665061bfc89085c6c446b8547b2ee84f83541a38040acfc9bc7b71b600"
    assert metadata["capture"]["complete_http_200_selected_response"] is True
    assert metadata["capture"]["production_binding_verified"] is False
    assert metadata["snapshot"]["request"] == {}
    return raw, metadata


def _snapshot(*, raw=None, native=None, transport=None, arguments=None):
    captured, metadata = _fixture()
    assert raw is None or native is None
    raw = (json.dumps(native, ensure_ascii=True, separators=(",", ":")).encode()
        if native is not None else captured if raw is None else raw)
    fields = deepcopy(metadata["snapshot"])
    # The original capture's request={} remains literal in CAPTURE.json.
    # Associate this engineered contract input with the explicitly chosen args.
    fields["request"] = deepcopy(ARGUMENTS if arguments is None else arguments)
    fields["content"] = raw
    fields["transport"].update(retained_body_bytes=len(raw), observed_body_bytes=len(raw))
    if transport is not None:
        fields["transport"].update(deepcopy(transport))
    return SourceSnapshot(**fields)


def _value(snapshot):
    return provider.provider_value(OPERATION, snapshot,
        artifact_ref="artifact_" + hashlib.sha256(snapshot.content).hexdigest())


def _receipt(snapshot):
    return provider.provider_receipt(_value(snapshot), source_ref=SOURCE_SYNTAX)


def _native():
    return json.loads(_fixture()[0])


class _SnapshotClients(PublicClients):
    """Actual selected request builder; one explicitly engineered HTTP reply.

    The supplied-client alternate-request seam deliberately uses the retained
    observed logical request, so the mismatch control reaches the publisher
    with its original contradiction instead of silently repairing the capture.
    """
    def __init__(self, snapshot):
        super().__init__(ncbi_email=None, timeout=30)
        self.snapshot, self.calls = deepcopy(snapshot), []

    def molecular_provider_request(self, *, operation, arguments):
        return super().molecular_provider_request(operation=operation,
            arguments=deepcopy(self.snapshot.request))

    def _http(self, service, url, params, media_type, **kwargs):
        assert not self.calls, "publication control attempted a second acquisition"
        self.calls.append(dict(service=service, url=url, params=deepcopy(params),
            media_type=media_type, **deepcopy(kwargs)))
        return deepcopy(self.snapshot)


def _dispatch(store, snapshot, *, arguments=None):
    """Use the real dispatcher/publication transaction, not a fabricated frame."""
    selected = deepcopy(ARGUMENTS if arguments is None else arguments)
    clients = _SnapshotClients(snapshot)
    registry = ToolRegistry(store, clients=clients)
    scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
    key = "engineering-hpa-publication"
    outcome = registry.execute(OPERATION, selected, scope=scope, operation_key=key)
    spec = provider.provider_request_spec(OPERATION, snapshot.request)
    assert clients.calls == [dict(spec, timeout_seconds=30)]
    assert outcome["status"] == ("completed" if outcome["result"]["acquired"] else "partial")
    row = store.db.execute("SELECT name,arguments,scope,result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
    assert row["name"] == OPERATION and json.loads(row["arguments"]) == selected and json.loads(row["scope"]) == scope
    assert json.loads(row["result"]) == outcome
    return outcome["result"], outcome["record_refs"]


def test_exact_captured_entity_fields_types_and_unknown_populations_are_retained():
    raw, metadata = _fixture()
    value = _value(_snapshot())
    native = json.loads(raw)
    assert len(native) == 119 and native["Ensembl"] == GENE and native["Gene"] == "TP53"
    assert value["native_json"] == native and list(value["native_json"]) == list(native)
    assert value["native_json"]["RNA single nuclei brain specific nCPM"] == {"astrocyte": "44.6"}
    assert value["native_json"]["RNA tissue specificity score"] is None
    assert value["native_json"]["Interactions"] == 998
    assert type(value["native_json"]["Interactions"]) is int
    assert value["native_json"]["Cancer prognostics - Bladder Urothelial Carcinoma (TCGA)"]["p_val"] == "5.89e-2"
    assert "release" not in native and "version" not in native
    assert value["population_coverage"] == "selected_response_only"
    assert value["response"]["retained_bytes"] == 9225
    assert value["response"]["declared_body_bytes"] is None
    assert value["raw_artifact_ref"] == "artifact_" + RAW_SHA256
    assert "source_ref" not in value
    assert provider.validate_provider_value(value) == value
    assert _receipt(_snapshot()) == dict(acquired=True, source_ref=SOURCE_SYNTAX,
        data_ref="artifact_" + RAW_SHA256, failure_code=None)
    assert metadata["snapshot"]["transport"]["request"]["url"] == "https://www.proteinatlas.org/" + GENE + ".json"


def test_fixed_request_and_all_exported_schemas_are_valid_and_detached():
    assert provider.provider_request_spec(OPERATION, ARGUMENTS) == dict(service="hpa",
        url="https://www.proteinatlas.org/" + GENE + ".json", params={},
        media_type="application/json", max_bytes=8388608, follow_redirects=False)
    for schema in (provider.PROVIDER_ARGUMENTS_SCHEMAS[OPERATION], provider.provider_value_schema(),
            provider.provider_result_schema(), provider.provider_receipt_schema()):
        Draft202012Validator.check_schema(schema)
    value = _value(_snapshot())
    rich = provider.provider_result(OPERATION, _snapshot(), source_ref=SOURCE_SYNTAX,
        artifact_ref="artifact_" + RAW_SHA256)
    assert provider.provider_result_from_value(value, source_ref=SOURCE_SYNTAX) == rich
    assert "observed_transfer" not in rich and rich["native_json"] == value["native_json"]
    value["native_json"]["Ensembl"] = "changed"
    assert _value(_snapshot())["native_json"]["Ensembl"] == GENE


@pytest.mark.parametrize("gene", ["TP53", "ENSG00000141510.1", "ensg00000141510",
    "ENSG00000141510\n", "ENSG0000014151", "ENSG000001415100", "ENSG00000141510?x=1", None, True])
def test_only_exact_ensembl_gene_identifiers_are_caller_operands(gene):
    with pytest.raises(ValueError):
        provider.validate_provider_arguments(OPERATION, dict(ARGUMENTS, gene_id=gene))


@pytest.mark.parametrize("cap", [True, False, 0, -1, 1.0, None, 8388609])
def test_byte_limit_requires_an_explicit_strict_positive_bounded_integer(cap):
    with pytest.raises(ValueError):
        provider.validate_provider_arguments(OPERATION, dict(ARGUMENTS, max_bytes=cap))


@pytest.mark.parametrize("extra", [dict(url="https://elsewhere.invalid"), dict(search="TP53"),
    dict(offset=0), dict(headers={}), dict(follow_redirects=True)])
def test_no_arbitrary_request_search_or_paging_arguments(extra):
    with pytest.raises(ValueError):
        provider.validate_provider_arguments(OPERATION, {**ARGUMENTS, **extra})


@pytest.mark.parametrize("identifier,code", [(None, "native_id_invalid"), (False, "native_id_invalid"),
    (998, "native_id_invalid"), ([], "native_id_invalid"), ("", "native_id_invalid"),
    ("ENSG00000134057", "native_id_differs_from_request"), (GENE + ".1", "native_id_differs_from_request")])
def test_native_top_level_ensembl_is_exact_and_never_normalized(identifier, code):
    native = _native(); native["Ensembl"] = identifier
    assert _receipt(_snapshot(native=native))["failure_code"] == "molecular_provider_" + code


def test_symbol_nested_identifier_or_related_id_cannot_replace_missing_top_identity():
    native = _native(); native.pop("Ensembl")
    native.update(Gene=GENE, related={"Ensembl": GENE}, source_ref=SOURCE_SYNTAX)
    receipt = _receipt(_snapshot(native=native))
    assert receipt == dict(acquired=False, source_ref=SOURCE_SYNTAX, data_ref=None,
        failure_code="molecular_provider_native_id_missing")


@pytest.mark.parametrize("raw", [b"[]", b"null", b"true", b'"TP53"',
    b'[{"Ensembl":"ENSG00000141510"}]'])
def test_other_json_root_types_do_not_select_a_first_gene_record(raw):
    assert _receipt(_snapshot(raw=raw))["failure_code"] == "molecular_provider_json_root_not_object"


@pytest.mark.parametrize("second", [GENE, "ENSG00000134057"])
def test_duplicate_native_identity_members_are_denied_without_overwriting_either_token(second):
    raw = ('{"Ensembl":"' + GENE + '","Ensembl":"' + second + '"}').encode()
    value = _value(_snapshot(raw=raw))
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert value["decode_error"] == "invalid_native_json"
    assert provider.provider_receipt(value, source_ref=SOURCE_SYNTAX)["failure_code"] == "molecular_provider_invalid_native_json"


@pytest.mark.parametrize("raw,code", [(b"\xff", "invalid_native_utf8"),
    (b'{"Ensembl":', "invalid_native_json"),
    (b'{"Ensembl":"ENSG00000141510","score":NaN}', "invalid_native_json"),
    (b'{"Ensembl":"ENSG00000141510","score":1e-9999}', "invalid_native_json")])
def test_bad_encoding_partial_json_and_nonrepresentable_numbers_remain_captured_failures(raw, code):
    value = _value(_snapshot(raw=raw))
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert provider.provider_receipt(value, source_ref=SOURCE_SYNTAX)["failure_code"] == "molecular_provider_" + code


def test_unselected_fields_null_zero_native_units_and_number_lexemes_are_not_reinterpreted():
    raw = (b'{ "Ensembl":"ENSG00000141510", "Gene":["unselected alias"], '
        b'"Unrecognized":{"nCPM":"44.6","missing":null,"zero":0,"number":1.2300e-4}, '
        b'"source_ref":"source_aaaaaaaaaaaaaaaaaaaaaaaa", "release":"unverified" }\n')
    value = _value(_snapshot(raw=raw))
    assert value["native_json"] == json.loads(raw)
    assert value["native_json"]["Unrecognized"] == dict(nCPM="44.6", missing=None, zero=0, number=0.000123)
    assert value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(raw).hexdigest()
    assert _receipt(_snapshot(raw=raw))["acquired"] is True


@pytest.mark.parametrize("status", [201, 204, 206, 301, 404, 500])
def test_hpa_requires_exact_http_200_without_changing_other_provider_status_rules(status):
    receipt = _receipt(_snapshot(transport=dict(status=status)))
    assert receipt["acquired"] is False and receipt["data_ref"] is None
    assert receipt["failure_code"] == "molecular_provider_" + (
        "http_redirect" if status == 301 else "http_not_success")


@pytest.mark.parametrize("change,code", [(dict(body_complete=False), "response_incomplete"),
    (dict(retained_body_bytes=0), "transport_count_conflict"),
    (dict(observed_body_bytes=0), "transport_count_conflict"),
    (dict(response_byte_limit=1), "transport_count_conflict"),
    (dict(declared_body_bytes=0), "transport_count_conflict"),
    (dict(declared_body_bytes=False), "transport_metadata_unavailable"),
    (dict(body_capture_failure="provider_response_byte_limit"), "response_byte_limit_exceeded"),
    (dict(body_capture_failure={}), "transport_metadata_unavailable")])
def test_transfer_absence_zero_malformed_and_incomplete_values_do_not_become_success(change, code):
    assert _receipt(_snapshot(transport=change))["failure_code"] == "molecular_provider_" + code


def test_retained_bytes_cannot_exceed_the_actual_selected_cap():
    with pytest.raises(ValueError, match="snapshot_byte_limit_conflict"):
        _value(_snapshot(arguments=dict(ARGUMENTS, max_bytes=9224)))


@pytest.mark.parametrize("change", [dict(service="other"), dict(url="https://www.proteinatlas.org/other.json"),
    dict(media_type="text/plain")])
def test_successful_snapshot_processing_or_selected_association_contradictions_are_rejected(change):
    with pytest.raises(ValueError, match="snapshot_request_conflict"):
        _value(replace(_snapshot(), **change))


def test_response_content_type_qualification_does_not_replace_native_identity():
    snapshot = _snapshot(transport=dict(headers={"content-type": "text/plain"}))
    value = _value(snapshot)
    assert any(issue["code"] == "content_type_mismatch" for issue in value["issues"])
    assert provider.provider_receipt(value, source_ref=SOURCE_SYNTAX)["acquired"] is True


def test_incomplete_capture_retains_actual_error_path_media_type_without_success_promotion():
    snapshot = replace(_snapshot(transport=dict(body_complete=False,
        body_capture_failure="provider_body_capture_failed")), media_type="application/json; charset=utf-8")
    value = _value(snapshot)
    assert value["response"]["media_type"] == snapshot.media_type
    assert provider.provider_receipt(value, source_ref=SOURCE_SYNTAX)["failure_code"] == "molecular_provider_response_incomplete"


def test_private_value_tamper_cannot_change_native_identity_or_erase_processing_contradiction():
    value = _value(_snapshot())
    for mutate in (lambda item: item["native_json"].update(Ensembl="ENSG00000134057"),
            lambda item: item["response"].update(media_type="text/plain")):
        changed = deepcopy(value); mutate(changed)
        with pytest.raises(ValueError):
            provider.validate_provider_value(changed)


@pytest.mark.parametrize("native_id", [GENE, "ENSG00000134057", None])
def test_real_publisher_retains_exact_raw_private_value_and_only_confirmed_data_refs(tmp_path, native_id):
    raw = _fixture()[0] if native_id == GENE else json.dumps(dict(Ensembl=native_id)).encode()
    snapshot = _snapshot(raw=raw)
    with Store(tmp_path / "store") as store:
        receipt, refs = _dispatch(store, snapshot)
        assert set(receipt) == {"acquired", "source_ref", "data_ref", "failure_code"}
        source = store.get(receipt["source_ref"])
        assert source["provider"] == "hpa" and source["origin"] == "external"
        assert source["version"] is None and source["accession"] == (GENE if native_id == GENE else None)
        assert store.get_artifact(source["artifact_ref"]) == raw
        assert json.loads(store.get_artifact(source["request_ref"])) == dict(
            request=snapshot.request, transport=snapshot.transport)
        assert len(source["auxiliary_artifact_refs"]) == 1
        private = json.loads(store.get_artifact(source["auxiliary_artifact_refs"][0]))
        assert private == _value(snapshot) and "source_ref" not in private
        assert refs == [source["id"], *([source["artifact_ref"]] if native_id == GENE else [])]
        assert receipt["acquired"] is (native_id == GENE)
        assert not set(source["auxiliary_artifact_refs"] + [source["request_ref"]]) & set(refs)
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


def test_publisher_request_failure_witness_is_private_and_not_a_fabricated_value(tmp_path):
    snapshot = replace(_snapshot(), service="contradictory_observed_service")
    with Store(tmp_path / "store") as store:
        receipt, refs = _dispatch(store, snapshot)
        source = store.get(receipt["source_ref"])
        assert receipt["acquired"] is False and receipt["data_ref"] is None
        assert source["accession"] is None and refs == [source["id"]]
        assert store.get_artifact(source["artifact_ref"]) == snapshot.content
        witness = json.loads(store.get_artifact(source["auxiliary_artifact_refs"][0]))
        assert witness == dict(version="molecular_provider_failure_witness_v1",
            observed_snapshot_service="contradictory_observed_service", observed_snapshot_url=snapshot.url,
            failure_code="molecular_provider_request_conflict")


def test_selected_arguments_mismatch_keeps_actual_capture_but_never_claims_selected_gene(tmp_path):
    snapshot = _snapshot()
    with Store(tmp_path / "store") as store:
        receipt, refs = _dispatch(store, snapshot, arguments=dict(ARGUMENTS, gene_id="ENSG00000134057"))
        source = store.get(receipt["source_ref"])
        assert receipt["failure_code"] == "molecular_provider_selected_request_conflict"
        assert receipt["data_ref"] is None and refs == [source["id"]]
        assert source["accession"] is None and store.get_artifact(source["artifact_ref"]) == snapshot.content


def test_no_response_has_no_source_or_data_and_does_not_publish_placeholder_evidence(tmp_path):
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        before = list(store.db.execute("SELECT * FROM records"))
        with pytest.raises(ValueError, match="snapshot_invalid"):
            provider.publish_molecular_provider_request(registry, OPERATION, ARGUMENTS, None)
        assert list(store.db.execute("SELECT * FROM records")) == before
        assert provider.failed_provider_receipt("data_acquisition_failed") == dict(
            acquired=False, source_ref=None, data_ref=None, failure_code="data_acquisition_failed")


def test_successful_hpa_does_not_infer_a_release_from_native_or_unrelated_transport_fields(tmp_path):
    native = _native(); native["release"] = "unverified_native_label"
    snapshot = _snapshot(native=native, transport=dict(job_details=dict(database=dict(version="not_HPA"))))
    with Store(tmp_path / "store") as store:
        receipt, _ = _dispatch(store, snapshot)
        assert receipt["acquired"] is True
        source = store.get(receipt["source_ref"])
        assert source["version"] is None
        assert json.loads(store.get_artifact(source["artifact_ref"]))["release"] == "unverified_native_label"
