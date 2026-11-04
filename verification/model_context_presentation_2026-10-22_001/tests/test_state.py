import copy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError, parse_sequences
from gene_annotation_episode.state import RevisionConflict, Store


def empty_payload():
    return {name: [] for name in ("structural_proposals", "terms", "source_subjects", "observations", "hypotheses", "assessments", "annotation_updates")}


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "store") as value:
        value.create_problem(raw_sequence="ATGTGATAA", molecule="dna", role="gene")
        yield value


def source(store, text="The protein binds zinc. The assay was positive."):
    artifact = store.artifact(text, "text/plain")
    return store.put("source", {"provider": "test", "accession": "X1", "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="external")


def hypothesis(store, subject=None, value="intact"):
    return store.put("hypothesis", {"subject_refs": [subject or store.targets()[0]["id"]],
        "predicate": "sequence_integrity", "value": {"type": "enum", "value": value},
        "context_refs": []}, origin="reasoning")


def observation(store, src=None, target=None, native_kind="comparison"):
    src = src or source(store)
    target = target or store.targets()[0]["id"]
    return store.put("observation", {"subject_refs": [target], "source_subject_refs": [target],
        "kind": native_kind, "source_ref": src["id"],
        "measurements": [{"name": "identity_fraction", "value": {"type": "number", "value": 0.7, "unit_ref": None}}],
        "dependencies": [], "anchor": None}, origin="tool")


def assessment(store, h, o, relation="strengthens", revision=0):
    return store.put("assessment", {"extent_basis": "observed_extent", "hypothesis_ref": h["id"], "observation_ref": o["id"],
        "relation": relation, "applicability": "direct", "condition_refs": [], "assumption_refs": [],
        "expected_revision": revision}, origin="reasoning")


def annotation(store, h, a, subject=None, revision=0):
    return store.put("annotation", {"subject_ref": subject or store.targets()[0]["id"],
        "footprint_kind": "localized", "coherent_sets": [{"interpretations": [{"hypothesis_ref": h["id"],
        "disposition": "supported", "assessment_refs": [a["id"]]}], "context_refs": []}],
        "alternative_refs": [], "resolution": "selected", "expected_revision": revision}, origin="reasoning")


def test_mixed_immutable_inputs_and_no_fake_genes(tmp_path):
    (tmp_path / "proteins.faa").write_text(">same first\nMKW*\n>same second\nMA*Q\n")
    manifest = {"schema_version": 1, "entries": [
        {"path": "proteins.faa", "format": "fasta", "molecule": "protein", "role": "protein"},
        {"sequence": "ACGUNN", "format": "raw", "molecule": "rna", "name": "rna"}]}
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(manifest))
    with Store(tmp_path / "db") as db:
        initial = db.create_problem(manifest_path=path, caller_context={"reported_taxon": "unknown"})
        assert [t["unit"] for t in db.targets()] == ["aa", "aa", "nt"]
        assert db.list("feature") == []
        assert "duplicate_source_identifier" in db.targets()[1]["input_issues"]
        assert "internal_protein_stop_symbol" in db.targets()[1]["input_issues"]
        source(db)
        hypothesis(db)
        assert db.problem() == initial
        assert db.get_artifact(db.targets()[0]["sequence_ref"]) == b"MKW*"


def test_unknown_modality_preserved_and_symbols_not_truth_gate(store):
    parsed = parse_sequences("AT?N", molecule="dna")[0]
    assert parsed.sequence == "AT?N"
    assert parsed.issues == ("unexpected_symbol_for_declared_molecule",)
    assert parse_sequences("ACGU")[0].sequence == "ACGU"
    assert "taxon" not in store.targets()[0]
    assert "genetic_code" not in store.problem()


def test_artifacts_and_reference_atoms(store):
    first = store.artifact("bytes")
    assert first == store.artifact(b"bytes")
    assert store.get_artifact(first) == b"bytes"
    with pytest.raises(ContractError, match="unknown_reference"):
        store.put("hypothesis", {"subject_refs": [store.targets()[0]["id"]], "predicate": "functional_family",
            "value": {"type": "term_ref", "ref": "term_"+"a"*24}, "context_refs": []}, origin="reasoning")
    with pytest.raises(ContractError, match="representation_error"):
        store.put("hypothesis", {"subject_refs": [store.targets()[0]["id"]], "predicate": "functional_family",
            "value": {"type": "enum", "value": "some lengthy invented findings"}, "context_refs": []}, origin="reasoning")


def test_exact_source_extraction_aliases_and_partial_feedback(store):
    src = source(store)
    target = store.targets()[0]["id"]
    quote = "protein binds zinc"
    raw = store.get_artifact(src["text_ref"])
    start = raw.index(quote.encode())
    anchor = {"source_ref": src["id"], "artifact_ref": src["text_ref"], "start": start,
              "end": start+len(quote), "quote": quote}
    payload = empty_payload()
    payload["terms"] = [{"alias": "zinc", "label": "zinc",
        "term_type": "chemical", "source_ref": src["id"], "anchor": anchor}]
    payload["hypotheses"] = [{"alias": "h", "subject_refs": [target], "predicate": "binds",
        "value": {"type": "term_ref", "ref": "@zinc"}, "context_refs": []},
        {"alias": "bad", "subject_refs": [target], "predicate": "binds", "value": {"type": "reference", "ref": "@missing"}, "context_refs": []}]
    scope = {"subject_refs": [target]}
    result = store.commit_reasoning(payload, scope, "action1")
    assert result["status"] == "partial"
    assert len(result["changed_record_refs"]) == 2
    assert result["errors"] == [{"section": "hypotheses", "row_index": 1, "code": "unresolved_alias",
                                "field_path": ["value", "ref"], "reference": "@missing"}]
    assert store.get(result["aliases"]["zinc"])["origin"] == "extracted"
    assert store.get(result["aliases"]["h"])["value"]["ref"] == result["aliases"]["zinc"]
    assert store.commit_reasoning(payload, scope, "action1") == result
    with pytest.raises(ContractError, match="operation_key_reused"):
        store.commit_reasoning(empty_payload(), scope, "action1")
    payload["terms"][0]["anchor"]["quote"] = "not the original text"
    bad = store.commit_reasoning(payload, scope, "action2")
    assert bad["status"] == "invalid"
    assert bad["errors"][0]["code"] == "anchor_transcription_mismatch"


@pytest.mark.parametrize('artifact_field', ['artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref'])
def test_exact_anchor_reads_are_bounded_and_preserve_full_source_integrity(store, tmp_path, monkeypatch, artifact_field):
    from gene_annotation_episode.materials import artifact_file

    quote = 'EEP domain α; localization remains unresolved.'
    prefix_size = 3 * 1024**2 + 37
    original = tmp_path / 'large-source.txt'
    with original.open('wb') as handle:
        for _ in range(3):
            handle.write(b'x' * 1024**2)
        handle.write(b'x' * 37)
        handle.write(quote.encode('utf-8'))
        handle.write(b'y' * 1024**2)
    large = artifact_file(store, original, 'text/plain')
    small = store.artifact('Other source representation.', 'text/plain')
    fields = dict(artifact_ref=small, text_ref=small, stdout_ref=small, stderr_ref=small)
    fields[artifact_field] = large
    src = store.put('source', dict(provider='test', accession=None, uri=None,
        request_ref=None, version=None, retrieved_at=None, **fields), origin='external')
    artifact = store.get(large)
    path = store.path / 'artifacts' / artifact['sha256'][:2] / artifact['sha256']
    real_open, read_sizes = Path.open, []

    class BoundedReader:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def read(self, size=-1):
            assert 0 <= size <= 1024**2, 'anchor validation must not materialize the whole source'
            read_sizes.append(size)
            return self.handle.read(size)

        def __getattr__(self, name):
            return getattr(self.handle, name)

    def tracked_open(selected, mode='r', *args, **kwargs):
        handle = real_open(selected, mode, *args, **kwargs)
        return BoundedReader(handle) if selected == path and mode == 'rb' else handle

    monkeypatch.setattr(Path, 'open', tracked_open)
    anchor = dict(source_ref=src['id'], artifact_ref=large, start=prefix_size,
        end=prefix_size + len(quote.encode('utf-8')), quote=quote)
    def commit(selected_anchor, operation_key):
        payload = empty_payload()
        payload['terms'] = [dict(alias='domain', label='EEP domain', term_type='domain',
            source_ref=src['id'], anchor=selected_anchor)]
        return store.commit_reasoning(payload, {'subject_refs': store.problem()['subject_refs']}, operation_key)

    first = commit(anchor, 'valid')
    assert first['status'] == 'completed', first
    term = store.get(first['aliases']['domain'])
    assert commit(anchor, 'duplicate')['changed_record_refs'] == []
    assert read_sizes and len(quote.encode('utf-8')) in read_sizes
    for index, invalid in enumerate(({'quote': quote[:-1]}, {'start': prefix_size + 1},
                                    {'end': path.stat().st_size + 1})):
        result = commit({**anchor, **invalid}, 'invalid-' + str(index))
        assert result['status'] == 'invalid'
        assert result['errors'][0]['code'] == 'anchor_transcription_mismatch'
    assert store.list('term') == [term]
    # Bytes outside the quoted interval remain covered by integrity checking.
    with path.open('r+b') as handle:
        handle.seek(0)
        handle.write(b'z')
    result = commit(anchor, 'source-corrupted')
    assert result['status'] == 'invalid'
    assert result['errors'][0]['code'] == 'artifact_digest_mismatch'
    assert store.get(term['id']) == term


def test_revisions_conflict_preserved_and_current_state(store):
    h, o = hypothesis(store), observation(store)
    a1 = assessment(store, h, o)
    n1 = annotation(store, h, a1)
    assert n1["footprint"] == store.coverage(store.targets()[0]["id"])
    assert n1["coherent_sets"][0]["id"].startswith("coherent_set_")
    a2 = assessment(store, h, o, relation="weakens", revision=1)
    assert store.current_assessments() == [a2]
    assert store.get(a1["id"])["relation"] == "strengthens"
    with pytest.raises(RevisionConflict) as err:
        assessment(store, h, o, relation="mixed", revision=1)
    assert err.value.detail["current_revision"] == 2
    assert store.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 1
    assert store.current_annotations() == [n1]


def test_features_products_have_true_input_units(store):
    target = store.targets()[0]["id"]
    f = store.put("feature", {"subject_ref": target, "kind": "CDS", "segments": [{"start": 0, "end": 6}],
        "strand": "+", "context_refs": []}, origin="tool")
    product = store.put("product", {"parent_refs": [f["id"]], "molecule": "protein", "sequence_ref": store.artifact("MW"),
        "derivation": "translation", "context_refs": [], "footprint": store.coverage(f["id"])}, origin="tool")
    assert store.coverage(product["id"]) == [{"target_ref": target, "start": 0, "end": 6, "unit": "nt"}]
    assert product["record_type"] == "product"
    h = hypothesis(store, product["id"])
    a = assessment(store, h, observation(store, target=product["id"]))
    assert annotation(store, h, a, subject=f["id"])["subject_ref"] == f["id"]
    with pytest.raises(ContractError, match="footprint_mismatch"):
        annotation(store, h, a, revision=0)


def test_scoped_segments_fixed_and_writes_contained(store):
    target = store.targets()[0]["id"]
    parent = {"subject_refs": [target], "segments": [{"target_ref": target, "start": 0, "end": 3, "unit": "nt"},
        {"target_ref": target, "start": 2, "end": 6, "unit": "nt"}]}
    normalized = store.validate_scope(parent)
    assert normalized["segments"] == [{"target_ref": target, "start": 0, "end": 6, "unit": "nt"}]
    assert not store.scope_contains(parent, {"subject_refs": [target]})
    feature = {"subject_ref": target, "kind": "CDS", "segments": [{"start": 1, "end": 7}], "strand": "+", "context_refs": []}
    with pytest.raises(ContractError, match="record_outside_scope_segments"):
        store.put("feature", feature, origin="reasoning", scope=parent)
    assert store.list("feature") == []
    feature["segments"][0]["end"] = 6
    store.put("feature", feature, origin="reasoning", scope=parent)
    with pytest.raises(ContractError, match="scope_segment_outside_input"):
        store.validate_scope({"subject_refs": [target], "segments": [{"target_ref": target, "start": 0, "end": 6, "unit": "aa"}]})


def test_external_assay_not_direct_target_measurement(store):
    src = source(store)
    ref = store.put("reference", {"reference_type": "assay", "source_ref": src["id"], "accession": "construct",
        "label": "actual construct", "sequence_ref": None, "molecule": None, "length": None,
        "term_refs": [], "context_refs": []}, origin="external")
    h = hypothesis(store)
    o = store.put("observation", {"subject_refs": [store.targets()[0]["id"]], "source_subject_refs": [ref["id"]],
        "kind": "assay_report", "source_ref": src["id"], "measurements": [], "dependencies": [], "anchor": None}, origin="external")
    with pytest.raises(ContractError, match="source_subject_mismatch"):
        assessment(store, h, o)
    record = {"extent_basis": "observed_extent", "hypothesis_ref": h["id"], "observation_ref": o["id"], "relation": "strengthens",
              "applicability": "transfer", "condition_refs": [], "assumption_refs": [], "expected_revision": 0}
    assert store.put("assessment", record, origin="reasoning")["applicability"] == "transfer"


def test_snapshot_respects_owning_transaction_and_two_connection_visibility(store):
    other = Store(store.path)
    try:
        baseline = store.list("source")
        with store.read_snapshot():
            assert store.list("source") == baseline
            source(other)
            assert store.list("source") == baseline
        assert len(store.list("source")) == len(baseline)+1
        with store.transaction():
            with store.read_snapshot():
                assert store.db.in_transaction
            assert store.db.in_transaction
    finally:
        other.close()


def test_caller_context_is_readable_source_and_sample_identity_linked(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"schema_version": 1, "entries": [
        {"sequence": "ACGT", "sample": "culture-A", "context": {"reported_medium": "soil extract"}},
        {"sequence": "GGGG", "sample": "culture-A"},
        {"sequence": "TTTT", "sample": "culture-B"}]}))
    with Store(tmp_path / "db") as db:
        problem = db.create_problem(manifest_path=path, caller_context={"observed_growth": "slow"})
        a, b, c = db.targets()
        assert a["sample_ref"] == b["sample_ref"] != c["sample_ref"]
        src = db.get(problem["caller_context_source_ref"])
        assert json.loads(db.get_artifact(src["text_ref"])) == {"observed_growth": "slow"}
        assert src["id"] in db.reasoning_view()["supplied_context_source_refs"]
        assert a["context_source_refs"][0] in db.reasoning_view()["supplied_context_source_refs"]


