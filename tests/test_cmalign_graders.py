"""Native Infernal cases and explicitly synthetic adversarial contracts."""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

import pytest

from gene_annotation_episode import cmalign_inputs as inputs
from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores

FIXTURES = Path(__file__).parent / "fixtures/cmalign_graders"


def native(name):
    directory = FIXTURES / "native" / name
    artifacts = [{"artifact_id": name+"/"+filename, "format": fmt,
                  "content": (directory/filename).read_text(), "complete": True}
        for filename, fmt in (("alignment.sto", "stockholm"), ("scores.txt", "cmalign_sfile"),
                              ("inserts.txt", "cmalign_ifile"), ("local_ends.txt", "cmalign_elfile"))
        if (directory/filename).exists()]
    return artifacts, json.loads((directory/"metadata.json").read_text())


def populated(name):
    artifacts, metadata = native(name)
    return inputs.populate_cmalign_sheet(artifacts, **metadata)


def synthetic(text, *, length=4, sequences=None, settings=None, artifacts=None, inherited_alignment=None):
    source = [{"artifact_id": "synthetic", "format": "stockholm", "content": text, "complete": True}]
    return inputs.populate_cmalign_sheet(source+(artifacts or []),
        operation={"program": "cmalign", "native_version": "1.1.5", "settings": settings or {}},
        model={"name": "synthetic", "consensus_length": length}, sequences=sequences,
        inherited_alignment=inherited_alignment)


def codes(sheet):
    return {i["code"] for i in sheet["issues"]}


def test_native_fixture_hashes_and_provenance():
    manifest = json.loads((FIXTURES/"NATIVE_SHA256.json").read_text())
    assert len(manifest) >= 36
    for name, expected in manifest.items():
        assert hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest() == expected


def test_native_full_and_truncated_values():
    sheet = populated("full_trunc")
    scores = calculate_cmalign_scores(sheet)
    assert scores["status"] == "available"
    full, short = scores["sequences"]
    assert full["native_bit_score"] == 40.84
    assert full["native_avg_pp"] == .992
    assert full["model_match_nucleotides"] == 71
    assert full["original_length"] == full["model_length"] == 72
    assert full["model_occupancy"] == pytest.approx(71/72)
    assert full["model_gap_positions"] == 1
    assert full["deleted_model_positions"] is None
    assert full["total_insert_nucleotides"] == 1
    assert full["posterior_lower_mean"] == pytest.approx(6790/7200)
    assert full["posterior_upper_mean"] == pytest.approx(7175/7200)
    assert full["posterior_upper_inclusive"] is False
    assert short["retained_nucleotides"] == short["model_match_nucleotides"] == 35
    assert short["missing_model_positions"] == 36
    assert short["model_gap_positions"] == 1
    assert short["deleted_model_positions"] is None
    assert short["model_occupancy"] == pytest.approx(35/72)
    assert short["sequence_matched_coverage"] == 1
    assert short["truncation"] == "5'&3'"
    first = next(c for c in sheet["sequences"][1]["correspondence"] if c["original_sequence_position"] is not None)
    assert (first["original_sequence_position"], first["model_position"], first["column_index"]) == (1, 20, 20)
    assert scores["columns"][0]["occupancy_numerator"] == scores["columns"][0]["occupancy_denominator"] == 1
    assert scores["columns"][0]["missing_rows"] == 1


def test_native_local_end_geometry_and_pairs():
    sheet = populated("local_end")
    scores = calculate_cmalign_scores(sheet)
    row = scores["sequences"][0]
    assert row["retained_nucleotides"] == 103
    assert row["model_match_nucleotides"] == 98
    assert row["model_length"] == 190
    assert row["model_gap_positions"] == 62
    assert row["missing_model_positions"] == 30
    assert row["deleted_model_positions"] is None
    assert row["local_end_skipped_model_positions"] is None
    assert row["retained_local_end_nucleotides"] == row["total_local_end_nucleotides"] == 4
    assert row["total_insert_nucleotides"] == 1
    assert row["native_avg_pp"] == .924
    assert row["posterior_lower_mean"] == pytest.approx(9025/10300)
    assert row["posterior_upper_mean"] == pytest.approx(9675/10300)
    el = [c for c in sheet["sequences"][0]["correspondence"] if c["kind"] == "local_end"]
    assert len(el) == 4
    assert [c["original_sequence_position"] for c in el] == [62,63,64,65]
    assert {c["after_model_position"] for c in el} == {123}
    assert all(c["model_position"] is None for c in el)
    pairs = scores["summary"]["pair_totals"]
    assert pairs["canonical_pairs"] == 16
    assert pairs["unambiguous_pair_denominator"] == 18
    assert pairs["canonical_pair_fraction"] == pytest.approx(16/18)
    assert pairs["excluded"] == {"gap":15, "missing":9, "ambiguous":0, "nonresidue":0, "unavailable":0}


