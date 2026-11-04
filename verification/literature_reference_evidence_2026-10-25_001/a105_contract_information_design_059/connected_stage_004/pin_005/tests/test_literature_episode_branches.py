"""Scripted literature choices over actual source tools and ordinary Episodes.

The article, provider and controller are synthetic. These tests establish
source custody, iterative decisions and controlled scientific delivery; they
make no live-model, detached-process or YbhP biological claim.
"""
import asyncio
from collections import defaultdict
from copy import deepcopy
import json

import pytest

from method_loop import ChildEpisodeUnit, Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress, project_finding_progress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, ROLES
from gene_annotation_episode.runtime import Record, TypedReportContract, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_hypervolume_runtime import annotation, assessment
from test_spreadsheet_tools import workbook


ARTICLE = ("<article><front><article-meta><article-id pub-id-type='pmcid'>PMC123</article-id>"
    "</article-meta></front><body><sec><title>Assay α</title>"
    "<p>ConstructX grows; target activity is unresolved.</p>"
    "<table-wrap><label>Table α</label><table><tr><th>Construct</th><th>Condition</th>"
    "<th>Outcome</th></tr><tr><td>ConstructX</td><td>glucose at 30 °C</td><td>growth</td>"
    "</tr></table><table-wrap-foot>ConstructX is an overexpression construct; target activity "
    "was not measured.</table-wrap-foot></table-wrap></sec></body></article>").encode()
TABLE_START = ARTICLE.index(b"<table-wrap>")
TABLE_END = ARTICLE.index(b"</table-wrap>") + len(b"</table-wrap>")


class SavedLiterature:
    """Deterministic provider responses; no network access."""
    def __init__(self):
        self.searches, self.reads = [], []
        self.body = ARTICLE

    def literature_search(self, query, **kwargs):
        self.searches.append(query)
        return SourceSnapshot("europepmc", "https://example.invalid/synthetic-search",
            {"query": query, **kwargs}, "2026-10-21T00:00:00+00:00",
            json.dumps({"results": [] if query == "unproductive literal" else [{"pmcid": "PMC123"}]}).encode(),
            "application/json", {"representation": "synthetic_no_network"})

    def literature_read(self, pmcid):
        self.reads.append(pmcid)
        return SourceSnapshot("europepmc", "https://example.invalid/synthetic-article",
            {"pmcid": pmcid}, "2026-10-21T00:00:00+00:00", self.body,
            "application/xml", {"representation": "synthetic_no_network"})


class LiteratureServices:
    """C7 ports backed by real ToolRegistry, Store and semantic receipts."""
    def __init__(self, store, tools):
        self.store, self.tools = store, tools
        self.receipts = EpisodeReceipts(store, "literature-fixture")
        self.outcomes = defaultdict(list)
        self.credit_calls = []

    def tool_catalog(self, scope):
        return [{"name": name, **definition} for name, definition in self.tools.catalog(plain(scope)).items()]

    async def execute_tool(self, name, arguments, *, scope, operation_key):
        return await self.tools.execute_async(name, arguments, scope=plain(scope), operation_key=operation_key)

    def read_record(self, reference):
        return self.store.get(reference)

    def reference_in_scope(self, reference, scope, namespace):
        if not self.store.reference_subset([reference], plain(scope)):
            return False
        kind = self.store.get(reference)["record_type"]
        return namespace is None or kind == namespace or namespace == "subject" and kind in {
            "input", "feature", "product", "read_subject"}

    def scientific_credit(self, context, receiver_selection):
        self.credit_calls.append((context, receiver_selection))
        known = (ref for ref in receiver_selection["known_record_refs"]
                 if self.store.get(ref)["record_type"] == "assessment")
        return project_finding_progress(self.store, plain(context.scope), FindingProgressPolicy(1),
                                        known_assessment_refs=known)

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        rows = [row for row in self.outcomes[episode_id]
                if tools is None or row["selected_tool"] in tools]
        return {"records": deepcopy(rows[offset:offset + limit]), "offset": offset, "limit": limit,
                "next_offset": offset + limit if len(rows) > offset + limit else None}


def page(source, *, representation="original"):
    return {"version": "page_assignment_v1", "source_ref": source["id"],
        "representation": representation,
        "artifact_ref": source["text_ref"] if representation == "text" and source.get("text_ref") else source["artifact_ref"],
        "question_context_refs": [], "prior_delivery_refs": []}