def test_view_pages_current_records_and_artifact_registry_excludes_diagnostics(store):
    h = hypothesis(store)
    for index in range(3):
        o = observation(store, src=source(store, text=str(index)))
        assessment(store, h, o)
    view = store.reasoning_view(limit=2)
    assert len(view["assessments"]) == 2
    assert view["pages"]["assessments"] == {"offset": 0, "limit": 2, "total": 3, "next_offset": 2, "current_only": True,
        "next_query": {"kind": "assessment", "offset": 2, "limit": 2, "current_only": True}}
    diagnostic = store.artifact("private error details")
    assert diagnostic not in store.references()["artifact"]
    assert store.targets()[0]["sequence_ref"] in store.references()["artifact"]
    assert len(store.current_assessments(limit=2, offset=2)) == 1


def test_claim_atoms_cannot_disguise_raw_prose_artifact_as_semantic_entity(store):
    artifact = store.artifact("an arbitrary paragraph")
    with pytest.raises(ContractError, match="semantic_value_requires_entity_reference"):
        store.put("hypothesis", {"subject_refs": [store.targets()[0]["id"]], "predicate": "functional_family",
            "value": {"type": "reference", "ref": artifact}, "context_refs": []}, origin="reasoning")


def test_one_acquisition_extracts_real_source_entity_and_commits_interpretation(store):
    target = store.targets()[0]["id"]
    text = "@construct: Construct A bound zinc in vitro."
    src = source(store, text=text)
    anchor = {"source_ref": src["id"], "artifact_ref": src["text_ref"], "start": 0, "end": len(text), "quote": text}
    payload = empty_payload()
    payload["source_subjects"] = [{"alias": "construct", "reference_type": "construct", "source_ref": src["id"],
                                   "label": "Construct A", "anchor": anchor}]
    payload["terms"] = [{"alias": "zinc", "label": "zinc", "term_type": "chemical", "source_ref": src["id"], "anchor": anchor}]
    payload["observations"] = [{"alias": "obs", "subject_refs": [target], "source_subject_refs": ["@construct"],
        "kind": "assay_report", "source_ref": src["id"], "measurements": [
            {"name": "assay_outcome", "value": {"type": "enum", "value": "positive"}},
            {"name": "substrate_ref", "value": {"type": "term_ref", "ref": "@zinc"}}],
        "dependencies": ["@construct"], "anchor": anchor}]
    payload["hypotheses"] = [{"alias": "hyp", "subject_refs": [target], "predicate": "binds",
        "value": {"type": "term_ref", "ref": "@zinc"}, "context_refs": []}]
    payload["assessments"] = [{"extent_basis": "observed_extent", "alias": "asm", "hypothesis_ref": "@hyp", "observation_ref": "@obs",
        "relation": "strengthens", "applicability": "transfer", "condition_refs": [], "assumption_refs": [], "expected_revision": 0}]
    payload["annotation_updates"] = [{"alias": "ann", "subject_ref": target, "footprint_kind": "localized",
        "coherent_sets": [{"interpretations": [{"hypothesis_ref": "@hyp", "disposition": "supported", "assessment_refs": ["@asm"]}], "context_refs": []}],
        "alternative_refs": [], "resolution": "selected", "expected_revision": 0}]
    result = store.commit_reasoning(payload, {"subject_refs": [target]}, "whole-acquisition")
    assert result["status"] == "completed", result
    assert len(result["changed_record_refs"]) == 6
    observed = store.get(result["aliases"]["obs"])
    assayed = store.get(observed["source_subject_refs"][0])
    assert assayed["label"] == "Construct A"
    assert assayed["sequence_ref"] is None
    assert assayed["id"] != target
    assert assayed["origin"] == "extracted"
    assert observed["dependencies"] == [assayed["id"]]
    assert observed["anchor"]["quote"] == text
    assert store.current_annotations()[0]["coherent_sets"][0]["interpretations"][0]["assessment_refs"] == [result["aliases"]["asm"]]
    assert store.get(result["aliases"]["zinc"])["namespace"] == "source_local"


