"""Exact, bounded inspection of synthetic scientific revisions and dependencies."""

import json

import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store


def source(store, text="Synthetic comparison fixture; not an experiment."):
    artifact = store.artifact(text, "text/plain")
    return store.put("source", {"provider": "synthetic_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact,
        "request_ref": None, "version": "1", "retrieved_at": None}, origin="caller")


def hypothesis(store, target, value="intact"):
    return store.put("hypothesis", {"subject_refs": [target], "predicate": "sequence_integrity",
        "value": {"type": "enum", "value": value}, "context_refs": []}, origin="reasoning")


def observation(store, target, src=None, *, anchor=None):
    src = src or source(store)
    return store.put("observation", {"subject_refs": [target], "source_subject_refs": [target],
        "kind": "comparison", "source_ref": src["id"], "measurements": [],
        "dependencies": [], "anchor": anchor}, origin="extracted" if anchor else "caller")


def assessment(store, h, o, *, revision=0, relation="strengthens", assumptions=None):
    return store.put("assessment", {"extent_basis": "observed_extent", "hypothesis_ref": h["id"], "observation_ref": o["id"],
        "relation": relation, "applicability": "direct", "condition_refs": [],
        "assumption_refs": assumptions or [], "expected_revision": revision}, origin="reasoning")


def annotation(store, target, h, a, *, revision=0, contexts=None):
    return store.put("annotation", {"subject_ref": target, "footprint_kind": "localized",
        "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"],
            "disposition": "supported", "assessment_refs": [a["id"]]}],
            "context_refs": contexts or []}], "alternative_refs": [],
        "resolution": "selected", "expected_revision": revision}, origin="reasoning")


def collect(store, query, scope=None):
    records = []
    pages = []
    while query is not None:
        page = store.query_records(scope=scope, **query)
        pages.append(page)
        records.extend(page["records"])
        query = page["next_query"]
    return records, pages


def test_view_next_query_reads_exact_current_rows_without_repeating_history(tmp_path):
    path = tmp_path / "store"
    with Store(path) as store:
        store.create_problem(raw_sequence="ACGT", molecule="dna")
        target = store.targets()[0]["id"]
        o = observation(store, target)
        histories = []
        for value in ("intact", "partial", "disrupted"):
            h = hypothesis(store, target, value)
            old = assessment(store, h, o)
            histories.append(old["id"])
            assessment(store, h, o, revision=1, relation="weakens")
        expected = store.current_assessments()
        view = store.reasoning_view(limit=1)
        rest, pages = collect(store, view["pages"]["assessments"]["next_query"])
        assert view["assessments"] + rest == expected
        assert all(page["total"] == 3 and page["current_only"] is True for page in pages)
        assert len({row["id"] for row in view["assessments"] + rest}) == 3
        assert not set(histories) & {row["id"] for row in expected}
        all_rows, all_pages = collect(store, {"kind": "assessment", "limit": 2})
        assert len(all_rows) == 6 and all(page["total"] == 6 for page in all_pages)
    with Store(path) as store:
        reopened, _ = collect(store, {"kind": "assessment", "limit": 1, "current_only": True})
        assert reopened == expected


def test_current_annotation_page_and_immutable_pages_share_view_contract(tmp_path):
    with Store(tmp_path / "store") as store:
        manifest = tmp_path / "input.json"
        manifest.write_text(json.dumps({"schema_version": 1, "entries": [
            {"sequence": "ACGT", "name": "A"}, {"sequence": "GGAA", "name": "B"}]}))
        store.create_problem(manifest_path=manifest)
        for target in store.targets():
            h = hypothesis(store, target["id"])
            o = observation(store, target["id"])
            a = assessment(store, h, o)
            annotation(store, target["id"], h, a)
            annotation(store, target["id"], h, a, revision=1, contexts=[h["id"]])
        view = store.reasoning_view(limit=1)
        for kind, field, getter in (("annotation", "annotations", store.current_annotations),
                                    ("hypothesis", "hypotheses", lambda: store.list("hypothesis"))):
            meta = view["pages"][field]
            assert meta["next_query"]["kind"] == kind
            rest, _ = collect(store, meta["next_query"])
            assert view[field] + rest == getter()