def context(scope, role, assignment):
    return BindingContext("literature-fixture", "episode_fixture", role, ((role, "fixture"),),
                          scope, assignment, {})


ASSESSMENT_FORM = obj({"assessments": {"type": "array", "x-source": "changed_assessment_refs",
    "items": {"type": "string", "format": "reference", "x-reference-namespace": "assessment"}}})


class OrdinaryLiteratureConsumer:
    """A C7 consumer fixture, using the same ordinary shared loop at every level.

    The source's choose callback is the scripted model boundary. It receives
    the previous actual outcome and admitted child forms on each invocation.
    This helper can also supply fixtures to the application's composition tests.
    """
    def __init__(self, services, binding, scope, choose, action_counts):
        self.services, self.binding, self.scope = services, binding, scope
        self.choose, self.action_counts = choose, action_counts
        self.controllers, self.sources, self.decisions = {}, {}, []

        def controller(path):
            value = FixtureController(str(path), 0, action_counts[path[-1][0]])
            self.controllers[path] = value
            return value
        self.grains = {role: Grain(role, "Selected scientific work", "Received scientific progress", controller)
                       for role in binding.roles}
        self.loop_context = Context(tree=EpisodeTree(self.grains["literature"], {
            self.grains[role]: tuple(self.grains[child] for child in binding.child_roles(role))
            for role in binding.roles}), run_id="literature-fixture")

    def build(self, role, key, assignment, *, parent=None, parent_path=(), contract=None):
        grain = self.grains[role]
        goal = (EpisodeGoal.root(objective="Investigate the synthetic source's applicability", result_contract={})
                if parent is None else EpisodeGoal.child(parent, objective="Resolve the assigned narrower uncertainty",
                                                         result_contract=contract.schema))
        path = (*parent_path, (role, key))
        identity = Episode.identity(self.loop_context, grain, key, parent_path=parent_path)
        parent_id = self.sources[parent_path].binding_context.episode_id if parent_path else None
        self.services.receipts.bind(identity.episode_id, parent_id)
        request = EpisodeRequest(goal, Record({"assignment": assignment}), contract)
        bound = BindingContext("literature-fixture", identity.episode_id, role, path,
                               self.scope, assignment, request.as_record())
        consumer = self

        class Source:
            binding_context = bound
            last_result = None

            def __init__(self):
                self.changed = []

            def credit(self):
                selection = {"episode_id": bound.episode_id,
                    "known_record_refs": consumer.services.receipts.known(bound.episode_id),
                    "initial_known_record_refs": consumer.services.receipts.known(bound.episode_id, baseline=True)}
                return Record({"credit": consumer.binding.credit_view(bound, selection)["credit"]})

            def record(self, selection, result, index, *, child=False):
                self.last_result = result
                refs = result.get("record_refs", [])
                consumer.services.receipts.receive(bound.episode_id, refs,
                    kind="child_form" if child else "own_action", source_index=index)
                self.changed.extend(ref for ref in result.get("changed_record_refs", []) if ref not in self.changed)
                consumer.services.outcomes[bound.episode_id].append({"decision_index": index,
                    "selected_tool": selection.get("tool"), "status": result["status"],
                    "record_refs": refs, "changed_record_refs": result.get("changed_record_refs", []),
                    "result_ref": result.get("operation_ref")})
                return self.credit()

            def next(self, view):
                inputs = view.model_inputs({**consumer.binding.decision_context(bound, view),
                    "last_local_outcome": self.last_result}, reports=view.child_reports)
                consumer.decisions.append((role, view.units_consumed, inputs))
                selection = consumer.choose(role, view.units_consumed, inputs)
                index = view.units_consumed
                if selection["kind"] == "child":
                    child_role = selection["role"]
                    assert child_role in consumer.binding.allowed_children(bound, ())
                    selected = consumer.binding.prepare_assignment(bound, child_role,
                        selection["assignment"], consumer.scope, f"{bound.episode_id}:{index}")
                    child_contract = TypedReportContract("Return the actual source-linked assessment references",
                        ASSESSMENT_FORM, lambda ref, namespace: consumer.services.reference_in_scope(ref, consumer.scope, namespace))
                    child = consumer.build(child_role, "child_" + str(index), selected,
                        parent=goal, parent_path=path, contract=child_contract)

                    def receive(result, *_):
                        form = result.as_record()["form"]
                        child_bound = consumer.sources[child.source.binding_context.path].binding_context
                        consumer.binding.validate_report(child_bound, form, child_contract.schema)
                        refs = form["assessments"]
                        return self.record(selection, {"status": "completed", "record_refs": refs,
                            "changed_record_refs": refs}, index, child=True)
                    return ChildEpisodeUnit(child, receive, lambda result, *_: result.as_record()["form"])

                async def perform(_):
                    if selection["kind"] == "reason":
                        result = consumer.services.store.commit_reasoning(selection["commit"],
                            consumer.scope, f"{bound.episode_id}:{index}")
                        assert result["status"] == "completed", result
                    else:
                        result = await consumer.binding.execute(bound, selection["tool"], selection["arguments"],
                            f"{bound.episode_id}:{index}")
                    assert result["status"] in {"completed", "partial"}, result
                    return self.record(selection, result, index)
                return Leaf(None, perform, lambda _, value: value, label=selection["kind"])

            def finish(self, _):
                if contract is None:
                    return self.credit()
                changed = [ref for ref in self.changed if consumer.services.store.get(ref)["record_type"] == "assessment"]
                return Record({"form": form_with_facts({}, contract.schema, {"changed_assessment_refs": changed})})

        source = Source()
        self.sources[path] = source
        return Episode(grain, key, source, request, source.finish)