def test_reasoning_cas_conflict_preserves_other_acquired_rows(store):
    h, o = hypothesis(store), observation(store)
    assessment(store, h, o)
    payload = empty_payload()
    payload["hypotheses"] = [{"alias": "new", "subject_refs": [store.targets()[0]["id"]],
        "predicate": "sequence_integrity", "value": {"type": "enum", "value": "frameshift"}, "context_refs": []}]
    payload["assessments"] = [{"extent_basis": "observed_extent", "alias": "stale", "hypothesis_ref": h["id"], "observation_ref": o["id"],
        "relation": "weakens", "applicability": "direct", "condition_refs": [], "assumption_refs": [], "expected_revision": 0}]
    result = store.commit_reasoning(payload, None, "stale-with-independent-work")
    assert result["status"] == "partial"
    assert len(result["changed_record_refs"]) == 1
    assert result["conflicts"][0]["current_revision"] == 1
    assert store.db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 1
    assert store.get(result["changed_record_refs"][0])["value"]["value"] == "frameshift"


def external_context(store, *, kind="context"):
    src = source(store, text="Synthetic external reference neighborhood record.")
    reference = store.put("reference", {"reference_type": "dna", "source_ref": src["id"], "accession": "fixture_reference",
        "label": "synthetic external chromosome", "sequence_ref": None, "molecule": "dna", "length": None,
        "term_refs": [], "context_refs": []}, origin="external")
    observation = store.put("observation", {"subject_refs": [reference["id"]], "source_subject_refs": [reference["id"]],
        "kind": kind, "source_ref": src["id"], "measurements": [],
        "dependencies": [src["id"], reference["id"]], "anchor": None}, origin="tool")
    return reference, observation