@pytest.mark.parametrize("full,filtered,omitted", [("full_trunc","matchonly",[20]),
                                                   ("local_end","local_end_matchonly",[22,62,63,64,65])])
def test_matchonly_reconstructs_exact_original_positions(full, filtered, omitted):
    a, b = populated(full), populated(filtered)
    ar, br = a["sequences"][0], b["sequences"][0]
    assert br["mapping"]["omitted_original_positions"] == omitted
    full_matches = [(c["model_position"],c["original_sequence_position"],c["symbol"])
                    for c in ar["correspondence"] if c["kind"] == "model"]
    filtered_matches = [(c["model_position"],c["original_sequence_position"],c["symbol"])
                    for c in br["correspondence"] if c["kind"] == "model"]
    assert full_matches == filtered_matches
    x, y = calculate_cmalign_scores(a)["sequences"][0], calculate_cmalign_scores(b)["sequences"][0]
    assert x["native_avg_pp"] == y["native_avg_pp"]
    assert x["posterior_available_count"] != y["posterior_available_count"]
    assert x["sequence_matched_coverage"] == y["sequence_matched_coverage"]


def test_matchonly_without_sidecars_does_not_guess_original_correspondence():
    artifacts, kwargs = native("local_end_matchonly")
    sheet = inputs.populate_cmalign_sheet(artifacts[:2], **kwargs)
    result = calculate_cmalign_scores(sheet)["sequences"][0]
    assert result["model_occupancy"] == pytest.approx(98/190)
    assert result["sequence_matched_coverage"] is None
    assert result["original_length"] == 103
    assert result["total_insert_nucleotides"] is None
    assert result["total_local_end_nucleotides"] is None
    assert all(c["original_sequence_position"] is None for c in sheet["sequences"][0]["correspondence"])
    assert "cmalign_matchonly_original_map_requires_ifile_and_local_elfile" in codes(sheet)


def test_no_pp_is_unknown_not_zero_and_native_timing_kept_separate():
    row = calculate_cmalign_scores(populated("noprob"))["sequences"][0]
    assert row["native_bit_score"] == 40.51
    assert row["native_avg_pp"] is None
    assert row["posterior_lower_mean"] is row["posterior_upper_mean"] is None
    assert row["posterior_available_count"] == 0
    assert row["posterior_unavailable_count"] == 72
    assert row["timing"]["total_seconds"] >= 0
    assert row["timing"]["matrix_mb"] > 0
    nonbanded = calculate_cmalign_scores(populated("global_nonbanded"))["sequences"][0]
    assert nonbanded["timing"]["band_seconds"] is None


def test_true_deletions_only_when_native_mode_establishes_them():
    global_row = calculate_cmalign_scores(populated("global"))["sequences"][0]
    assert global_row["deleted_model_positions"] == global_row["model_gap_positions"] == 1
    assert global_row["local_end_skipped_model_positions"] == 0
    assert global_row["native_bit_score"] == 52.3
    artifacts, kwargs = native("global")
    kwargs["operation"]["settings"]["sub"] = True
    submodel = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert calculate_cmalign_scores(submodel)["sequences"][0]["deleted_model_positions"] is None


def test_native_submodel_truncation_is_not_reclassified_as_deletions():
    sheet = populated("submodel")
    assert "cmalign_notrunc_setting_conflicts_with_native_truncation" not in codes(sheet)
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["truncation"] != "no"
    assert row["retained_nucleotides"] == 35
    assert row["model_gap_positions"] > 0
    assert row["deleted_model_positions"] is None


@pytest.mark.parametrize("case", ["local_end", "local_end_matchonly"])
def test_contradictory_global_mode_cannot_relabel_local_end_counts(case):
    artifacts, kwargs = native(case)
    kwargs["operation"]["settings"]["global"] = True
    kwargs["operation"]["settings"]["notrunc"] = True
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["deleted_model_positions"] is None
    assert row["total_local_end_nucleotides"] == 4
    assert any("global_setting_conflicts" in c for c in codes(sheet))