def reasoning_from_window(store, target, hypothesis, window):
    """Typed synthetic interpretation produced by the fixture's work call."""
    anchor = {key: window[key] for key in ("source_ref", "artifact_ref", "start", "end")}
    anchor["quote"] = window["text"]
    assert "ConstructX" in anchor["quote"] and "glucose at 30 °C" in anchor["quote"]
    payload = {name: [] for name in store.reasoning_schema()["required"]}
    payload["source_subjects"] = [{"alias": "construct", "reference_type": "construct",
        "source_ref": window["source_ref"], "label": "ConstructX", "anchor": anchor}]
    payload["contexts"] = [{"alias": "condition", "context_type": "assay_condition",
        "name": "glucose at 30 °C", "source_ref": window["source_ref"],
        "attributes": [], "related_refs": ["@construct"], "anchor": anchor}]
    payload["observations"] = [{"alias": "observed", "subject_refs": ["@construct"],
        "source_subject_refs": ["@construct"], "kind": "source_content", "source_ref": window["source_ref"],
        "measurements": [], "dependencies": ["@condition"], "anchor": anchor}]
    row = assessment(hypothesis, "@observed", "scope_limited", alias="qualified")
    row["condition_refs"] = ["@condition"]
    row["investigation_finding"] = {"source_claim": {"subject_refs": ["@construct"],
        "predicate": "growth_capability", "value": {"type": "enum", "value": "positive"},
        "context_refs": ["@condition"]}, "qualification": {"kind": "measurement_does_not_establish_claim",
        "context_refs": ["@condition"], "assumption_refs": []}, "status": "retained",
        "withdrawal_reason": "not_withdrawn", "same_source_claim_as_ref": None, "replaces_refs": []}
    payload["assessments"] = [row]
    return payload