def assessment_record(h, observation, bridge=None, *, revision=0, applicability="contextual", extent_basis="inferred_extent"):
    return {"extent_basis": extent_basis, "hypothesis_ref": h["id"], "observation_ref": observation["id"], "relation": "strengthens",
        "applicability": applicability, "condition_refs": [], "assumption_refs": [],
        "target_footprint": bridge, "expected_revision": revision}


@pytest.mark.parametrize("molecule,sequence,unit", [("dna", "ATGAAATAA", "nt"), ("protein", "MKWVQ", "aa")])
def test_external_context_bridge_is_explicit_and_keeps_native_source_identity(tmp_path, molecule, sequence, unit):
    with Store(tmp_path / "bridge") as db:
        db.create_problem(raw_sequence=sequence, molecule=molecule)
        target = db.targets()[0]
        external, observation = external_context(db)
        payload = empty_payload()
        payload["hypotheses"] = [{"alias": "h", "subject_refs": [target["id"]], "predicate": "biological_role",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}]
        bridge = [{"target_ref": target["id"], "start": 1, "end": 4, "unit": unit}]
        payload["assessments"] = [{"extent_basis": "inferred_extent", "alias": "a", "hypothesis_ref": "@h", "observation_ref": observation["id"],
            "relation": "strengthens", "applicability": "contextual", "condition_refs": [], "assumption_refs": [],
            "target_footprint": bridge, "expected_revision": 0}]
        scope = {"subject_refs": [target["id"]], "segments": bridge}
        result = db.commit_reasoning(payload, scope, "external-context-attribution")
        assert result["status"] == "completed", result
        a = db.get(result["aliases"]["a"])
        assert a["target_footprint"] == bridge
        assert a["observation_ref"] == observation["id"]
        assert db.current_assessments(scope) == [a]
        assert db.get(observation["id"]) == observation
        assert observation["subject_refs"] == observation["source_subject_refs"] == [external["id"]]
        assert len(db.list("observation")) == 1, "an assessed bridge is not another measurement"


