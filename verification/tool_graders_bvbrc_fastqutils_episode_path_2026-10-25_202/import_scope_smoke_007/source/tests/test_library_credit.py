"""Synthetic scientific fixtures for fixed original read-position geometry."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.credit import AXES, CreditPolicy, project_credit, softened_hypervolume
from gene_annotation_episode.numerical import YieldController
from test_credit import StoreView

LIBRARY_REF = "input_" + "1"*24
MEMBER_A, MEMBER_B = "member_" + "a"*24, "member_" + "b"*24
READ_A, READ_B = ("read_subject_" + LIBRARY_REF[6:] + ref[7:] for ref in (MEMBER_A, MEMBER_B))


class SparseView(StoreView):
    """Shared protocol plus only the fixture's actual touched native reads.

    Large descriptor mass/count can represent an implicit untouched remainder;
    no context winner requests enumeration of that artificial universe.
    """
    def __init__(self, *, mass=30, count=2):
        super().__init__()
        self.library = {"id": LIBRARY_REF, "record_type": "input", "target_kind": "read_library",
            "position_mass": mass, "member_count": count, "binding_version": "fixed_original_read_position_measure_v1",
            "membership_sha256": "fixture", "measure": "original_member_local_position_mass_not_unique_genes_or_genome_completeness",
            "collection_refs": ["collection_fixture"], "molecule": "dna"}
        self.inputs = [self.library]
        self.assessments = {}
        self.add_read("a", 10)
        self.add_read("b", 20)

    @staticmethod
    def read_id(name):
        return {"a": READ_A, "b": READ_B}[name]

    def add_read(self, name, length):
        member_ref = {"a": MEMBER_A, "b": MEMBER_B}[name]
        self.records[self.read_id(name)] = {"id": self.read_id(name), "record_type": "read_subject",
            "library_ref": self.library["id"], "member_ref": member_ref, "length": length, "unit": "nt"}
        native = {"id": member_ref, "record_type": "collection_member", "ordinal": len(self.records)-1,
            "collection_ref": "collection_fixture", "name": name, "description": "Synthetic touched original read",
            "length": length, "molecule": "dna", "source_ref": "source_fixture",
            "material_ref": "material_fixture", "quality_encoding": "unspecified",
            "sequence_ref": None, "quality_ref": None, "header_ref": None}
        self.db.execute("INSERT INTO material_members VALUES(?,?,?,?)", (
            member_ref, native["collection_ref"], native["ordinal"], json.dumps(native)))

    def get(self, ref):
        native = self.db.execute("SELECT data FROM material_members WHERE id=?", (ref,)).fetchone()
        return json.loads(native[0]) if native is not None else super().get(ref)

    def coverage(self, ref):
        row = self.get(ref)
        if row.get("target_kind") == "read_library":
            return []
        if row["record_type"] == "read_subject":
            return [{"target_ref": row["library_ref"], "member_ref": row["member_ref"],
                "start": 0, "end": row["length"], "unit": row["unit"]}]
        return row.get("footprint", [])

    def current_annotations(self, *args, **kwargs):
        pytest.fail("library projection materialized all current annotations")

    def current_assessments(self, scope=None, limit=None, offset=0):
        if limit is None:
            pytest.fail("library projection materialized all current assessments")
        return super().current_assessments(scope, limit, offset)

    def iter_scope_coverage(self, *args, **kwargs):
        pytest.fail("sparse projection enumerated unseen original reads")


def interpreted(store, read="a", *, key="a", kind="alignment", relation="strengthens",
        applicability="direct", disposition="supported", extent_basis="observed_extent", footprint=None):
    subject = store.read_id(read)
    store.records["hypothesis:"+key] = {"id": "hypothesis:"+key, "record_type": "hypothesis", "subject_refs": [subject]}
    store.records["observation:"+key] = {"id": "observation:"+key, "record_type": "observation", "kind": kind,
        "origin": "tool", "subject_refs": [subject], "source_subject_refs": [], "source_ref": "source:"+key}
    assessment = {"id": "assessment:"+key, "hypothesis_ref": "hypothesis:"+key,
        "observation_ref": "observation:"+key, "relation": relation, "applicability": applicability,
        "condition_refs": [], "assumption_refs": [], "extent_basis": extent_basis}
    if footprint is not None:
        assessment["target_footprint"] = footprint
    store.assessments[assessment["id"]] = assessment
    interpretation = {"hypothesis_ref": "hypothesis:"+key, "disposition": disposition, "assessment_refs": [assessment["id"]]}
    annotation = {"id": "annotation:"+key, "subject_ref": subject, "footprint": store.coverage(subject),
        "footprint_kind": "localized", "coherent_sets": [{"id": "coherent:"+key,
            "interpretations": [interpretation], "context_refs": []}]}
    store.annotations.append(annotation)
    return annotation, interpretation


def test_library_mass_is_fixed_sparse_and_member_positions_do_not_merge():
    store = SparseView(mass=10**12, count=10**10)
    interpreted(store)
    first = project_credit(store)
    expected = 100*10/10**12*softened_hypervolume({"comparative": 1})
    assert first.credit == pytest.approx(expected)
    assert first.targets[0]["position_mass"] == 10**12
    assert first.targets[0]["projected_footprint_units"] == 10
    assert "length" not in first.targets[0] and "unit" not in first.targets[0]
    assert first.source_contributions == ()  # explicit summary, not a hidden science cap
    assert first.as_record()["detail_pages"]["source_contributions"] == {
        "offset": 0, "limit": 0, "total": 1, "returned": 0, "next_offset": 0,
        "row_unit": "one_winning_original_interval_and_source_operand"}
    interpreted(store, "b", key="b", kind="mechanism")
    both = project_credit(store, details_limit=10)
    assert both.credit == pytest.approx(expected*3)
    assert both.targets[0]["projected_footprint_units"] == 30
    assert both.axis_components["comparative"] == 10/10**12
    assert both.axis_components["mechanistic"] == 20/10**12
    assert {row["member_ref"] for row in both.source_contributions} == {MEMBER_A, MEMBER_B}
    assert all(isinstance(row["footprint"], list) and row["footprint"][0]["member_ref"] == row["member_ref"]
               for row in both.source_contributions)
    assert json.loads(json.dumps(both.as_record(), allow_nan=False))["credit"] == both.credit


def test_child_local_position_mass_stays_fixed_and_ancestor_projects_original_library():
    store = SparseView()
    interpreted(store)
    scope = {"subject_refs": [store.library["id"]], "segments": [
        {"target_ref": store.library["id"], "member_ref": MEMBER_A, "start": 2, "end": 7, "unit": "nt"}]}
    root, child = project_credit(store), project_credit(store, scope, details_limit=10)
    assert child.targets[0]["scoped_length"] == 5
    assert child.targets[0]["projected_footprint_units"] == 5
    assert child.credit == pytest.approx(3*root.credit)
    before = child.as_record()
    interpreted(store, "b", key="outside")
    # State basis reflects the current snapshot; local meaning/score do not grow.
    after = project_credit(store, scope, details_limit=10)
    assert after.credit == before["credit"] and after.targets == child.targets
    assert after.source_contributions == child.source_contributions
    assert project_credit(store).credit > root.credit


def test_coherent_alternatives_duplicate_views_and_correction_keep_exact_signed_credit():
    store = SparseView()
    first, a = interpreted(store)
    base = project_credit(store)
    second, b = interpreted(store, key="renamed")
    first["coherent_sets"][0]["interpretations"].append(b)
    store.annotations.append(deepcopy(first))
    assert project_credit(store).credit == base.credit
    third, c = interpreted(store, key="mechanism", kind="mechanism")
    separate = project_credit(store).credit
    first["coherent_sets"].append(third["coherent_sets"][0])
    assert project_credit(store).credit == separate
    first["coherent_sets"] = [{"id": "coherent:combined", "interpretations": [a, b, c], "context_refs": []}]
    store.annotations = [first]
    combined = project_credit(store)
    assert combined.credit > separate
    controller = YieldController("fixed-library", combined.credit, .001)
    for row in store.assessments.values():
        row["applicability"] = "incomparable"
    corrected = project_credit(store)
    assert corrected.credit == 0
    step = controller.observe("reason:attribution-correction", corrected)
    assert step.marginal_credit == -combined.credit
    assert controller.estimator.scores == (-combined.credit,)


def test_bounded_operand_pages_and_inactive_pages_preserve_summary():
    store = SparseView()
    interpreted(store)
    interpreted(store, "b", key="b")
    summary = project_credit(store)
    first, second = [project_credit(store, details_limit=1, details_offset=i) for i in (0, 1)]
    assert first.credit == second.credit == summary.credit
    assert first.detail_pages["source_contributions"]["next_offset"] == 1
    assert second.detail_pages["source_contributions"]["next_offset"] is None
    assert first.source_contributions[0]["member_ref"] != second.source_contributions[0]["member_ref"]
    assert first.detail_pages["state_basis_sha256"] == second.detail_pages["state_basis_sha256"]
    store.assessments.pop("assessment:a")
    changed = project_credit(store, details_limit=1)
    assert changed.inactive_dependencies[0]["reason"] == "not_current_assessment_revision"
    assert changed.as_record()["detail_pages"]["inactive_dependencies"]["total"] == 1
    with pytest.raises(ValueError, match="nonnegative"):
        project_credit(store, details_limit=True)
    with pytest.raises(ValueError, match="details_offset_requires_explicit_details_limit"):
        project_credit(store, details_offset=1)


def test_nonwinning_overlap_does_not_split_an_unchanged_winning_source_page():
    store = SparseView()
    interpreted(store)
    baseline = project_credit(store, details_limit=10)
    weaker, _ = interpreted(store, key="weaker", applicability="transfer")
    weaker["footprint"][0].update(start=2, end=7)
    result = project_credit(store, details_limit=10)
    assert result.credit == baseline.credit
    assert result.source_contributions == baseline.source_contributions
    assert result.detail_pages["source_contributions"]["total"] == 1


def test_observed_read_interval_and_explicit_inference_use_member_local_geometry():
    store = SparseView()
    annotation, _ = interpreted(store)
    obs = store.records["observation:a"]
    obs["operand_intervals"] = [{"role": "query", "subject_ref": READ_A, "start": 2, "end": 5, "unit": "nt"}]
    # A metadata-only exact map, like the actual Store's original-read mapping.
    store.has_exact_mapping = lambda ref: True
    store.sequence_mapping = lambda ref: {"version": "fixture", "path": []}
    store.map_segments = lambda ref, spans: [{**store.coverage(ref)[0], **row} for row in spans]
    exact = project_credit(store, details_limit=10)
    assert exact.targets[0]["projected_footprint_units"] == 3
    assert exact.source_contributions[0]["native_operand_interval"]["subject_ref"] == READ_A
    assert exact.source_contributions[0]["weight"] == 1
    # Measured member A cannot become member B merely by equal local numbers.
    store.records["hypothesis:a"]["subject_refs"] = [READ_B]
    annotation["subject_ref"] = READ_B
    annotation["footprint"] = store.coverage(READ_B)
    assert project_credit(store).credit == 0
    assessed = store.assessments["assessment:a"]
    assessed.update(extent_basis="inferred_extent", applicability="transfer", target_footprint=[
        {"target_ref": store.library["id"], "member_ref": MEMBER_B, "start": 10, "end": 14, "unit": "nt"}])
    # No misleading exact-path fixture for inference provenance is needed here.
    store.has_exact_mapping = lambda ref: False
    inferred = project_credit(store, details_limit=10)
    assert inferred.targets[0]["projected_footprint_units"] == 4
    row = inferred.source_contributions[0]
    assert row["member_ref"] == MEMBER_B and row["weight"] == .6
    assert row["source_operand_intervals"] == obs["operand_intervals"]


def test_whole_library_context_does_not_invent_a_linear_extent():
    store = SparseView()
    annotation, _ = interpreted(store, kind="context")
    store.records["hypothesis:a"]["subject_refs"] = [store.library["id"]]
    annotation.update(subject_ref=store.library["id"], footprint=[], footprint_kind="whole_input_context")
    result = project_credit(store, details_limit=10)
    assert result.credit == 0
    assert result.targets[0]["context_extent_binding"] == "fixed_original_position_set_v1"
    assert result.inactive_dependencies[0]["reason"] == "hypothesis_has_no_submitted_target_coverage"


def _native_fixture(store, tmp_path):
    from gene_annotation_episode.tools import ToolRegistry
    path = tmp_path / "fixed.fastq"
    # Equal sequence bytes are still distinct original observations/members.
    path.write_bytes(b"@same first\nATGAAATTTGGG\n+\nIIIIIIIIIIII\n@same second\nATGAAATTTGGG\n+\n!!!!!!!!!!!!\n")
    store.create_problem(path, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store)
    result = tools.execute("library.members", {"library_ref": target["id"]})
    assert result["status"] == "completed", result
    return target, result["result"]["members"], tools


def _reference(store, sequence, molecule="dna"):
    artifact = store.artifact("Synthetic comparison fixture, not an experimental result.")
    source = store.put("source", {"provider": "synthetic_fixture", "accession": "fixture",
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": "fixture", "retrieved_at": None}, origin="external")
    return store.put("reference", {"reference_type": molecule, "source_ref": source["id"],
        "accession": "fixture", "label": "Synthetic comparison operand", "sequence_ref": store.artifact(sequence),
        "molecule": molecule, "length": len(sequence), "term_refs": [], "context_refs": []}, origin="external")


def _commit_native(store, subject, observation, *, key, footprint=None, hypothesis=None,
        revision=0, extent_basis="observed_extent", applicability="direct"):
    assessment = {"alias": "basis", "expected_revision": revision, "hypothesis_ref": hypothesis or "@candidate",
        "observation_ref": observation, "relation": "strengthens", "applicability": applicability,
        "condition_refs": [], "assumption_refs": [], "extent_basis": extent_basis}
    if footprint is not None:
        assessment["target_footprint"] = footprint
    result = store.commit_reasoning({"structural_proposals": [], "terms": [], "source_subjects": [],
        "contexts": [], "observations": [], "hypotheses": [] if hypothesis else [{
            "alias": "candidate", "subject_refs": [subject], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "intact"}, "context_refs": []}],
        "assessments": [assessment], "annotation_updates": [{"alias": "current", "subject_ref": subject,
            "expected_revision": revision, "footprint_kind": "localized", "coherent_sets": [{
                "interpretations": [{"hypothesis_ref": hypothesis or "@candidate", "disposition": "supported",
                    "assessment_refs": ["@basis"]}], "context_refs": []}], "alternative_refs": [], "resolution": "selected"}]},
        store.validate_scope(), key)
    assert result["status"] == "completed", result
    return result


def test_real_store_same_members_views_selection_reopen_and_no_source_hydration(tmp_path, monkeypatch):
    from gene_annotation_episode.state import Store
    path = tmp_path / "native"
    with Store(path) as store:
        target, (a, b), tools = _native_fixture(store, tmp_path)
        original = store.problem()
        reference = _reference(store, "ATGAAATTTGGG")
        result = tools.execute("sequence.align", {"query_ref": a["id"], "reference_ref": reference["id"],
            "molecule": "dna", "mode": "global"}, operation_key="native-read-comparison")
        assert result["status"] == "completed", result
        observation_ref = result["result"]["observation_ref"]
        interpreted_a = _commit_native(store, a["id"], observation_ref, key="interpret-a")
        first = project_credit(store, details_limit=10)
        assert first.targets[0]["position_mass"] == 24 and first.targets[0]["projected_footprint_units"] == 12
        selected = tools.execute("library.select", {"library_ref": target["id"], "member_refs": [a["member_ref"]]})
        assert selected["status"] == "completed", selected
        scope = selected["result"]["scope"]
        child = project_credit(store, scope, details_limit=10)
        assert child.credit == 2*first.credit
        assert child.targets[0]["scoped_length"] == 12
        view = tools.execute("sequence.view", {"subject_ref": a["id"], "molecule": "dna"})
        assert view["status"] == "completed", view
        viewed = view["result"]["records"][0]["product_ref"]
        _commit_native(store, viewed, observation_ref, key="another-view-same-original-positions")
        assert project_credit(store).credit == first.credit
        assert project_credit(store, scope).credit == child.credit
        assert store.problem() == original and len(store.targets()) == 1
        monkeypatch.setattr(store, "get_artifact", lambda ref: pytest.fail("credit hydrated an artifact"))
        monkeypatch.setattr(store, "iter_scope_coverage", lambda *a, **k: pytest.fail("credit enumerated unseen reads"))
        frozen = project_credit(store, details_limit=1).as_record()
        assert frozen["source_contributions"][0]["member_ref"] == a["member_ref"]
        assert frozen["source_contributions"][0]["native_operand_interval"]["subject_ref"] == a["id"]
    with Store(path) as reopened:
        assert project_credit(reopened, details_limit=1).as_record() == frozen
        assert reopened.get(a["id"])["member_ref"] != reopened.get(b["id"])["member_ref"]


def test_real_store_cross_read_inference_and_signed_correction_keep_native_bounds(tmp_path):
    from gene_annotation_episode.state import Store
    with Store(tmp_path / "native") as store:
        target, (a, b), tools = _native_fixture(store, tmp_path)
        reference = _reference(store, "AAATTT")
        aligned = tools.execute("sequence.align", {"query_ref": a["id"], "reference_ref": reference["id"],
            "molecule": "dna", "mode": "local"}, operation_key="partial-read-comparison")
        assert aligned["status"] == "completed", aligned
        observation = store.get(aligned["result"]["observation_ref"])
        assert aligned["result"]["query_interval"] == [3, 9]
        assert aligned["result"]["query_coverage"] == .5
        _commit_native(store, a["id"], observation["id"], key="actual-member-extent")
        measured = project_credit(store, details_limit=10)
        assert measured.targets[0]["projected_footprint_units"] == 6
        assert measured.source_contributions[0]["weight"] == 1
        b_footprint = [{**store.coverage(b["id"])[0], "start": 2, "end": 10}]
        initial = _commit_native(store, b["id"], observation["id"], key="infer-member-b", footprint=b_footprint,
            extent_basis="inferred_extent", applicability="transfer")
        inferred = project_credit(store, details_limit=10)
        b_rows = [row for row in inferred.source_contributions if row["member_ref"] == b["member_ref"]]
        assert len(b_rows) == 1 and b_rows[0]["weight"] == .6*.5
        assert b_rows[0]["source_operand_mappings"][0]["physical_source_segments"] == [
            {"subject_ref": a["id"], "start": 3, "end": 9, "unit": "nt", "strand": "+"}]
        scoped_span = {**store.coverage(b["id"])[0], "start": 4, "end": 8}
        fixed_child = {"subject_refs": [target["id"]], "segments": [scoped_span]}
        local = project_credit(store, fixed_child, details_limit=10)
        assert local.targets[0]["scoped_length"] == local.targets[0]["projected_footprint_units"] == 4
        assert local.credit == pytest.approx(100*softened_hypervolume({"comparative": .6*.5}))
        assert local.source_contributions[0]["contributing_segments"] == [scoped_span]
        controller = YieldController("fixed-original-members", measured.credit, .001)
        assert controller.observe("reason:explicit-cross-member-inference", inferred).marginal_credit > 0
        _commit_native(store, b["id"], observation["id"], key="correct-to-observed-member", revision=1,
            hypothesis=initial["aliases"]["candidate"], footprint=b_footprint)
        corrected = project_credit(store, details_limit=10)
        assert corrected.credit == measured.credit
        assert controller.observe("reason:correct-attribution", corrected).marginal_credit == measured.credit-inferred.credit
        assert store.get(observation["id"]) == observation


def test_real_store_translated_read_exact_residue_extent_not_fractionally_scaled(tmp_path):
    from gene_annotation_episode.state import Store
    with Store(tmp_path / "native") as store:
        target, (a, _), tools = _native_fixture(store, tmp_path)
        translated = tools.execute("sequence.translate", {"subject_ref": a["id"], "code": 11})
        assert translated["status"] == "completed", translated
        product = translated["result"]["records"][0]["product_ref"]
        reference = _reference(store, "KF", "protein")
        aligned = tools.execute("sequence.align", {"query_ref": product, "reference_ref": reference["id"],
            "molecule": "protein", "mode": "local"})
        assert aligned["status"] == "completed", aligned
        _commit_native(store, product, aligned["result"]["observation_ref"], key="translated-read-region")
        projected = project_credit(store, details_limit=10)
        assert projected.targets[0]["projected_footprint_units"] == 6
        row, = projected.source_contributions
        assert row["weight"] == 1 and row["member_ref"] == a["member_ref"]
        assert row["contributing_segments"] == [{"target_ref": target["id"], "member_ref": a["member_ref"],
            "start": 3, "end": 9, "unit": "nt"}]
        assert row["native_query_interval"] == {"start": 1, "end": 3, "unit": "aa"}


def test_real_scalar_summary_and_detail_page_preserve_frozen_nondefault_policy(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path / "scalar") as store:
        target = store.create_problem(raw_sequence="ATGAAATTTGGG", molecule="dna")["subject_refs"][0]
        reference = _reference(store, "ATGAAATTTGGG")
        aligned = ToolRegistry(store).execute("sequence.align", {"query_ref": target,
            "reference_ref": reference["id"], "molecule": "dna", "mode": "global"})
        assert aligned["status"] == "completed", aligned
        _commit_native(store, target, aligned["result"]["observation_ref"], key="scalar-comparison")
        policy = CreditPolicy(epsilon=.37, scale=7., applicability_weights={
            "direct": .8, "transfer": .4, "contextual": .2, "scope_limited": .1, "incomparable": 0.})
        full = project_credit(store, policy=policy)
        summary = project_credit(store, policy=policy, details_limit=0)
        page = project_credit(store, policy=policy, details_limit=1)
        assert summary.credit == page.credit == full.credit
        assert summary.axis_components == page.axis_components == full.axis_components
        assert page.as_record()["policy"] == full.as_record()["policy"] == policy.as_record()
        assert page.source_contributions[0]["assessment_ref"] == full.source_contributions[0]["assessment_ref"]
