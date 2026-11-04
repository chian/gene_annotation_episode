"""Journal-backed BV-BRC host fixture with controlled native response bytes.

This supplies selected actions and actual structural episode identities. The
production API executor creates all handoffs, results, sheets and receipts;
the fixture never constructs a QualifiedResult or installs qualification flags.
It does not run Workflow, a model, a service request or a scientific experiment.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json

from method_loop import EpisodeGoal, EpisodeRequest
from method_loop.communication import ReportContract
from method_loop.identities import EpisodeRef

from gene_annotation_episode.api_bvbrc import DATA_QUERY_OPERATION, DATA_RESULT_OPERATION
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import Record
from gene_annotation_episode.tools import ToolRegistry

from test_api_bvbrc_data_v2 import envelope, request, selector, snapshot


def fact_form(*sources):
    fields = {"facts_" + str(i): deepcopy(bvbrc_data_fact_sources()[source]["report_schema"])
              for i, source in enumerate(sources)}
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


class HostFixture:
    def __init__(self, store, directory, monkeypatch, *, run_id="bvbrc-host-recovery"):
        self.store, self.directory, self.run_id = store, directory, run_id
        subject, = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]
        self.scope = {"subject_refs": [subject]}
        self.journal = Journal(store, run_id)
        self.configuration = {"bvbrc": {"kind": "api", "service": "bvbrc_data"}}
        self.api = self.reopen()
        self.goals = {}
        self.next_child = {}
        self.calls, self.responses = [], []

        def query_prepared(client, prepared):
            if not self.responses:
                raise AssertionError("Unselected BV-BRC GET in host fixture")
            body = self.responses.pop(0)
            self.calls.append(deepcopy(prepared))
            return snapshot(prepared, body)

        monkeypatch.setattr("gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared", query_prepared)
        self.parent = self.context("annotation", {}, path=(("annotation", "root"),))

    def reopen(self):
        return APIServiceExecution(self.store, run_id=self.run_id, directory=self.directory,
            configuration=self.configuration, tool_registry=ToolRegistry(self.store),
            handoff_unit=3, acquired_record_unit=2)

    def context(self, role, assignment, *, parent=None, path=None, schema=None, scope=None):
        scope = deepcopy(self.scope if scope is None else scope)
        schema = schema or fact_form("execution_bvbrc_pages")
        contract = None if parent is None else ReportContract(
            decision="Return the requested retained source measurements and availability",
            measurements={"schema": schema},
            information={key: value.get("description", key) for key, value in schema["properties"].items()})
        if parent is None:
            path = path or ((role, "root"),)
            goal = EpisodeGoal.root(objective="Verify explicit BV-BRC result custody", result_contract={"role": role})
        else:
            index = self.next_child.get(parent.episode_id, 0)
            self.next_child[parent.episode_id] = index + 1
            path = (*parent.path, (role, "child_" + str(index)))
            goal = EpisodeGoal.child(self.goals[parent.episode_id],
                objective="Acquire this selected BV-BRC result with its original inputs", result_contract=schema)
            self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
                "action": canonical({"kind": "episode_child", "role": role,
                    "goal": goal.objective, "purpose": contract.decision, "scope": scope,
                    "assignment": assignment, "schema_json": json.dumps(schema), "initial_report_json": "{}"}),
                "result": None, "credit": None})
        identity = EpisodeRef(self.run_id, path)
        message = {"scope": scope, "initial_report": {}, "episode_assignment": deepcopy(assignment)}
        record = plain(EpisodeRequest(goal, Record(message), contract).as_record())
        value = BindingContext(self.run_id, identity.episode_id, role, path, scope, assignment, record)
        self.goals[value.episode_id] = goal
        self.journal.save("runtime_episodes", {"episode_id": value.episode_id,
            "path": canonical(path), "request": canonical(record), "initial_credit": 0, "state": "active"})
        return value

    def select(self, context, name, *, index=0):
        self.journal.save("runtime_actions", {"episode_id": context.episode_id,
            "decision_index": index, "action": canonical({"kind": "tool", "tool": name, "arguments": {}}),
            "result": None, "credit": None})
        return f"{self.run_id}:{context.episode_id}:{index}"

    def execute(self, context, name, *, index=0, select=True):
        key = self.select(context, name, index=index) if select else f"{self.run_id}:{context.episode_id}:{index}"
        outcome = asyncio.run(self.api.execute(context, name, {}, key))
        self.journal.save("runtime_actions", {"episode_id": context.episode_id,
            "decision_index": index,
            "action": self.journal.row("runtime_actions", context.episode_id, index)["action"],
            "result": canonical(outcome)})
        return outcome

    def launch(self, query=None, *, body=None, parent=None):
        query = request("genome", fields=["genome_id", "genome_length"]) if query is None else query
        body = envelope([{"genome_id": "g", "genome_length": 12}]) if body is None else body
        context = self.launch_context(query, parent=parent)
        self.responses.append(body)
        outcome = self.execute(context, DATA_QUERY_OPERATION)
        assert outcome["status"] == "completed", outcome
        return context, outcome["result"]["handoff_ref"]

    def launch_context(self, query, *, parent=None):
        assignment = {"version": "api_service_assignment_v1", "resource_id": "bvbrc",
            "service": "bvbrc_data", "request": query, "endpoint": "usable_handoff", "constraints": {}}
        schema = {"type": "object", "properties": {"references": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "execution_handoff"},
            "x-source": "execution_handoff_refs"}}, "required": ["references"], "additionalProperties": False}
        launch = self.context("launch", {"version": "execution_launch_assignment_v1",
            "requests": {"bvbrc": assignment}, "immutable_input_versions": [], "constraints": {}},
            parent=parent or self.parent, schema=schema)
        return self.context("launch_api", assignment, parent=launch, schema=schema)

    def results_context(self, handoff, selection=None, *, parent=None, sources=("execution_bvbrc_pages",)):
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": handoff,
                      "selector": selector() if selection is None else selection}
        return self.context("results", assignment, parent=parent or self.parent, schema=fact_form(*sources))

    def acquire(self, query=None, selection=None, *, body=None, parent=None, sources=("execution_bvbrc_pages",)):
        _, handoff = self.launch(query, body=body, parent=parent)
        context = self.results_context(handoff, selection, parent=parent, sources=sources)
        outcome = self.execute(context, DATA_RESULT_OPERATION)
        assert outcome["status"] in {"completed", "partial"}, outcome
        return context, outcome

    def directory_for(self, context, index=0):
        key = f"{self.run_id}:{context.episode_id}:{index}"
        return self.api._episode_directory(context.episode_id) / "actions" / digest(key)

    def record_return(self, child, *, parent=None):
        parent = self.parent if parent is None else parent
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        facts = self.api.facts(child, {})
        form = {name: facts[node["x-source"]] for name, node in schema["properties"].items()}
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24],
            "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(form), "failure": None})
        return form, schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form"

    def admit(self, child, *, parent=None):
        parent = self.parent if parent is None else parent
        form, schema, key = self.record_return(child, parent=parent)
        return self.api.record_bvbrc_admission(parent, form, schema, key)

