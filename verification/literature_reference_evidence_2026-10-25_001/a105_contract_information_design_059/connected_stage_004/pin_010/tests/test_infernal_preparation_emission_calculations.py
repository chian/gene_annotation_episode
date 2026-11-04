"""Independently check generated-data numbers and recalculation from saved JSON."""
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from gene_annotation_episode import infernal_preparation_emission as reader
from gene_annotation_episode.infernal_preparation_emission_calculations import (
    CHECK_NAMES, COMPONENT_NAMES, ISSUE_CODES, calculate_cmemit_components,
)
from test_infernal_preparation_emission import build_sheet, rows, PRIOR, NATIVE


def calculated(sheet):
    return calculate_cmemit_components(sheet, parameters={})


def calc_row(result, key):
    return next(r for r in result["rows"] if r["record_key"] == key)


def checks(row):
    return {c["check"]: c["outcome"] for c in row["checks"]}


def test_native_alignment_known_numbers_and_model_count():
    sheet = build_sheet((PRIOR/"cmemit_stockholm/emitted.out").read_bytes(), mode="sample_aligned", fmt="stockholm")
    result = calculated(sheet)
    first = calc_row(result, rows(sheet)[0]["record_key"])
    c = first["components"]
    assert {k: c[k]["value"] for k in ("residue_count","canonical_count","gc_count","ambiguity_count","gap_count","column_count")} == {
        "residue_count":11,"canonical_count":11,"gc_count":8,"ambiguity_count":0,"gap_count":1,"column_count":12}
    assert c["gc_denominator"]["value"] == 11
    assert c["gc_fraction_canonical"]["value"] == pytest.approx(8/11)
    assert c["gap_fraction"]["value"] == pytest.approx(1/12)
    model = calc_row(result, sheet["input_records"][0]["record_key"])
    assert model["components"]["expected_sequence_count"]["value"] == 2
    assert model["components"]["actual_sequence_count"]["value"] == 2
    assert checks(model)["cmemit_sequence_count_matches"] == "pass"
    assert all(set(row["components"]) == COMPONENT_NAMES for row in result["rows"])
    assert not result["issues"]


def test_synthetic_ambiguity_gc_population_and_gaps():
    sheet = build_sheet("# STOCKHOLM 1.0\nfixture246-sample1 aCGUnN-._\n#=GC RF xxxxxxxxx\n//\n",
        mode="sample_aligned", fmt="stockholm", settings={"-N":1,"--idx":1,"--rna":True})
    row = calc_row(calculated(sheet), rows(sheet)[0]["record_key"])
    c = row["components"]
    assert c["residue_count"]["value"] == 6
    assert c["canonical_count"]["value"] == 4
    assert c["ambiguity_count"]["value"] == 2
    assert c["gc_count"]["value"] == 2
    assert c["gc_fraction_canonical"]["value"] == .5
    assert c["gap_count"]["value"] == 3
    assert c["column_count"]["value"] == 9
    assert c["gap_fraction"]["value"] == pytest.approx(1/3)


@pytest.mark.parametrize("sequence", ["", "NNN", "---"])
def test_zero_denominators_remain_unavailable_not_zero_gc(sequence):
    if sequence == "---":
        text="# STOCKHOLM 1.0\nfixture246-sample1 ---\n#=GC RF xxx\n//\n"
        sheet=build_sheet(text,mode="sample_aligned",fmt="stockholm",settings={"-N":1,"--idx":1,"--rna":True})
    else:
        sheet=build_sheet(">fixture246-sample1\n"+sequence+"\n",settings={"-N":1,"--idx":1,"--rna":True})
    c=calc_row(calculated(sheet),rows(sheet)[0]["record_key"])["components"]
    assert c["gc_count"]["value"] == 0
    assert c["gc_denominator"]["value"] == 0
    assert c["gc_fraction_canonical"]["state"] == "not_measured"
    if sequence == "---":
        assert c["gap_fraction"]["value"] == 1
    else:
        assert c["gap_fraction"]["state"] == "not_measured"


def test_missing_symbols_are_not_gaps_or_ambiguity():
    sheet=build_sheet("# STOCKHOLM 1.0\nfixture246-sample1 AC~?--\n#=GC RF xxxxxx\n//\n",
        mode="sample_aligned",fmt="stockholm",settings={"-N":1,"--idx":1,"--rna":True})
    row=rows(sheet)[0]
    c=calc_row(calculated(sheet),row["record_key"])["components"]
    assert c["residue_count"]["value"] == 2
    assert c["ambiguity_count"]["value"] == 0
    assert c["gap_count"]["value"] == 2
    assert c["column_count"]["value"] == 6
    assert c["gap_fraction"]["value"] == pytest.approx(2/6)
    assert "cmemit_missing_sequence_symbols" in {i["code"] for i in sheet["issues"]}