@pytest.mark.parametrize("reading_role", ["literature_ordered", "literature_targeted", "literature_table"])
def test_nested_choices_revise_from_search_and_read_outcomes_and_return_typed_science(tmp_path, reading_role):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        hypothesis = store.put("hypothesis", {"subject_refs": [target], "predicate": "biological_role",
            "value": {"type": "enum", "value": "unresolved"}, "context_refs": []}, origin="reasoning")["id"]
        provider = SavedLiterature()
        services = LiteratureServices(store, ToolRegistry(store, clients=provider))
        binding = LiteratureEpisodes(services)
        observations = []

        def tool(name, args):
            return {"kind": "tool", "tool": name, "arguments": args}

        def child(role, assignment):
            return {"kind": "child", "role": role, "assignment": assignment}

        def choose(role, index, inputs):
            previous = inputs["last_local_outcome"]
            if role == "literature":
                if index == 0:
                    return child("literature_strategy", {"version": "strategy_assignment_v1",
                        "question_context_refs": [hypothesis], "prior_search_refs": []})
                returned, = inputs["child_reports"]
                assessed = store.get(returned["assessments"][0])
                assert assessed["investigation_finding"]["qualification"]["kind"] == "measurement_does_not_establish_claim"
                observations.append("parent retained uncertainty after receiving the source's construct/condition distinction")
                payload = {name: [] for name in store.reasoning_schema()["required"]}
                payload["annotation_updates"] = [annotation(target, hypothesis, returned["assessments"], 0, alias="parent")]
                return {"kind": "reason", "commit": payload}
            if role == "literature_strategy":
                if index == 0:
                    return tool("public.literature.search", {"query": "unproductive literal"})
                assert previous["result"]["provider_result"]["results"] == []
                return child("literature_search", {"version": "search_assignment_v1",
                    "question_context_refs": [hypothesis], "search_result_refs": [previous["result"]["source_ref"]]})
            if role == "literature_search":
                if index == 0:
                    assert inputs["literature_assignment"]["search_result_refs"]
                    return tool("public.literature.search", {"query": "ConstructX glucose experiment"})
                if index == 1:
                    record, = previous["result"]["provider_result"]["results"]
                    return tool("public.literature.read", {"pmcid": record["pmcid"]})
                return child("literature_page", page(store.get(previous["result"]["source_ref"]), representation="text"))
            if role == "literature_page":
                selected = inputs["literature_assignment"]
                if index == 0:
                    return tool("source.read", {"source_ref": selected["source_ref"], "representation": "text"})
                assert "glucose" not in previous["result"]["text"]
                observations.append("page chose original XML after paragraph projection omitted the table conditions")
                source = store.get(selected["source_ref"])
                window = {"source_ref": source["id"], "representation": "original", "offset": 0, "limit": 140}
                return child(reading_role, {"version": "reading_assignment_v1", "page": page(source),
                    "selection": {"spans": [window]} if reading_role == "literature_targeted" else window})
            selected = inputs["literature_assignment"]
            if index == 0:
                return tool("source.read", selected["selection"]["spans"][0]
                    if role == "literature_targeted" else selected["selection"])
            if index == 1:
                assert "glucose" not in previous["result"]["text"]
                return tool("source.read", {"source_ref": selected["page"]["source_ref"],
                    "representation": "original", "offset": TABLE_START, "limit": TABLE_END - TABLE_START})
            assert previous["result"]["start"] == TABLE_START
            return {"kind": "reason", "commit": reasoning_from_window(store, target, hypothesis, previous["result"])}

        consumer = OrdinaryLiteratureConsumer(services, binding, scope, choose,
            {"literature": 2, "literature_strategy": 2, "literature_search": 3,
             "literature_page": 2, reading_role: 3})
        root = consumer.build("literature", "root", {"version": "literature_assignment_v1",
            "question_context_refs": [hypothesis], "source_refs": []})
        result = asyncio.run(root.run_async(consumer.loop_context))
        assert result.units_consumed == 2 and result.controller_state.scores == [1, 0]
        assert provider.searches == ["unproductive literal", "ConstructX glucose experiment"]
        assert provider.reads == ["PMC123"] and len(observations) == 2
        assert sum(len(controller.scores) for controller in consumer.controllers.values()) == 12
        actual, = store.current_assessments()
        observed = store.get(actual["observation_ref"])
        source_subject = store.get(observed["source_subject_refs"][0])
        condition = store.get(actual["condition_refs"][0])
        assert source_subject["label"] == "ConstructX" and condition["name"] == "glucose at 30 °C"
        anchor = observed["anchor"]
        assert anchor["start"] == TABLE_START != len(ARTICLE[:TABLE_START].decode())
        assert ARTICLE[anchor["start"]:anchor["end"]] == anchor["quote"].encode()
        assert store.get_artifact(anchor["artifact_ref"]) == ARTICLE
        for source in consumer.sources.values():
            assert source.credit().as_record()["credit"] == 1
        parent, = store.current_annotations()
        assert parent["resolution"] == "unresolved"
        assert parent["coherent_sets"][0]["interpretations"][0]["assessment_refs"] == [actual["id"]]
        # Each nested investigation is one received parent action. No hidden
        # extraction/composer calls or navigation credit exist in this fixture.
        assert not store.list("product") and len(store.targets()) == 1


