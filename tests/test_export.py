"""Synthetic scientific records test export meaning, not annotation accuracy."""
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from gene_annotation_episode.credit import unavailable_annotation_score
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import FORMAT, export_annotation
from gene_annotation_episode.state import Store


@pytest.fixture
def store(tmp_path):
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps({"schema_version": 1, "entries": [
        {"sequence": "ATGAAAATGTAA", "molecule": "dna", "role": "assembly", "name": "dna;fixture=one", "sample": "S1"},
        {"sequence": "ACGUACGU", "molecule": "rna", "role": "transcript", "name": "rna"},
        {"sequence": "MKWV", "molecule": "protein", "role": "protein", "name": "protein"}]}))
    with Store(tmp_path / "state") as value:
        value.create_problem(manifest_path=manifest, caller_context={"fixture": "synthetic", "reported_growth": "unknown"})
        yield value


def source(store):
    ref = store.artifact("Synthetic fixture: construct Z binds zinc; manganese is an alternative. Assay at pH 7.", "text/plain")
    return store.put("source", {"provider": "synthetic_export_fixture", "accession": "fixture", "uri": None,
        "artifact_ref": ref, "text_ref": ref, "request_ref": None, "version": None, "retrieved_at": None}, origin="external")


def feature(store, target, start, end, *, kind="gene", strand="+"):
    return store.put("feature", {"subject_ref": target["id"], "kind": kind,
        "segments": [{"start": start, "end": end}], "strand": strand, "context_refs": []}, origin="tool")


def hypothesis(store, subject, value="intact"):
    return store.put("hypothesis", {"subject_refs": [subject["id"]], "predicate": "sequence_integrity",
        "value": {"type": "enum", "value": value}, "context_refs": []}, origin="reasoning")


def account(store, subject, src, *, resolution="selected"):
    h = hypothesis(store, subject)
    construct = store.put("reference", {"reference_type": "construct", "source_ref": src["id"],
        "accession": "synthetic_construct_Z", "label": "construct Z", "sequence_ref": None,
        "molecule": None, "length": None, "term_refs": [], "context_refs": []}, origin="external")
    condition = store.put("context", {"context_type": "assay_condition", "name": "synthetic_reported_assay",
        "source_ref": src["id"], "attributes": [{"name": "ph", "value": {"type": "number", "value": 7.0, "unit_ref": None}}],
        "related_refs": [construct["id"]]}, origin="external")
    o = store.put("observation", {"subject_refs": [subject["id"]], "source_subject_refs": [construct["id"]],
        "kind": "assay_report", "source_ref": src["id"], "measurements": [{"name": "assay_outcome", "value": {"type": "enum", "value": "positive"}}],
        "dependencies": [condition["id"]], "anchor": None}, origin="external")
    a = store.put("assessment", {"extent_basis": "inferred_extent", "hypothesis_ref": h["id"], "observation_ref": o["id"], "relation": "strengthens",
        "target_footprint": store.coverage(subject["id"]), "applicability": "transfer", "condition_refs": [condition["id"]], "assumption_refs": [], "expected_revision": 0}, origin="reasoning")
    n = store.put("annotation", {"subject_ref": subject["id"], "footprint_kind": "localized",
        "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "supported", "assessment_refs": [a["id"]]}], "context_refs": [condition["id"]]}],
        "alternative_refs": [], "resolution": resolution, "expected_revision": 0}, origin="reasoning")
    return h, o, a, n, construct, condition


def payload(record):
    return {key: value for key, value in record.items() if key not in {"id", "record_type", "origin", "revision", "footprint"}}


def reference_values(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == "ref" or key.endswith("_ref")) and child is not None:
                yield child
            elif key.endswith("_refs") or key == "dependencies":
                yield from child
            else:
                yield from reference_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from reference_values(child)


def load(result):
    return json.loads(Path(result["json"]["path"]).read_text())