def test_matchonly_setting_cannot_hide_native_insert_columns():
    artifacts, kwargs = native("full_trunc")
    kwargs["operation"]["settings"]["matchonly"] = True
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_matchonly_setting_conflicts_with_native_insert_columns" in codes(sheet)
    assert calculate_cmalign_scores(sheet)["sequences"][0]["sequence_matched_coverage"] is None


def test_native_interleaving_and_pfam_agree_numerically():
    full, interleaved = populated("pfam_stress"), populated("interleaved_stress")
    assert interleaved["alignments"][0]["native_record"]["block_count"] > 1
    a, b = full["sequences"][0], interleaved["sequences"][0]
    assert a["measurements"] == b["measurements"]
    assert a["correspondence"] == b["correspondence"]
    assert a["posterior"] == b["posterior"]
    assert "tau" in populated("local_end_interleaved")["sequences"][0]["native_scores"]
    for fragment in b["native"]["fragments"]:
        raw = interleaved["artifacts"][0]["content"].encode()
        loc = fragment["locator"]
        assert raw[loc["byte_start"]:loc["byte_end"]].decode() == fragment["raw"]


def test_mapali_inherited_rows_and_population_filtering():
    sheet = populated("mapali")
    assert len(sheet["sequences"]) == 6
    assert [r["origin"] for r in sheet["sequences"]] == ["inherited"]*5+["newly_aligned"]
    assert all(r["inherited_join"]["status"] == "sequence_identity_verified" for r in sheet["sequences"][:5])
    assert all(r["native_scores"] is None for r in sheet["sequences"][:5])
    sections = [p["sections"][0] for p in sheet["parsed_sidecars"] if "sections" in p]
    assert all(s["native_header_present"] is False for s in sections)
    assert all(s["header_source"] == "supplied_model_for_declared_mapali" for s in sections)
    all_scores = calculate_cmalign_scores(sheet)
    new_scores = calculate_cmalign_scores(sheet, parameters={"population":"newly_aligned"})
    old_scores = calculate_cmalign_scores(sheet, parameters={"population":"inherited"})
    assert all_scores["sequences"] == new_scores["sequences"] == old_scores["sequences"]
    assert all_scores["summary"]["selected_sequence_count"] == 6
    assert new_scores["summary"]["selected_sequence_count"] == 1
    assert old_scores["summary"]["selected_sequence_count"] == 5
    assert new_scores["summary"]["pair_totals"]["canonical_pairs"] == 20
    assert old_scores["summary"]["pair_totals"]["canonical_pairs"] == 103
    assert new_scores["columns"][0]["occupancy_denominator"] == 1
    assert old_scores["columns"][0]["occupancy_denominator"] == 5


def test_mapali_header_absence_requires_declared_mode_and_supplied_model():
    artifacts, kwargs = native("mapali")
    no_model = {**kwargs,"model":None}
    missing = inputs.populate_cmalign_sheet(artifacts, **no_model)
    assert "cmalign_insert_model_header_invalid" in codes(missing)
    assert all(r["model_length"] is None for r in missing["sequences"])
    kwargs["operation"]["settings"]["mapali"] = False
    not_declared = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_insert_model_header_invalid" in codes(not_declared)
    kwargs["operation"]["settings"]["mapali"] = True
    kwargs["model"]["native_header"] = "NAME wrong_model\nCLEN 72\n"
    mismatch = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_model_header_metadata_mismatch" in codes(mismatch)
    assert all(r["model_length"] is None for r in mismatch["sequences"])


def test_malformed_inherited_alignment_does_not_create_new_work():
    artifacts, kwargs = native("mapali")
    kwargs["inherited_alignment"]["content"] = kwargs["inherited_alignment"]["content"].removesuffix("//\n")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_inherited_alignment_invalid_or_ambiguous" in codes(sheet)
    assert all(r["origin"] == "unknown" for r in sheet["sequences"][:5])
    assert sheet["sequences"][-1]["origin"] == "newly_aligned"


def test_sampled_alignment_remains_sampled():
    scores = calculate_cmalign_scores(populated("sample_serial"))
    assert scores["alignment_kind"] == "sampled_alignment"
    assert scores["operation"]["settings"]["seed"] == 181
    assert scores["operation"]["settings"]["cpu"] == 0


