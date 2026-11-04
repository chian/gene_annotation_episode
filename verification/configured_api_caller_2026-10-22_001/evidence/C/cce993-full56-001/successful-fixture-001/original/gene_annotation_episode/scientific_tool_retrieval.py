"""One durable information-retrieval tool call against the actual callable map.

This is neither an episode nor an action selector. The parent receives tool
contracts and still commissions its own child. Model audit and this operation's
cache are separate from scientific records, receipts and controller history.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
import inspect
import json
import uuid

from jsonschema import Draft202012Validator, ValidationError
from method_loop.durable import canonical, content_digest

from .boundary_validation import ModelOutputError, schema_failure_diagnostic
from .domain import identity
from .scientific_tool_library import tool_names


VERSION = "scientific_tool_retrieval_v1"
SEMANTIC = "semantic_fast_v1"
LITERAL = "literal_test_v1"
INSTRUCTIONS = """Retrieve actual callable tools for the parent's desired investigation.
Return only {"tools":[actual callable names]} under the supplied schema. Inspect
the complete supplied map: names, descriptions and exact input contracts. Select
all operations useful for carrying out this investigation with the available
capabilities, including prerequisites and reading/checking their real results.
Keep the set relevant to this investigation. Do not select an operation merely
because its description shares a word. Source/data reading can be useful, but a
scientific data question does not itself request an unrelated publication search
or literature-reading investigation. There is no fixed group or selection quota.
Do not invent tools, capabilities, tool arguments or replacements for an absent
operation. When a specialized capability is absent, select only actually useful
available operations; an empty selection is permitted. This retrieval supplies
information: do no scientific work, choose no hypothesis, job, resource, action,
child episode or timer, and return no findings, plan or scientific judgment.
"""


def configuration(value):
    """Validate explicit caller opt-in; None preserves the existing v3 binding."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("scientific_tool_retrieval_configuration_invalid")
    value = json.loads(canonical(value))
    expected = {"version", "mode"}
    if value.get("mode") == SEMANTIC:
        expected.add("model")
        model = value.get("model")
        if (not isinstance(model, dict) or set(model) != {"model", "reasoning_effort"}
                or any(not isinstance(item, str) or not item for item in model.values())):
            raise ValueError("scientific_tool_retrieval_configuration_invalid")
    if (set(value) != expected or value.get("version") != VERSION
            or value.get("mode") not in {SEMANTIC, LITERAL}):
        raise ValueError("scientific_tool_retrieval_configuration_invalid")
    return value


def output_schema(names, *, transport=False):
    """The map supplies the enum; uniqueness is additionally checked on return."""
    names = tool_names(list(names))
    selected = {"type": "array", "items": {"type": "string"}}
    if names:
        selected["items"]["enum"] = names
    else:
        # JSON Schema forbids an empty enum. An empty map has no valid names.
        selected["maxItems"] = 0
    if not transport:
        selected["uniqueItems"] = True
    return {"type": "object", "properties": {"tools": selected},
        "required": ["tools"], "additionalProperties": False}


def _outcome(status, operation_ref, *, result=None, code=None, detail=None):
    return {"status": status, "operation_ref": operation_ref, "record_refs": [],
        "changed_record_refs": [], "result": result,
        "feedback": None if code is None else {"category": "tool_retrieval", "code": code,
            **({"detail": detail} if detail is not None else {})}}