def test_json_preserves_current_alternatives_and_exact_dependency_history(store, tmp_path):
    dna = store.targets()[0]
    f = feature(store, dna, 0, 9)
    product = store.put("product", {"parent_refs": [f["id"]], "molecule": "protein", "sequence_ref": store.artifact("MKM"),
        "derivation": "translation", "context_refs": [], "footprint": store.coverage(f["id"])}, origin="tool")
    h, o, a1, n1, construct, condition = account(store, product, source(store))
    other = hypothesis(store, product, "disrupted")
    update = payload(n1)
    update["coherent_sets"] = [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "unresolved", "assessment_refs": [a1["id"]]},
        {"hypothesis_ref": other["id"], "disposition": "unresolved", "assessment_refs": []}], "context_refs": [condition["id"]]}]
    update.update(alternative_refs=[other["id"]], resolution="alternatives_retained", expected_revision=1)
    n2 = store.put("annotation", update, origin="reasoning")
    assessment_update = payload(a1)
    assessment_update.update(relation="weakens", expected_revision=1)
    a2 = store.put("assessment", assessment_update, origin="reasoning")
    private = store.artifact("private execution diagnostic")
    result = export_annotation(store, tmp_path / "annotation.json", page_size=1)
    document = load(result)
    assert document["format"] == FORMAT
    assert document["problem"] == store.problem()
    assert {row["id"] for row in document["inputs"]} == set(store.problem()["subject_refs"])
    records = {row["id"]: row for row in document["records"]}
    membership = document["membership"]
    assert membership["current_annotation_refs"] == [n2["id"]]
    assert membership["current_assessment_refs"] == [a2["id"]]
    assert membership["referenced_noncurrent_assessment_refs"] == [a1["id"]]
    assert n1["id"] not in records
    assert records[n2["id"]] == n2
    assert records[o["id"]]["source_subject_refs"] == [construct["id"]]
    assert records[construct["id"]]["sequence_ref"] is None
    assert records[a1["id"]]["condition_refs"] == [condition["id"]]
    assert records[condition["id"]]["attributes"][0]["value"]["value"] == 7.0
    assert records[n2["id"]]["resolution"] == "alternatives_retained"
    assert document["credit_projection"] is None
    artifact_refs = {row["id"] for row in document["artifacts"]}
    assert private not in artifact_refs
    known = set(records) | artifact_refs | {row["id"] for row in document["inputs"]}
    for row in document["inputs"] + document["records"]:
        assert set(reference_values(row)) <= known


def test_optional_credit_reports_unavailable_without_hydrating_artifacts(store, tmp_path, monkeypatch):
    dna = store.targets()[0]
    f = feature(store, dna, 0, 9)
    account(store, f, source(store))
    scope = {"subject_refs": [dna["id"]], "segments": [{"target_ref": dna["id"], "start": 0, "end": 9, "unit": "nt"}]}
    monkeypatch.setattr(store, "get_artifact", lambda ref: pytest.fail("export must not hydrate raw artifact bytes"))
    document = load(export_annotation(store, tmp_path / "credit.json", scope=scope, include_credit=True))
    assert document["credit_projection"] == unavailable_annotation_score()
    assert document["credit_projection"]["annotation_score"] is None
    assert document["scope"] == scope
    assert all(not a["content_included"] and a["relative_path"] is None for a in document["artifacts"])


def test_bundle_is_portable_hash_checked_and_streamed(store, tmp_path, monkeypatch):
    monkeypatch.setattr(store, "get_artifact", lambda ref: pytest.fail("bundle copy must stream from content-addressed files"))
    result = export_annotation(store, tmp_path / "portable.json", include_artifacts=True, page_size=1)
    document = load(result)
    for artifact in document["artifacts"]:
        copied = Path(result["json"]["path"]).parent / artifact["relative_path"]
        raw = copied.read_bytes()
        assert artifact["content_included"]
        assert hashlib.sha256(raw).hexdigest() == artifact["sha256"]
        assert len(raw) == artifact["size"]
    assert document["problem"]["caller_context_source_ref"] in {row["id"] for row in document["records"]}


def test_gff3_only_projects_actual_nt_features_and_preserves_alternatives(store, tmp_path):
    dna, rna, protein = store.targets()
    gene = feature(store, dna, 0, 9)
    cds = feature(store, dna, 0, 9, kind="CDS")
    trna = feature(store, rna, 0, 8, kind="tRNA", strand="-")
    domain = feature(store, protein, 0, 3, kind="protein_domain")
    nested = feature(store, gene, 0, 9, kind="sequence_region")
    h, o, a, n, _, condition = account(store, gene, source(store))
    alt = hypothesis(store, gene, "partial")
    update = payload(n)
    update["coherent_sets"] = [{"interpretations": [{"hypothesis_ref": h["id"], "disposition": "unresolved", "assessment_refs": [a["id"]]}], "context_refs": [condition["id"]]}]
    update.update(alternative_refs=[alt["id"]], resolution="alternatives_retained", expected_revision=1)
    current = store.put("annotation", update, origin="reasoning")
    result = export_annotation(store, tmp_path / "annotation.gff3", format="gff3")
    document = load(result)
    text = Path(result["gff3"]["path"]).read_text()
    rows = [line.split("\t") for line in text.splitlines() if line and not line.startswith("#")]
    assert {row[2] for row in rows} == {"gene", "tRNA"}
    assert {row[0] for row in rows} == {dna["id"], rna["id"]}
    gene_row = next(row for row in rows if row[2] == "gene")
    assert gene_row[3:8] == ["1", "9", ".", "+", "."]
    assert "dna%3Bfixture%3Done" in gene_row[8]
    assert "account_resolution=alternatives_retained" in gene_row[8]
    assert "interpretation_dispositions=unresolved" in gene_row[8]
    assert "alternative_hypothesis_refs=" + alt["id"] in gene_row[8]
    assert "current_annotation_refs=" + current["id"] in gene_row[8]
    exclusions = {row["feature_ref"]: row["code"] for row in document["gff3_projection"]["excluded_features"]}
    assert exclusions == {cds["id"]: "cds_phase_not_recorded", domain["id"]: "original_input_not_declared_nucleotide", nested["id"]: "feature_not_directly_on_original_input"}
    assert result["gff3"]["emitted_features"] == 2
    assert result["gff3"]["excluded_features"] == 3
    assert result["json"]["sha256"] in text
    assert trna["id"] in document["gff3_projection"]["emitted_feature_refs"]