def test_supplied_model_mismatch_suppresses_model_coordinates_and_ratios():
    artifacts, kwargs = native("full_trunc")
    kwargs["model"]["consensus_length"] = 70
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_sidecar_model_metadata_mismatch" in codes(sheet)
    for row in calculate_cmalign_scores(sheet)["sequences"]:
        assert row["model_occupancy"] is row["model_length"] is None
    assert all(c["model_position"] is None for r in sheet["sequences"] for c in r["correspondence"])


@pytest.mark.parametrize("change", ["content", "length", "accession"])
def test_supplied_sequence_mismatch_is_not_silently_joined(change):
    artifacts, kwargs = native("full_trunc")
    if change == "content":
        kwargs["sequences"][0]["sequence"] = "A"*72
    elif change == "length":
        kwargs["sequences"][0]["length"] = 74
    else:
        kwargs["sequences"][0]["accession"] = "WRONG"
        artifacts[0]["content"] = artifacts[0]["content"].replace("#=GF AU Infernal 1.1.5", "#=GF AU Infernal 1.1.5\n#=GS tRNA6 AC actual")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["sequence_matched_coverage"] is None
    assert row["original_length"] is None
    assert row["model_match_nucleotides"] == 71


def test_missing_model_and_original_denominators_remain_missing():
    artifacts, kwargs = native("full_trunc")
    sheet = inputs.populate_cmalign_sheet(artifacts[:1], operation=kwargs["operation"])
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["model_length"] is row["original_length"] is None
    assert row["model_occupancy"] is row["sequence_matched_coverage"] is None
    assert row["retained_nucleotides"] == 72


def test_absent_sfile_preserves_other_available_numerical_results():
    artifacts, kwargs = native("full_trunc")
    sheet = inputs.populate_cmalign_sheet([a for a in artifacts if a["format"] != "cmalign_sfile"], **kwargs)
    scores = calculate_cmalign_scores(sheet)
    assert scores["status"] == "partial"
    assert scores["sequences"][0]["native_bit_score"] is None
    assert scores["sequences"][0]["model_occupancy"] == pytest.approx(71/72)
    assert "cmalign_score_sidecar_missing_or_unjoined" in codes(sheet)


def test_quantized_pp_bounds_and_unknown_bins_not_point_probabilities():
    text = "# STOCKHOLM 1.0\nx ACGU\n#=GR x PP 019*\n#=GC RF xxxx\n#=GC SS_cons <..>\n//\n"
    sheet = synthetic(text, sequences=[{"name":"x","sequence":"ACGU"}])
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["posterior_lower_mean"] == pytest.approx((0+5+85+95)/400)
    assert row["posterior_upper_mean"] == pytest.approx((5+15+95+100)/400)
    assert row["posterior_upper_inclusive"] is False
    stars = calculate_cmalign_scores(synthetic(text.replace("019*","****"), sequences=[{"name":"x","sequence":"ACGU"}]))["sequences"][0]
    assert stars["posterior_lower_mean"] == .95
    assert stars["posterior_upper_mean"] == 1
    assert stars["posterior_upper_inclusive"] is True
    missing = calculate_cmalign_scores(synthetic(text.replace("019*","0..?")))["sequences"][0]
    assert missing["posterior_available_count"] == 1
    assert missing["posterior_unavailable_count"] == 3
    assert missing["posterior_lower_mean"] == 0
    assert missing["posterior_upper_mean"] == .05


def test_pp_cons_is_retained_as_its_own_native_quantized_annotation():
    text = "# STOCKHOLM 1.0\nx ACGU\n#=GR x PP ****\n#=GC PP_cons 09**\n#=GC RF xxxx\n#=GC SS_cons <..>\n//\n"
    sheet = synthetic(text)
    result = calculate_cmalign_scores(sheet)
    assert sheet["alignments"][0]["native_pp_cons"] == "09**"
    assert result["columns"][0]["native_pp_cons_bounds"]["lower_hundredths"] == 0
    assert result["columns"][1]["native_pp_cons_bounds"]["upper_hundredths"] == 95
    assert result["columns"][2]["native_pp_cons_bounds"]["upper_inclusive"] is True
    assert result["sequences"][0]["posterior_lower_mean"] == .95
    assert "cmalign_pp_cons_symbol_invalid" in codes(synthetic(text.replace("09**", "09*?")))