def test_assessment_bridge_bounds_hypothesis_and_assigned_scope(store):
    target = store.targets()[0]
    feature = store.put("feature", {"subject_ref": target["id"], "kind": "gene", "segments": [{"start": 1, "end": 7}],
        "strand": "+", "context_refs": []}, origin="reasoning")
    h = hypothesis(store, feature["id"])
    _, o = external_context(store)
    def span(start, end, unit="nt"):
        return [{"target_ref": target["id"], "start": start, "end": end, "unit": unit}]
    cases = [(span(0, 9), "assessment_target_footprint_outside_hypothesis"),
             (span(0, 10), "assessment_target_footprint_outside_input"),
             (span(1, 7, "aa"), "assessment_target_footprint_outside_input"),
             ([], "representation_error")]
    for bridge, code in cases:
        with pytest.raises(ContractError, match=code):
            store.put("assessment", assessment_record(h, o, bridge), origin="reasoning")
    assigned = {"subject_refs": [target["id"]], "segments": span(2, 5)}
    with pytest.raises(ContractError, match="assessment_target_footprint_outside_scope"):
        store.put("assessment", assessment_record(h, o, span(1, 7)), origin="reasoning", scope=assigned)
    assert store.current_assessments() == []
    a = store.put("assessment", assessment_record(h, o, span(2, 5)), origin="reasoning", scope=assigned)
    assert a["target_footprint"] == assigned["segments"]


