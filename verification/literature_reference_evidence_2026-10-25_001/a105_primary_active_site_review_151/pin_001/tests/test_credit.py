"""Scientific state/credit integration cases, without a model or external call."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from contextlib import nullcontext
import sqlite3
import weakref
import json

import pytest

from gene_annotation_episode.credit import (
    AXES, CreditPolicy, project_credit, softened_hypervolume,
)
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.domain import ContractError


class StoreView:
    """Test-only current-state facade using the single production protocol.

    SQLite and the same mask/scope helpers provide scalar/native geometry. The
    small scientific rows below are fixture inputs, not a legacy projection API.
    """

    def __init__(self, *, length=100, molecule="protein"):
        self.inputs = [{"id": "input:q", "length": length, "molecule": molecule,
                        "unit": "aa" if molecule == "protein" else "nt", "record_type": "input"}]
        self.annotations = []
        self.assessments = []
        self.records = {}
        self.db = sqlite3.connect("")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE material_members(id TEXT PRIMARY KEY,collection_ref TEXT,ordinal INTEGER,data TEXT)")
        weakref.finalize(self, self.db.close)

    def read_snapshot(self):
        return nullcontext()

    def targets(self):
        return deepcopy(self.inputs)

    def problem(self):
        return {"subject_refs": [row["id"] for row in self.inputs]}

    def get_input(self, ref):
        from gene_annotation_episode.domain import ContractError
        for row in self.inputs:
            if row["id"] == ref:
                return deepcopy(row)
        raise ContractError("unknown_input")

    def iter_current_annotations(self, scope=None):
        yield from deepcopy(self.annotations)

    def current_assessment_subset(self, refs):
        rows = self.assessments.values() if isinstance(self.assessments, dict) else self.assessments
        return {row["id"]: deepcopy(row) for row in rows if row["id"] in refs}

    def current_assessments(self, scope=None, limit=None, offset=0):
        """Current synthetic rows through the production bounded-page port."""
        normalized = self.validate_scope(scope) if scope is not None else None
        if limit is not None and (type(limit) is not int or limit < 0
                or type(offset) is not int or offset < 0):
            raise ContractError("invalid_page")
        rows = self.assessments.values() if isinstance(self.assessments, dict) else self.assessments
        selected = []
        for row in rows:
            if normalized is not None:
                if "context_account_scope" in row:
                    if not self.context_mask_overlap(row["context_account_scope"], normalized):
                        continue
                else:
                    hypothesis = self.get(row["hypothesis_ref"])
                    spans = [span for ref in hypothesis["subject_refs"]
                             if self.get(ref)["record_type"] in {"input", "read_subject", "feature", "product"}
                             for span in self.coverage(ref)]
                    roots = sorted({span["target_ref"] for span in spans})
                    if not set(roots) <= set(normalized["subject_refs"]):
                        continue
                    if spans and not self.context_mask_overlap({"subject_refs": roots,
                            "segments": spans}, normalized):
                        continue
            selected.append(row)
        from gene_annotation_episode.state import Store
        selected = sorted(selected, key=lambda row: Store.assessment_key(self, row))
        return deepcopy(selected if limit is None else selected[offset:offset+limit])

    def get(self, ref):
        for row in self.inputs:
            if row["id"] == ref:
                return deepcopy(row)
        if ref == "external:reference":
            return {"id": ref, "record_type": "reference"}
        return deepcopy(self.records[ref])

    def _require(self, ref, kinds=None):
        from gene_annotation_episode.domain import ContractError
        try:
            row = self.get(ref)
        except KeyError as error:
            raise ContractError("unknown_reference") from error
        if kinds is not None and row["record_type"] not in kinds:
            raise ContractError("reference_type_mismatch")
        return row

    @staticmethod
    def _unit(molecule):
        return "aa" if molecule == "protein" else "nt" if molecule in {"dna", "rna"} else "symbol"

    @staticmethod
    def _merge_segments(spans):
        from gene_annotation_episode.state import Store
        return Store._merge_segments(spans)

    @staticmethod
    def _covered_by(spans, allowed):
        from gene_annotation_episode.state import Store
        return Store._covered_by(spans, allowed)

    def validate_scope(self, scope=None, parent_scope=None):
        from gene_annotation_episode import library_targets
        return library_targets.validate_scope(self, scope, parent_scope)

    def scope_measure(self, scope, target_ref):
        from gene_annotation_episode import library_targets
        return library_targets.measure(self, scope, target_ref)

    def footprint_dimension(self, span):
        from gene_annotation_episode import library_targets
        return library_targets.footprint_dimension(self, span)

    def scope_dimension_segments(self, scope, dimension_ref):
        from gene_annotation_episode import library_targets
        return library_targets.dimension_segments(self, scope, dimension_ref)

    def normalize_context_mask(self, mask):
        from gene_annotation_episode import context_masks
        return context_masks.normalize(self, mask)

    def context_mask_identity(self, mask):
        from gene_annotation_episode import context_masks
        return context_masks.identity_digest(self, mask)

    def context_mask_measure(self, mask, target_ref):
        from gene_annotation_episode import context_masks
        return context_masks.measure(self, mask, target_ref)

    def context_mask_subset(self, left, right):
        from gene_annotation_episode import context_masks
        return context_masks.subset(self, left, right)

    def context_mask_overlap(self, left, right):
        from gene_annotation_episode import context_masks
        return context_masks.overlap(self, left, right)

    def context_mask_target_full(self, mask, target_ref):
        from gene_annotation_episode import context_masks
        return context_masks.target_full(self, mask, target_ref)

    def context_mask_target_query(self, mask, target_ref):
        from gene_annotation_episode import context_masks
        return context_masks.target_query(self, mask, target_ref)

    def context_mask_dimension_segments(self, mask, dimension_ref):
        from gene_annotation_episode import context_masks
        return context_masks.dimension_segments(self, mask, dimension_ref)

    def coverage(self, ref):
        row = self.get(ref)
        if row["record_type"] == "input":
            return [{"target_ref": ref, "start": 0, "end": row["length"], "unit": row["unit"]}]
        return deepcopy(row["footprint"])


def add_interpretation(store, kind="alignment", *, disposition="supported",
        relation="strengthens", applicability="direct", extent_basis="observed_extent", key="a", source=None,
        start=0, end=None, target="input:q", footprint_kind="localized"):
    unit = next(row["unit"] for row in store.inputs if row["id"] == target)
    length = next(row["length"] for row in store.inputs if row["id"] == target)
    observation_ref = f"observation:{key}"
    assessment_ref = f"assessment:{key}"
    hypothesis_ref = f"hypothesis:{key}"
    store.records[hypothesis_ref] = {"id": hypothesis_ref, "record_type": "hypothesis",
                                    "subject_refs": [target]}
    store.records[observation_ref] = {"id": observation_ref, "kind": kind,
        "source_ref": source or f"source:{key}", "origin": "tool",
        "subject_refs": [target], "source_subject_refs": [target, "external:reference"]}
    store.assessments.append({"extent_basis": extent_basis, "id": assessment_ref, "hypothesis_ref": hypothesis_ref,
        "observation_ref": observation_ref, "relation": relation,
        "applicability": applicability, "condition_refs": [], "assumption_refs": []})
    interpretation = {"hypothesis_ref": hypothesis_ref, "disposition": disposition,
                      "assessment_refs": [assessment_ref]}
    annotation = {"id": f"annotation:{key}", "subject_ref": target, "revision": 1,
        "footprint_kind": footprint_kind,
        "footprint": [{"target_ref": target, "start": start,
                       "end": length if end is None else end, "unit": unit}],
        "coherent_sets": [{"id": f"coherent:{key}", "interpretations": [interpretation],
                           "context_refs": []}],
        "alternative_refs": [], "resolution": "selected"}
    store.annotations.append(annotation)
    return annotation, interpretation


def test_softened_volume_zero_baseline_no_missing_axis_veto_and_continuity():
    assert softened_hypervolume({}) == 0
    assert softened_hypervolume(dict.fromkeys(AXES, 1)) == 1
    single = softened_hypervolume({"comparative": .8})
    assert single > 0
    assert softened_hypervolume({"comparative": .8, "biological_context": .2}) > single
    assert softened_hypervolume({"comparative": .8000001}) == pytest.approx(single, abs=1e-8)


def test_reasoning_can_gain_from_existing_evidence_and_correction_remains_signed():
    store = StoreView()
    annotation, interpretation = add_interpretation(store)
    actual_assessments = store.assessments
    store.assessments = []
    # Same observations before and after. An unassessed tool result contributes
    # nothing; an actual source-linked interpretation makes its meaning current.
    assert project_credit(store).credit == 0
    store.assessments = actual_assessments
    explained = project_credit(store)
    assert explained.credit > 0
    controller = YieldController("fixed-episode", explained.credit, .001)
    # Correcting false direct attribution can remove prior support. No plateau
    # clamp or synthetic positive award conceals that actual correction.
    store.assessments[0]["applicability"] = "incomparable"
    corrected = project_credit(store)
    assert corrected.credit == 0
    step = controller.observe("reasoning:correct-attribution", corrected)
    assert step.marginal_credit == -explained.credit
    assert controller.estimator.scores == (-explained.credit,)


def test_grounded_refutation_and_provisional_alternatives_can_earn_progress():
    store = StoreView()
    _, interpretation = add_interpretation(store, "assay_report", relation="weakens")
    positive_claim = project_credit(store)
    assert positive_claim.credit == 0  # contradicted claim has no positive support
    interpretation["disposition"] = "unresolved"
    provisional = project_credit(store)
    assert provisional.credit > 0
    interpretation["disposition"] = "weakened"
    weakened = project_credit(store)
    assert weakened.credit > provisional.credit
    assert weakened.axis_components["empirical"] == 1
    assert weakened.axis_components["discrimination"] == 1
    assert weakened.source_contributions[0]["source_subject_refs"] == [
        "input:q", "external:reference"]


def test_compatible_evidence_combines_but_incompatible_alternatives_do_not():
    store = StoreView()
    first, a = add_interpretation(store, "alignment", key="comparison")
    second, b = add_interpretation(store, "mechanism", key="mechanism")
    separate = project_credit(store)
    first["coherent_sets"].append(second["coherent_sets"][0])
    store.annotations = [first]
    alternatives = project_credit(store)
    assert alternatives.credit == separate.credit
    first["coherent_sets"] = [{"id": "coherent:compatible",
                              "interpretations": [a, b], "context_refs": []}]
    compatible = project_credit(store)
    assert compatible.credit > alternatives.credit
    assert compatible.axis_components["comparative"] == 1
    assert compatible.axis_components["mechanistic"] == 1


def test_duplicate_source_records_assessments_and_renamed_hypotheses_do_not_inflate():
    store = StoreView()
    first, a = add_interpretation(store, source="source:same", key="original")
    initial = project_credit(store).credit
    second, b = add_interpretation(store, source="source:same", key="renamed")
    first["coherent_sets"][0]["interpretations"].append(b)
    store.annotations.append(deepcopy(first))
    assert project_credit(store).credit == initial
    # Opposing evidence is also a maximum, not repeated penalties for copies.
    store.assessments[0]["relation"] = "weakens"
    store.assessments[1]["relation"] = "weakens"
    a["disposition"] = "weakened"
    b["disposition"] = "weakened"
    one = project_credit(store).credit
    store.assessments.extend(deepcopy(store.assessments))
    assert project_credit(store).credit == one


def test_genome_locus_uses_fixed_original_units_and_whole_context_preserves_native_axes():
    store = StoreView(length=10000, molecule="dna")
    annotation, _ = add_interpretation(store, end=1000)
    locus = project_credit(store)
    whole = StoreView(length=1000, molecule="dna")
    add_interpretation(whole)
    assert locus.credit == pytest.approx(project_credit(whole).credit / 10)
    assert locus.targets[0]["projected_footprint_units"] == 1000
    assert locus.targets[0]["unit"] == "nt"
    # Whole-context presentation must preserve the actual source evidence axis.
    annotation["footprint_kind"] = "whole_input_context"
    annotation["footprint"][0]["end"] = 10000
    assert project_credit(store).credit > 0
    assert project_credit(store).axis_components["comparative"] > 0
    store.records["observation:a"]["kind"] = "context"
    context = project_credit(store)
    assert context.credit > 0
    assert context.axis_components["comparative"] == 0
    assert context.axis_components["biological_context"] == 1
    protein = StoreView(length=100)
    add_interpretation(protein, end=50)
    assert project_credit(protein).targets[0]["unit"] == "aa"
    assert project_credit(protein).targets[0]["projected_footprint_units"] == 50


def test_fixed_input_targets_weights_and_scope_never_expand_with_new_candidates():
    store = StoreView()
    store.inputs.append({"id": "input:other", "length": 100, "unit": "aa", "record_type": "input"})
    add_interpretation(store)
    both = project_credit(store)
    scoped = project_credit(store, {"subject_refs": ["input:q"]})
    assert both.credit == scoped.credit / 2
    assert project_credit(store, policy=CreditPolicy(
        target_weights=(("input:q", 3), ("input:other", 1)))).credit == pytest.approx(scoped.credit*.75)
    with pytest.raises(ContractError, match="^unknown_or_empty_scope$"):
        project_credit(store, {"subject_refs": ["external:new-candidate"]})


def test_parent_fixed_region_has_local_denominator_and_ancestor_keeps_whole_input():
    store = StoreView(length=10000, molecule="dna")
    add_interpretation(store, start=2000, end=3000)
    fixed_scope = {"subject_refs": ["input:q"], "segments": [
        {"target_ref": "input:q", "start": 2000, "end": 3000, "unit": "nt"}]}
    root = project_credit(store)
    child = project_credit(store, fixed_scope)
    assert child.credit == pytest.approx(root.credit * 10)
    assert child.targets[0]["length"] == 10000
    assert child.targets[0]["scoped_length"] == 1000
    assert child.targets[0]["projected_footprint_units"] == 1000
    # Newly interpreted work outside that assignment can refresh the ancestor
    # projection, but it never enlarges this child's fixed credit denominator.
    add_interpretation(store, "mechanism", start=4000, end=5000, key="outside")
    assert project_credit(store).credit > root.credit
    assert project_credit(store, fixed_scope).as_record() == child.as_record()
    overlap_scope = {"subject_refs": ["input:q"], "segments": [
        {"target_ref": "input:q", "start": 2000, "end": 2700, "unit": "nt"},
        {"target_ref": "input:q", "start": 2500, "end": 3000, "unit": "nt"}]}
    assert project_credit(store, overlap_scope).credit == child.credit


def test_broad_annotation_cannot_expand_local_hypothesis_or_observation_coverage():
    store = StoreView(length=1000, molecule="dna")
    annotation, _ = add_interpretation(store)
    full = project_credit(store).credit
    store.records["feature:local"] = {"id": "feature:local", "record_type": "feature",
        "footprint": [{"target_ref": "input:q", "start": 100, "end": 200, "unit": "nt"}]}
    store.records["hypothesis:a"]["subject_refs"] = ["feature:local"]
    local_hypothesis = project_credit(store)
    assert local_hypothesis.credit == pytest.approx(full*.1)
    assert local_hypothesis.targets[0]["projected_footprint_units"] == 100
    store.records["hypothesis:a"]["subject_refs"] = ["input:q"]
    store.records["observation:a"]["subject_refs"] = ["feature:local"]
    assert project_credit(store).credit == local_hypothesis.credit
    store.records["observation:a"]["subject_refs"] = ["input:q"]
    store.records["observation:a"]["source_subject_refs"] = ["feature:local", "external:reference"]
    assert project_credit(store).credit == local_hypothesis.credit
    store.records["hypothesis:a"]["subject_refs"] = ["external:reference"]
    unrelated = project_credit(store)
    assert unrelated.credit == 0
    assert unrelated.targets[0]["inactive_dependencies"][0]["reason"] == \
        "hypothesis_has_no_submitted_target_coverage"


def test_compatible_evidence_on_disjoint_loci_does_not_create_spatial_frankenstein():
    store = StoreView(length=1000, molecule="dna")
    first, a = add_interpretation(store, "assay_report", key="empirical")
    second, b = add_interpretation(store, "comparison", key="comparative")
    for key, start in (("empirical", 100), ("comparative", 500)):
        feature = "feature:" + key
        store.records[feature] = {"id": feature, "record_type": "feature", "footprint": [
            {"target_ref": "input:q", "start": start, "end": start+100, "unit": "nt"}]}
        store.records["observation:" + key]["subject_refs"] = [feature]
    first["coherent_sets"][0]["interpretations"] = [a, b]
    store.annotations = [first]
    result = project_credit(store)
    expected = 100 * .2 * softened_hypervolume({"comparative": 1})
    assert result.credit == pytest.approx(expected)
    assert result.axis_components["empirical"] == .1
    assert result.axis_components["comparative"] == .1


def test_native_input_query_interval_is_exact_and_unmapped_product_extent_is_declared():
    store = StoreView(length=100)
    add_interpretation(store)
    observation = store.records["observation:a"]
    observation["measurements"] = [
        {"name": "query_start", "value": {"type": "number", "value": 20, "unit_ref": None}},
        {"name": "query_end", "value": {"type": "number", "value": 40, "unit_ref": None}},
        {"name": "query_coverage", "value": {"type": "number", "value": .2, "unit_ref": None}}]
    exact = project_credit(store)
    assert exact.targets[0]["projected_footprint_units"] == 20
    assert exact.source_contributions[0]["extent_mode"] == "native_input_query_interval"
    assert exact.source_contributions[0]["contributing_segments"] == [{"start": 20, "end": 40}]
    store.records["product:query"] = {"id": "product:query", "record_type": "product", "footprint": [
        {"target_ref": "input:q", "start": 0, "end": 100, "unit": "aa"}]}
    observation["subject_refs"] = ["product:query"]
    inferred = project_credit(store)
    assert inferred.targets[0]["projected_footprint_units"] == 100
    assert inferred.source_contributions[0]["extent_mode"] == \
        "fractional_query_coverage_without_residue_map"
    assert inferred.axis_components["comparative"] == .2
    assert inferred.source_contributions[0]["weight"] == .2


@pytest.mark.parametrize("strand,expected", [
    ("+", [{"start": 16, "end": 25}]),
    ("-", [{"start": 55, "end": 64}]),
])
def test_exact_product_query_extent_uses_original_path_without_second_coverage_factor(
        strand, expected):
    from gene_annotation_episode.sequence_mapping import VERSION, map_interval

    class MappedView(StoreView):
        def has_exact_mapping(self, ref):
            return ref == "product:query"

        def sequence_mapping(self, ref):
            assert ref == "product:query"
            return {"version": VERSION, "units_per_symbol": 3, "symbol_length": 20,
                "path": [{"subject_ref": "input:q", "start": 10, "end": 70,
                          "unit": "nt", "strand": strand}]}

        def map_segments(self, ref, segments):
            return [{"target_ref": row["subject_ref"], "start": row["start"],
                     "end": row["end"], "unit": row["unit"]}
                for segment in segments for row in map_interval(
                    self.sequence_mapping(ref), segment["start"], segment["end"])]

    store = MappedView(length=100, molecule="dna")
    add_interpretation(store)
    store.records["product:query"] = {"id": "product:query", "record_type": "product",
        "footprint": [{"target_ref": "input:q", "start": 10, "end": 70, "unit": "nt"}]}
    store.records["observation:a"].update(subject_refs=["product:query"], measurements=[
        {"name": "query_start", "value": {"type": "number", "value": 2, "unit_ref": None}},
        {"name": "query_end", "value": {"type": "number", "value": 5, "unit_ref": None}},
        {"name": "query_coverage", "value": {"type": "number", "value": .15, "unit_ref": None}}])
    projected = project_credit(store)
    assert projected.targets[0]["projected_footprint_units"] == 9
    assert projected.axis_components["comparative"] == pytest.approx(.09)
    source = projected.source_contributions[0]
    assert source["extent_mode"] == "native_query_interval_mapped_to_original_input"
    assert source["native_query_interval"] == {"start": 2, "end": 5, "unit": "aa"}
    assert source["unit"] == "nt"
    assert source["query_coverage"] == .15
    assert source["weight"] == 1
    assert source["contributing_segments"] == expected
    assert source["mapping_subject_ref"] == "product:query"
    assert source["mapping_version"] == VERSION


def test_exact_query_crossing_compound_path_retains_disjoint_original_segments():
    from gene_annotation_episode.sequence_mapping import VERSION, map_interval

    class CompoundView(StoreView):
        def has_exact_mapping(self, ref):
            return ref == "feature:query"

        def sequence_mapping(self, ref):
            assert ref == "feature:query"
            return {"version": VERSION, "units_per_symbol": 3, "symbol_length": 3,
                "path": [{"subject_ref": "input:q", "start": 10, "end": 14, "unit": "nt", "strand": "+"},
                         {"subject_ref": "input:q", "start": 50, "end": 55, "unit": "nt", "strand": "-"}]}

        def map_segments(self, ref, segments):
            return [{"target_ref": row["subject_ref"], "start": row["start"],
                     "end": row["end"], "unit": row["unit"]}
                for segment in segments for row in map_interval(
                    self.sequence_mapping(ref), segment["start"], segment["end"])]

    store = CompoundView(length=100, molecule="dna")
    add_interpretation(store)
    store.records["feature:query"] = {"id": "feature:query", "record_type": "feature", "footprint": [
        {"target_ref": "input:q", "start": 10, "end": 14, "unit": "nt"},
        {"target_ref": "input:q", "start": 50, "end": 55, "unit": "nt"}]}
    store.records["observation:a"].update(subject_refs=["feature:query"], measurements=[
        {"name": "query_start", "value": {"type": "number", "value": 1, "unit_ref": None}},
        {"name": "query_end", "value": {"type": "number", "value": 2, "unit_ref": None}},
        {"name": "query_coverage", "value": {"type": "number", "value": 1/3, "unit_ref": None}}])
    projected = project_credit(store)
    assert projected.targets[0]["projected_footprint_units"] == 3
    assert projected.axis_components["comparative"] == pytest.approx(.03)
    segments = [span for row in projected.source_contributions for span in row["contributing_segments"]]
    assert segments == [{"start": 13, "end": 14}, {"start": 53, "end": 55}]
    assert all(row["weight"] == 1 for row in projected.source_contributions)


def test_tool_observation_of_external_subject_does_not_borrow_native_query_coordinates():
    store = StoreView(length=1000, molecule="dna")
    add_interpretation(store, "comparison", applicability="transfer", extent_basis="inferred_extent")
    store.records["observation:a"].update(subject_refs=["external:reference"],
        source_subject_refs=["external:reference"], measurements=[
            {"name": "query_start", "value": {"type": "number", "value": 1500, "unit_ref": None}},
            {"name": "query_end", "value": {"type": "number", "value": 1700, "unit_ref": None}},
            {"name": "query_coverage", "value": {"type": "number", "value": .4, "unit_ref": None}}])
    store.has_exact_mapping = lambda ref: pytest.fail("external source has no native input mapping")
    store.assessments[0]["target_footprint"] = [
        {"target_ref": "input:q", "start": 200, "end": 300, "unit": "nt"}]
    projection = project_credit(store)
    assert projection.targets[0]["projected_footprint_units"] == 100
    assert projection.source_contributions[0]["extent_mode"] == "assessment_inferred_target_extent"
    assert projection.source_contributions[0]["weight"] == pytest.approx(.6 * .4)


def test_native_operand_intervals_cover_both_inputs_independently():
    store = StoreView(length=100)
    store.inputs.append({"id": "input:r", "length": 100, "unit": "aa", "record_type": "input"})
    add_interpretation(store)
    add_interpretation(store, key="reference", target="input:r")
    observation = store.records["observation:a"]
    observation["source_subject_refs"] = ["input:r"]
    observation["operand_intervals"] = [
        {"role": "query", "subject_ref": "input:q", "start": 20, "end": 30, "unit": "aa"},
        {"role": "reference", "subject_ref": "input:r", "start": 60, "end": 70, "unit": "aa"}]
    store.assessments[1]["observation_ref"] = "observation:a"
    for target, expected in [("input:q", {"start": 20, "end": 30}),
                             ("input:r", {"start": 60, "end": 70})]:
        projection = project_credit(store, {"subject_refs": [target]})
        assert projection.targets[0]["projected_footprint_units"] == 10
        assert projection.source_contributions[0]["contributing_segments"] == [expected]
        assert projection.source_contributions[0]["weight"] == 1


def test_native_sites_keep_disjoint_extent_and_explicit_unexamined_state():
    store = StoreView(length=100)
    add_interpretation(store, "mechanism")
    observation = store.records["observation:a"]
    observation["operand_intervals"] = [
        {"role": "query", "subject_ref": "input:q", "start": 2, "end": 3, "unit": "aa"},
        {"role": "query", "subject_ref": "input:q", "start": 5, "end": 6, "unit": "aa"}]
    measured = project_credit(store)
    assert measured.targets[0]["projected_footprint_units"] == 2
    assert [span for row in measured.source_contributions for span in row["contributing_segments"]] == [
        {"start": 2, "end": 3}, {"start": 5, "end": 6}]
    observation["operand_intervals"] = []
    assert project_credit(store).credit == 0
    store.assessments[0]["target_footprint"] = [
        {"target_ref": "input:q", "start": 0, "end": 100, "unit": "aa"}]
    assert project_credit(store).credit == 0


def test_legacy_query_proxy_does_not_rescale_exact_other_operand():
    store = StoreView(length=100)
    store.inputs.append({"id": "input:r", "length": 100, "unit": "aa", "record_type": "input"})
    add_interpretation(store)
    add_interpretation(store, key="reference", target="input:r")
    store.records["product:legacy"] = {"id": "product:legacy", "record_type": "product",
        "footprint": [{"target_ref": "input:q", "start": 0, "end": 100, "unit": "aa"}]}
    store.records["observation:a"].update(subject_refs=["product:legacy"], source_subject_refs=["input:r"],
        measurements=[{"name": "query_coverage", "value": {"type": "number", "value": .2, "unit_ref": None}},
                      {"name": "target_coverage", "value": {"type": "number", "value": .1, "unit_ref": None}}],
        operand_intervals=[
            {"role": "query", "subject_ref": "product:legacy", "start": 2, "end": 4, "unit": "aa"},
            {"role": "reference", "subject_ref": "input:r", "start": 60, "end": 70, "unit": "aa"}])
    store.assessments[1]["observation_ref"] = "observation:a"
    query = project_credit(store, {"subject_refs": ["input:q"]})
    assert query.targets[0]["projected_footprint_units"] == 100
    assert query.source_contributions[0]["weight"] == .2
    assert query.source_contributions[0]["extent_mode"] == "fractional_query_coverage_without_residue_map"
    reference = project_credit(store, {"subject_refs": ["input:r"]})
    assert reference.targets[0]["projected_footprint_units"] == 10
    assert reference.source_contributions[0]["weight"] == 1
    assert reference.source_contributions[0]["contributing_segments"] == [{"start": 60, "end": 70}]


def _sequence_reference_fixture(store, sequence, accession):
    artifact = store.artifact(f"Synthetic sequence fixture {accession}: {sequence}")
    source = store.put("source", {"provider": "synthetic_fixture", "accession": accession,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="external")
    return store.put("reference", {"reference_type": "dna" if accession.endswith("dna") else "protein",
        "source_ref": source["id"], "accession": accession, "label": "synthetic sequence fixture",
        "sequence_ref": store.artifact(sequence), "molecule": "dna" if accession.endswith("dna") else "protein",
        "length": len(sequence), "term_refs": [], "context_refs": []}, origin="external")


def _commit_comparison_fixture(store, scope, subject, observation, reference, *,
        footprint=None, hypothesis=None, revision=0, assessment_revision=None,
        operation="interpret-comparison", extent_basis="observed_extent",
        applicability="transfer", relation="strengthens", disposition="supported"):
    assessment = {"extent_basis": extent_basis, "alias": "basis", "hypothesis_ref": hypothesis or "@candidate",
        "observation_ref": observation, "relation": relation, "applicability": applicability,
        "condition_refs": [], "assumption_refs": [],
        "expected_revision": revision if assessment_revision is None else assessment_revision}
    if footprint is not None:
        assessment["target_footprint"] = footprint
    payload = {"structural_proposals": [], "terms": [], "source_subjects": [], "observations": [],
        "hypotheses": [] if hypothesis else [{"alias": "candidate", "subject_refs": [subject],
            "predicate": "functional_family", "value": {"type": "reference", "ref": reference}, "context_refs": []}],
        "assessments": [assessment], "annotation_updates": [{"alias": "current", "subject_ref": subject,
            "expected_revision": revision, "footprint_kind": "localized", "coherent_sets": [{
                "interpretations": [{"hypothesis_ref": hypothesis or "@candidate", "disposition": disposition,
                                     "assessment_refs": ["@basis"]}], "context_refs": []}],
            "alternative_refs": [], "resolution": "selected"}]}
    result = store.commit_reasoning(payload, scope, operation)
    assert result["status"] == "completed", result
    return result


@pytest.mark.parametrize("molecule", ["protein", "unspecified"])
def test_real_external_query_input_reference_is_bounded_by_native_reference_interval(tmp_path, molecule):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / "reference-operand") as store:
        target = store.create_problem(raw_sequence="MMADFKGWW", molecule=molecule,
                                      role="protein" if molecule == "protein" else "unspecified")["subject_refs"][0]
        unit = "aa" if molecule == "protein" else "symbol"
        scope = {"subject_refs": [target]}
        query = _sequence_reference_fixture(store, "DF", "fixture:query")
        tools = ToolRegistry(store)
        aligned = tools.execute("sequence.align", {"query_ref": query["id"], "reference_ref": target,
            "molecule": "protein", "mode": "local"}, scope=scope, operation_key="external-query-native-reference")
        assert aligned["status"] == "completed", aligned
        observation = store.get(aligned["result"]["observation_ref"])
        assert observation["subject_refs"] == [query["id"]]
        assert observation["source_subject_refs"] == [target]
        assert observation["operand_intervals"] == [
            {"role": "query", "subject_ref": query["id"], "start": 0, "end": 2, "unit": "aa", "model_unit": "aa"},
            {"role": "reference", "subject_ref": target, "start": 3, "end": 5, "unit": unit, "model_unit": "aa"}]
        assert project_credit(store, scope).credit == 0
        _commit_comparison_fixture(store, scope, target, observation["id"], query["id"], footprint=[
            {"target_ref": target, "start": 0, "end": 9, "unit": unit}])
        projection = project_credit(store, scope)
        assert projection.targets[0]["projected_footprint_units"] == 2
        assert projection.source_contributions[0]["contributing_segments"] == [{"start": 3, "end": 5}]
        assert projection.source_contributions[0]["native_reference_interval"] == {"start": 3, "end": 5, "unit": unit}
        assert projection.source_contributions[0]["native_operand_interval"]["model_unit"] == "aa"
        assert projection.source_contributions[0]["unit"] == unit
        assert store.get_input(target)["molecule"] == molecule
        assert projection.source_contributions[0]["extent_mode"] == "native_reference_interval_mapped_to_original_input"
        assert projection.credit == pytest.approx(100 * 2/9 * softened_hypervolume({"comparative": .6}))
        assert store.get(observation["id"]) == observation


def test_real_external_query_reference_sites_are_disjoint_or_explicitly_unexamined(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / "native-reference-sites") as store:
        target = store.create_problem(raw_sequence="MMADFKGWW", molecule="protein", role="protein")["subject_refs"][0]
        scope = {"subject_refs": [target]}
        query = _sequence_reference_fixture(store, "DFKG", "fixture:query")
        tools = ToolRegistry(store)
        aligned = tools.execute("sequence.align", {"query_ref": query["id"], "reference_ref": target,
            "molecule": "protein", "mode": "local"}, scope=scope, operation_key="align-for-sites")
        assert aligned["status"] == "completed", aligned
        measured = tools.execute("sequence.sites", {"alignment_ref": aligned["result"]["observation_ref"],
            "positions": [3, 6]}, scope=scope, operation_key="inspect-mapped-sites")
        assert measured["status"] == "completed", measured
        observation = store.get(measured["result"]["observation_ref"])
        assert observation["kind"] == "comparison"
        reference_intervals = [row for row in observation["operand_intervals"] if row["role"] == "reference"]
        assert [(row["start"], row["end"]) for row in reference_intervals] == [(3, 4), (6, 7)]
        footprint = [{"target_ref": target, "start": 0, "end": 9, "unit": "aa"}]
        committed = _commit_comparison_fixture(store, scope, target, observation["id"], query["id"],
            footprint=footprint, operation="interpret-mapped-sites")
        before = project_credit(store, scope)
        assert before.targets[0]["projected_footprint_units"] == 2
        assert [span for row in before.source_contributions for span in row["contributing_segments"]] == [
            {"start": 3, "end": 4}, {"start": 6, "end": 7}]
        assert before.credit == pytest.approx(100 * 2/9 * softened_hypervolume({"comparative": .6}))
        unexamined = tools.execute("sequence.sites", {"alignment_ref": aligned["result"]["observation_ref"],
            "positions": [0, 8]}, scope=scope, operation_key="inspect-unmapped-sites")
        assert unexamined["status"] == "completed", unexamined
        unexamined_observation = store.get(unexamined["result"]["observation_ref"])
        assert unexamined_observation["operand_intervals"] == []
        _commit_comparison_fixture(store, scope, target, unexamined_observation["id"], query["id"],
            footprint=footprint, hypothesis=committed["aliases"]["candidate"], revision=1,
            assessment_revision=0, operation="record-unexamined-site-basis")
        after = project_credit(store, scope)
        assert after.credit == 0
        assert store.get(observation["id"]) == observation
        controller = YieldController("actual-site-extents", before.credit, .001)
        assert controller.observe("changed-site-basis", after).marginal_credit == -before.credit


@pytest.mark.parametrize("derived", ["reference", "product", "feature"])
def test_real_source_only_query_and_derivation_need_explicit_target_attribution(tmp_path, derived):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / "external-only") as store:
        target = store.create_problem(raw_sequence="AAAA", molecule="protein", role="protein")["subject_refs"][0]
        scope = {"subject_refs": [target]}
        targets_before = store.targets()
        tools = ToolRegistry(store)
        if derived != "reference":
            source_dna = _sequence_reference_fixture(store, "ATGGCTGACTTCAAAGGGTAA", "fixture:source_dna")
            translated = tools.execute("sequence.translate", {"subject_ref": source_dna["id"], "code": 11,
                "strand": "+", "frame": 0, "cds": True}, scope=scope, operation_key="translate-external")
            assert translated["status"] == "completed", translated
            query_ref = translated["result"]["records"][0]["product_ref"]
            assert store.has_exact_mapping(query_ref)
            assert store.coverage(query_ref) == []
            assert store.map_segments(query_ref, [{"start": 2, "end": 4}]) == []
            if derived == "feature":
                query_ref = store.put("feature", {"subject_ref": query_ref, "kind": "protein_domain",
                    "segments": [{"start": 1, "end": 5}], "strand": ".", "context_refs": []},
                    origin="reasoning", scope=scope)["id"]
                assert store.coverage(query_ref) == []
                assert store.has_exact_mapping(query_ref)
            reference = _sequence_reference_fixture(store, "DF", "fixture:fragment")
            expected_coverage = .5 if derived == "feature" else 1/3
        else:
            query_ref = _sequence_reference_fixture(store, "DF", "fixture:query")["id"]
            reference = _sequence_reference_fixture(store, "MMADFKGWW", "fixture:reference")
            expected_coverage = 1.
        aligned = tools.execute("sequence.align", {"query_ref": query_ref, "reference_ref": reference["id"],
            "molecule": "protein", "mode": "local"}, scope=scope, operation_key="align-external")
        assert aligned["status"] == "completed", aligned
        observation = store.get(aligned["result"]["observation_ref"])
        assert observation["subject_refs"] == [query_ref]
        unbound = _commit_comparison_fixture(store, scope, target, observation["id"], reference["id"], extent_basis="inferred_extent")
        assert project_credit(store, scope).credit == 0
        footprint = [{"target_ref": target, "start": 0, "end": 1, "unit": "aa"}]
        _commit_comparison_fixture(store, scope, target, observation["id"], reference["id"],
            footprint=footprint, hypothesis=unbound["aliases"]["candidate"], revision=1,
            operation="attribute-external-comparison", extent_basis="inferred_extent")
        projection = project_credit(store, scope)
        assert projection.targets[0]["projected_footprint_units"] == 1
        assert projection.credit == pytest.approx(100/4 * softened_hypervolume({"comparative": .6*expected_coverage}))
        source = projection.source_contributions[0]
        assert source["extent_mode"] == "assessment_inferred_target_extent"
        assert source["extent_basis"] == "inferred_extent"
        assert source["source_operand_intervals"] == observation["operand_intervals"]
        assert source["contributing_segments"] == [{"start": 0, "end": 1}]
        assert source["weight"] == pytest.approx(.6*expected_coverage)
        if derived != "reference":
            assert source["source_operand_mappings"][0]["physical_source_segments"] == [
                {"subject_ref": source_dna["id"], "start": 6, "end": 12, "unit": "nt", "strand": "+"}]
            assert source["source_operand_intervals"][0]["unit"] == "aa"
            assert source["unit"] == "aa"  # target B, not the measured source DNA
        assert store.get(observation["id"]) == observation
        assert store.targets() == targets_before


@pytest.mark.parametrize("strand,frame,cds,expected", [
    ("+", 0, True, [{"start": 9, "end": 15}]),
    ("-", 0, True, [{"start": 12, "end": 18}]),
    ("+", 1, False, [{"start": 10, "end": 16}]),
])
@pytest.mark.parametrize("on_feature", [False, True])
def test_real_derivation_alignment_credit_maps_exact_query_and_reopens(
        tmp_path, monkeypatch, strand, frame, cds, expected, on_feature):
    """Real local tools/state/projection; synthetic fragment, no biology claim."""
    from Bio.Seq import Seq
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    coding = "ATGGCTGACTTCAAAGGGTAA"  # MADFKG and a terminal stop.
    region = ("C" if frame else "") + coding
    if strand == "-":
        region = str(Seq(region).reverse_complement())
    dna = "GGG" + region + "CCC"
    path = tmp_path / "exact-native"
    with Store(path) as store:
        target = store.create_problem(raw_sequence=dna, molecule="dna", role="gene")["subject_refs"][0]
        scope = {"subject_refs": [target]}
        tools = ToolRegistry(store)
        derived = tools.execute("sequence.translate", {"subject_ref": target,
            "code": 11, "start": 3, "end": 3+len(region), "strand": strand,
            "frame": frame, "cds": cds}, scope=scope, operation_key="native-translate")
        assert derived["status"] == "completed", derived
        product_ref = derived["result"]["records"][0]["product_ref"]
        product = store.get(product_ref)
        assert product["mapping_source_ref"] == derived["result"]["source_ref"]
        assert store.has_exact_mapping(product_ref)
        query_ref = product_ref
        if on_feature:
            query_ref = store.put("feature", {"subject_ref": product_ref, "kind": "protein_domain",
                "segments": [{"start": 1, "end": 5}], "strand": ".", "context_refs": []},
                origin="reasoning", scope=scope)["id"]
        artifact = store.artifact("Synthetic DF fragment for deterministic coordinate validation.")
        source = store.put("source", {"provider": "synthetic_fixture", "accession": "fixture:fragment",
            "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="external")
        reference = store.put("reference", {"reference_type": "protein", "source_ref": source["id"],
            "accession": "fixture:DF", "label": "synthetic fragment", "sequence_ref": store.artifact("DF"),
            "molecule": "protein", "length": 2, "term_refs": [], "context_refs": []}, origin="external")
        aligned = tools.execute("sequence.align", {"query_ref": query_ref,
            "reference_ref": reference["id"], "molecule": "protein", "mode": "local"},
            scope=scope, operation_key="native-alignment")
        assert aligned["status"] == "completed", aligned
        assert aligned["result"]["query_interval"] == ([1, 3] if on_feature else [2, 4])
        assert project_credit(store, scope).credit == 0
        payload = {"structural_proposals": [], "terms": [], "source_subjects": [], "observations": [],
            "hypotheses": [{"alias": "candidate", "subject_refs": [query_ref], "predicate": "functional_family",
                "value": {"type": "reference", "ref": reference["id"]}, "context_refs": []}],
            "assessments": [{"extent_basis": "observed_extent", "alias": "comparison", "hypothesis_ref": "@candidate",
                "observation_ref": aligned["result"]["observation_ref"], "relation": "strengthens",
                "applicability": "direct", "condition_refs": [], "assumption_refs": [], "expected_revision": 0}],
            "annotation_updates": [{"alias": "current", "subject_ref": query_ref, "expected_revision": 0,
                "footprint_kind": "localized", "coherent_sets": [{"interpretations": [
                    {"hypothesis_ref": "@candidate", "disposition": "supported", "assessment_refs": ["@comparison"]}],
                    "context_refs": []}], "alternative_refs": [], "resolution": "selected"}]}
        result = store.commit_reasoning(payload, scope, "interpret-native-comparison")
        assert result["status"] == "completed", result
        monkeypatch.setattr(store, "get_artifact", lambda ref: pytest.fail("credit hydrated sequence/source"))
        projection = project_credit(store, scope)
        assert projection.targets[0]["projected_footprint_units"] == 6
        assert projection.credit == pytest.approx(100 * 6 / len(dna) * softened_hypervolume({"comparative": 1}))
        contribution = projection.source_contributions[0]
        assert contribution["contributing_segments"] == expected
        assert contribution["native_query_interval"] == {
            "start": 1 if on_feature else 2, "end": 3 if on_feature else 4, "unit": "aa"}
        assert contribution["extent_mode"] == "native_query_interval_mapped_to_original_input"
        assert contribution["mapping_subject_ref"] == query_ref
        assert contribution["unit"] == "nt"
        assert contribution["weight"] == 1  # Exact spatial clipping already expresses partial extent.
        frozen = projection.as_record()
        local = project_credit(store, {"subject_refs": [target], "segments": [
            {"target_ref": target, "unit": "nt", **span} for span in expected]})
        assert local.credit == pytest.approx(projection.credit * len(dna)/6)
    with Store(path) as reopened:
        assert project_credit(reopened, scope).as_record() == frozen


@pytest.mark.parametrize("kind,applicability,axis", [
    ("biochemical_assay", "transfer", "empirical"),
    ("context", "contextual", "biological_context"),
])
def test_external_fact_requires_explicit_assessed_extent_and_keeps_source_identity(
        kind, applicability, axis):
    store = StoreView(length=1000, molecule="dna")
    add_interpretation(store, kind, applicability=applicability, extent_basis="inferred_extent")
    observation = store.records["observation:a"]
    observation.update(subject_refs=["external:reference"],
                       source_subject_refs=["external:reference"], origin="external")
    original = deepcopy(observation)
    assert project_credit(store).credit == 0
    store.assessments[0]["target_footprint"] = None
    assert project_credit(store).credit == 0

    footprint = [{"target_ref": "input:q", "start": 200, "end": 300, "unit": "nt"}]
    store.assessments[0]["target_footprint"] = footprint
    projected = project_credit(store)
    strength = dict(CreditPolicy().applicability_weights)[applicability]
    assert projected.credit == pytest.approx(100 * .1 * softened_hypervolume({axis: strength}))
    assert projected.targets[0]["projected_footprint_units"] == 100
    source = projected.source_contributions[0]
    assert source["extent_mode"] == "assessment_inferred_target_extent"
    assert source["assessment_target_footprint"] == footprint
    assert source["observation_subject_refs"] == ["external:reference"]
    assert source["source_subject_refs"] == ["external:reference"]
    assert source["origin"] == "external"
    assert source["applicability"] == applicability
    assert source["contributing_segments"] == [{"start": 200, "end": 300}]
    assert store.records["observation:a"] == original

    # The child's fixed denominator is its assigned interval; it does not
    # retroactively award this locus whole-genome credit to the ancestor.
    child = project_credit(store, {"subject_refs": ["input:q"], "segments": footprint})
    assert child.credit == pytest.approx(projected.credit * 10)
    # Even an explicit target attribution cannot turn an external-only claim
    # into a hypothesis about submitted material.
    store.records["hypothesis:a"]["subject_refs"] = ["external:reference"]
    assert project_credit(store).credit == 0


def test_assessed_extent_intersects_native_observation_and_physical_source_extent():
    store = StoreView(length=100)
    add_interpretation(store)
    observation = store.records["observation:a"]
    observation["measurements"] = [
        {"name": "query_start", "value": {"type": "number", "value": 20, "unit_ref": None}},
        {"name": "query_end", "value": {"type": "number", "value": 40, "unit_ref": None}}]
    original = deepcopy(observation)
    store.assessments[0]["target_footprint"] = [
        {"target_ref": "input:q", "start": 10, "end": 30, "unit": "aa"}]
    bounded = project_credit(store)
    assert bounded.targets[0]["projected_footprint_units"] == 10
    assert bounded.source_contributions[0]["extent_mode"] == "native_input_query_interval"
    assert bounded.source_contributions[0]["contributing_segments"] == [{"start": 20, "end": 30}]
    # A wide assessment never expands this native query's 20-residue result.
    store.assessments[0]["target_footprint"][0].update(start=0, end=100)
    assert project_credit(store).targets[0]["projected_footprint_units"] == 20
    store.assessments[0]["target_footprint"][0].update(start=40, end=60)
    assert project_credit(store).credit == 0
    assert store.records["observation:a"] == original

    # Input extent carried by an actual source operand also constrains the
    # attribution, even when its observation subject is an external entity.
    store.records["feature:assayed"] = {"id": "feature:assayed", "record_type": "feature",
        "footprint": [{"target_ref": "input:q", "start": 25, "end": 35, "unit": "aa"}]}
    observation.update(subject_refs=["external:reference"],
                       source_subject_refs=["feature:assayed"], origin="external")
    store.assessments[0]["target_footprint"][0].update(start=0, end=100)
    physical = project_credit(store)
    assert physical.targets[0]["projected_footprint_units"] == 10
    assert physical.source_contributions[0]["contributing_segments"] == [{"start": 25, "end": 35}]


@pytest.mark.parametrize("kind", ["source_content", "source_annotation", "coordinate_mapping"])
def test_fetching_labels_and_deterministic_coordinate_transforms_are_not_evidence(kind):
    store = StoreView()
    add_interpretation(store, kind)
    assert project_credit(store).credit == 0


def test_current_dependency_correction_is_visible_and_policy_serializes_immutably():
    store = StoreView()
    annotation, _ = add_interpretation(store)
    previous = project_credit(store).credit
    store.assessments[0] = {**store.assessments[0], "id": "assessment:new-revision",
                             "applicability": "incomparable"}
    projected = project_credit(store)
    assert projected.credit < previous
    assert projected.targets[0]["inactive_dependencies"] == [{
        "annotation_ref": annotation["id"], "coherent_set_ref": "coherent:a",
        "assessment_ref": "assessment:a", "reason": "not_current_assessment_revision"}]
    record = json.loads(json.dumps(projected.as_record(), allow_nan=False))
    assert CreditPolicy.from_record(record["policy"]).as_record() == record["policy"]
    with pytest.raises(FrozenInstanceError):
        projected.policy.epsilon = .5


def test_native_store_reasoning_commit_credit_provenance_and_reopen(tmp_path, monkeypatch):
    """Synthetic science fixture using REAL state/commit/credit implementations.

    This checks the integration, not the biological truth of a fictional assay.
    It requires no model and claims no external measurement was performed.
    """
    from gene_annotation_episode.state import Store

    path = tmp_path / "native"
    with Store(path) as store:
        target = store.create_problem(raw_sequence="MKTAA", molecule="protein",
                                      role="protein")["subject_refs"][0]
        source_artifact = store.artifact("Synthetic fixture: external protein shows kinase activity.")
        source = store.put("source", {"provider": "synthetic_fixture", "accession": "fixture:1",
            "uri": None, "artifact_ref": source_artifact, "text_ref": source_artifact,
            "request_ref": None, "version": "fixture-v1", "retrieved_at": None}, origin="external")
        external = store.put("reference", {"reference_type": "protein", "source_ref": source["id"],
            "accession": "fixture:protein", "label": "external protein", "sequence_ref": None,
            "molecule": "protein", "length": None, "term_refs": [], "context_refs": []}, origin="external")
        term = store.put("term", {"namespace": "fixture", "accession": "kinase", "label": "kinase activity",
            "term_type": "molecular_role", "source_ref": source["id"], "anchor": None}, origin="external")
        observation = store.put("observation", {"subject_refs": [external["id"]],
            "source_subject_refs": [external["id"]], "kind": "biochemical_assay",
            "source_ref": source["id"], "measurements": [{"name": "assay_outcome",
                "value": {"type": "enum", "value": "positive"}}],
            "dependencies": [], "anchor": None}, origin="external")
        footprint = [{"target_ref": target, "start": 1, "end": 4, "unit": "aa"}]
        scope = {"subject_refs": [target], "segments": footprint}
        focal = store.put("feature", {"subject_ref": target, "kind": "protein_domain",
            "segments": [{"start": 1, "end": 4}], "strand": ".", "context_refs": []},
            origin="reasoning", scope=scope)
        assert project_credit(store, scope).credit == 0
        payload = {"structural_proposals": [], "terms": [], "source_subjects": [], "observations": [],
            "hypotheses": [{"alias": "role", "subject_refs": [focal["id"]], "predicate": "biological_role",
                "value": {"type": "term_ref", "ref": term["id"]}, "context_refs": []}],
            "assessments": [{"extent_basis": "inferred_extent", "alias": "transfer", "hypothesis_ref": "@role",
                "observation_ref": observation["id"], "relation": "strengthens",
                "applicability": "transfer", "condition_refs": [], "assumption_refs": [],
                "expected_revision": 0}],
            "annotation_updates": [{"alias": "annotation", "subject_ref": focal["id"],
                "expected_revision": 0, "footprint_kind": "localized", "coherent_sets": [
                    {"interpretations": [{"hypothesis_ref": "@role", "disposition": "unresolved",
                        "assessment_refs": ["@transfer"]}], "context_refs": []}],
                "alternative_refs": ["@role"], "resolution": "alternatives_retained"}]}
        committed = store.commit_reasoning(payload, scope, "fixture-reasoning-1")
        assert committed["status"] == "completed", committed
        assert store.commit_reasoning(payload, scope, "fixture-reasoning-1") == committed
        assert project_credit(store, scope).credit == 0
        # Reuse the unchanged source observation. The new scientific state is
        # the explicit assessed application, not another fabricated assay.
        hypothesis_ref = committed["aliases"]["role"]
        bounded = {"structural_proposals": [], "terms": [], "source_subjects": [], "observations": [], "hypotheses": [],
            "assessments": [{"extent_basis": "inferred_extent", "alias": "bounded", "hypothesis_ref": hypothesis_ref,
                "observation_ref": observation["id"], "relation": "strengthens",
                "applicability": "transfer", "condition_refs": [], "assumption_refs": [],
                "target_footprint": footprint, "expected_revision": 1}],
            "annotation_updates": [{"alias": "annotation", "subject_ref": focal["id"],
                "expected_revision": 1, "footprint_kind": "localized", "coherent_sets": [
                    {"interpretations": [{"hypothesis_ref": hypothesis_ref, "disposition": "unresolved",
                        "assessment_refs": ["@bounded"]}], "context_refs": []}],
                "alternative_refs": [hypothesis_ref], "resolution": "alternatives_retained"}]}
        applied = store.commit_reasoning(bounded, scope, "fixture-bounded-transfer-2")
        assert applied["status"] == "completed", applied
        assert store.get(observation["id"]) == observation
        assert store.current_assessments(scope)[0]["target_footprint"] == footprint
        from gene_annotation_episode.domain import ContractError
        with pytest.raises(ContractError, match="source_subject_mismatch"):
            store.put("assessment", {**{key: value for key, value in bounded["assessments"][0].items()
                if key != "alias"}, "applicability": "direct", "extent_basis": "observed_extent", "expected_revision": 2},
                origin="reasoning", scope=scope)
        # Projection consumes compact scientific metadata, never source bodies.
        monkeypatch.setattr(store, "get_artifact", lambda ref: pytest.fail("credit hydrated raw data"))
        before = project_credit(store, scope)
        assert before.credit > 0
        assert before.targets[0]["unit"] == "aa"
        assert before.source_contributions[0]["source_subject_refs"] == [external["id"]]
        assert before.source_contributions[0]["observation_subject_refs"] == [external["id"]]
        assert before.source_contributions[0]["applicability"] == "transfer"
        assert before.source_contributions[0]["extent_mode"] == "assessment_inferred_target_extent"
        assert before.source_contributions[0]["assessment_ref"] == applied["aliases"]["bounded"]
        assert before.source_contributions[0]["annotation_ref"] == applied["aliases"]["annotation"]
        assert project_credit(store).credit == pytest.approx(before.credit * 3/5)

        # The parent's closed typed form refers to the very same committed
        # application, annotation and source fact used by the projection.
        from gene_annotation_episode.communication import (
            form_with_facts, reference_resolver, validate_form)
        schema = {"type": "object", "additionalProperties": False, "properties": {
            "assessment_refs": {"type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "assessment"}, "x-source": "changed_assessment_refs"},
            "annotation_refs": {"type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "annotation"}, "x-source": "changed_annotation_refs"},
            "source_observation_ref": {"type": "string", "format": "reference", "x-reference-namespace": "observation"},
            "extent_basis": {"type": "string", "enum": ["observed_extent", "inferred_extent"]},
            "credit": {"type": "number", "x-source": "credit"}},
            "required": ["assessment_refs", "annotation_refs", "source_observation_ref", "extent_basis", "credit"]}
        form = form_with_facts({"source_observation_ref": observation["id"],
            "extent_basis": before.source_contributions[0]["extent_basis"]}, schema, {
            "changed_assessment_refs": [applied["aliases"]["bounded"]],
            "changed_annotation_refs": [applied["aliases"]["annotation"]], "credit": before.credit})
        admitted = validate_form(form, schema, reference_resolver(store.references(scope)))
        assert admitted["source_observation_ref"] == before.source_contributions[0]["observation_ref"]
        assert admitted["assessment_refs"] == [before.source_contributions[0]["assessment_ref"]]
        assert admitted["annotation_refs"] == [before.source_contributions[0]["annotation_ref"]]
        assert admitted["extent_basis"] == store.get(admitted["assessment_refs"][0])["extent_basis"]
        serialized = before.as_record()

    with Store(path) as reopened:
        assert project_credit(reopened, scope).as_record() == serialized
        # Reinterpret existing evidence, then publish a matching annotation
        # revision. There is still exactly the same external observation.
        hypothesis_ref = committed["aliases"]["role"]
        correction = {"structural_proposals": [], "terms": [], "source_subjects": [], "observations": [], "hypotheses": [],
            "assessments": [{"extent_basis": "inferred_extent", "alias": "limited", "hypothesis_ref": hypothesis_ref,
                "observation_ref": observation["id"], "relation": "strengthens",
                "applicability": "incomparable", "condition_refs": [], "assumption_refs": [],
                "target_footprint": footprint, "expected_revision": 2}],
            "annotation_updates": [{"alias": "correction", "subject_ref": focal["id"],
                "expected_revision": 2, "footprint_kind": "localized", "coherent_sets": [
                    {"interpretations": [{"hypothesis_ref": hypothesis_ref, "disposition": "unresolved",
                        "assessment_refs": ["@limited"]}], "context_refs": []}],
                "alternative_refs": [hypothesis_ref], "resolution": "unresolved"}]}
        corrected = reopened.commit_reasoning(correction, scope, "fixture-correction-2")
        assert corrected["status"] == "completed", corrected
        after = project_credit(reopened, scope)
        assert after.credit == 0
        assert len(reopened.list("observation", scope)) == 1
        controller = YieldController("native-fixed-scope", before.credit, .001)
        assert controller.observe("reasoning-correction", after).marginal_credit == -before.credit


def _three_input_inference_fixture(store, tmp_path):
    """Fixed actual aa inputs, with B distinct from both physical operands."""
    manifest = tmp_path / 'inputs.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': [
        {'name': 'A', 'format': 'raw', 'sequence': 'MMADFKGWW', 'molecule': 'protein'},
        {'name': 'B', 'format': 'raw', 'sequence': 'MKTAA', 'molecule': 'protein'},
        {'name': 'C', 'format': 'raw', 'sequence': 'DF', 'molecule': 'protein'}]}))
    store.create_problem(manifest_path=manifest)
    return {row['name']: row['id'] for row in store.targets()}


@pytest.mark.parametrize('source_kind', ['original', 'external', 'derived_original', 'derived_external'])
def test_inferred_source_role_factor_and_target_scope_are_identity_independent(tmp_path, source_kind):
    """Same actual comparison, same inferred B credit, never a source→B map."""
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    with Store(tmp_path / source_kind) as store:
        targets = _three_input_inference_fixture(store, tmp_path)
        root_scope = {'subject_refs': list(targets.values())}
        target_scope = {'subject_refs': [targets['B']]}
        tools = ToolRegistry(store)
        query = targets['A']
        if 'external' in source_kind:
            query = _sequence_reference_fixture(store, 'MMADFKGWW', 'fixture:A')['id']
        if source_kind.startswith('derived'):
            viewed = tools.execute('sequence.view', {'subject_ref': query, 'molecule': 'protein',
                'segments': [{'start': 0, 'end': 9}], 'orientation': 'as_is'}, scope=root_scope, operation_key='source-view')
            assert viewed['status'] == 'completed', viewed
            query = viewed['result']['records'][0]['product_ref']
        aligned = tools.execute('sequence.align', {'query_ref': query, 'reference_ref': targets['C'],
            'molecule': 'protein', 'mode': 'local'}, scope=root_scope, operation_key='source-comparison')
        assert aligned['status'] == 'completed', aligned
        observation = store.get(aligned['result']['observation_ref'])
        footprint = store.coverage(targets['B'])
        committed = _commit_comparison_fixture(store, target_scope, targets['B'], observation['id'], targets['C'],
            footprint=footprint, extent_basis='inferred_extent')
        assert committed['notices'] == []
        projected = project_credit(store, target_scope)
        assert projected.credit == pytest.approx(100 * softened_hypervolume({'comparative': .6*2/9}))
        assert len(projected.source_contributions) == 1  # not one B inference per source operand
        row = projected.source_contributions[0]
        assert row['extent_basis'] == 'inferred_extent'
        assert row['extent_mode'] == 'assessment_inferred_target_extent'
        assert row['weight'] == pytest.approx(.6*2/9)
        assert row['source_extent_factor'] == pytest.approx(2/9)
        assert row['source_extent_factor_basis'] == 'reported_query_coverage'
        assert row['source_operand_intervals'] == observation['operand_intervals']
        assert len(row['source_operand_mappings']) == 2
        assert all(part['mapping_status'] == 'exact_physical_source_path'
                   for part in row['source_operand_mappings'])
        measured_sources = {segment['subject_ref'] for part in row['source_operand_mappings']
                            for segment in part['physical_source_segments']}
        assert targets['B'] not in measured_sources
        assert row['assessment_target_footprint'] == footprint
        assert row['contributing_segments'] == [{'start': 0, 'end': 5}]
        assert store.get(observation['id']) == observation
        assert [r['id'] for r in store.targets()] == list(targets.values())


def test_sibling_loci_same_original_input_can_infer_then_correct_to_observed_extent(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    path = tmp_path / 'siblings'
    with Store(path) as store:
        target = store.create_problem(raw_sequence='MMADFKGWWQQMMADFKGWW', molecule='protein')['subject_refs'][0]
        scope = {'subject_refs': [target]}
        left, right = [store.put('feature', {'subject_ref': target, 'kind': 'protein_domain',
            'segments': [{'start': start, 'end': end}], 'strand': '.', 'context_refs': []},
            origin='reasoning', scope=scope)['id'] for start, end in [(0, 9), (11, 20)]]
        reference = _sequence_reference_fixture(store, 'DF', 'fixture:fragment')
        tools = ToolRegistry(store)
        aligned = tools.execute('sequence.align', {'query_ref': left, 'reference_ref': reference['id'],
            'molecule': 'protein', 'mode': 'local'}, scope=scope, operation_key='left-source-comparison')
        assert aligned['status'] == 'completed', aligned
        observation = store.get(aligned['result']['observation_ref'])
        footprint = store.coverage(right)
        first = _commit_comparison_fixture(store, scope, right, observation['id'], reference['id'],
            footprint=footprint, extent_basis='inferred_extent')
        inferred = project_credit(store, scope)
        assert inferred.targets[0]['projected_footprint_units'] == 9
        assert inferred.credit == pytest.approx(100 * 9/20 * softened_hypervolume({'comparative': .6*2/9}))
        source = inferred.source_contributions[0]
        assert source['source_operand_mappings'][0]['physical_source_segments'] == [
            {'subject_ref': target, 'start': 3, 'end': 5, 'unit': 'aa', 'strand': '+'}]
        assert source['contributing_segments'] == [{'start': 11, 'end': 20}]
        controller = YieldController('fixed-sibling-scope', 0, .001)
        gain = controller.observe('inferred-current-interpretation', inferred)
        assert gain.marginal_credit == inferred.credit
        _commit_comparison_fixture(store, scope, right, observation['id'], reference['id'],
            footprint=footprint, extent_basis='observed_extent', hypothesis=first['aliases']['candidate'],
            revision=1, operation='correct-to-measured-extent')
        observed = project_credit(store, scope)
        assert observed.credit == 0  # Same original target ID cannot erase locus identity.
        loss = controller.observe('observed-current-interpretation', observed)
        assert loss.marginal_credit == -inferred.credit
        assert len(controller.state().history) == 2
        assert store.get(observation['id']) == observation
        frozen = observed.as_record()
    with Store(path) as reopened:
        assert project_credit(reopened, scope).as_record() == frozen


def test_inference_missing_extent_notice_and_direct_contradiction_preserve_valid_rows(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.export import export_annotation

    with Store(tmp_path / 'diagnostics') as store:
        target = store.create_problem(raw_sequence='MKTAA', molecule='protein')['subject_refs'][0]
        scope = {'subject_refs': [target]}
        external = _sequence_reference_fixture(store, 'MKTAA', 'fixture:assayed')
        observation = store.put('observation', {'subject_refs': [external['id']],
            'source_subject_refs': [external['id']], 'kind': 'biochemical_assay',
            'source_ref': external['source_ref'], 'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')
        first = _commit_comparison_fixture(store, scope, target, observation['id'], external['id'],
            extent_basis='inferred_extent')
        assessment_ref = first['aliases']['basis']
        assert first['status'] == 'completed' and first['errors'] == []
        assert first['notices'] == [{'section': 'assessments', 'row_index': 0,
            'record_ref': assessment_ref, 'field_path': ['target_footprint'],
            'code': 'inferred_extent_requires_target_footprint'}]
        before = project_credit(store, scope)
        assert before.credit == 0
        inactive = before.targets[0]['inactive_dependencies'][0]
        assert inactive['assessment_ref'] == assessment_ref
        assert inactive['reason'] == first['notices'][0]['code']
        assert inactive['field_path'] == first['notices'][0]['field_path']
        assert store.reasoning_view(scope)['assessments'][0]['extent_basis'] == 'inferred_extent'
        query = store.query_records('assessment', scope, current_only=True)
        assert query['records'][0]['id'] == assessment_ref
        # A contradictory representation fails only its row, while an independent
        # explicitly bounded scientific correction commits through the same call.
        hyp = first['aliases']['candidate']
        other_hyp = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
            'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []}, origin='reasoning')['id']
        payload = {name: [] for name in store.reasoning_schema()['required']}
        payload['assessments'] = [
            {'alias': 'contradiction', 'hypothesis_ref': other_hyp, 'observation_ref': observation['id'],
             'relation': 'strengthens', 'applicability': 'direct', 'extent_basis': 'inferred_extent',
             'target_footprint': store.coverage(target), 'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0},
            {'alias': 'bounded', 'hypothesis_ref': hyp, 'observation_ref': observation['id'],
             'relation': 'strengthens', 'applicability': 'transfer', 'extent_basis': 'inferred_extent',
             'target_footprint': store.coverage(target), 'condition_refs': [], 'assumption_refs': [], 'expected_revision': 1}]
        payload['annotation_updates'] = [{'alias': 'current', 'subject_ref': target, 'expected_revision': 1,
            'footprint_kind': 'localized', 'coherent_sets': [{'interpretations': [{'hypothesis_ref': hyp,
                'disposition': 'supported', 'assessment_refs': ['@bounded']}], 'context_refs': []}],
            'alternative_refs': [], 'resolution': 'selected'}]
        result = store.commit_reasoning(payload, scope, 'independent-contribution-survives')
        assert result['status'] == 'partial'
        assert result['errors'][0]['code'] == 'assessment_inferred_extent_cannot_be_direct'
        assert result['errors'][0]['field_path'] == ['extent_basis']
        assert 'contradiction' not in result['aliases'] and 'bounded' in result['aliases']
        assert result['notices'] == []
        assert project_credit(store, scope).credit > 0
        exported = export_annotation(store, tmp_path / 'extent.json', scope=scope, include_credit=True)
        from pathlib import Path
        document = json.loads(Path(exported['json']['path']).read_text())
        records = {r['id']: r for r in document['records']}
        assert records[result['aliases']['bounded']]['extent_basis'] == 'inferred_extent'
        assert records[result['aliases']['bounded']]['target_footprint'] == store.coverage(target)
        assert records[observation['id']] == observation
        contribution = document['credit_projection']['source_contributions'][0]
        assert contribution['extent_basis'] == records[result['aliases']['bounded']]['extent_basis']
        assert contribution['assessment_ref'] == result['aliases']['bounded']
        assert document['credit_projection']['projection_version'].endswith('_v7')
        missing = {key: value for key, value in payload['assessments'][0].items() if key != 'extent_basis'}
        missing['alias'] = 'missing_basis'
        payload = {name: [] for name in store.reasoning_schema()['required']}
        payload['assessments'] = [missing]
        absent = store.commit_reasoning(payload, scope, 'missing-required-extent-basis')
        assert absent['status'] == 'invalid'
        assert absent['errors'][0]['code'] == 'representation_error'
        assert store.get(observation['id']) == observation


@pytest.mark.parametrize('case', ['measured_gap', 'outside_alignment'])
def test_actual_gap_inference_is_distinct_from_observed_extent_and_unexamined_sites(tmp_path, case):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry

    reference_sequence = 'MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE'
    query_sequence = (reference_sequence[:15] + reference_sequence[16:] if case == 'measured_gap'
                      else reference_sequence[5:35])
    position = 15 if case == 'measured_gap' else 0
    with Store(tmp_path / case) as store:
        target = store.create_problem(raw_sequence=query_sequence, molecule='protein')['subject_refs'][0]
        scope = {'subject_refs': [target]}
        reference = _sequence_reference_fixture(store, reference_sequence, 'fixture:site-reference')
        tools = ToolRegistry(store)
        aligned = tools.execute('sequence.align', {'query_ref': target, 'reference_ref': reference['id'],
            'molecule': 'protein', 'mode': 'global' if case == 'measured_gap' else 'local'},
            scope=scope, operation_key='align-for-native-site')
        assert aligned['status'] == 'completed', aligned
        sites = tools.execute('sequence.sites', {'alignment_ref': aligned['result']['observation_ref'],
            'positions': [position]}, scope=scope, operation_key='inspect-native-site')
        assert sites['status'] == 'completed', sites
        site = sites['result']['sites'][0]
        assert site['relationship'] == ('gap' if case == 'measured_gap' else 'outside_alignment')
        assert site['query_position'] is None
        observation = store.get(sites['result']['observation_ref'])
        if case == 'measured_gap':
            assert observation['operand_intervals'] == [{'role': 'reference', 'subject_ref': reference['id'],
                'start': 15, 'end': 16, 'unit': 'aa', 'model_unit': 'aa'}]
        else:
            assert observation['operand_intervals'] == []
        footprint = [{'target_ref': target, 'start': 10, 'end': 20, 'unit': 'aa'}]
        recorded = _commit_comparison_fixture(store, scope, target, observation['id'], reference['id'],
            footprint=footprint, extent_basis='observed_extent')
        assert project_credit(store, scope).credit == 0
        # The episode's interpretation is explicit. A measured source gap can
        # weaken a scoped target claim without creating a missing query residue.
        # An unexamined site is recorded here as does_not_discriminate; no host
        # scientific judge infers that relation merely from the interval list.
        relation = 'weakens' if case == 'measured_gap' else 'does_not_discriminate'
        _commit_comparison_fixture(store, scope, target, observation['id'], reference['id'],
            footprint=footprint, extent_basis='inferred_extent', applicability='contextual',
            relation=relation, disposition='weakened', hypothesis=recorded['aliases']['candidate'],
            revision=1, operation='interpret-source-relationship')
        inferred = project_credit(store, scope)
        if case == 'measured_gap':
            assert inferred.credit == pytest.approx(100 * 10/len(query_sequence) * softened_hypervolume({
                'comparative': .35, 'discrimination': .35}))
            row = inferred.source_contributions[0]
            assert row['source_extent_factor'] == 1
            assert row['source_extent_factor_basis'] == 'query_coverage_unreported_unit_factor'
            assert row['source_operand_intervals'] == observation['operand_intervals']
            assert row['source_operand_mappings'][0]['physical_source_segments'] == [
                {'subject_ref': reference['id'], 'start': 15, 'end': 16, 'unit': 'aa', 'strand': '+'}]
            assert row['contributing_segments'] == [{'start': 10, 'end': 20}]
            assert 'native_query_interval' not in row
        else:
            assert inferred.credit == 0
        assert store.get(observation['id']) == observation


@pytest.mark.parametrize('same_original', [True, False])
def test_native_observed_sibling_query_and_reference_project_independently(tmp_path, same_original):
    """Real local alignment; original packaging cannot clip the other operand."""
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.domain import ContractError

    with Store(tmp_path / 'native-observed-operands') as store:
        if same_original:
            target = store.create_problem(raw_sequence='MMADFKGWWQQMMADFKGWW', molecule='protein')['subject_refs'][0]
            parents = [target, target]
            intervals = [(0, 9), (11, 20)]
        else:
            manifest = tmp_path / 'separate-inputs.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'entries': [
                {'name': 'A', 'sequence': 'MMADFKGWW', 'format': 'raw', 'molecule': 'protein'},
                {'name': 'B', 'sequence': 'MMADFKGWW', 'format': 'raw', 'molecule': 'protein'}]}))
            parents = store.create_problem(manifest_path=manifest)['subject_refs']
            intervals = [(0, 9), (0, 9)]
        root_scope = {'subject_refs': store.problem()['subject_refs']}
        features = [store.put('feature', {'subject_ref': parent, 'kind': 'protein_domain',
            'segments': [{'start': start, 'end': end}], 'strand': '.', 'context_refs': []},
            origin='reasoning', scope=root_scope)['id'] for parent, (start, end) in zip(parents, intervals)]
        query, reference = features
        aligned = ToolRegistry(store).execute('sequence.align', {'query_ref': query, 'reference_ref': reference,
            'molecule': 'protein', 'mode': 'global'}, scope=root_scope, operation_key='native-sibling-comparison')
        assert aligned['status'] == 'completed', aligned
        observation = store.get(aligned['result']['observation_ref'])
        assert observation['source_subject_refs'] == [reference]
        assert observation['operand_intervals'] == [
            {'role': role, 'subject_ref': ref, 'start': 0, 'end': 9, 'unit': 'aa', 'model_unit': 'aa'}
            for role, ref in [('query', query), ('reference', reference)]]
        for parent, subject, role, interval in zip(parents, features, ['query', 'reference'], intervals):
            scope = {'subject_refs': [parent], 'segments': store.coverage(subject)}
            _commit_comparison_fixture(store, scope, subject, observation['id'], reference,
                extent_basis='observed_extent', applicability='direct', operation='interpret-'+role)
            projected = project_credit(store, scope)
            assert projected.credit == pytest.approx(100*softened_hypervolume({'comparative': 1}))
            assert projected.targets[0]['projected_footprint_units'] == 9
            assert len(projected.source_contributions) == 1
            contribution = projected.source_contributions[0]
            assert contribution['native_operand_interval']['role'] == role
            assert contribution['mapping_subject_ref'] == subject
            assert contribution['weight'] == 1
            assert contribution['contributing_segments'] == [{'start': interval[0], 'end': interval[1]}]
        complete = project_credit(store, root_scope)
        assert len(complete.source_contributions) == 2
        assert sum(row['projected_footprint_units'] for row in complete.targets) == 18
        expected_fraction = .9 if same_original else 1.
        assert complete.credit == pytest.approx(expected_fraction*100*softened_hypervolume({'comparative': 1}))
        assert store.get(observation['id']) == observation
        # A direct assay of the reference remains a different physical claim.
        text = store.artifact('Synthetic fixture: construct B was assayed, not construct A.')
        source = store.put('source', {'provider': 'synthetic_fixture', 'accession': 'assayed-B', 'uri': None,
            'artifact_ref': text, 'text_ref': text, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='external')
        assay = store.put('observation', {'subject_refs': [query], 'source_subject_refs': [reference],
            'kind': 'assay_report', 'source_ref': source['id'], 'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')
        query_hypothesis = next(row for row in store.list('hypothesis') if row['subject_refs'] == [query])
        with pytest.raises(ContractError, match='source_subject_mismatch'):
            store.put('assessment', {'hypothesis_ref': query_hypothesis['id'], 'observation_ref': assay['id'],
                'relation': 'strengthens', 'applicability': 'direct', 'extent_basis': 'observed_extent',
                'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0}, origin='reasoning')


def test_extracted_assay_with_interval_fields_keeps_physical_source_restriction(tmp_path):
    """Reported coordinates cannot opt into the native operand dispatcher."""
    from gene_annotation_episode.state import Store

    with Store(tmp_path / 'reported-assay') as store:
        target = store.create_problem(raw_sequence='MMADFKGWWQQMMADFKGWW', molecule='protein')['subject_refs'][0]
        scope = {'subject_refs': [target]}
        query, assayed = [store.put('feature', {'subject_ref': target, 'kind': 'protein_domain',
            'segments': [{'start': start, 'end': end}], 'strand': '.', 'context_refs': []}, origin='reasoning')['id']
            for start, end in [(0, 9), (11, 20)]]
        quote = 'Synthetic fixture: construct B had a positive assay; A was not assayed.'
        artifact = store.artifact(quote, 'text/plain')
        source = store.put('source', {'provider': 'synthetic_fixture', 'accession': 'reported-assay-B', 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='external')
        anchor = {'source_ref': source['id'], 'artifact_ref': artifact, 'start': 0,
                  'end': len(quote.encode()), 'quote': quote}
        observation = store.put('observation', {'subject_refs': [query], 'source_subject_refs': [assayed],
            'kind': 'assay_report', 'source_ref': source['id'], 'measurements': [], 'dependencies': [],
            'anchor': anchor, 'operand_intervals': [
                {'role': 'query', 'subject_ref': query, 'start': 0, 'end': 9, 'unit': 'aa'},
                {'role': 'reference', 'subject_ref': assayed, 'start': 0, 'end': 9, 'unit': 'aa'}]}, origin='extracted')
        _commit_comparison_fixture(store, scope, query, observation['id'], assayed,
            footprint=store.coverage(query), extent_basis='observed_extent')
        projected = project_credit(store, scope)
        assert projected.credit == 0
        assert projected.targets[0]['inactive_dependencies'][0]['reason'] == 'observation_has_no_matching_target_coverage'
        assert store.get(observation['id']) == observation