def test_input_itself_never_becomes_fabricated_gff_gene(store, tmp_path):
    result = export_annotation(store, tmp_path / "no-features.gff3", format="gff3")
    assert result["gff3"]["emitted_features"] == 0
    assert all(not line or line.startswith("#") for line in Path(result["gff3"]["path"]).read_text().splitlines())
    assert load(result)["membership"]["candidate_feature_refs"] == []


def test_scoped_export_keeps_real_coordinates_and_original_problem(store, tmp_path):
    dna = store.targets()[0]
    overlapping = feature(store, dna, 0, 9)
    outside = feature(store, dna, 10, 12)
    scope = {"subject_refs": [dna["id"]], "segments": [{"target_ref": dna["id"], "start": 3, "end": 6, "unit": "nt"}]}
    result = export_annotation(store, tmp_path / "local.json", scope=scope)
    document = load(result)
    assert document["problem"] == store.problem()
    assert document["membership"]["candidate_feature_refs"] == [overlapping["id"]]
    records = {row["id"]: row for row in document["records"]}
    assert records[overlapping["id"]]["segments"] == [{"start": 0, "end": 9}]
    assert outside["id"] not in records
    assert document["eligible_footprint"] == scope["segments"]


def test_paged_stream_is_complete_deterministic_and_skips_unreferenced_history(store, tmp_path, monkeypatch):
    dna = store.targets()[0]
    for start in range(4):
        feature(store, dna, start, start+3)
    f = feature(store, dna, 0, 9)
    h, o, a, n, _, _ = account(store, f, source(store))
    update = payload(n)
    update["coherent_sets"] = [{key:value for key,value in group.items() if key != "id"} for group in update["coherent_sets"]]
    update.update(resolution="unresolved", expected_revision=1)
    latest = store.put("annotation", update, origin="reasoning")
    original_list = store.list
    def no_history(kind, *args, **kwargs):
        assert kind not in {"annotation", "assessment"}, "use current pointer pages rather than loading audit history"
        return original_list(kind, *args, **kwargs)
    monkeypatch.setattr(store, "list", no_history)
    one = export_annotation(store, tmp_path / "one.json", page_size=1)
    many = export_annotation(store, tmp_path / "many.json", page_size=3)
    assert Path(one["json"]["path"]).read_bytes() == Path(many["json"]["path"]).read_bytes()
    document = load(one)
    assert len(document["membership"]["candidate_feature_refs"]) == 5
    assert document["membership"]["current_annotation_refs"] == [latest["id"]]
    assert n["id"] not in {row["id"] for row in document["records"]}


def test_export_keeps_one_snapshot_when_requested_scoring_is_unavailable(store, tmp_path, monkeypatch):
    f = feature(store, store.targets()[0], 0, 9)
    h, o, a1, n, _, _ = account(store, f, source(store))
    expected = unavailable_annotation_score()
    other = Store(store.path)
    original_list = store.list
    fired = False
    def interleave(kind, *args, **kwargs):
        nonlocal fired
        rows = original_list(kind, *args, **kwargs)
        if not fired:
            fired = True
            revision = payload(a1)
            revision.update(relation="weakens", expected_revision=1)
            other.put("assessment", revision, origin="reasoning")
        return rows
    monkeypatch.setattr(store, "list", interleave)
    try:
        document = load(export_annotation(store, tmp_path / "snapshot.json", include_credit=True))
        assert document["membership"]["current_assessment_refs"] == [a1["id"]]
        assert document["credit_projection"] == expected
        assert store.current_assessments()[0]["id"] != a1["id"]
    finally:
        other.close()


def test_corrupt_bundle_does_not_publish_new_document(store, tmp_path):
    target = store.targets()[0]
    artifact = store.get(target["sequence_ref"])
    raw = store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
    raw.write_bytes(b"corruption")
    output = tmp_path / "annotation.json"
    output.write_text("previous published export")
    with pytest.raises(ContractError, match="export_artifact_digest_mismatch"):
        export_annotation(store, output, include_artifacts=True)
    assert output.read_text() == "previous published export"