def test_assessment_bridge_cannot_give_external_hypothesis_input_coverage(store):
    target = store.targets()[0]
    external, observation = external_context(store)
    h = hypothesis(store, external["id"])
    bridge = [{"target_ref": target["id"], "start": 0, "end": target["length"], "unit": target["unit"]}]
    with pytest.raises(ContractError, match="assessment_hypothesis_has_no_input_coverage"):
        store.put("assessment", assessment_record(h, observation, bridge), origin="reasoning")
    assert store.roots(h["id"]) == []
    assert store.current_assessments() == []


def test_bridge_never_converts_external_assay_into_direct_target_experiment(store):
    target = store.targets()[0]
    _, o = external_context(store, kind="assay_report")
    h = hypothesis(store)
    bridge = [{"target_ref": target["id"], "start": 0, "end": target["length"], "unit": target["unit"]}]
    with pytest.raises(ContractError, match="source_subject_mismatch"):
        store.put("assessment", assessment_record(h, o, bridge, applicability="direct", extent_basis="observed_extent"), origin="reasoning")
    a = store.put("assessment", assessment_record(h, o, bridge, applicability="transfer"), origin="reasoning")
    assert a["applicability"] == "transfer"
    assert a["observation_ref"] == o["id"]
    assert store.get(o["id"])["source_subject_refs"] == o["source_subject_refs"]