def test_pairs_exclude_gap_missing_ambiguity_nonresidue_with_explicit_t_rule():
    text = "# STOCKHOLM 1.0\na AT\nb GC\nc GU\nd AA\ne A-\nf ~U\ng NU\nh *U\n#=GC RF xx\n#=GC SS_cons <>\n//\n"
    sheet = synthetic(text, length=2)
    scores = calculate_cmalign_scores(sheet)
    pair = scores["pairs"][0]
    assert pair["canonical_pairs"] == 3
    assert pair["noncanonical_pairs"] == 1
    assert pair["observed_two_nucleotide_pairs"] == 5
    assert pair["unambiguous_pair_denominator"] == 4
    assert pair["canonical_pair_fraction"] == .75
    assert pair["excluded"] == {"gap":1,"missing":1,"ambiguous":1,"nonresidue":1,"unavailable":0}
    assert "T->U" in sheet["normalization"]["pair_bases"]
    assert scores["columns"][0]["occupancy_denominator"] == 6


def test_wuss_pseudoknots_and_malformed_structure():
    source = "# STOCKHOLM 1.0\nx ACGU\n#=GC RF xxxx\n#=GC SS_cons <A>a\n//\n"
    sheet = synthetic(source)
    assert sheet["alignments"][0]["pairs"] == [[0,2],[1,3]]
    invalid = synthetic(source.replace("<A>a", "([)]"))
    assert invalid["pairs"] == []
    assert invalid["alignments"][0]["pair_map_available"] is False
    assert calculate_cmalign_scores(invalid)["summary"]["pair_map_unavailable_alignment_count"] == 1


def test_interleaved_records_preserve_all_annotations_and_locators():
    text = "# STOCKHOLM 1.0\n#=GF XX retained free text\n#=GS x AC exact\n\nx AC\n#=GR x PP 99\n#=GR x ZZ ab\n#=GC RF xx\n#=GC SS_cons <<\n\nx GU\n#=GR x PP **\n#=GR x ZZ cd\n#=GC RF xx\n#=GC SS_cons >>\n//\n"
    sheet = synthetic(text, sequences=[{"name":"x","sequence":"ACGU","accession":"exact"}])
    row = sheet["sequences"][0]
    assert row["native"]["aligned_sequence"] == "ACGU"
    assert row["native"]["column_annotations"]["ZZ"]["text"] == "abcd"
    assert row["posterior"]["native_pp"] == "99**"
    assert len(row["native"]["fragments"]) == 2
    assert sheet["alignments"][0]["pairs"] == [[0,3],[1,2]]
    assert sheet["artifacts"][0]["content"] == text


def test_truncated_stockholm_keeps_valid_partial_rows():
    artifacts, kwargs = native("full_trunc")
    artifacts[0]["content"] = artifacts[0]["content"].removesuffix("//\n")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert sheet["status"] == "partial"
    assert sheet["sequences"][0]["measurements"]["retained_nucleotides"] == 72
    assert "cmalign_stockholm_incomplete" in codes(sheet)
    assert sheet["alignments"][0]["complete"] is False


def test_malformed_stockholm_keeps_valid_independent_sequence():
    text = "# STOCKHOLM 1.0\ngood ACGU\nbad AC\n#=GC RF xxxx\n#=GC SS_cons <..>\n//\n"
    sheet = synthetic(text)
    assert sheet["status"] == "partial"
    scores = calculate_cmalign_scores(sheet)
    assert scores["sequences"][0]["retained_nucleotides"] == 4
    assert scores["sequences"][1]["retained_nucleotides"] is None
    assert scores["columns"][0]["unavailable_rows"] == 1
    assert scores["pairs"][0]["excluded"]["unavailable"] == 1
    assert synthetic("not stockholm") ["status"] == "invalid"


