"""Engineered saved alignments, not Cas9 experiments or native aligner runs.

Literal strings/paths below are hand-supplied carriers. The existing pure
Biopython/common grader prepares retained authority; no aligner is invoked.
Host producer, receipt and Source publication proof is deliberately outside
this Store-free contract suite.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode import reference_edit_outcomes as core
from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
from gene_annotation_episode.domain import canonical


def identifier(kind, ordinal):
    return kind + "_" + format(ordinal, "024x")


def native(query="AC", reference="AC", coordinates=None, *, mode="global", lengths=None):
    """Declare native-shaped cells; this does not run a native producer."""
    lengths = lengths or (len(query.replace("-", "")), len(reference.replace("-", "")))
    return dict(native_format="biopython_pairwise_native_v2", aligned=True, native_score=0,
        query_length=lengths[0], reference_length=lengths[1], mode=mode,
        matrix="engineered_literal_model", gap_open=-2, gap_extend=-.5,
        biopython_version="engineered_no_native_execution", aligned_query=query, aligned_reference=reference,
        query_interval=[coordinates[0][0], coordinates[0][-1]] if coordinates is not None else [0, lengths[0]],
        reference_interval=[coordinates[1][0], coordinates[1][-1]] if coordinates is not None else [0, lengths[1]],
        coordinates=coordinates if coordinates is not None else [[0, lengths[0]], [0, lengths[1]]])


def capture(raw=None, *, ordinal=1, molecule="dna", mappings=True):
    raw = native() if raw is None else deepcopy(raw)
    grading = grade_biopython_pairwise(raw, molecule=molecule, _retain_correspondence=True)
    common = grading.pop("correspondence")
    grading["failure"] = None
    qref, rref = identifier("input", ordinal * 2), identifier("reference", ordinal * 2 + 1)
    def operand(reference, length):
        return dict(subject_ref=reference, length=length, unit="nt", alignment_unit="nt", molecule=molecule)
    operands = dict(query=operand(qref, raw.get("query_length")), reference=operand(rref, raw.get("reference_length")))
    def mapping(operand):
        length = operand["length"]
        return None if not length else dict(version="oriented_source_subject_path_v2", units_per_symbol=1,
            symbol_length=length, path=[dict(subject_ref=operand["subject_ref"], start=0, end=length, unit="nt", strand="+")])
    return dict(source=dict(alignment_ref=identifier("observation", ordinal), source_ref=identifier("source", ordinal),
        native_artifact_ref=identifier("artifact", ordinal), provider="biopython.alignment", format="biopython_pairwise_json",
        native_version="engineered_no_native_execution", native_locator={}), operands=operands, grading=grading,
        correspondence=common, original_mappings={role: mapping(row) for role, row in operands.items()} if mappings else None)


def request(captures, *, groups=None, bins=None, guides=None, templates=None):
    rows = []
    for i, supplied in enumerate(captures):
        rows.append(dict(reference_ref=identifier("reference", 999) if supplied is None else supplied["operands"]["reference"]["subject_ref"],
            edited_ref=identifier("input", 999) if supplied is None else supplied["operands"]["query"]["subject_ref"],
            alignment_ref=None if supplied is None else supplied["source"]["alignment_ref"],
            group_label=None if groups is None else groups[i]))
    return dict(version=core.REQUEST_VERSION, population=rows, gap_bins=bins,
        guide_comparisons=guides or [], template_comparisons=templates or [])


def sheet(captures, *, selected=None, sequences=None):
    return core.populate_reference_edit_outcome_sheet(request(captures) if selected is None else selected,
        alignment_inputs=captures, comparison_inputs=dict(sequences=sequences or []))


def returned(saved):
    return core.project_reference_edit_outcome_return(core.calculate_reference_edit_outcome_components(saved),
        source_ref=identifier("source", 1000))


@pytest.mark.parametrize("query,reference,coordinates,expected,changes", [
    ("AC", "AC", [[0, 2], [0, 2]], "unchanged", []),
    ("AT", "AC", [[0, 2], [0, 2]], "substitution_only", ["substitution"]),
    ("ACG", "A-G", [[0, 1, 2, 3], [0, 1, 1, 2]], "insertion_only", ["insertion"]),
    ("A-G", "ACG", [[0, 1, 1, 2], [0, 1, 2, 3]], "deletion_only", ["deletion"]),
    ("AT-C", "A-GT", [[0, 1, 2, 2, 3], [0, 1, 1, 2, 3]], "mixed", ["substitution", "insertion", "deletion"]),
])
def test_whole_global_types_copy_saved_counts_and_native_event_order(query, reference, coordinates, expected, changes):
    original = capture(native(query, reference, coordinates))
    value = returned(sheet([original]))
    pair, = value["pairs"]
    assert pair["counts"] == original["grading"]["sheet"]["measured_column_counts"]
    assert pair["counts"] == original["correspondence"]["instances"][0]["components"]["rows"][0]["counts"]
    assert pair["state"] == value["status"] == "complete"
    assert pair["full_global_pair"] and pair["whole_pair_type"] == expected
    assert pair["observed_change_types"] == changes
    assert pair["native"]["parameters"] == dict(matrix="engineered_literal_model", gap_open=-2, gap_extend=-.5)
    assert pair["native"]["score"] == 0
    assert pair["gap_bins"] is None
    assert [event["event_ordinal"] for event in pair["events"]] == list(range(len(pair["events"])))
    if expected == "mixed":
        assert [event["kind"] for event in pair["events"]] == ["insertion", "deletion", "substitution"]
        assert pair["events"][0]["reference_boundary"] == 1
        assert pair["events"][1]["query_mapping"] == dict(status="not_applicable", intervals=[], reason=None)
    assert pair["count_units"]["substituted_positions"] == "nt"
    assert pair["count_units"]["query_gap_columns"] == "alignment_columns"


def test_substitution_only_is_never_no_mutation_and_two_population_denominators_remain_separate():
    changed = capture(native("AT", "AC"), ordinal=1)
    unchanged = capture(ordinal=2)
    local = capture(native("AT", "AC", [[2, 4], [1, 3]], mode="local", lengths=(6, 5)), ordinal=3)
    selected = request([changed, changed, unchanged, local, None], groups=["line A", "line A", "line B", None, None])
    value = returned(sheet([changed, changed, unchanged, local, None], selected=selected))
    population = value["populations"]["overall"]
    assert [row["pair_ordinal"] for row in value["pairs"]] == [0, 1, 2, 3, 4]
    assert [population[key] for key in ("declared_pair_count", "selected_alignment_count", "classified_pair_count", "unclassified_pair_count")] == [5, 4, 3, 2]
    substitution = population["categories"][1]
    assert substitution == dict(kind="substitution_only", count=2,
        fraction_of_classified=dict(value=2/3, numerator=2, denominator=3, unit="fraction"),
        observed_fraction_of_declared=dict(value=2/5, numerator=2, denominator=5, unit="fraction"))
    assert value["pairs"][3]["observed_change_types"] == ["substitution"]
    assert value["pairs"][3]["whole_pair_type"] is None
    assert value["pairs"][3]["coverage_scope"] == "selected_alignment"
    assert value["pairs"][4]["state"] == "not_selected"
    assert [row["group_label"] for row in value["populations"]["by_group"]] == ["line A", "line B", None]
    assert value["status"] == "partial"


@pytest.mark.parametrize("shape", ["empty_population", "not_selected", "no_alignment", "missing_traceback", "bad_geometry", "unknown_length", "legacy", "missing_grading", "failed_calculator"])
def test_missing_partial_conflicting_and_observed_zero_are_distinct(shape):
    original = capture()
    if shape == "empty_population":
        value = returned(sheet([]))
        assert value["status"] == "complete" and value["pairs"] == []
        assert value["populations"]["overall"]["declared_pair_count"] == 0
    elif shape == "not_selected":
        value = returned(sheet([None]))
        assert value["pairs"][0]["counts"]["substituted_positions"] is None
    else:
        if shape == "no_alignment":
            original = capture(dict(native_format="biopython_pairwise_native_v2", aligned=False, mode="local",
                query_length=2, reference_length=2, matrix="engineered", biopython_version="engineered_no_native_execution"))
        elif shape == "missing_traceback":
            raw = native(); raw.pop("aligned_query"); original = capture(raw)
        elif shape == "bad_geometry":
            original = capture(native("AT", "AC", [[0, 2], [0, 1]]))
        elif shape == "unknown_length":
            original["operands"]["query"]["length"] = None
        elif shape == "legacy":
            original.update(grading=None, correspondence=None)
        elif shape == "missing_grading":
            original.update(grading=dict(sheet=None, scores=None, failure=dict(code="unavailable")), correspondence=None)
        elif shape == "failed_calculator":
            original["grading"].update(scores=None, failure=dict(code="calculator_failed")); original["correspondence"] = None
        value = returned(sheet([original]))
        pair, = value["pairs"]
        if shape == "no_alignment":
            assert pair["counts"]["substituted_positions"] == pair["counts"]["query_gap_columns"] == 0
            assert pair["events"] == [] and pair["observed_change_types"] == []
            assert pair["state"] == "no_alignment" and pair["whole_pair_type"] is None
        elif shape == "bad_geometry":
            assert pair["counts"]["substituted_positions"] == 1
            assert pair["observed_change_types"] == ["substitution"]
            assert pair["events"] is None and pair["state"] == "conflicting" and pair["whole_pair_type"] is None
        elif shape == "failed_calculator":
            assert pair["whole_pair_type"] == "unchanged" and pair["state"] == "partial"
            assert pair["counts"]["identical_positions"] == 2
            assert pair["issue_codes"] == ["grading_failed", "grading_unavailable"]
        elif shape == "unknown_length":
            assert pair["counts"]["identical_positions"] == 2 and pair["events"] == []
            assert not pair["full_global_pair"] and pair["whole_pair_type"] is None
        else:
            assert pair["counts"]["identical_positions"] is None and pair["events"] is None
            assert pair["whole_pair_type"] is None
            if shape == "missing_traceback":
                assert pair["state"] == "unavailable" and "alignment_geometry_unavailable" in pair["issue_codes"]
    population = value["populations"]["overall"]
    if shape != "failed_calculator":
        assert population["classified_pair_count"] == 0
        assert all(row["fraction_of_classified"]["value"] is None and row["fraction_of_classified"]["denominator"] == 0
            for row in population["categories"])


def test_caller_bins_use_total_gap_bases_and_never_change_observed_edit_type():
    deletion = capture(native("A" + "-" * 11, "A" + "C" * 11, [[0, 1, 1], [0, 1, 12]]))
    selected = request([deletion], bins=dict(deletion_upper_bounds_nt=[10, 30], insertion_upper_bounds_nt=[1]))
    value = returned(sheet([deletion], selected=selected))
    pair, = value["pairs"]
    assert pair["counts"]["query_gap_columns"] == 11 and pair["whole_pair_type"] == "deletion_only"
    assert pair["gap_bins"] == dict(deletion=dict(bin_ordinal=1, lower_exclusive_nt=10, upper_inclusive_nt=30), insertion=None)
    selected["gap_bins"]["deletion_upper_bounds_nt"] = [3]
    other = returned(sheet([deletion], selected=selected))["pairs"][0]
    assert other["gap_bins"]["deletion"] == dict(bin_ordinal=1, lower_exclusive_nt=3, upper_inclusive_nt=None)
    assert other["counts"] == pair["counts"] and other["whole_pair_type"] == pair["whole_pair_type"]
    assert returned(sheet([deletion]))["pairs"][0]["gap_bins"] is None


def test_mapping_missing_and_conflicting_do_not_erase_original_local_events():
    missing = capture(native("AT", "AC"), mappings=False)
    value = returned(sheet([missing]))
    event, = value["pairs"][0]["events"]
    assert event["reference_interval"] == [1, 2] and event["query_interval"] == [1, 2]
    assert event["query_mapping"]["status"] == "unavailable"
    assert value["pairs"][0]["whole_pair_type"] == "substitution_only"
    original = capture(native("AT", "AC"))
    original["original_mappings"]["query"]["symbol_length"] = 999
    event = returned(sheet([original]))["pairs"][0]["events"][0]
    assert event["query_mapping"]["status"] == "incompatible"
    assert event["reference_mapping"]["status"] == "available"


def test_event_original_paths_use_existing_oriented_mapping_without_inferred_ancestry():
    original = capture(native("AT", "AC"))
    for role, start, strand in (("query", 10, "-"), ("reference", 20, "+")):
        original["original_mappings"][role]["path"] = [dict(subject_ref=identifier("input", 200), start=start,
            end=start + 2, unit="nt", strand=strand)]
    event = returned(sheet([original]))["pairs"][0]["events"][0]
    assert event["query_mapping"]["intervals"] == [dict(subject_ref=identifier("input", 200), start=10, end=11, unit="nt", strand="-")]
    assert event["reference_mapping"]["intervals"] == [dict(subject_ref=identifier("input", 200), start=21, end=22, unit="nt", strand="+")]


def test_legacy_sheet_counts_survive_without_promoting_unqualified_legacy_scores():
    raw = native("AT", "AC")
    raw.pop("native_format")
    raw.update(paired_positions=2, identical_positions=1, identity_fraction=.5, query_coverage=1, reference_coverage=1)
    original = capture(raw)
    original["correspondence"] = None
    # A legacy carrier's unqualified score cells are retained, not promoted.
    original["grading"]["scores"]["substituted_positions"] = 999
    before = deepcopy(original)
    saved = sheet([original])
    value = returned(saved)
    assert saved["alignment_inputs"][0] == before
    assert value["pairs"][0]["counts"]["substituted_positions"] == 1
    assert value["pairs"][0]["native"]["format"] is None
    assert value["pairs"][0]["issue_codes"] == ["saved_correspondence_unavailable"]
    assert value["pairs"][0]["whole_pair_type"] == "substitution_only" and value["status"] == "partial"


def test_declared_processing_model_does_not_reclassify_original_operand_metadata():
    original = capture(native("AT", "AC"), molecule="rna")
    for operand in original["operands"].values(): operand["molecule"] = "dna"
    saved = sheet([original])
    assert saved["alignment_inputs"][0]["operands"]["query"]["molecule"] == "dna"
    assert returned(saved)["pairs"][0]["native"]["molecule"] == "rna"


def test_reported_native_conflict_does_not_replace_saved_traceback_counts():
    raw = native("AT", "AC")
    raw.update(paired_positions=20, identical_positions=20, identity_fraction=1)
    original = capture(raw)
    saved = sheet([original])
    value = returned(saved)
    assert saved["alignment_inputs"][0]["grading"]["sheet"]["reported_measurements"]["identical_positions"] == 20
    assert value["pairs"][0]["counts"]["identical_positions"] == 1
    assert value["pairs"][0]["whole_pair_type"] == "substitution_only"
    assert "retained_alignment_qualified" in value["pairs"][0]["issue_codes"]


def test_retained_pair_does_not_run_another_builder_or_component_calculator(monkeypatch):
    import gene_annotation_episode.alignment_correspondence as common
    import gene_annotation_episode.biopython_pairwise_grader as existing
    original = capture(native("AT", "AC"))
    def forbidden(*args, **kwargs): raise AssertionError("outcome must copy retained scientific components")
    monkeypatch.setattr(common, "calculate_correspondence_components", forbidden)
    for name in ("build_biopython_pairwise_sheet", "grade_biopython_pairwise", "calculate_biopython_pairwise_scores"):
        monkeypatch.setattr(existing, name, forbidden)
    monkeypatch.setattr(core, "count_literal_alignment_columns", forbidden)
    value = returned(sheet([original]))
    assert value["pairs"][0]["counts"]["substituted_positions"] == 1


def comparisons(*, guide="AC", template="TG", orientation="as_is", molecule="dna", interval=None, reference_window=True):
    original = capture(native("ATGT", "ACGT"), molecule=molecule)
    guide_ref, template_ref = identifier("input", 100), identifier("input", 101)
    selected = request([original], guides=[dict(pair_ordinal=0, guide_ref=guide_ref, reference_interval=interval or [0, 2],
        orientation=orientation, molecule=molecule)], templates=[dict(pair_ordinal=0, template_ref=template_ref,
        edited_interval=[1, 3], reference_interval=[1, 3] if reference_window else None, orientation="as_is", molecule=molecule)])
    rref, qref = selected["population"][0]["reference_ref"], selected["population"][0]["edited_ref"]
    sequences = [dict(subject_ref=guide_ref, sequence=guide), dict(subject_ref=rref, sequence="ACGT"),
        dict(subject_ref=template_ref, sequence=template), dict(subject_ref=qref, sequence="ATGT")]
    return original, selected, sequences


def test_supplied_guide_offsets_and_whole_template_windows_make_no_repair_claim():
    original, selected, sequences = comparisons()
    value = returned(sheet([original], selected=selected, sequences=sequences))
    guide, = value["guide_comparisons"]
    assert guide["placement_basis"] == "caller_supplied" and guide["literal_comparison"]["identity"]["value"] == 1
    assert guide["event_offsets"] == [dict(event_ordinal=0, reference_interval=[1, 2], reference_boundary=None)]
    template, = value["template_comparisons"]
    assert template["edited_comparison"]["identical_symbols"] == 2
    assert template["reference_comparison"]["identical_symbols"] == 1
    assert template["reference_comparison"]["substituted_symbols"] == 1
    assert not any(token in canonical(value) for token in ("HDR", "NHEJ", "repair_mechanism", "on_target", "cut_site"))


def test_reverse_guide_keeps_explicit_oriented_offsets_without_searching_or_normalizing():
    original, selected, sequences = comparisons(guide="AC", orientation="reverse_complement", interval=[2, 4])
    value = returned(sheet([original], selected=selected, sequences=sequences))
    guide = value["guide_comparisons"][0]
    assert guide["literal_comparison"]["identical_symbols"] == 2
    assert guide["event_offsets"] == [dict(event_ordinal=0, reference_interval=[2, 3], reference_boundary=None)]
    sequences[0]["sequence"] = "ac"
    guide = returned(sheet([original], selected=selected, sequences=sequences))["guide_comparisons"][0]
    assert guide["literal_comparison"]["identical_symbols"] == 0
    assert guide["literal_comparison"]["substituted_symbols"] == 2


def test_rna_reverse_complement_uses_existing_declared_model_and_template_reference_can_be_unrequested():
    original, selected, sequences = comparisons(guide="AC", orientation="reverse_complement", molecule="rna", interval=[2, 4], reference_window=False)
    # RNA complement of AC is GU; literal DNA T remains distinct from RNA U.
    value = returned(sheet([original], selected=selected, sequences=sequences))
    assert value["guide_comparisons"][0]["literal_comparison"]["identical_symbols"] == 1
    assert value["template_comparisons"][0]["reference_comparison"] is None
    assert value["pairs"][0]["native"]["symbol_interpretation"]["native_nucleotide_normalization"] == "U_to_T_before_alignment"


@pytest.mark.parametrize("fault,state", [("missing", "unavailable"), ("empty", "empty"), ("width", "length_conflict"),
    ("bounds", "bounds_conflict"), ("symbol", "unsupported"), ("gap", "unsupported"), ("empty_window", "empty")])
def test_optional_comparison_failures_are_qualified_not_zero_matches(fault, state):
    original, selected, sequences = comparisons()
    if fault == "missing": sequences[0]["sequence"] = None
    elif fault == "empty": sequences[0]["sequence"] = ""
    elif fault == "width": sequences[0]["sequence"] = "A"
    elif fault == "bounds": selected["guide_comparisons"][0]["reference_interval"] = [3, 8]
    elif fault == "symbol": sequences[0]["sequence"] = "AX"
    elif fault == "gap": sequences[0]["sequence"] = "A-"
    else: selected["guide_comparisons"][0]["reference_interval"] = [1, 1]
    value = returned(sheet([original], selected=selected, sequences=sequences))
    compared = value["guide_comparisons"][0]["literal_comparison"]
    assert compared["state"] == state and compared["identical_symbols"] is None
    assert compared["identity"] == dict(value=None, numerator=None, denominator=None, unit="fraction")
    assert value["pairs"][0]["whole_pair_type"] == "substitution_only" and value["status"] == "partial"


def test_insertion_boundary_guide_offset_is_a_boundary_not_a_base_position():
    original = capture(native("ACG", "A-G", [[0, 1, 2, 3], [0, 1, 1, 2]]))
    guide_ref = identifier("input", 100)
    selected = request([original], guides=[dict(pair_ordinal=0, guide_ref=guide_ref, reference_interval=[0, 2], orientation="reverse_complement", molecule="dna")])
    sequences = [dict(subject_ref=guide_ref, sequence="CT"), dict(subject_ref=selected["population"][0]["reference_ref"], sequence="AG")]
    guide = returned(sheet([original], selected=selected, sequences=sequences))["guide_comparisons"][0]
    assert guide["event_offsets"] == [dict(event_ordinal=0, reference_interval=None, reference_boundary=1)]


@pytest.mark.parametrize("fault", ["bool_bin", "float_bin", "duplicate_bin", "descending_bin", "zero_bin", "bool_pair", "float_interval", "negative_interval", "extra_request", "extra_capture", "wrong_pair", "version", "length", "scores", "source", "unselected", "population", "missing_native", "protein", "bad_failure", "scores_without_sheet"])
def test_closed_inputs_and_selected_saved_identities_reject_tampering(fault):
    original = capture()
    selected = request([original])
    if fault.endswith("bin"):
        selected["gap_bins"] = dict(deletion_upper_bounds_nt={"bool_bin": [True], "float_bin": [1.0], "duplicate_bin": [1, 1],
            "descending_bin": [3, 2], "zero_bin": [0]}[fault], insertion_upper_bounds_nt=[])
    elif fault in ("bool_pair", "float_interval", "negative_interval"):
        selected["guide_comparisons"] = [dict(pair_ordinal=True if fault == "bool_pair" else 0,
            guide_ref="guide", reference_interval=[0, 1.0] if fault == "float_interval" else [-1, 1] if fault == "negative_interval" else [0, 1],
            orientation="as_is", molecule="dna")]
    elif fault == "extra_request": selected["threshold"] = .8
    elif fault == "extra_capture": original["authority"] = True
    elif fault == "wrong_pair": selected["population"][0]["edited_ref"] = identifier("input", 999)
    elif fault == "version": original["source"]["native_version"] = "different"
    elif fault == "length": original["operands"]["query"]["length"] = 3
    elif fault == "scores": original["grading"]["scores"]["identical_positions"] = 0
    elif fault == "source": original["source"]["provider"] = "invented"
    elif fault == "unselected": selected["population"][0]["alignment_ref"] = None
    elif fault == "missing_native": original["grading"]["sheet"].pop("native_result")
    elif fault == "protein": original["grading"]["sheet"]["molecule"] = "protein"
    elif fault == "bad_failure": original["grading"]["failure"] = []
    elif fault == "scores_without_sheet": original["grading"]["sheet"] = None
    else: selected["population"].append(deepcopy(selected["population"][0]))
    with pytest.raises(ValueError): sheet([original], selected=selected)


@pytest.mark.parametrize("fault", ["missing", "extra", "order", "duplicate", "operand_length"])
def test_comparison_identity_population_is_exact(fault):
    original, selected, sequences = comparisons()
    if fault == "missing": sequences.pop()
    elif fault == "extra": sequences.append(dict(subject_ref="unrequested", sequence="A"))
    elif fault == "order": sequences.reverse()
    elif fault == "duplicate": sequences[1] = deepcopy(sequences[0])
    else: sequences[1]["sequence"] = "ACGTA"
    with pytest.raises(ValueError): sheet([original], selected=selected, sequences=sequences)


@pytest.mark.parametrize("fault", ["count", "event", "status", "ordinal", "input"])
def test_saved_sheet_conflicts_do_not_get_repaired(fault):
    saved = sheet([capture(native("AT", "AC"))])
    if fault == "count": saved["pairs"][0]["counts"]["substituted_positions"] = 0
    elif fault == "event": saved["pairs"][0]["events"][0]["reference_interval"] = [0, 1]
    elif fault == "status": saved["status"] = "partial"
    elif fault == "ordinal": saved["pairs"][0]["pair_ordinal"] = True
    else: saved["alignment_inputs"][0]["operands"]["query"]["subject_ref"] = "different"
    with pytest.raises(ValueError): core.calculate_reference_edit_outcome_components(saved)


@pytest.mark.parametrize("fault", ["population", "guide", "template"])
def test_projected_components_keep_original_declared_selection(fault):
    original, selected, sequences = comparisons()
    components = core.calculate_reference_edit_outcome_components(sheet([original], selected=selected, sequences=sequences))
    if fault == "population": components["request"]["population"][0]["edited_ref"] = "another_input"
    elif fault == "guide": components["request"]["guide_comparisons"][0]["orientation"] = "reverse_complement"
    else: components["request"]["template_comparisons"][0]["reference_interval"] = None
    with pytest.raises(ValueError): core.project_reference_edit_outcome_return(components, source_ref=identifier("source", 1000))


@pytest.mark.parametrize("fault", ["bool_count", "float_count", "unit", "category", "population", "bin", "source", "private", "event", "mapping", "mixed_null", "full", "status"])
def test_public_dto_is_closed_strict_and_preserves_relationships(fault):
    value = returned(sheet([capture(native("AT", "AC"))]))
    pair = value["pairs"][0]
    if fault == "bool_count": pair["counts"]["substituted_positions"] = True
    elif fault == "float_count": pair["counts"]["substituted_positions"] = 1.0
    elif fault == "unit": pair["count_units"]["substituted_positions"] = "fraction"
    elif fault == "category": pair["whole_pair_type"] = "unchanged"
    elif fault == "population": value["populations"]["overall"]["declared_pair_count"] = 2
    elif fault == "bin": pair["gap_bins"] = dict(deletion=None, insertion=None)
    elif fault == "source": value["source_ref"] = identifier("artifact", 1)
    elif fault == "private": value["grading_artifact_ref"] = identifier("artifact", 1)
    elif fault == "event": pair["events"][0]["query_sequence"] = "TT"
    elif fault == "mapping": pair["events"][0]["query_mapping"]["intervals"] = None
    elif fault == "mixed_null": pair["counts"]["identical_positions"] = None
    elif fault == "full": pair["native"]["mode"] = "local"
    else: value["status"] = "partial"
    with pytest.raises(ValueError): core.validate_reference_edit_outcome_return(value)


def test_public_comparison_offsets_and_qualifications_cannot_be_erased_or_injected():
    original, selected, sequences = comparisons()
    value = returned(sheet([original], selected=selected, sequences=sequences))
    changed = deepcopy(value); changed["guide_comparisons"][0]["event_offsets"][0]["reference_interval"] = [0, 1]
    with pytest.raises(ValueError): core.validate_reference_edit_outcome_return(changed)
    changed = deepcopy(value); changed["template_comparisons"][0]["reference_comparison"] = None
    with pytest.raises(ValueError): core.validate_reference_edit_outcome_return(changed)
    sequences[0]["sequence"] = None
    changed = returned(sheet([original], selected=selected, sequences=sequences))
    changed["guide_comparisons"][0]["literal_comparison"]["issue_code"] = "comparison_empty"
    with pytest.raises(ValueError): core.validate_reference_edit_outcome_return(changed)


def test_projection_and_frozen_shape_validation_do_not_read_or_recalculate_original_authorities(monkeypatch):
    saved = sheet([capture(native("AT", "AC"))])
    components = core.calculate_reference_edit_outcome_components(saved)
    original = deepcopy(components)
    def forbidden(*args, **kwargs): raise AssertionError("projection reopened original authority")
    for name in ("_validate_sheet", "validate_tool_correspondence", "count_literal_alignment_columns", "populate_reference_edit_outcome_sheet",
                 "calculate_reference_edit_outcome_components", "_gapped_columns", "map_operand_interval", "frozen_reverse_complement"):
        monkeypatch.setattr(core, name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    value = core.project_reference_edit_outcome_return(components, source_ref=identifier("source", 1000))
    assert core.validate_reference_edit_outcome_return(value) == value
    assert components == original
    value["pairs"][0]["counts"]["substituted_positions"] = 0
    assert components == original


def test_only_result_source_is_a_semantic_reference_and_all_original_ordinals_survive():
    def references(node, path=()):
        found = [path] if type(node) is dict and node.get("format") == "reference" else []
        if type(node) is dict:
            for key, child in node.items(): found.extend(references(child, path + (key,)))
        elif type(node) is list:
            for i, child in enumerate(node): found.extend(references(child, path + (i,)))
        return found
    assert references(core.RETURN_SCHEMA) == [("properties", "source_ref")]
    original = capture()
    inputs = [original] * 137
    selected = request(inputs)
    before = deepcopy((inputs, selected))
    value = returned(sheet(inputs, selected=selected))
    assert len(value["pairs"]) == 137 and value["pairs"][-1]["pair_ordinal"] == 136
    assert value["populations"]["overall"]["categories"][0]["count"] == 137
    assert (inputs, selected) == before
    assert not any(key in canonical(value) for key in ("native_artifact_ref", "original_mappings", "correspondence", "alignment_inputs"))


def test_published_schema_copy_cannot_weaken_the_pure_validator(monkeypatch):
    value = returned(sheet([capture()]))
    monkeypatch.setitem(core.RETURN_SCHEMA, "additionalProperties", True)
    value["unexpected_private_control"] = "retained"
    with pytest.raises(ValueError): core.validate_reference_edit_outcome_return(value)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), {1: "non_string_key"}, {"not_json"}])
def test_nonfinite_or_nonjson_input_is_not_lossily_coerced(bad):
    original = capture()
    selected = request([original]); selected["population"][0]["group_label"] = bad
    with pytest.raises(ValueError): sheet([original], selected=selected)


@pytest.mark.parametrize("shape,expected_state,expected_count,expected_issue", [
    ("missing_reference", "unavailable", None, "alignment_geometry_unavailable"),
    ("both_missing", "unavailable", None, "alignment_geometry_unavailable"),
    ("unequal_strings_without_path", "conflicting", None, "alignment_geometry_conflict"),
    ("empty_query_without_path", "conflicting", None, "alignment_geometry_conflict"),
    ("valid_strings_without_path", "partial", 1, "alignment_geometry_unavailable"),
])
def test_traceback_evidence_distinguishes_missing_symbols_from_supplied_contradictions(
        shape, expected_state, expected_count, expected_issue):
    raw = native("AT", "AC")
    if shape == "missing_reference":
        raw.pop("aligned_reference")
    elif shape == "both_missing":
        raw.pop("aligned_query"); raw.pop("aligned_reference")
    else:
        raw.pop("coordinates")
        if shape == "unequal_strings_without_path": raw["aligned_query"] = "A"
        elif shape == "empty_query_without_path": raw["aligned_query"] = ""
    original = capture(raw)
    value = returned(sheet([original]))
    pair, = value["pairs"]
    assert original["grading"]["sheet"]["traceback"]["status"] == (
        "unavailable" if shape == "both_missing" else "valid" if shape == "valid_strings_without_path" else "invalid")
    assert pair["state"] == expected_state and expected_issue in pair["issue_codes"]
    assert pair["counts"]["substituted_positions"] == expected_count
    assert pair["events"] is None and pair["whole_pair_type"] is None
    assert value["status"] == "partial"
    assert value["populations"]["overall"]["classified_pair_count"] == 0