def test_closed_assignments_registration_and_original_form_guards(tmp_path):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        tools = ToolRegistry(store, clients=SavedLiterature())
        imported = tools.execute("public.literature.read", {"pmcid": "PMC123"})
        source = store.get(imported["result"]["source_ref"])
        binding = LiteratureEpisodes(LiteratureServices(store, tools))
        registry = EpisodeBindingRegistry((binding,))
        assert registry.roles == ROLES and registry.for_role("literature_targeted") is binding
        assert binding.entry_roles == ("literature",)
        assert binding.child_roles("literature_page") == ("literature_table", "literature_ordered", "literature_targeted")
        with pytest.raises(ValueError, match="duplicate_episode_role"):
            registry.register(binding)
        bound = context(scope, "literature_page", page(source))
        assert binding.credit_kind(bound.role) == "scientific"
        assert {"reason", "child", "wait"} <= set(binding.permitted_common_actions(bound))
        with pytest.raises(ContractError, match="representation_error"):
            binding.prepare_assignment(bound, "literature_ordered", {"version": "reading_assignment_v1",
                "page": page(source), "selection": {"source_ref": source["id"], "representation": "original",
                "offset": 0, "limit": 10}, "goal": "silently replace common ownership"}, scope, "selection")
        with pytest.raises(ReportBoundaryError, match="unavailable"):
            binding.validate_report(bound, {"observed": target}, obj({"observed": {"type": "string",
                "format": "reference", "x-reference-namespace": "observation"}}))
        with pytest.raises(ReportBoundaryError, match="semantic type"):
            binding.validate_report(bound, {"findings": "unrestricted prose"}, obj({"findings": {"type": "string"}}))
        assert binding.fact_sources(bound.role) == binding.facts(bound, {}) == {}
        assert "no stop rule" in binding.instructions(bound)


def test_source_versions_failed_reads_and_deliberate_rereads_preserve_actual_custody(tmp_path):
    async def exercise(store):
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        provider = SavedLiterature()
        tools = ToolRegistry(store, clients=provider)
        first = await tools.execute_async("public.literature.read", {"pmcid": "PMC123"}, operation_key="first")
        old = store.get(first["result"]["source_ref"])
        provider.body = ARTICLE.replace(b"<body>", b"\n<body>")
        second = await tools.execute_async("public.literature.read", {"pmcid": "PMC123"}, operation_key="second")
        new = store.get(second["result"]["source_ref"])
        services = LiteratureServices(store, tools)
        binding = LiteratureEpisodes(services)
        bound = context(scope, "literature_page", page(old))
        bad = {**page(old), "artifact_ref": new["artifact_ref"]}
        with pytest.raises(ContractError, match="source_artifact_mismatch"):
            binding.decision_context(context(scope, "literature_page", bad), None)
        wrong = await binding.execute(bound, "source.read", {"source_ref": new["id"]}, "wrong-version")
        assert wrong["status"] == "invalid" and wrong["feedback"]["code"] == "literature_reading_outside_assigned_source"
        unicode_start = ARTICLE.index("α".encode())
        failed = await binding.execute(bound, "source.read", {"source_ref": old["id"],
            "representation": "original", "offset": unicode_start + 1}, "failed-unicode")
        assert failed["status"] == "invalid" and failed["feedback"]["code"] == "source_offset_not_utf8_boundary"
        query = {"source_ref": old["id"], "representation": "original", "offset": unicode_start, "limit": 2}
        reads = [await binding.execute(bound, "source.read", query, key) for key in ("reread1", "reread2")]
        assert [row["result"]["text"] for row in reads] == ["α", "α"]
        assert all(row["result"]["artifact_ref"] == old["artifact_ref"] for row in reads)
        assert all(row["record_refs"] == [] for row in reads)
        assert not store.list("assessment") and not store.list("observation")
        assert provider.reads == ["PMC123", "PMC123"]
        assert not any(entry["name"].startswith("public.") for entry in binding.catalog(bound))
    with Store(tmp_path / "state") as store:
        asyncio.run(exercise(store))