class ScientificToolRetriever:
    """Cache one selected ordinary operation; never take over an unfinished one."""

    def __init__(self, store, *, run_id, provider, library, configuration):
        self.store, self.run_id, self.provider, self.library = store, run_id, provider, library
        self.configuration = globals()["configuration"](configuration)
        if self.configuration is None or self.configuration["mode"] != SEMANTIC:
            raise ValueError("semantic_tool_retrieval_configuration_required")
        with store.transaction():
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_tool_retrievals (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                request_sha256 TEXT NOT NULL, request TEXT NOT NULL, dispatch_token TEXT NOT NULL,
                response TEXT, result TEXT,
                PRIMARY KEY(run_id,episode_id,operation_key))""")

    def _publish(self, key, digest, token, response, result):
        # A competing reader cannot replace an active writer's request or
        # response. Only the claimant can terminally publish this operation.
        with self.store.transaction():
            changed = self.store.db.execute("""UPDATE runtime_tool_retrievals
                SET response=?,result=? WHERE run_id=? AND episode_id=? AND operation_key=?
                AND request_sha256=? AND dispatch_token=? AND result IS NULL""",
                (None if response is None else canonical(response), canonical(result),
                    *key, digest, token)).rowcount
            if changed != 1:
                raise ValueError("scientific_tool_retrieval_publication_conflict")

    async def retrieve(self, investigation, *, episode_id, operation_key, available_catalog):
        operation_ref = identity("operation", {"key": operation_key,
            "name": "process.tools", "arguments": {"investigation": investigation}})
        if (not isinstance(investigation, str) or not investigation.strip()
                or not isinstance(episode_id, str) or not episode_id
                or not isinstance(operation_key, str) or not operation_key):
            return _outcome("invalid", operation_ref, code="scientific_tool_retrieval_input_invalid")
        catalog = self.library.catalog()
        names = [entry["name"] for entry in catalog]
        self.library.resolve(names, available_catalog)
        schema = output_schema(names)
        context = {"investigation": investigation, "catalog": catalog}
        call_id = "scientific_tool_retrieval_" + content_digest({
            "run_id": self.run_id, "episode_id": episode_id, "operation_key": operation_key})[:32]
        request = {"version": "scientific_tool_retrieval_request_v1",
            "owner": {"run_id": self.run_id, "episode_id": episode_id,
                "operation_key": operation_key}, "configuration": self.configuration,
            "library": self.library.as_record(), "call_identity": call_id,
            "role": "FAST", "instructions": INSTRUCTIONS, "context": context,
            "selection_schema": schema, "output_schema": output_schema(names, transport=True)}
        serialized, digest = canonical(request), content_digest(request)
        key, token = (self.run_id, episode_id, operation_key), uuid.uuid4().hex
        with self.store.transaction():
            old = self.store.db.execute("SELECT * FROM runtime_tool_retrievals WHERE "
                "run_id=? AND episode_id=? AND operation_key=?", key).fetchone()
            if old is not None:
                if old["request_sha256"] != digest or old["request"] != serialized:
                    return _outcome("invalid", operation_ref,
                        code="scientific_tool_retrieval_request_conflict")
                if old["result"] is not None:
                    return json.loads(old["result"])
                # Do not infer that an active writer is dead or overwrite it.
                # Recovery also cannot tell whether an unrecorded response
                # existed, so it returns this same explicit ambiguity.
                return _outcome("failed", operation_ref,
                    code="scientific_tool_retrieval_result_ambiguous")
            self.store.db.execute("INSERT INTO runtime_tool_retrievals VALUES(?,?,?,?,?,?,NULL,NULL)",
                (*key, digest, serialized, token))
        if not names:
            result = _outcome("completed", operation_ref,
                result={"investigation": investigation, "tools": [], "catalog": []})
            self._publish(key, digest, token, None, result)
            return result
        response = None
        try:
            try:
                roles = getattr(self.provider, "roles", {})
                actual = roles.get("FAST")
                actual = ({"model": actual.model, "reasoning_effort": actual.reasoning_effort}
                          if actual is not None and hasattr(actual, "model") else actual)
                if actual != self.configuration["model"]:
                    result = _outcome("unavailable", operation_ref,
                        code="scientific_tool_retrieval_model_binding_mismatch")
                elif not callable(getattr(self.provider, "release", None)):
                    result = _outcome("unavailable", operation_ref,
                        code="scientific_tool_retrieval_provider_release_required")
                else:
                    response = await self.provider.complete(call_id, "FAST", INSTRUCTIONS,
                        deepcopy(context), deepcopy(request["output_schema"]))
                    response = json.loads(canonical(response))
                    Draft202012Validator(schema).validate(response)
                    selected = tool_names(response["tools"])
                    result = _outcome("completed", operation_ref, result={
                        "investigation": investigation, "tools": selected,
                        "catalog": self.library.resolve(selected, available_catalog)})
            except ValidationError as error:
                result = _outcome("invalid", operation_ref,
                    code="scientific_tool_retrieval_output_invalid",
                    detail=schema_failure_diagnostic(error))
            except ModelOutputError as error:
                response = {"raw_response": error.raw_response}
                result = _outcome("invalid", operation_ref,
                    code="scientific_tool_retrieval_output_unparseable",
                    detail=error.diagnostic)
            except ValueError as error:
                # A non-JSON provider value cannot be canonicalized. The
                # provider's transport audit retains its raw representation.
                response = None
                result = _outcome("invalid", operation_ref,
                    code="scientific_tool_retrieval_output_invalid",
                    detail={"exception_type": type(error).__name__})
            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                self._publish(key, digest, token, response, _outcome("failed", operation_ref,
                    code="scientific_tool_retrieval_interrupted"))
                raise
            except Exception as error:
                result = _outcome("failed", operation_ref,
                    code="scientific_tool_retrieval_call_failed",
                    detail={"exception_type": type(error).__name__})
            self._publish(key, digest, token, response, result)
            return result
        finally:
            release = getattr(self.provider, "release", None)
            if callable(release):
                released = release(call_id)
                if inspect.isawaitable(released):
                    await released


__all__ = ["ScientificToolRetriever", "configuration", "output_schema", "VERSION",
    "SEMANTIC", "LITERAL"]
