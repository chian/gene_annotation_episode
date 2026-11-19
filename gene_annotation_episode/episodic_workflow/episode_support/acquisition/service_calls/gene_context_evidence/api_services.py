"""Concrete single-request API primitives used by the common API episode.

These implementations supply operations, not episode decisions or polling loops.
The owning episode retains intents, responses, native handles and typed returns.
"""
from __future__ import annotations

from copy import deepcopy
import json

from jsonschema import Draft202012Validator



def object_schema(properties, required=()):
    return {"type": "object", "properties": properties,
            "required": list(required), "additionalProperties": False}


def validate_value(value, schema, code):
    """Validate a JSON value without inserting defaults or changing operands."""
    try:
        value = json.loads(json.dumps(value, allow_nan=False))
        Draft202012Validator(schema).validate(value)
    except Exception as error:
        raise ValueError(code) from error
    return value


def event(kind, state, *, native_handle=None, handoff_ready=False,
          result_available=False, facts=None, failure_code=None):
    return {"kind": kind, "state": state, "native_handle": native_handle,
            "handoff_ready": bool(handoff_ready), "result_available": bool(result_available),
            "facts": dict(facts or {}), "failure_code": failure_code}


def validate_service_configuration(service, configuration):
    if service == "bvbrc_appservice":
        from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.gene_context_evidence.bvbrc_appservice_contracts import validate_contract
        return validate_contract("ServiceConfiguration", configuration)
    if service not in {"uniprot", "bvbrc_data", "ncbi_blast", "bvbrc_minhash"}:
        raise ValueError("api_service_unknown")
    if not isinstance(configuration, dict):
        raise ValueError("api_service_configuration_invalid")
    allowed = {"kind", "service"}
    if service == "bvbrc_data":
        allowed |= {"base_url"}
    if service == "bvbrc_minhash":
        allowed |= {"endpoint", "authorization_env", "authorization_origins"}
    if (set(configuration) - allowed or configuration.get("kind", "api") != "api"
            or configuration.get("service", service) != service):
        raise ValueError("api_service_configuration_invalid")
    return deepcopy(configuration)


def build_service(service, configuration, tool_registry, *, publication_callback=None):
    """One configured API service. Only a BV-BRC AppService service takes a ``publication_callback`` (the
    results binding's AppService publication); without one its ``publish`` raises ``appservice_publication_unbound``."""
    configuration = validate_service_configuration(service, configuration)
    if service == "bvbrc_appservice":
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.gene_context_evidence.api_bvbrc_appservice import BVBRCAppServiceService
        return BVBRCAppServiceService(tool_registry, configuration=configuration,
                                      publication_callback=publication_callback)
    if publication_callback is not None:
        raise ValueError("api_service_publication_callback_is_for_bvbrc_appservice_only")
    if service == "uniprot":
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.api_uniprot import UniProtService
        return UniProtService(tool_registry, configuration=configuration)
    if service == "ncbi_blast":
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.gene_context_evidence.api_blast import NCBIBlastService
        return NCBIBlastService(tool_registry, configuration=configuration)
    if service == "bvbrc_minhash":
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.api_bvbrc_minhash import BVBRCMinhashService
        return BVBRCMinhashService(tool_registry, configuration=configuration)
    from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_bvbrc import BVBRCDataService
    return BVBRCDataService(tool_registry, configuration=configuration)


def publish_existing_acquisition(tools, name, arguments, snapshot, scope, operation_key, *,
                                 publisher=None):
    """Publish a retained response without acquiring it a second time.

    This uses the existing tool publication receipt; no service-specific database
    or new action is introduced. The outer episode journals the selected result.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical, identity

    publication_name = "internal.api_service." + name
    operands = {"arguments": arguments, "snapshot_sha256": snapshot.sha256,
                "request": snapshot.request, "transport": snapshot.transport}
    saved = tools.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
                                   (operation_key,)).fetchone()
    if saved is not None:
        if (saved["name"] != publication_name or saved["arguments"] != canonical(operands)
                or saved["scope"] != canonical(scope)):
            raise ContractError("operation_key_reused_for_different_work")
        return json.loads(saved["result"])
    tools.store.validate_scope(scope)
    token = tools._publications.set([])
    grading_failures = tools._grading_failures.set([])
    try:
        outcome = {"status": "completed", "operation_ref": identity("operation", {
            "key": operation_key, "name": publication_name, "arguments": operands}),
            "record_refs": [], "changed_record_refs": [], "result": None, "feedback": None}
        with tools.store.transaction():
            try:
                outcome["result"], outcome["record_refs"] = (publisher() if publisher is not None
                    else tools._import(name, arguments, snapshot))
                if outcome["result"].get("projection_errors"):
                    outcome.update(status="partial", feedback={"category": "representation",
                        "code": "api_result_rows_partially_projected",
                        "source_ref": outcome["result"]["source_ref"],
                        "rows": outcome["result"]["projection_errors"]})
            except Exception as error:
                retained = list(dict.fromkeys(tools._written))
                if not retained:
                    raise
                sources = [ref for ref in retained if tools.store.get(ref)["record_type"] == "source"]
                outcome.update(status="partial", record_refs=retained,
                    result={"source_ref": sources[0] if sources else None,
                            "retained_record_refs": retained},
                    feedback={"category": "partial_execution", "code": "api_result_partially_projected",
                              "exception_type": type(error).__name__, "message": str(error),
                              "diagnostic_ref": tools.store.artifact(
                                  f"{type(error).__name__}: {error}", "text/plain")})
            outcome["changed_record_refs"] = list(outcome["record_refs"])
            tools._save(operation_key, publication_name, operands, scope, outcome)
        return outcome
    finally:
        tools._grading_failures.reset(grading_failures)
        tools._publications.reset(token)
