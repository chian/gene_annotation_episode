"""Real registry/episode paths with complete, explicitly controlled HTTP bodies.

The transport seam below performs no HTTP. The five earlier entity vectors and
all transport/action scaffolding are engineering fixtures, not biological findings.
The HPA entity bytes are retained from566; its transport and action scaffolding
remain engineering controls rather than another live provider acquisition.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode import molecular_provider_acquisition as provider
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.molecular_provider_acquisition import (
    OPERATIONS, PROVIDER_ARGUMENTS_SCHEMAS, validate_provider_receipt, validate_provider_value,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_prompt import text_instructions
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import action
from test_molecular_provider_acquisition import HPA_RAW


IDS = ["9606.ENSP00000269305", "9606.ENSP00000266970"]
ARGUMENTS = {
    "public.string.network": {"string_ids": IDS, "taxon_id": 9606,
        "required_score": 0, "max_bytes": 32768},
    "public.kegg.reaction": {"reaction_id": "R00259", "max_bytes": 32768},
    "public.reactome.record": {"stable_id": "R-HSA-141409", "max_bytes": 32768},
    "public.quickgo.term": {"term_id": "GO:0000001", "max_bytes": 32768},
    "public.pubchem.compound": {"cid": 2244, "max_bytes": 32768},
    "public.hpa.gene": {"gene_id": "ENSG00000141510", "max_bytes": 32768},
}
URLS = {
    "string": "https://version-12-5.string-db.org/api/json/network",
    "kegg": "https://rest.kegg.jp/get/rn:R00259",
    "reactome": "https://reactome.org/ContentService/data/query/R-HSA-141409",
    "quickgo": "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO%3A0000001",
    "pubchem": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/JSON",
    "hpa": "https://www.proteinatlas.org/ENSG00000141510.json",
}
# Complete literal bodies are the transport fixtures. No DTO/preview is used as
# a substitute for original entity bytes. The long Reactome field also exceeds
# the upstream convenience wrapper's 10,000-character output truncation point.
RAW = {
    "hpa": HPA_RAW,
    "string": b'''[
 {"stringId_A":"9606.ENSP00000269305","stringId_B":"9606.ENSP00000266970",
  "preferredName_A":"first","preferredName_B":"second","ncbiTaxonId":9606,
  "score":0.0,"nscore":0,"fscore":null,"pscore":0.1,"ascore":0.2,
  "escore":0.3,"dscore":0.4,"tscore":0.5,"unknown":{"empty":[],"flag":false}},
 {"stringId_A":"9606.ENSP00000266970","stringId_B":"9606.ENSP00000269305",
  "preferredName_A":"second","preferredName_B":"first","ncbiTaxonId":9606,
  "score":0.0,"unknown":null}
]\n''',
    "kegg": (
        "ENTRY       R00259                      Reaction\r\n"
        "NAME        retained first name;\r\n"
        "            retained continuation\r\n"
        "DEFINITION  literal compound relationship\r\n"
        "EQUATION    C00024 + C00025 <=> C00010 + C00624\r\n"
        "RCLASS      RC00064  C00025_C00624\r\n"
        "ENZYME      2.3.1.1\r\n"
        "PATHWAY     rn00220  supplied pathway label\r\n"
        "ORTHOLOGY   K00618  supplied orthology label\r\n"
        "UNKNOWN     0; null; literal text, not measured quantities\r\n"
        "///\r\n"
    ).encode("utf-8"),
    "reactome": (
        '{"dbId":141409,"stId":"R-HSA-141409","schemaClass":"Reaction",'
        '"species":[{"taxId":"9606","displayName":"Homo sapiens"}],'
        '"compartment":[{"dbId":70101,"accession":"0005829","databaseName":"GO"}],'
        '"input":[{"stId":"R-HSA-141433","stoichiometry":null}],'
        '"output":[{"stId":"R-HSA-141441","hasComponent":[]}],'
        '"isInferred":false,"native_version":"literal-native-version",'
        '"unknown":{"zero":0,"null":null,"empty":[],"full_text":"'
        + "x" * 12000 + '"}}\n'
    ).encode("utf-8"),
    "quickgo": b'''{
 "numberOfHits":1,"pageInfo":{"current":1,"total":1,"resultsPerPage":1},
 "results":[{"id":"GO:0000001","name":"literal term name","isObsolete":true,
 "definition":{"text":"literal definition","xrefs":["GO_REF:0000001"]},
 "synonyms":[],"replacements":["GO:0000002"],
 "children":[{"id":"GO:0000003","relation":"is_a"}],
 "unknown":{"zero":0,"null":null,"empty":[]}}],"unknown_envelope":null
}\n''',
    "pubchem": b'''{
 "PC_Compounds":[{"id":{"id":{"cid":2244}},
 "props":[{"urn":{"label":"literal property"},"value":{"sval":"retained native value"}}],
 "unknown":{"zero":0,"null":null,"empty":[],"false":false}},
 {"id":{"id":{"cid":2244}},"unknown":{"occurrence":"second"}}],
 "unknown_envelope":{"native":"uninterpreted"}
}\n''',
}


def forbidden(*args, **kwargs):
    raise AssertionError("controlled acquisition attempted HTTP/native work or closed replay actions")


class ControlledClients(PublicClients):
    """Override only the HTTP seam; real selected client/registry code runs."""
    def __init__(self, *, mode="success"):
        super().__init__(ncbi_email=None, timeout=3, string_caller_identity="controlled-provider-contract")
        self.mode, self.calls, self.captures = mode, [], []

    def _http(self, service, url, params, media_type, **kwargs):
        self.calls.append({"service": service, "url": url, "params": deepcopy(params),
            "media_type": media_type, **deepcopy(kwargs)})
        if self.mode == "no_response":
            raise AcquisitionError("provider_connection_failed", phase="http_request",
                diagnostic={"qualification": "controlled failure without any HTTP response"})
        raw = b'{"incomplete":' if self.mode == "malformed" else RAW[service]
        if self.mode == "native_mismatch":
            if service == "kegg":
                raw = raw.replace(b"R00259", b"R00001")
            else:
                native = json.loads(raw)
                if service == "string":
                    native[-1]["stringId_B"] = "9606.UNREQUESTED"
                elif service == "reactome":
                    native["stId"] = "R-HSA-141410"
                elif service == "quickgo":
                    native["results"].append({"id": "GO:0000002"})
                elif service == "hpa":
                    native["Ensembl"] = "ENSG00000134057"
                else:
                    assert service == "pubchem"
                    native["PC_Compounds"].append({"id": {"id": {"cid": 2245}}})
                raw = json.dumps(native).encode()
        elif self.mode == "empty_lookup":
            assert service in {"quickgo", "pubchem"}
            raw = (b'{"numberOfHits":0,"pageInfo":{"current":1,"total":0},"results":[]}'
                if service == "quickgo" else b'{"PC_Compounds":[],"unknown":null}')
        elif self.mode == "empty_network":
            assert service == "string"
            raw = b"[]"
        elif self.mode == "string_taxon_text":
            assert service == "string"
            native = json.loads(raw)
            for row in native:
                row["ncbiTaxonId"] = "9606"
            raw = json.dumps(native).encode()
        limit = kwargs["max_bytes"]
        retained = raw[:limit]
        complete = len(raw) <= limit
        address = url + ("?" + urlencode(params, doseq=True) if params else "")
        status = {"redirect": 302, "http_error": 404}.get(self.mode, 200)
        headers = {"content-type": media_type, "x-uniprot-release": "foreign-protein-release"}
        if self.mode == "string_taxon_text":
            headers["content-type"] = "text/html; charset=utf-8"
        if status == 302:
            headers["location"] = "https://example.invalid/never-follow"
        transport = {"status": status, "headers": headers,
            "header_items": [[key, value] for key, value in headers.items()],
            "request": {"method": "GET", "url": address,
                "headers": {"Accept": media_type}},
            "request_policy": {"timeout_seconds": kwargs["timeout_seconds"],
                "automatic_redirects": kwargs["follow_redirects"]},
            "body_complete": complete, "retained_body_bytes": len(retained),
            "observed_body_bytes": len(raw) if complete else limit + 1,
            "declared_body_bytes": len(raw), "response_byte_limit": limit,
            "job_details": {"database": {"version": "foreign-database-version"}},
            "response": {"headers": {"x-uniprot-release": "foreign-nested-release"}},
            "qualification": "complete engineering HTTP body; no live provider request"}
        if not complete:
            transport["body_capture_failure"] = "provider_response_byte_limit"
        if self.mode == "bad_count":
            transport["retained_body_bytes"] = 0
        elif self.mode == "missing_transfer":
            transport["body_complete"] = None
        capture = SourceSnapshot(service, address if status >= 300 else url, deepcopy(params),
            "2026-10-31T12:00:00+00:00", retained, media_type, transport)
        self.captures.append(capture)
        if status >= 300 or not complete:
            raise AcquisitionError("provider_http_" + str(status) if status >= 300
                else "provider_response_byte_limit", snapshot=capture, phase="http_response")
        return capture


def _tables(store):
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _artifacts(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()}


def _scope(store):
    return {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}


def _expected_call(operation, arguments):
    service = operation.split(".")[1]
    params = ({"identifiers": "\r".join(IDS), "species": 9606, "required_score": 0,
        "network_type": "functional", "add_nodes": 0,
        "caller_identity": "controlled-provider-contract"} if service == "string" else {})
    return {"service": service, "url": URLS[service], "params": params,
        "media_type": "text/plain" if service == "kegg" else "application/json",
        "max_bytes": arguments["max_bytes"], "timeout_seconds": 3, "follow_redirects": False}


def _assert_retained_source(store, outcome, client, operation, arguments):
    receipt = validate_provider_receipt(outcome["result"])
    source = store.get(receipt["source_ref"])
    capture = client.captures[-1]
    assert outcome["record_refs"] == [source["id"], *([source["artifact_ref"]] if receipt["acquired"] else [])]
    assert receipt["data_ref"] == (source["artifact_ref"] if receipt["acquired"] else None)
    assert source["record_type"] == "source" and source["origin"] == "external"
    assert source["provider"] == operation.split(".")[1]
    assert source["uri"] == capture.transport["request"]["url"]
    assert source["retrieved_at"] == capture.retrieved_at
    assert source["version"] is None  # Native/foreign release labels are not a provider release join.
    expected_accession = arguments.get("reaction_id", arguments.get("stable_id", arguments.get("term_id")))
    if operation == "public.pubchem.compound":
        expected_accession = str(arguments["cid"])
    elif operation == "public.hpa.gene":
        expected_accession = arguments["gene_id"] if receipt["acquired"] else None
    assert source["accession"] == expected_accession
    assert source["artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()
    assert store.get_artifact(source["artifact_ref"]) == capture.content
    provenance = json.loads(store.get_artifact(source["request_ref"]))
    assert canonical(provenance) == canonical({"request": arguments, "transport": capture.transport})
    value_ref, = source["auxiliary_artifact_refs"]
    result = validate_provider_value(json.loads(store.get_artifact(value_ref)))
    assert "source_ref" not in result and result["raw_artifact_ref"] == source["artifact_ref"]
    assert value_ref not in outcome["record_refs"] and source["request_ref"] not in outcome["record_refs"]
    assert result["population_coverage"] == "selected_response_only"
    return result, source


@pytest.mark.parametrize("operation", OPERATIONS)
def test_real_registry_controlled_provider_request_retention_and_exact_cache(tmp_path, monkeypatch, operation):
    client = ControlledClients()
    monkeypatch.setattr(client, "_skill", forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        entry = tools.catalog(scope)[operation]
        assert entry["input_schema"] == PROVIDER_ARGUMENTS_SCHEMAS[operation]
        assert entry["description"]
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="controlled-original")
        assert outcome["status"] == "completed" and outcome["feedback"] is None
        assert client.calls == [_expected_call(operation, arguments)]
        value, _ = _assert_retained_source(store, outcome, client, operation, arguments)
        assert value["issues"] == [] and value["response"]["body_complete"] is True
        assert value["response"]["retained_bytes"] == len(RAW[client.calls[0]["service"]])
        if operation == "public.kegg.reaction":
            assert value["native_json"] is None and value["native_text"].encode() == RAW["kegg"]
            assert value["native_fields"][1]["lines"][1] == {
                "line_number": 3, "text": "            retained continuation\r\n"}
            assert [block["field"] for block in value["native_fields"]][-4:] == [
                "PATHWAY", "ORTHOLOGY", "UNKNOWN", "///"]
        else:
            assert value["native_json"] == json.loads(RAW[client.calls[0]["service"]])
        if operation == "public.string.network":
            assert value["native_json"][0]["fscore"] is None
            assert value["native_json"][0]["score"] == 0.0
            assert type(value["native_json"][0]["score"]) is float
            assert value["native_json"][0]["unknown"] == {"empty": [], "flag": False}
            assert value["native_json"][1]["stringId_A"] == IDS[1]
        elif operation == "public.reactome.record":
            assert len(value["native_json"]["unknown"]["full_text"]) == 12000
            assert value["native_json"]["input"][0]["stoichiometry"] is None
            assert value["native_json"]["unknown"]["zero"] == 0
            assert value["native_json"]["unknown"]["empty"] == []
        elif operation == "public.quickgo.term":
            term = value["native_json"]["results"][0]
            assert term["isObsolete"] is True and term["replacements"] == ["GO:0000002"]
            assert value["requested"]["term_id"] == "GO:0000001"
        elif operation == "public.pubchem.compound":
            compounds = value["native_json"]["PC_Compounds"]
            assert [row["id"]["id"]["cid"] for row in compounds] == [2244, 2244]
            assert all(type(row["id"]["id"]["cid"]) is int for row in compounds)
            assert compounds[0]["unknown"] == {"zero": 0, "null": None, "empty": [], "false": False}
            assert compounds[1]["unknown"] == {"occurrence": "second"}
            assert value["native_json"]["unknown_envelope"] == {"native": "uninterpreted"}
        elif operation == "public.hpa.gene":
            assert value["native_json"]["Ensembl"] == arguments["gene_id"]
            assert value["native_json"]["RNA single nuclei brain specific nCPM"] == {"astrocyte": "44.6"}
            assert value["native_json"]["RNA tissue specificity score"] is None
            assert client.captures[0].content == HPA_RAW
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(provider, "publish_molecular_provider_request", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, arguments, scope=scope, operation_key="controlled-original") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("mode,expected", [("redirect", "partial"), ("http_error", "partial"),
    ("cap", "partial"), ("malformed", "partial")])
def test_registry_controlled_http_redirect_error_cap_and_malformed_bytes_keep_source(
        tmp_path, monkeypatch, operation, mode, expected):
    client = ControlledClients(mode=mode)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        if mode == "cap":
            arguments["max_bytes"] = 32
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="controlled-failure")
        assert outcome["status"] == expected
        assert validate_provider_receipt(outcome["result"])["acquired"] is False
        assert client.calls == [_expected_call(operation, arguments)]
        value, _ = _assert_retained_source(store, outcome, client, operation, arguments)
        observed_codes = {issue["code"] for issue in value["issues"]}
        if mode in ("redirect", "http_error"):
            assert value["response"]["http_status"] == (302 if mode == "redirect" else 404)
            assert "http_not_success" in observed_codes
            assert ("http_redirect" in observed_codes) == (mode == "redirect")
            assert outcome["feedback"]["category"] == "acquisition"
        elif mode == "cap":
            assert value["response"]["retained_bytes"] == 32
            assert value["response"]["observed_body_bytes"] == 33
            assert value["response"]["declared_body_bytes"] == len(RAW[operation.split(".")[1]])
            assert value["response"]["body_complete"] is False
            assert "response_byte_limit_exceeded" in observed_codes
        else:
            assert value["response"]["body_complete"] is True
            assert value["representation_state"] == "invalid"
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(provider, "publish_molecular_provider_request", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, arguments, scope=scope, operation_key="controlled-failure") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", OPERATIONS)
def test_registry_transport_failure_without_response_creates_no_provider_source(tmp_path, monkeypatch, operation):
    client = ControlledClients(mode="no_response")
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        sources_before = {row["id"] for row in store.list("source")}
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="controlled-no-response")
        assert outcome["status"] == "failed"
        assert validate_provider_receipt(outcome["result"]) == provider.failed_provider_receipt("data_acquisition_failed")
        assert outcome["record_refs"] == [] and client.captures == []
        assert outcome["feedback"]["code"] == "provider_connection_failed"
        assert tools.retained_molecular_reference_access(None,
            outcome["feedback"]["diagnostic_ref"], "artifact") is False
        assert client.calls == [_expected_call(operation, arguments)]
        assert {row["id"] for row in store.list("source")} == sources_before
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, arguments, scope=scope, operation_key="controlled-no-response") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("changed", [{"max_bytes": True}, {"endpoint": "https://example.invalid/other"}])
def test_registry_rejects_invalid_selected_arguments_before_transport(tmp_path, operation, changed):
    client = ControlledClients()
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        outcome = tools.execute(operation, {**ARGUMENTS[operation], **changed},
            scope=_scope(store), operation_key="invalid-controlled-input")
        assert outcome["status"] == "invalid" and outcome["record_refs"] == []
        assert client.calls == [] and client.captures == []


def _controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _two_step_controller(path, initial):
    return FixtureController(str(path), initial, 2)


def _credit(*args, **kwargs):
    return 0


def _session(directory):
    role = {"model": "provider-receipt-engineering", "reasoning_effort": "low"}
    return _SessionConnection({"connection": {"command": ["unselected-model-command"]},
        "FAST": role, "REASONING": role, "routing": {}}, directory, directory.parent)


class ReceivingProvider(ScriptedProvider):
    """Actual DecisionSource callbacks and pure Session presentation; no RPC."""
    def __init__(self, script, connection):
        super().__init__(script)
        self.connection, self.dispatches = connection, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        wire, model_instructions = self.connection._presentation(episode_id, role, instructions, context)
        self.dispatches.append(dict(episode_id=episode_id, role=role, instructions=instructions,
            context=deepcopy(context), schema=deepcopy(output_schema), wire=wire,
            model_instructions=model_instructions))
        return await super().complete(episode_id, role, instructions, context, output_schema)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_current_episode_getter_receiving_builder_pending_recovery_and_closed_replay(
        tmp_path, monkeypatch, operation):
    """One current episode acquires then reads; no getter-specific child/report."""
    class LostReply(RuntimeError):
        pass
    client = ControlledClients()
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, directory = _scope(store), tmp_path / "run"
        arguments = deepcopy(ARGUMENTS[operation])
        connection = _session(tmp_path / "session")
        actor = ReceivingProvider([action(operation, arguments)], connection)
        def workflow(selected_provider):
            return Workflow(store, tools, selected_provider, directory, "controlled-current-molecular-provider",
                _two_step_controller, _credit, project_child_credit=_credit, root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[])
        current = workflow(actor)
        goal = ("Evaluate molecular evidence for the supplied protein while keeping its correspondence to "
            "caller-selected reference data unresolved. Acquiring a record does not settle a scientific conclusion.")
        root = current.build("improvement", "root", goal, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        assert current.permits_common_action(root.source, "tool")
        assert operation in {item["name"] for item in current.catalog(scope, source=root.source)}
        original_execute, lost = ToolRegistry.execute_async, []
        async def lose_reply(registry, name, selected, **kwargs):
            outcome = await original_execute(registry, name, selected, **kwargs)
            if name == operation and not lost:
                assert outcome["status"] == "completed"
                lost.append(deepcopy(outcome))
                raise LostReply()
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_reply)
            with pytest.raises(LostReply):
                asyncio.run(root.run_async(current.context))
        assert store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0] is None
        assert len(lost) == len(actor.contexts) == len(client.calls) == 1
        value, source = _assert_retained_source(store, lost[0], client, operation, arguments)
        receipt = validate_provider_receipt(lost[0]["result"])
        def read_acquired(context):
            observed = context["last_local_outcome"]
            assert observed["result"] == receipt and observed["record_refs"] == lost[0]["record_refs"]
            assert set(observed["result"]) == {"acquired", "source_ref", "data_ref", "failure_code"}
            assert context["requested_form"] is None
            return action("source.read", dict(source_ref=source["id"], representation="original", offset=0, limit=512))
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(provider, "publish_molecular_provider_request", forbidden)
        monkeypatch.setattr(provider, "provider_value", forbidden)
        recovered_actor = ReceivingProvider([read_acquired], connection)
        recovered = workflow(recovered_actor)
        recovered_root = recovered.build("improvement", "root", goal, scope)
        record = asyncio.run(recovered_root.run_async(recovered.context))
        final = asyncio.run(recovered_root.build_result(record)).as_record()
        assert client.calls == [_expected_call(operation, arguments)]
        assert len(actor.dispatches) == len(recovered_actor.dispatches) == 1
        dispatches = actor.dispatches + recovered_actor.dispatches
        calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
        for dispatched, call in zip(dispatches, calls):
            saved_request = json.loads(call["request"])
            assert saved_request["context"] == dispatched["context"] and call["response"] is not None
            assert dispatched["wire"].startswith("TASK\n") and "\n\nSTEERING\n" in dispatched["wire"]
            assert goal in dispatched["wire"]
            assert "Absent: no parent return form was supplied." in dispatched["wire"]
            assert dispatched["model_instructions"] == text_instructions(dispatched["instructions"])
            assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
            assert goal in json.dumps(dispatched["context"]["goal"])
        assert dispatches[1]["context"]["last_local_outcome"]["result"] == receipt
        context = recovered.binding_context(recovered_root.source)
        assert set(recovered.receipts.known(context.episode_id)) == baseline | set(lost[0]["record_refs"])
        assert {row[0] for row in store.db.execute("SELECT record_ref FROM runtime_record_receipts "
            "WHERE episode_id=? AND receipt_kind='own_action'", (context.episode_id,))} == set(lost[0]["record_refs"])
        resolve = recovered.resolver(plain(context.scope), context=context)
        for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact")):
            assert resolve(reference, namespace) is True
            assert tools.retained_molecular_reference_access(context, reference, namespace) is True
            item, path = recovered.services.read_received_molecular_input(context, reference, namespace, file_format="text")
            assert item["failure"] is None and item["input"]["file"]["artifact_ref"] == source["artifact_ref"]
            assert path.read_bytes() == RAW[operation.split(".")[1]]
        private = {source["request_ref"], *source["auxiliary_artifact_refs"]}
        assert private.isdisjoint(recovered.receipts.known(context.episode_id))
        assert all(reference not in dispatched["wire"] for dispatched in dispatches for reference in private)
        for reference in private:
            assert resolve(reference, "artifact") is False
            assert tools.retained_molecular_reference_access(context, reference, "artifact") is False
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
            "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls", "tool_operations")}
        assert counts == {"runtime_episodes": 1, "runtime_actions": 2, "runtime_observations": 2,
            "runtime_model_calls": 2, "tool_operations": 2}
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
        assert [json.loads(row[0])["kind"] for row in store.db.execute(
            "SELECT action FROM runtime_actions ORDER BY decision_index")] == ["tool", "tool"]
        before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        restored_actor = ScriptedProvider([])
        restored = workflow(restored_actor)
        restored_root = restored.build("improvement", "root", goal, scope)
        restored_record = asyncio.run(restored_root.run_async(restored.context))
        assert asyncio.run(restored_root.build_result(restored_record)).as_record() == final
        assert restored_actor.contexts == [] and len(client.calls) == 1
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        assert _artifacts(directory / "archive") == archives


class MismatchedRequestClients(ControlledClients):
    """Supported supplied-client seam; the controlled reply has another request.

    Alternate requests and their complete bodies agree with one another. The
    type-only case deliberately damages the logical request after transport.
    Neither case performs HTTP or claims a genuine provider measurement.
    """
    def __init__(self, *, type_only=False):
        super().__init__()
        self.type_only = type_only

    def molecular_provider_request(self, *, operation, arguments):
        from dataclasses import replace

        actual = deepcopy(arguments)
        if not self.type_only:
            if operation == "public.string.network":
                actual["string_ids"] = ["9606.ENSP00000000001", "9606.ENSP00000000002"]
            elif operation == "public.kegg.reaction":
                actual["reaction_id"] = "R00001"
            elif operation == "public.reactome.record":
                actual["stable_id"] = "R-HSA-141410"
            elif operation == "public.quickgo.term":
                actual["term_id"] = "GO:0000002"
            elif operation == "public.hpa.gene":
                actual["gene_id"] = "ENSG00000134057"
            else:
                assert operation == "public.pubchem.compound"
                actual["cid"] = 2245
        snapshot = super().molecular_provider_request(operation=operation, arguments=actual)
        if self.type_only:
            actual["max_bytes"] = float(actual["max_bytes"])
            delivered = replace(snapshot, request=actual)
        else:
            service = operation.split(".")[1]
            if service == "kegg":
                raw = RAW[service].replace(b"R00259", actual["reaction_id"].encode("ascii"))
            else:
                body = json.loads(RAW[service])
                if service == "string":
                    for row in body:
                        row["stringId_A"] = actual["string_ids"][IDS.index(row["stringId_A"])]
                        row["stringId_B"] = actual["string_ids"][IDS.index(row["stringId_B"])]
                elif service == "reactome":
                    body["stId"] = actual["stable_id"]
                elif service == "quickgo":
                    body["results"][0]["id"] = actual["term_id"]
                elif service == "hpa":
                    body["Ensembl"] = actual["gene_id"]
                else:
                    assert service == "pubchem"
                    for compound in body["PC_Compounds"]:
                        compound["id"]["id"]["cid"] = actual["cid"]
                raw = json.dumps(body, allow_nan=False).encode()
            transport = deepcopy(snapshot.transport)
            transport.update(retained_body_bytes=len(raw), observed_body_bytes=len(raw),
                declared_body_bytes=len(raw))
            delivered = replace(snapshot, content=raw, transport=transport)
        self.captures[-1] = delivered
        return delivered


def _assert_selected_request_mismatch_is_retained_and_cached(tmp_path, monkeypatch, operation, *, type_only=False):
    from gene_annotation_episode.execution_contracts import canonical
    from gene_annotation_episode.molecular_provider_acquisition import validate_provider_arguments

    client = MismatchedRequestClients(type_only=type_only)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        original = deepcopy(arguments)
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="mismatched-selected-request")
        assert arguments == original
        assert outcome["status"] == "partial"
        assert outcome["feedback"]["category"] == "acquisition"
        code = ("molecular_provider_request_conflict" if type_only else
            "molecular_provider_selected_request_conflict")
        assert outcome["feedback"]["code"] == code
        assert len(client.calls) == len(client.captures) == 1
        capture = client.captures[0]
        if type_only:
            assert capture.request == arguments  # Python equality is intentionally insufficient.
            assert type(capture.request["max_bytes"]) is float and type(arguments["max_bytes"]) is int
        else:
            assert validate_provider_arguments(operation, capture.request) == capture.request
            assert capture.request != arguments
        assert canonical(capture.request) != canonical(arguments)
        source_ref, = outcome["record_refs"]
        assert validate_provider_receipt(outcome["result"]) == provider.failed_provider_receipt(
            code, source_ref=source_ref)
        source = store.get(source_ref)
        assert source["provider"] == operation.split(".")[1] and source["origin"] == "external"
        expected_accession = capture.request.get("reaction_id",
            capture.request.get("stable_id", capture.request.get("term_id")))
        if operation == "public.pubchem.compound":
            expected_accession = str(capture.request["cid"])
        assert source["accession"] == expected_accession
        assert source["uri"] == capture.url
        assert source["artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()
        assert store.get_artifact(source["artifact_ref"]) == capture.content
        assert json.loads(store.get_artifact(source["request_ref"])) == {
            "request": capture.request, "transport": capture.transport}
        private_ref, = source["auxiliary_artifact_refs"]
        evidence = json.loads(store.get_artifact(private_ref))
        if type_only:
            assert evidence == dict(version="molecular_provider_failure_witness_v1",
                observed_snapshot_service=capture.service, observed_snapshot_url=capture.url, failure_code=code)
        else:
            assert validate_provider_value(evidence)["requested"] == capture.request
        saved, = list(store.db.execute("SELECT * FROM tool_operations"))
        assert saved["name"] == operation and saved["arguments"] == canonical(original)
        assert saved["scope"] == canonical(scope) and json.loads(saved["result"]) == outcome
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "molecular_provider_request", forbidden)
        monkeypatch.setattr(provider, "publish_molecular_provider_request", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, original, scope=scope, operation_key="mismatched-selected-request") == outcome
        assert len(client.calls) == len(client.captures) == 1
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", OPERATIONS)
def test_supplied_client_alternate_valid_request_retains_source_without_selected_interpretation(
        tmp_path, monkeypatch, operation):
    _assert_selected_request_mismatch_is_retained_and_cached(tmp_path, monkeypatch, operation)


@pytest.mark.parametrize("operation", ["public.quickgo.term", "public.pubchem.compound"])
def test_supplied_client_numeric_request_type_mismatch_cannot_use_python_equality(tmp_path, monkeypatch, operation):
    _assert_selected_request_mismatch_is_retained_and_cached(tmp_path, monkeypatch,
        operation, type_only=True)


@pytest.mark.parametrize("operation,mode,code", [
    ("public.string.network", "native_mismatch", "native_edge_outside_request"),
    ("public.kegg.reaction", "native_mismatch", "native_id_differs_from_request"),
    ("public.reactome.record", "native_mismatch", "native_id_differs_from_request"),
    ("public.quickgo.term", "native_mismatch", "native_id_differs_from_request"),
    ("public.quickgo.term", "empty_lookup", "empty_lookup"),
    ("public.pubchem.compound", "native_mismatch", "native_id_differs_from_request"),
    ("public.pubchem.compound", "empty_lookup", "empty_lookup"),
    ("public.hpa.gene", "native_mismatch", "native_id_differs_from_request"),
])
def test_native_identity_or_empty_lookup_failure_returns_source_only_and_exact_cached_confirmation(
        tmp_path, monkeypatch, operation, mode, code):
    client = ControlledClients(mode=mode)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="native-request-qualification")
        assert outcome["status"] == "partial"
        assert outcome["result"] == provider.failed_provider_receipt("molecular_provider_" + code,
            source_ref=outcome["record_refs"][0])
        assert outcome["feedback"]["category"] == "acquisition"
        assert outcome["feedback"]["code"] == "molecular_provider_" + code
        value, source = _assert_retained_source(store, outcome, client, operation, arguments)
        if mode == "empty_lookup":
            assert value["representation_state"] == "complete" and value["issues"] == []
        assert source["artifact_ref"] not in outcome["record_refs"]
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(provider, "provider_value", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, arguments, scope=scope,
            operation_key="native-request-qualification") == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("mode", ["empty_network", "string_taxon_text"])
def test_string_empty_network_and_exact_native_string_taxon_are_confirmed_without_erasing_qualifications(
        tmp_path, mode):
    operation, client = "public.string.network", ControlledClients(mode=mode)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        arguments = deepcopy(ARGUMENTS[operation])
        outcome = tools.execute(operation, arguments, scope=_scope(store), operation_key="string-literal-native")
        assert outcome["status"] == "completed" and outcome["feedback"] is None
        assert validate_provider_receipt(outcome["result"])["acquired"] is True
        value, _ = _assert_retained_source(store, outcome, client, operation, arguments)
        if mode == "empty_network":
            assert value["native_json"] == [] and value["issues"] == []
        else:
            assert [row["ncbiTaxonId"] for row in value["native_json"]] == ["9606", "9606"]
            assert [row["code"] for row in value["issues"]] == [
                "content_type_mismatch", "native_taxon_invalid", "native_taxon_invalid"]
            assert value["representation_state"] == "partial"


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("mode,code", [
    ("bad_count", "transport_count_conflict"), ("missing_transfer", "response_incomplete")])
def test_incomplete_transfer_authority_cannot_confirm_an_otherwise_complete_native_record(
        tmp_path, operation, mode, code):
    client = ControlledClients(mode=mode)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        arguments = deepcopy(ARGUMENTS[operation])
        outcome = tools.execute(operation, arguments, scope=_scope(store), operation_key="transfer-authority")
        value, source = _assert_retained_source(store, outcome, client, operation, arguments)
        assert value["representation_state"] == "complete"
        assert outcome["status"] == "partial" and outcome["record_refs"] == [source["id"]]
        assert outcome["result"] == provider.failed_provider_receipt("molecular_provider_" + code,
            source_ref=source["id"])


@pytest.mark.parametrize("operation", OPERATIONS)
def test_legacy_import_and_actual_toolop_writer_keep_rich_cache_literal_without_new_value(
        tmp_path, monkeypatch, operation):
    """Engineered legacy publication through original owners, not runtime history."""
    client = ControlledClients()
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        capture = client.molecular_provider_request(operation=operation, arguments=arguments)
        key = "engineered-legacy-provider-publication"
        token = tools._publications.set([])
        try:
            with store.transaction():
                value, references = tools._import(operation, arguments, capture)
                outcome = dict(status="completed", operation_ref=identity("operation", {
                    "key": key, "name": operation, "arguments": arguments}),
                    record_refs=references, changed_record_refs=references, result=value, feedback=None)
                tools._save(key, operation, arguments, scope, outcome)
        finally:
            tools._publications.reset(token)
        assert provider.validate_provider_result(value) == value
        assert value["version"] == "molecular_provider_result_v1"
        source = store.get(value["source_ref"])
        assert references == [source["id"]] and not source.get("auxiliary_artifact_refs")
        assert value["raw_artifact_ref"] == source["artifact_ref"]
        assert store.get_artifact(source["artifact_ref"]) == capture.content
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "molecular_provider_request", forbidden)
        monkeypatch.setattr(provider, "publish_molecular_provider_request", forbidden)
        monkeypatch.setattr(provider, "provider_value", forbidden)
        monkeypatch.setattr(provider, "provider_result", forbidden)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        assert tools.execute(operation, arguments, scope=scope, operation_key=key) == outcome
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files


@pytest.mark.parametrize("operation", OPERATIONS)
def test_same_scope_unreceived_context_denies_native_file_source_body_and_private_controls_before_bytes(
        tmp_path, monkeypatch, operation):
    client = ControlledClients()
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        scope, arguments = _scope(store), deepcopy(ARGUMENTS[operation])
        owner = Workflow(store, tools, ScriptedProvider([action(operation, arguments)]),
            tmp_path / "producer", "provider-current-owner", _controller, _credit,
            project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
            initial_known_record_refs=[])
        root = owner.build("improvement", "root", "Evaluate supplied protein evidence without assuming a conclusion.", scope)
        record = asyncio.run(root.run_async(owner.context))
        asyncio.run(root.build_result(record))
        outcome = json.loads(store.db.execute("SELECT result FROM tool_operations").fetchone()[0])
        source = store.get(outcome["result"]["source_ref"])
        other = Workflow(store, tools, ScriptedProvider([]), tmp_path / "unreceived", "provider-unreceived-owner",
            _controller, _credit, project_child_credit=_credit, root_role="improvement",
            episode_record_receipts=True, initial_known_record_refs=[])
        receiver = other.build("improvement", "root", "Evaluate the same supplied protein with existing receipts only.", scope)
        context = other.binding_context(receiver.source)
        known = set(other.receipts.known(context.episode_id))
        assert {source["id"], source["artifact_ref"]}.isdisjoint(known)
        monkeypatch.setattr(Store, "get_artifact", forbidden)
        monkeypatch.setattr("gene_annotation_episode.molecular_sequence_input_bindings.retained_native_file", forbidden)
        resolve = other.resolver(plain(context.scope), context=context)
        for reference, namespace in ((source["id"], "source"), (source["artifact_ref"], "artifact"),
                (source["request_ref"], "artifact"), *[(ref, "artifact") for ref in source["auxiliary_artifact_refs"]]):
            assert resolve(reference, namespace) is False
            assert tools.retained_molecular_reference_access(context, reference, namespace) is False
            item, path = other.services.read_received_molecular_input(context, reference, namespace, file_format="text")
            assert item["input"] is None and item["failure"] is not None and path is None
        read_args = dict(source_ref=source["id"], representation="original", offset=0, limit=32768)
        with tools.current_invocation(context, read_received=other.services.read_received_molecular_input,
                tool_name="source.read", arguments=read_args, operation_key="unreceived-provider-metadata-probe"):
            with pytest.raises(ContractError, match=operation.split(".")[1] + "_source_primary_body_not_received"):
                tools._check_molecular_source_bytes("source.read", read_args)
        assert set(other.receipts.known(context.episode_id)) == known
        assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE episode_id=?", (context.episode_id,)).fetchone()[0] == 0


@pytest.mark.parametrize("cid", [True, False, 0, -1, 2244.0, "2244", None])
def test_pubchem_registry_rejects_nonliteral_cid_before_any_transport_or_source(tmp_path, cid):
    operation, client = "public.pubchem.compound", ControlledClients()
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        arguments = {**ARGUMENTS[operation], "cid": cid}
        scope = _scope(store)
        before = {source["id"] for source in store.list("source")}
        outcome = tools.execute(operation, arguments, scope=scope, operation_key="invalid-pubchem-cid")
        assert outcome["status"] == "invalid" and outcome["record_refs"] == []
        assert outcome["result"] == provider.failed_provider_receipt("invalid_tool_input")
        assert client.calls == [] and client.captures == []
        assert {source["id"] for source in store.list("source")} == before


def test_pubchem_provenance_preserves_tuple_headers_through_json_storage(tmp_path):
    """Engineering regression for the original560 verification comparison."""
    class TupleHeaderClients(ControlledClients):
        def _http(self, *args, **kwargs):
            capture = super()._http(*args, **kwargs)
            capture.transport["header_items"] = [tuple(pair) for pair in capture.transport["header_items"]]
            return capture
    operation, client = "public.pubchem.compound", TupleHeaderClients()
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        arguments = deepcopy(ARGUMENTS[operation])
        outcome = tools.execute(operation, arguments, scope=_scope(store), operation_key="tuple-header-provenance")
        assert outcome["status"] == "completed" and len(client.calls) == 1
        value, source = _assert_retained_source(store, outcome, client, operation, arguments)
        assert value["issues"] == []
        actual = json.loads(store.get_artifact(source["request_ref"]))
        assert all(type(pair) is tuple for pair in client.captures[0].transport["header_items"])
        assert all(type(pair) is list for pair in actual["transport"]["header_items"])