def test_consensus_n_is_not_sample_count():
    sheet=build_sheet((PRIOR/"cmemit_consensus/emitted.out").read_bytes(),mode="consensus",settings={"-N":97,"--rna":True})
    result=calculated(sheet)
    model=calc_row(result,sheet["input_records"][0]["record_key"])
    assert model["components"]["expected_sequence_count"]["value"] == 1
    assert model["components"]["actual_sequence_count"]["value"] == 1
    c=calc_row(result,rows(sheet)[0]["record_key"])["components"]
    assert c["residue_count"]["value"] == 12
    assert c["gc_fraction_canonical"]["value"] == pytest.approx(2/3)


def test_saved_json_recalculation_uses_no_io_network_native_or_parser(monkeypatch):
    sheet=build_sheet((PRIOR/"cmemit_stockholm/emitted.out").read_bytes(),mode="sample_aligned",fmt="stockholm")
    expected=calculated(sheet)
    saved=json.loads(json.dumps(sheet,allow_nan=False))
    def forbidden(*args,**kwargs):
        raise AssertionError("recalculation invoked acquisition or parsing")
    with monkeypatch.context() as patch:
        patch.setattr("builtins.open",forbidden)
        patch.setattr(socket,"socket",forbidden)
        patch.setattr(subprocess,"Popen",forbidden)
        patch.setattr(reader,"populate_cmemit_sheet",forbidden)
        patch.setattr(reader,"iter_hmmalign_stockholm_records",forbidden)
        assert calculated(saved) == expected
    assert saved == sheet


def test_populate_itself_is_pure_with_supplied_models(monkeypatch):
    from gene_annotation_episode.infernal_preparation_models import extract_infernal_models
    from test_infernal_preparation_emission import artifact
    data=(PRIOR/"cmemit_fasta/model.cm").read_bytes()
    ma=artifact(data,"models","infernal_cm_ascii")
    models=extract_infernal_models(data,artifact=ma,format=ma["format"],engine_version="1.1.5")
    output=b">fixture246-sample1\nACGU\n"
    oa=artifact(output,"generated_sequences","fasta")
    def forbidden(*args,**kwargs):
        raise AssertionError("pure parser performed IO")
    with monkeypatch.context() as patch:
        patch.setattr("builtins.open",forbidden)
        patch.setattr(socket,"socket",forbidden)
        patch.setattr(subprocess,"Popen",forbidden)
        sheet=reader.populate_cmemit_sheet(operation={"program":"cmemit","mode":"sample_unaligned","engine_version":"1.1.5",
            "settings":{"-N":1,"--idx":1,"--rna":True}},artifacts=[ma,oa],models=models,output={"artifact":oa,"content":output})
        assert rows(sheet)[0]["values"]["residue_count"]["value"] == 4


def test_partial_model_population_never_becomes_complete_expected_count():
    sheet=build_sheet(">fixture246-sample1\nACGU\n",model_complete="partial")
    model=calc_row(calculated(sheet),sheet["input_records"][0]["record_key"])
    assert model["components"]["expected_sequence_count"]["state"] == "missing"
    assert checks(model)["cmemit_model_population_complete"] == "unknown"


def test_partial_output_counts_and_confirmation_are_distinct():
    sheet=build_sheet(">fixture246-sample1\nACGU\n>fixture246-sample2\nAC",complete="partial")
    result=calculated(sheet)
    first,second=[calc_row(result,r["record_key"]) for r in rows(sheet)]
    assert first["components"]["gc_fraction_canonical"]["value"] == .5
    assert second["components"]["gc_fraction_canonical"]["state"] == "truncated"
    model=calc_row(result,sheet["input_records"][0]["record_key"])
    assert checks(model)["cmemit_sequence_count_matches"] == "unknown"


def test_empty_output_has_actual_zero_and_unsatisfied_expected_count():
    sheet=build_sheet("")
    model=calc_row(calculated(sheet),sheet["input_records"][0]["record_key"])
    assert model["components"]["actual_sequence_count"]["value"] == 0
    assert model["components"]["expected_sequence_count"]["value"] == 2
    assert checks(model)["cmemit_sequence_count_matches"] == "fail"


def test_unresolved_duplicate_models_do_not_become_zero_samples():
    data=(NATIVE/"duplicate_models/model.cm").read_bytes()
    sheet=build_sheet(">fixture246-sample1\nACGU\n",model_content=data,complete="partial")
    result=calculated(sheet)
    for model in sheet["input_records"]:
        assert calc_row(result,model["record_key"])["components"]["actual_sequence_count"]["state"] == "missing"


def test_saved_count_tampering_is_reported_without_overwriting_sheet():
    sheet=build_sheet(">fixture246-sample1\nACGU\n",settings={"-N":1,"--idx":1,"--rna":True})
    rows(sheet)[0]["values"]["gc_count"]["value"]=3
    before=deepcopy(sheet)
    result=calculated(sheet)
    row=calc_row(result,rows(sheet)[0]["record_key"])
    assert row["components"]["gc_count"]["state"] == "invalid"
    assert row["components"]["gc_fraction_canonical"]["state"] == "invalid"
    assert checks(row)["cmemit_counts_consistent"] == "fail"
    assert sheet == before