def test_duplicate_name_metadata_and_sidecar_join_require_explicit_occurrence():
    text = "# STOCKHOLM 1.0\nx AC\nx GU\n#=GC RF xx\n#=GC SS_cons <>\n//\n"
    table = "# idx seq name length cm from cm to trunc bit sc avg pp band calc alignment total mem (Mb)\n1 x 2 1 2 no 1.0 - 0 0 0 1\n2 x 2 1 2 no 2.0 - 0 0 0 1\n"
    side = [{"artifact_id":"score","format":"cmalign_sfile","content":table,"complete":True}]
    ambiguous = synthetic(text, length=2, sequences=[{"name":"x","sequence":"AC"}], artifacts=side)
    assert "cmalign_sidecar_join_ambiguous" in codes(ambiguous)
    assert all(r["native_scores"] is None for r in ambiguous["sequences"])
    explicit = synthetic(text, length=2, sequences=[{"name":"x","sequence":"AC","occurrence":0},
        {"name":"x","sequence":"GU","occurrence":1}], artifacts=side)
    rows = calculate_cmalign_scores(explicit)["sequences"]
    assert [r["native_bit_score"] for r in rows] == [1,2]
    assert [r["original_length"] for r in rows] == [2,2]


def test_mapali_same_name_new_score_occurrence_excludes_inherited_prefix():
    seed = {"artifact_id":"seed", "format":"stockholm", "complete":True,
            "content":"# STOCKHOLM 1.0\nx AC\n#=GC RF xx\n#=GC SS_cons <>\n//\n"}
    text = "# STOCKHOLM 1.0\nx AC\nx GU\n#=GC RF xx\n#=GC SS_cons <>\n//\n"
    score = "# idx seq name length cm from cm to trunc bit sc avg pp band calc alignment total mem (Mb)\n1 x 2 1 2 no 7.0 - 0 0 0 1\n"
    artifacts = [{"artifact_id":"sfile","format":"cmalign_sfile","complete":True,"content":score}]
    artifacts += [{"artifact_id":fmt,"format":fmt,"complete":True,"content":"x 2 1 2\nx 2 1 2\n//\n"}
                  for fmt in ("cmalign_ifile","cmalign_elfile")]
    metadata = [{"name":"x","sequence":"GU","occurrence":1,"origin":"newly_aligned"}]
    sheet = synthetic(text, length=2, settings={"mapali":True}, inherited_alignment=seed,
                      artifacts=artifacts, sequences=metadata)
    rows = calculate_cmalign_scores(sheet)["sequences"]
    assert [r["origin"] for r in rows] == ["inherited","newly_aligned"]
    assert [r["native_bit_score"] for r in rows] == [None,7]
    assert sheet["sequences"][0]["inherited_join"]["status"] == "sequence_identity_verified"
    assert rows[1]["mapping"]["status"] == "exact"
    del metadata[0]["occurrence"]
    ambiguous = synthetic(text, length=2, settings={"mapali":True}, inherited_alignment=seed,
                      artifacts=artifacts, sequences=metadata)
    assert ambiguous["sequences"][1]["native_scores"] is None


def test_native_mapali_name_collision_preserves_native_prefix_and_associations():
    sheet = populated("mapali_collision")
    rows = calculate_cmalign_scores(sheet)["sequences"]
    assert rows[0]["name"] == rows[-1]["name"] == "tRNA1"
    assert rows[0]["origin"] == "inherited"
    assert rows[-1]["origin"] == "newly_aligned"
    assert rows[0]["native_bit_score"] is None
    assert rows[-1]["native_bit_score"] == 40.84
    assert rows[-1]["original_length"] == 72
    assert rows[-1]["native_avg_pp"] == .992
    assert rows[0]["native_name"] == "0|tRNA1"
    assert rows[-1]["native_name"] == "5|tRNA1"
    assert rows[-1]["name_mapping"]["association_occurrence"] == 1
    assert sheet["sequences"][-1]["native"]["name"] == "5|tRNA1"
    assert rows[0]["posterior_available_count"] == 0
    assert rows[-1]["posterior_available_count"] == 72


@pytest.mark.parametrize("change", ["no_warning", "missing_prefix", "wrong_prefix", "incomplete"])
def test_native_name_prefix_requires_complete_warning_and_all_rows(change):
    artifacts, kwargs = native("mapali_collision")
    if change == "no_warning":
        artifacts[0]["content"] = "\n".join(line for line in artifacts[0]["content"].splitlines() if not line.startswith("# WARNING:"))+"\n"
    elif change == "missing_prefix":
        artifacts[0]["content"] = artifacts[0]["content"].replace("5|tRNA1", "tRNA1")
    elif change == "wrong_prefix":
        artifacts[0]["content"] = artifacts[0]["content"].replace("5|tRNA1", "4|tRNA1")
    else:
        artifacts[0]["complete"] = False
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert all(r["name_mapping"] is None for r in sheet["sequences"])
    assert all(r["native_scores"] is None for r in sheet["sequences"])
    if change != "no_warning":
        assert "cmalign_native_name_prefix_mapping_unverified" in codes(sheet)