def test_reverse_query_finds_real_semantic_paths_and_anchor_provenance_not_quotes(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKW", molecule="protein")
        target = store.targets()[0]["id"]
        assumption = hypothesis(store, target, "partial")
        h = hypothesis(store, target)
        # The quote is exactly the hypothesis ID: its textual presence alone
        # must not become a dependency, while the anchor's real references do.
        src = source(store, assumption["id"])
        anchor = {"source_ref": src["id"], "artifact_ref": src["text_ref"],
            "start": 0, "end": len(assumption["id"]), "quote": assumption["id"]}
        o = observation(store, target, src, anchor=anchor)
        a = assessment(store, h, o, assumptions=[assumption["id"]])
        n = annotation(store, target, h, a, contexts=[assumption["id"]])
        result = store.query_records("assessment", references=[assumption["id"]], current_only=True)
        assert result["records"] == [a]
        assert result["reference_matches"] == [{"record_ref": a["id"],
            "reference_ref": assumption["id"], "field_path": ["assumption_refs", 0]}]
        assert store.query_records("observation", references=[assumption["id"]])["total"] == 0
        assert store.query_records("hypothesis", references=[assumption["id"]])["total"] == 0
        page = store.query_records("annotation", references=[assumption["id"]])
        assert page["records"] == [n]
        assert page["reference_matches"][0]["field_path"] == ["coherent_sets", 0, "context_refs", 0]
        page = store.query_records("observation", references=[src["id"]])
        assert page["records"] == [o]
        assert {tuple(row["field_path"]) for row in page["reference_matches"]} == {
            ("source_ref",), ("anchor", "source_ref")}
        page = store.query_records("observation", references=[src["text_ref"]])
        assert page["reference_matches"] == [{"record_ref": o["id"],
            "reference_ref": src["text_ref"], "field_path": ["anchor", "artifact_ref"]}]


def test_reference_filter_is_or_paged_and_current_only_keeps_latest_attribution(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKW", molecule="protein")
        target = store.targets()[0]["id"]
        first, second = hypothesis(store, target), hypothesis(store, target, "partial")
        o = observation(store, target)
        old = assessment(store, first, o, assumptions=[second["id"]])
        new = assessment(store, first, o, revision=1, assumptions=[second["id"]], relation="weakens")
        other = assessment(store, second, o, assumptions=[first["id"]])
        query = {"kind": "assessment", "limit": 1, "current_only": True,
                 "references": [first["id"], second["id"]]}
        rows, pages = collect(store, query)
        assert rows == store.current_assessments()
        assert {row["id"] for row in rows} == {new["id"], other["id"]}
        assert all(page["total"] == 2 for page in pages)
        assert pages[0]["next_query"]["references"] == query["references"]
        historical = store.query_records("assessment", references=[second["id"]])
        assert old in historical["records"] and new in historical["records"]
        assert len({row["id"] for row in historical["records"]}) == historical["total"]


def test_subject_union_is_bounded_scoped_and_filtered_without_subject_materialization(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        manifest = tmp_path / "input.json"
        manifest.write_text(json.dumps({"schema_version": 1, "entries": [
            {"sequence": "ACGT", "name": "A", "molecule": "dna"},
            {"sequence": "GGAA", "name": "B", "molecule": "dna"}]}))
        store.create_problem(manifest_path=manifest)
        targets = {target["name"]: target for target in store.targets()}
        features, products = {}, {}
        for name, target in targets.items():
            features[name] = store.put("feature", {"subject_ref": target["id"], "kind": "sequence_region",
                "segments": [{"start": 0, "end": 2}], "strand": "+", "context_refs": []}, origin="reasoning")
            products[name] = store.put("product", {"parent_refs": [features[name]["id"]],
                "molecule": "dna", "sequence_ref": store.artifact("AC" if name == "A" else "GG"),
                "derivation": "extraction", "context_refs": [],
                "footprint": store.coverage(features[name]["id"])}, origin="tool")
        expected = store.subjects()
        monkeypatch.setattr(store, "subjects", lambda *a, **k: pytest.fail("materialized all subjects"))
        monkeypatch.setattr(store, "get_artifact", lambda *a: pytest.fail("hydrated sequence/source data"))
        rows, pages = collect(store, {"kind": "subject", "limit": 1})
        assert rows == expected and all(page["total"] == 6 for page in pages)
        scope = {"subject_refs": [targets["A"]["id"]]}
        rows, _ = collect(store, {"kind": "subject", "limit": 1}, scope)
        assert rows == [targets["A"], features["A"], products["A"]]
        page = store.query_records("subject", scope=scope, references=[targets["B"]["id"]])
        assert page["records"] == [] and page["total"] == 0
        page = store.query_records("subject", scope=scope, references=[features["A"]["id"]])
        assert page["records"] == [products["A"]]
        page = store.query_records("subject", scope=scope, references=[targets["A"]["source_ref"]])
        assert page["records"] == [targets["A"]]


def test_reverse_query_preserves_existing_scope_and_does_not_change_credit_or_state(tmp_path):
    with Store(tmp_path / "store") as store:
        manifest = tmp_path / "input.json"
        manifest.write_text(json.dumps({"schema_version": 1, "entries": [
            {"sequence": "MKW", "molecule": "protein", "name": "A"},
            {"sequence": "MKR", "molecule": "protein", "name": "B"}]}))
        store.create_problem(manifest_path=manifest)
        a, b = store.targets()
        assumption = hypothesis(store, a["id"], "partial")
        for target in (a, b):
            h = hypothesis(store, target["id"])
            o = observation(store, target["id"])
            ass = assessment(store, h, o, assumptions=[assumption["id"]])
            annotation(store, target["id"], h, ass)
        before = project_credit(store).as_record()
        changes = store.db.total_changes
        page = store.query_records("assessment", scope={"subject_refs": [a["id"]]},
            references=[assumption["id"]], current_only=True)
        assert len(page["records"]) == 1
        assert store.roots(page["records"][0]["id"]) == [a["id"]]
        assert store.db.total_changes == changes
        assert project_credit(store).as_record() == before


def test_query_count_and_rows_share_one_snapshot_across_concurrent_commit(tmp_path):
    path = tmp_path / "store"
    with Store(path) as reader, Store(path) as writer:
        reader.create_problem(raw_sequence="MKW", molecule="protein")
        target = reader.targets()[0]["id"]
        first = hypothesis(reader, target)
        wrote = False

        def interleave(statement):
            nonlocal wrote
            if "SELECT v.data FROM visible" in statement and not wrote:
                wrote = True
                hypothesis(writer, target, "partial")

        reader.db.set_trace_callback(interleave)
        page = reader.query_records("hypothesis", limit=10)
        reader.db.set_trace_callback(None)
        assert wrote
        assert page["total"] == 1 and page["records"] == [first]
        assert reader.query_records("hypothesis")["total"] == 2


def test_query_rejects_malformed_selectors_without_state_mutation(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKW", molecule="protein")
        target = store.targets()[0]["id"]
        changes = store.db.total_changes
        for arguments, code in (({"limit": True}, "invalid_page"),
                ({"current_only": "yes"}, "invalid_current_only"),
                ({"references": []}, "invalid_reference_filter"),
                ({"references": ["hypothesis_" + "f" * 24]}, "unknown_reference")):
            with pytest.raises(ContractError, match=code):
                store.query_records("hypothesis", **arguments)
        assert store.query_records("hypothesis", references=[target, target])["references"] == [target]
        assert store.db.total_changes == changes