def test_saved_embedding_and_alphabet_rechecked_even_without_old_issues():
    sheet=build_sheet(">fixture246-sample1/1-4\nACGU\n",settings={"-N":1,"--idx":1,"--rna":True,"-e":4})
    row=rows(sheet)[0]
    row["embedded_interval"]={"start":0,"end":8}
    row["alphabet"]="DNA"
    sheet["issues"]=[]
    answer=calc_row(calculated(sheet),row["record_key"])
    assert checks(answer)["cmemit_embedding_interval_valid"] == "fail"
    assert checks(answer)["cmemit_alphabet_matches"] == "fail"


def test_compact_a2m_counts_present_but_gap_denominator_unavailable():
    sheet=build_sheet((NATIVE/"a2m_insertions/emitted.out").read_bytes(),mode="sample_aligned",fmt="a2m",
        settings={"-N":5,"--idx":1,"--rna":True,"--outformat":"A2M"})
    row=calc_row(calculated(sheet),rows(sheet)[0]["record_key"])
    assert row["components"]["residue_count"]["value"] == 12
    assert row["components"]["gc_fraction_canonical"]["value"] == pytest.approx(8/12)
    assert row["components"]["gap_fraction"]["state"] == "not_measured"


def test_geometry_and_annotation_failures_preserve_useful_counts():
    sheet=build_sheet("# STOCKHOLM 1.0\nfixture246-sample1 ACG\nfixture246-sample2 AC\n#=GC RF xxx\n#=GC SS_cons <.\n//\n",
                     mode="sample_aligned",fmt="stockholm")
    result=calculated(sheet)
    al=calc_row(result,rows(sheet,"generated_alignment")[0]["record_key"])
    assert checks(al)["cmemit_alignment_geometry"] == "fail"
    assert checks(al)["cmemit_annotation_geometry"] == "fail"
    assert calc_row(result,rows(sheet)[0]["record_key"])["components"]["gc_count"]["value"] == 2


@pytest.mark.parametrize("change", ["subject_ref","bool_count","bad_member","bad_origin"])
def test_closed_saved_sheet_validation(change):
    sheet=build_sheet((PRIOR/"cmemit_stockholm/emitted.out").read_bytes(),mode="sample_aligned",fmt="stockholm")
    if change=="subject_ref": rows(sheet)[0]["subject_ref"]="target"
    elif change=="bool_count": rows(sheet)[0]["values"]["gc_count"]["value"]=True
    elif change=="bad_member": rows(sheet,"generated_alignment")[0]["sequence_keys"].append("absent")
    else: rows(sheet)[0]["origin"]="observed_sequence"
    with pytest.raises(ValueError): calculated(sheet)


def test_parameters_not_silently_ignored_and_declared_outputs():
    sheet=build_sheet(">fixture246-sample1\nNN\n",settings={"-N":1,"--idx":1,"--rna":True})
    with pytest.raises(ValueError): calculate_cmemit_components(sheet,parameters={"confidence_weight":1})
    result=calculated(sheet)
    assert {i["code"] for i in result["issues"]} <= ISSUE_CODES
    assert {c["check"] for r in result["rows"] for c in r["checks"]} <= CHECK_NAMES


@pytest.mark.parametrize("family", ["cm", "hmm"])
def test_native_trace_scores_are_reported_separately_and_recalculable(family):
    directory=NATIVE/("trace_unaligned_"+family)
    sheet=build_sheet((directory/"emitted.out").read_bytes(),trace=(directory/"traces.txt").read_bytes(),
        settings={"-N":2,"--idx":1,"--rna":True,**({"--hmmonly":True} if family=="hmm" else {})})
    before=deepcopy(sheet)
    result=calculated(json.loads(json.dumps(sheet)))
    row=calc_row(result,sheet["native_rows"][0]["record_key"])
    assert row["components"]["score_bits"]["value"] == (11.17 if family=="cm" else 9.94)
    assert row["components"]["score_bits"]["basis"] == "native_reported"
    assert row["components"]["structure_score_bits"]["value"] == (.71 if family=="cm" else None)
    assert row["components"]["structure_score_bits"]["state"] == ("present" if family=="cm" else "not_measured")
    assert checks(row)["cmemit_model_association"] == "pass"
    assert checks(row)["cmemit_trace_decoded"] == "unknown"
    assert sheet == before


def test_trace_reference_forgery_rejected():
    d=NATIVE/"trace_unaligned_cm"
    sheet=build_sheet((d/"emitted.out").read_bytes(),trace=(d/"traces.txt").read_bytes())
    sheet["native_rows"][0]["sequence_keys"]=["absent"]
    with pytest.raises(ValueError): calculated(sheet)