def test_optional_bridge_absence_and_null_do_not_create_semantic_revisions(store):
    h, o = hypothesis(store), observation(store)
    original = assessment(store, h, o)
    row = assessment_record(h, o, None, revision=1, applicability="direct", extent_basis="observed_extent")
    unchanged = store.put("assessment", row, origin="reasoning")
    assert unchanged == original
    assert "target_footprint" not in unchanged
    payload = empty_payload()
    payload["assessments"] = [{"alias": "same", **row}]
    result = store.commit_reasoning(payload, None, "null-bridge-representation")
    assert result["status"] == "completed", result
    assert result["record_refs"] == [original["id"]]
    assert result["changed_record_refs"] == []
    del payload["assessments"][0]["target_footprint"]
    result2 = store.commit_reasoning(payload, None, "absent-bridge-representation")
    assert result2["status"] == "completed"
    assert result2["changed_record_refs"] == []
    assert store.current_assessments() == [original]
    schema = store.reasoning_schema()["properties"]["assessments"]["items"]
    assert "target_footprint" in schema["properties"]
    assert "target_footprint" not in schema["required"]
    assert "expected_revision" in schema["required"]


def test_bridge_changes_use_cas_and_equivalent_union_reuses_current_revision(store):
    target = store.targets()[0]
    h = hypothesis(store)
    _, o = external_context(store)
    initial = store.put("assessment", assessment_record(h, o), origin="reasoning")
    pieces = [{"target_ref": target["id"], "start": 3, "end": 6, "unit": "nt"},
              {"target_ref": target["id"], "start": 1, "end": 4, "unit": "nt"}]
    updated = store.put("assessment", assessment_record(h, o, pieces, revision=1), origin="reasoning")
    assert updated["revision"] == 2
    assert updated["target_footprint"] == [{"target_ref": target["id"], "start": 1, "end": 6, "unit": "nt"}]
    equivalent = store.put("assessment", assessment_record(h, o, updated["target_footprint"], revision=2), origin="reasoning")
    assert equivalent == updated
    assert store.get(initial["id"])["revision"] == 1
    with pytest.raises(RevisionConflict):
        store.put("assessment", assessment_record(h, o, pieces, revision=1), origin="reasoning")