def test_native_name_mapping_strips_only_generated_prefix_not_original_pipe():
    warning = '# WARNING: seq names have been made unique by adding a prefix of "<seq#>|"'
    text = f"# STOCKHOLM 1.0\n{warning}\n0|a|b AC\n1|a|b GU\n#=GC RF xx\n#=GC SS_cons <>\n//\n"
    sheet = synthetic(text, length=2, sequences=[{"name":"a|b","occurrence":0,"sequence":"AC"},
                                                {"name":"a|b","occurrence":1,"sequence":"GU"}])
    assert [r["name"] for r in sheet["sequences"]] == ["a|b","a|b"]
    assert [r["native_name"] for r in sheet["sequences"]] == ["0|a|b","1|a|b"]
    assert all(r["mapping"]["status"] == "exact" for r in sheet["sequences"])


def test_inconsistent_interleaved_occurrences_are_ambiguous():
    text = "# STOCKHOLM 1.0\nx AC\nx GU\n#=GC RF xx\n\nx GU\n#=GC RF xx\n//\n"
    sheet = synthetic(text, sequences=[{"name":"x","occurrence":0,"sequence":"ACGU"}])
    assert "cmalign_interleaved_occurrence_ambiguous" in codes(sheet)
    assert sheet["sequences"][0]["metadata"] is None


def test_multiple_alignment_artifacts_do_not_multiply_a_sidecar_join():
    artifacts, kwargs = native("full_trunc")
    second = {**artifacts[0],"artifact_id":"second_alignment"}
    sheet = inputs.populate_cmalign_sheet(artifacts+[second], **kwargs)
    assert len(sheet["sequences"]) == 4
    assert len({r["record_key"] for r in sheet["sequences"]}) == 4
    assert all(r["native_scores"] is None for r in sheet["sequences"])
    assert "cmalign_sidecar_join_ambiguous" in codes(sheet)


def test_zero_denominators_are_not_zero_fraction_and_unknown_origin_preserved():
    sheet = synthetic("# STOCKHOLM 1.0\nx -\n#=GC RF .\n#=GC SS_cons .\n//\n", length=0,
                      sequences=[{"name":"x","sequence":"","length":0,"origin":"unknown"}])
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["origin"] == "unknown"
    assert row["model_length"] == row["original_length"] == 0
    assert row["model_occupancy"] is row["sequence_matched_coverage"] is None
    assert row["posterior_lower_mean"] is None
    empty = inputs.populate_cmalign_sheet([], operation={"program":"cmalign","native_version":"1.1.5","settings":{}})
    assert empty["status"] == "missing"
    assert calculate_cmalign_scores(empty)["summary"]["pair_totals"]["canonical_pair_fraction"] is None


def test_partial_sfile_keeps_independent_valid_native_numbers():
    artifacts, kwargs = native("full_trunc")
    artifacts[1]["content"] = artifacts[1]["content"].replace("0.992", "broken")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["native_bit_score"] == 40.84
    assert row["native_avg_pp"] is None
    assert row["posterior_available_count"] == 72
    assert "cmalign_sfile_number_invalid" in codes(sheet)


def test_overlapping_insertion_ranges_and_bad_sidecar_model_rejected():
    artifacts, kwargs = native("local_end_matchonly")
    artifacts[-1]["content"] = artifacts[-1]["content"].replace("123 62 4", "123 22 4")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_matchonly_omitted_ranges_conflict" in codes(sheet)
    assert calculate_cmalign_scores(sheet)["sequences"][0]["sequence_matched_coverage"] is None


def test_matchonly_sidecar_anchor_requires_more_than_count_agreement():
    artifacts, kwargs = native("local_end_matchonly")
    artifacts[-1]["content"] = artifacts[-1]["content"].replace("123 62 4", "20 62 4")
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_sidecar_anchor_original_coordinate_mismatch" in codes(sheet)
    row = calculate_cmalign_scores(sheet)["sequences"][0]
    assert row["sequence_matched_coverage"] is None
    assert row["total_local_end_nucleotides"] is None
    assert all(c["original_sequence_position"] is None for c in sheet["sequences"][0]["correspondence"])