def test_export_cannot_replace_authoritative_storage(store):
    with pytest.raises(ContractError, match="authoritative_storage"):
        export_annotation(store, store.path / "state.sqlite3")
    with pytest.raises(ContractError, match="authoritative_storage"):
        export_annotation(store, store.path / "artifacts" / "bad-output.json")


def test_discontinuous_gff_segments_retain_identity_and_order_without_circularity(store, tmp_path):
    rna = store.targets()[1]
    f = store.put("feature", {"subject_ref": rna["id"], "kind": "ncRNA",
        "segments": [{"start": 6, "end": 8}, {"start": 0, "end": 3}], "strand": "-", "context_refs": []}, origin="reasoning")
    result = export_annotation(store, tmp_path / "segments.gff3", format="gff3")
    text = Path(result["gff3"]["path"]).read_text()
    rows = [line.split("\t") for line in text.splitlines() if line and not line.startswith("#")]
    assert [row[3:5] for row in rows] == [["7", "8"], ["1", "3"]]
    assert all("ID=" + f["id"] in row[8] for row in rows)
    assert "segment_index=0" in rows[0][8]
    assert "segment_index=1" in rows[1][8]
    assert "Is_circular" not in text


@pytest.mark.parametrize("content", [
    b">good\nACGT\n>empty\n>later\nTGCA\n",
    b"@good\nACGT\n+\n!@+~\n@bad\nACGT\n+\n!!\n",
])
def test_partial_material_export_keeps_exact_indexed_errors_and_portable_members(tmp_path, content):
    workspace = tmp_path / "partial-state"
    with Store(workspace) as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=content, name="partial-supplied")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial"
        actual = store.material_errors(attempt["id"])["errors"]
        expected = [{"parse_ref": attempt["id"], "parse_key": attempt["parse_key"],
                     "error_index": index, **error} for index, error in enumerate(actual)]
        native_members = store.material_members(attempt["collection_ref"])["members"]
    with Store(workspace) as store:
        result = export_annotation(store, tmp_path / "partial.json", include_artifacts=True, page_size=1)
        data = load(result)
        assert data["parse_errors"] == expected
        exported_attempt = next(row for row in data["records"] if row["id"] == attempt["id"])
        assert exported_attempt["error_count"] == len(data["parse_errors"]) == 1
        assert exported_attempt["valid_records"] == len(native_members)
        members = [row for row in data["records"] if row["record_type"] == "collection_member"
                   and row["collection_ref"] == attempt["collection_ref"]]
        packed_index = next((row for row in data["packed_material_indexes"]
                             if row["collection_ref"] == attempt["collection_ref"]), None)
        if packed_index is not None:
            assert members == []  # valid unexamined prefix remains in the compact index
            index_path = Path(result["json"]["path"]).parent / packed_index["relative_path"]
            assert hashlib.sha256(index_path.read_bytes()).hexdigest() == packed_index["sha256"]
            with sqlite3.connect(index_path) as index:
                members = [json.loads(row[0]) for row in index.execute("SELECT data FROM material_members ORDER BY ordinal")]
                for member in members:
                    assert member == store.get(member["id"])
                    selected = store.material_member(member["id"])
                    for component in ("sequence", "quality"):
                        value = bytearray()
                        spans = index.execute("SELECT c.artifact_ref,s.start,s.end FROM material_component_spans s JOIN material_pack_chunks c ON c.parse_key=? AND c.chunk_index=s.chunk_index WHERE s.member_ref=? AND s.component=? ORDER BY s.part",
                            (attempt["parse_key"], member["id"], component))
                        for ref, start, end in spans:
                            artifact = next(row for row in data["artifacts"] if row["id"] == ref)
                            chunk = (Path(result["json"]["path"]).parent / artifact["relative_path"]).read_bytes()
                            assert hashlib.sha256(chunk).hexdigest() == artifact["sha256"]
                            value.extend(chunk[start:end])
                        assert value.decode("ascii") == selected[component]
                        assert hashlib.sha256(value).hexdigest() == member["storage"]["components"][component]["sha256"]
        assert {row["id"] for row in members} == {row["id"] for row in native_members}
        artifacts = {row["id"]: row for row in data["artifacts"]}
        original = store.get(material["source_ref"])["artifact_ref"]
        assert (Path(result["json"]["path"]).parent / artifacts[original]["relative_path"]).read_bytes() == content
        for member in members:
            for field in ("sequence_ref", "quality_ref"):
                if member[field] is None:
                    continue
                artifact = artifacts[member[field]]
                saved = Path(result["json"]["path"]).parent / artifact["relative_path"]
                assert hashlib.sha256(saved.read_bytes()).hexdigest() == artifact["sha256"]
                assert saved.read_bytes() == store.get_artifact(member[field])
        assert len(data["inputs"]) == 1