def test_selected_native_table_rows_retain_headers_and_allow_iterative_reselection(tmp_path):
    async def exercise(store):
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        path, _ = workbook(tmp_path)
        material = store.register_material(path)
        source = store.get(material["source_ref"])
        tools = ToolRegistry(store)
        binding = LiteratureEpisodes(LiteratureServices(store, tools))
        selected = {"source_ref": source["id"], "sheet_key": "selected", "offset": 0,
            "limit": 1, "header_row": 1, "where": None}
        assignment = {"version": "reading_assignment_v1", "page": page(source), "selection": selected}
        bound = context(scope, "literature_table", assignment)
        assert binding.decision_context(bound, None)["literature_assignment"] == assignment
        first = await binding.execute(bound, "source.xlsx.rows", selected, "native-table-first")
        assert first["status"] == "completed", first
        next_selection = {**selected, "offset": 1, "limit": 2}
        second = await binding.execute(bound, "source.xlsx.rows", next_selection, "native-table-next")
        assert second["status"] == "completed", second
        assert first["result"]["header"]["row_number"] == second["result"]["header"]["row_number"] == 1
        row = second["result"]["rows"][0]
        assert row["row_number"] == 2 and row["cells"][0]["address"] == "A2"
        assert store.get(second["result"]["source_ref"])["parent_source_refs"] == [source["id"]]
        wrong = await binding.execute(bound, "source.xlsx.rows", {**selected, "sheet_key": "other"}, "wrong-sheet")
        assert wrong["status"] == "invalid" and wrong["feedback"]["code"] == "literature_table_sheet_mismatch"
        assert not store.list("assessment") and not store.current_annotations()
    with Store(tmp_path / "state") as store:
        asyncio.run(exercise(store))


def test_runtime_consumer_routes_literature_iteration_and_parent_uses_its_typed_return(tmp_path):
    """Application composition, with scripted decisions and real state/tools."""
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]
        scope = {"subject_refs": [target]}
        hypothesis = store.put("hypothesis", {"subject_refs": [target], "predicate": "biological_role",
            "value": {"type": "enum", "value": "unresolved"}, "context_refs": []}, origin="reasoning")["id"]
        tools = ToolRegistry(store, clients=SavedLiterature())
        imported = tools.execute("public.literature.read", {"pmcid": "PMC123"}, operation_key="seed-article")
        source_ref = imported["result"]["source_ref"]
        commission = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": {"version": "literature_assignment_v1", "question_context_refs": [hypothesis],
                "source_refs": [source_ref]}, "goal": "Investigate what this source establishes about target activity",
            "scope": scope, "purpose": "Return source-linked assessments preserving assayed subjects and conditions",
            "schema_json": json.dumps(ASSESSMENT_FORM), "initial_report_json": "{}"}, "report_update": {}}

        def read_original(inputs):
            assert inputs["literature_assignment"]["source_refs"] == [source_ref]
            assert "glucose" not in inputs["last_local_outcome"]["result"]["text"]
            assert any(row["name"] == "source.read" for row in inputs["tools"])
            return {"selection": {"kind": "tool", "tool": "source.read", "arguments": {
                "source_ref": source_ref, "representation": "original",
                "offset": ARTICLE.index("α".encode()) + 1}}, "report_update": {}}

        def repair_read(inputs):
            assert inputs["feedback"]["code"] == "source_offset_not_utf8_boundary"
            assert inputs["last_local_outcome"]["status"] == "invalid"
            return {"selection": {"kind": "tool", "tool": "source.read", "arguments": {
                "source_ref": source_ref, "representation": "original", "offset": TABLE_START,
                "limit": TABLE_END - TABLE_START}}, "report_update": {}}

        def interpret(inputs):
            window = inputs["last_local_outcome"]["result"]
            assert window["representation"] == "original" and window["source_ref"] == source_ref
            return {"selection": {"kind": "reason", "commit": reasoning_from_window(
                store, target, hypothesis, window)}, "report_update": {}}

        received = []
        def integrate(inputs):
            report, = inputs["child_reports"]
            received.append(report)
            row = store.get(report["assessments"][0])
            assert row["applicability"] == "scope_limited"
            assert store.get(row["condition_refs"][0])["name"] == "glucose at 30 °C"
            payload = {name: [] for name in store.reasoning_schema()["required"]}
            payload["annotation_updates"] = [annotation(target, hypothesis, report["assessments"], 0, alias="parent")]
            return {"selection": {"kind": "reason", "commit": payload}, "report_update": {}}

        provider = ScriptedProvider([commission,
            {"selection": {"kind": "tool", "tool": "source.read", "arguments": {
                "source_ref": source_ref, "representation": "text"}}, "report_update": {}},
            read_original, repair_read, interpret, integrate])
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 3)
            controllers.append(value)
            return value

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
            controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[hypothesis, source_ref],
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 1 and len(received) == 1
        assert [value.scores for value in controllers] == [[1, 0], [0, 0, 1]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert len(provider.contexts) == 6
        saved, = store.db.execute("SELECT form FROM runtime_forms").fetchall()
        assert json.loads(saved[0]) == received[0]
        current, = store.current_annotations()
        assert current["coherent_sets"][0]["interpretations"][0]["assessment_refs"] == received[0]["assessments"]