def test_duplicate_artifact_representation_is_explicit():
    artifacts, kwargs = native("full_trunc")
    second = {**artifacts[0], "artifact_id":"duplicate"}
    sheet = inputs.populate_cmalign_sheet(artifacts+[second], **kwargs)
    assert sheet["duplicate_artifact_groups"] == [[artifacts[0]["artifact_id"], "duplicate"]]
    assert "cmalign_duplicate_native_representation" in codes(sheet)


def test_saved_recalculation_disables_parsers_io_subprocess_network_and_preserves_sheet():
    sheet = json.loads(json.dumps(populated("mapali")))
    before = json.dumps(sheet, sort_keys=True)
    expected = calculate_cmalign_scores(sheet, parameters={"population":"newly_aligned"})
    def forbidden(*args, **kwargs):
        raise AssertionError("calculator attempted parsing, acquisition, or execution")
    with patch.object(inputs,"populate_cmalign_sheet",forbidden), patch.object(inputs,"parse_cmalign_stockholm",forbidden), \
            patch.object(inputs,"parse_cmalign_sfile",forbidden), patch.object(inputs,"parse_cmalign_insert_file",forbidden), \
            patch.object(inputs,"iter_hmmalign_stockholm_records",forbidden), patch.object(inputs,"posterior_bin_bounds",forbidden), \
            patch.object(builtins,"open",forbidden), patch.object(io,"open",forbidden), \
            patch.object(subprocess,"Popen",forbidden), patch.object(socket,"socket",forbidden):
        actual = calculate_cmalign_scores(sheet, parameters={"population":"newly_aligned"})
    assert actual == expected
    assert json.dumps(sheet, sort_keys=True) == before
    assert actual["summary"]["selected_sequence_count"] == 1
    assert len(actual["sequences"]) == 6


@pytest.mark.parametrize("parameters", [{"overall_confidence":True}, {"population":"unknown"}, [], {"population":None}, {"population":[]}])
def test_unknown_calculator_knobs_rejected(parameters):
    with pytest.raises(ValueError):
        calculate_cmalign_scores(populated("full_trunc"), parameters=parameters)


def test_nonfinite_and_corrupt_saved_numbers_rejected():
    sheet = populated("full_trunc")
    invalid = deepcopy(sheet)
    invalid["sequences"][0]["posterior"]["lower_sum_hundredths"] += 1
    invalid_row = calculate_cmalign_scores(invalid)["sequences"][0]
    assert invalid_row["status"] == "invalid"
    assert invalid_row["name"] == "tRNA6"
    assert invalid_row["model_occupancy"] is None
    invalid = deepcopy(sheet)
    invalid["operation"]["settings"]["arbitrary"] = float("nan")
    with pytest.raises(ValueError, match="finite_json"):
        calculate_cmalign_scores(invalid)
    invalid = deepcopy(sheet)
    invalid["sequences"][0]["native_scores"]["avg_pp"] = 2
    assert calculate_cmalign_scores(invalid)["sequences"][0]["status"] == "invalid"


def test_saved_population_references_must_name_the_actual_sequence():
    sheet = populated("full_trunc")
    for group in sheet["columns"][0]["populations"].values():
        group["record_keys"] = [k.replace("sequence:0", "sequence:200") for k in group["record_keys"]]
    with pytest.raises(ValueError, match="population_reference"):
        calculate_cmalign_scores(sheet)


def test_invalid_model_shape_and_missing_stockholm_header_are_explicit():
    artifacts, kwargs = native("full_trunc")
    kwargs["model"]["name"] = {"unexpected":"object"}
    sheet = inputs.populate_cmalign_sheet(artifacts, **kwargs)
    assert "cmalign_model_metadata_invalid" in codes(sheet)
    assert all(r["model_length"] is None for r in sheet["sequences"])
    assert synthetic("garbage\n")["status"] == "invalid"


def test_numerical_definitions_have_required_meaning_fields():
    result = calculate_cmalign_scores(populated("local_end"))
    for definition in result["definitions"].values():
        assert {"inputs","formula_or_native_source","units","population","denominator", "coordinate_convention",
                "uncertainty","missing_behavior","kind"} <= set(definition)
    assert "deleted_model_positions" in result["definitions"]
    assert "timing" in result["definitions"]
