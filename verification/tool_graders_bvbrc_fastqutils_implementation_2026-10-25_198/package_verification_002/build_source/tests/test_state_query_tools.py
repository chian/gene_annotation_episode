"""Ordinary query access must agree with the owner's current working view.

These are local integration fixtures, not biological or model-run evidence.
"""
import json

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def _hypothesis(store, target, value="intact"):
    return store.put("hypothesis", {"subject_refs": [target],
        "predicate": "sequence_integrity", "value": {"type": "enum", "value": value},
        "context_refs": []}, origin="reasoning")


def _assessment(store, hypothesis, observation, *, relation="strengthens", revision=0,
                assumptions=()):
    return store.put("assessment", {"extent_basis": "observed_extent", "hypothesis_ref": hypothesis["id"],
        "observation_ref": observation, "relation": relation, "applicability": "direct",
        "condition_refs": [], "assumption_refs": list(assumptions),
        "expected_revision": revision}, origin="reasoning")


def _inspect(tools, target):
    result = tools.execute("sequence.inspect", {"subject_ref": target})
    assert result["status"] == "completed", result
    return next(ref for ref in result["record_refs"] if ref.startswith("observation_"))


def test_follow_advertised_current_pages_through_ordinary_tool(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        tools = ToolRegistry(store)
        observation = _inspect(tools, target)
        first_hypothesis = _hypothesis(store, target)
        second_hypothesis = _hypothesis(store, target, "frameshift")
        _assessment(store, first_hypothesis, observation)
        _assessment(store, second_hypothesis, observation)
        revised = _assessment(store, first_hypothesis, observation, relation="weakens", revision=1)
        scope = {"subject_refs": [target]}
        before = project_credit(store, scope).as_record()
        view = store.reasoning_view(scope, limit=1)
        records = list(view["assessments"])
        query = view["pages"]["assessments"]["next_query"]
        assert query["current_only"] is True
        while query is not None:
            reply = tools.execute("state.query", query, scope=scope)
            assert reply["status"] == "completed", reply
            page = reply["result"]
            assert page["total"] == 2
            records.extend(page["records"])
            query = page["next_query"]
        assert records == store.current_assessments(scope)
        assert len({row["id"] for row in records}) == 2
        assert revised in records
        history = tools.execute("state.query", {"kind": "assessment"}, scope=scope)
        assert history["result"]["total"] == 3
        assert project_credit(store, scope).as_record() == before


def test_reverse_reference_filter_reaches_current_interpretation_and_keeps_paths(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        tools = ToolRegistry(store)
        observation = _inspect(tools, target)
        assumption = _hypothesis(store, target)
        function = _hypothesis(store, target, "frameshift")
        _assessment(store, function, observation)
        dependent = _assessment(store, function, observation, revision=1,
                                assumptions=[assumption["id"]])
        result = tools.execute("state.query", {"kind": "assessment", "current_only": True,
            "references": [assumption["id"], assumption["id"]], "limit": 1})
        assert result["status"] == "completed", result
        page = result["result"]
        assert page["records"] == [dependent]
        assert page["references"] == [assumption["id"]]
        assert page["total"] == 1 and page["next_query"] is None
        assert page["reference_matches"] == [{"record_ref": dependent["id"],
            "reference_ref": assumption["id"], "field_path": ["assumption_refs", 0]}]
        own_id_is_not_an_edge = tools.execute("state.query", {"kind": "hypothesis",
            "references": [assumption["id"]]})
        assert own_id_is_not_an_edge["result"]["records"] == []


def test_exact_empty_refs_stays_empty_and_mixed_query_modes_are_actionable(tmp_path):
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        hypothesis = _hypothesis(store, target)
        tools = ToolRegistry(store)
        empty = tools.execute("state.query", {"refs": []})
        assert empty["status"] == "completed", empty
        assert empty["result"]["records"] == []
        assert tools.execute("state.query", {"refs": [hypothesis["id"]]})["result"]["records"] == [hypothesis]
        before = store.db.execute("SELECT id,data FROM records ORDER BY id").fetchall()
        for selector in ({"kind": "hypothesis"}, {"offset": 0}, {"limit": 1},
                         {"current_only": False}, {"references": [target]}):
            args = {"refs": [hypothesis["id"]], **selector}
            key = "mixed-query-" + next(iter(selector))
            bad = tools.execute("state.query", args, operation_key=key)
            assert bad["status"] == "invalid", bad
            assert bad["feedback"]["code"] == "exact_refs_cannot_be_combined_with_page_selectors"
            assert bad["feedback"]["detail"] == {
                "selection_mode": "exact_references",
                "conflicting_fields": list(selector), "allowed_fields": ["refs"]}
            assert bad["record_refs"] == []
            assert tools.execute("state.query", args, operation_key=key) == bad
        mixed = tools.execute("state.query", {"refs": [hypothesis["id"]],
            "kind": "hypothesis", "limit": 1})
        assert mixed["feedback"]["detail"]["conflicting_fields"] == ["kind", "limit"]
        assert store.db.execute("SELECT id,data FROM records ORDER BY id").fetchall() == before


def test_subject_pages_preserve_scope_and_do_not_materialize_inventory(tmp_path, monkeypatch):
    fasta = tmp_path / "input.fna"
    fasta.write_text(">one\nATGAAATAA\n>two\nATGTGGTAA\n")
    with Store(tmp_path / "store") as store:
        targets = store.create_problem(input_path=fasta, molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        derivatives = {}
        for target in targets:
            translated = tools.execute("sequence.translate", {"subject_ref": target, "code": 11})
            assert translated["status"] == "completed", translated
            derivatives[target] = translated["result"]["records"][0]
        scope = {"subject_refs": [targets[0]]}

        def no_whole_inventory(*args, **kwargs):
            raise AssertionError("state.query must not load all subjects")

        monkeypatch.setattr(store, "subjects", no_whole_inventory)
        query = {"kind": "subject", "limit": 1}
        seen = []
        while query is not None:
            result = tools.execute("state.query", query, scope=scope)
            assert result["status"] == "completed", result
            page = result["result"]
            assert page["total"] == 3
            seen.extend(row["id"] for row in page["records"])
            query = page["next_query"]
        assert seen == [targets[0], derivatives[targets[0]]["feature_ref"],
                        derivatives[targets[0]]["product_ref"]]
        assert not set(seen).intersection({targets[1], *derivatives[targets[1]].values()})
        filtered = tools.execute("state.query", {"kind": "subject", "references": [targets[0]]}, scope=scope)
        assert filtered["status"] == "completed", filtered
        assert [row["id"] for row in filtered["result"]["records"]] == [
            derivatives[targets[0]]["feature_ref"], derivatives[targets[0]]["product_ref"]]
        assert json.loads(store.db.execute("SELECT arguments FROM tool_operations WHERE id=?",
            (filtered["operation_ref"],)).fetchone()[0])["references"] == [targets[0]]
