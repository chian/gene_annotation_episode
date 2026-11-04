from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import infernal_search_inputs as inputs
from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores

FIXTURES = Path(__file__).parent / "fixtures/infernal_search_graders"


def metadata():
    seqs = []
    for block in (FIXTURES / "tiny.fa").read_text().split(">")[1:]:
        name, *lines = block.splitlines()
        sequence = "".join(lines)
        seqs.append({"name": name, "sequence": sequence, "length": len(sequence)})
    return seqs, [{"name": "tRNA5", "consensus_length": 72}, {"name": "tRNA5-hand", "consensus_length": 74}]


def artifact(name="cmsearch_fmt3", *, content=None, complete=True, table_format=None, artifact_id=None):
    if table_format is None:
        table_format = 2 if name.startswith("cmscan") and "no_hits" in name else int(name[-1]) if "fmt" in name else 3
    return {"artifact_id": artifact_id or name, "format": "infernal_tblout", "table_format": table_format,
            "complete": complete, "content": (FIXTURES / (name+".hits.tbl")).read_text() if content is None else content}


def populate(arts=None, *, program="cmsearch", supplied=True, sequence_metadata=None, model_metadata=None, **operation):
    seqs, models = metadata()
    return inputs.populate_infernal_search_sheet(arts or [artifact()],
        operation={"program": program, "native_version": "1.1.5", "settings": {}, **operation},
        sequence_metadata=sequence_metadata if sequence_metadata is not None else seqs if supplied else None,
        model_metadata=model_metadata if model_metadata is not None else models if supplied else None)


def codes(value):
    return {r["code"] for r in value["issues"]}


def replace_cell(text, row_number, cell, value, *, fmt=3):
    lines = text.splitlines()
    count = 0
    fixed = 28 if fmt == 2 else 19 if fmt == 3 else 17
    for index, line in enumerate(lines):
        if not line or line.startswith("#"):
            continue
        if count == row_number:
            values = line.split(maxsplit=fixed)
            values[cell] = value
            lines[index] = " ".join(values)
            return "\n".join(lines)+"\n"
        count += 1
    raise AssertionError("row missing")


@pytest.mark.parametrize("program,fmt", [("cmsearch",1),("cmsearch",3),("cmscan",1),("cmscan",2),("cmscan",3)])
def test_actual_native_formats_roles_numerators_and_denominators(program, fmt):
    native = artifact(f"{program}_fmt{fmt}")
    sheet = populate([native], program=program)
    assert sheet["status"] == "available"
    assert len(sheet["hits"]) == 10
    assert sheet["artifacts"][0]["content"] == native["content"]
    assert sheet["artifacts"][0]["native_complete"] is True
    assert [h["locator"]["line"] for h in sheet["hits"]] == list(range(3, 13))
    first = sheet["hits"][0]
    assert first["sequence"]["name"] == "native_forward"
    assert first["model"]["name"] == "tRNA5"
    assert first["sequence"]["native_role"] == ("target" if program == "cmsearch" else "query")
    assert first["model"]["native_role"] == ("query" if program == "cmsearch" else "target")
    assert first["bitscore"] == 71.4
    assert first["bias_bits"] == 0
    assert first["gc_fraction"] == .5
    assert first["evalue"] == (1.9e-22 if program == "cmsearch" else 6.7e-23)
    assert all(h["inclusion"] == "?" for h in sheet["hits"])
    scores = calculate_infernal_search_scores(sheet)
    assert scores["status"] == "available"
    assert scores["hits"][0]["components"]["model_span_fraction"] == 1
    repeat = next(g for g in scores["sequence_strand_aggregates"] if g["sequence_names"] == ["native_repeat"])
    assert repeat["hit_count"] == 4
    assert repeat["union_intervals"] == [[0,72],[122,194]]
    assert repeat["union_numerator"] == 144
    assert repeat["union_denominator"] == 194
    assert repeat["union_span_fraction"] == pytest.approx(144/194)
    assert len(repeat["overlap_memberships"]) == 2
    assert len(repeat["identical_interval_memberships"]) == 2


def test_native_reverse_sequence_does_not_reverse_model():
    sheet = populate()
    hit = next(h for h in sheet["hits"] if h["sequence"]["name"] == "native_reverse")
    assert (hit["sequence_from"], hit["sequence_to"], hit["strand"]) == (72,1,"-")
    assert (hit["model_from"], hit["model_to"]) == (1,72)
    assert hit["sequence_interval"] == [0,72]
    assert hit["model_interval"] == [0,72]
    groups = calculate_infernal_search_scores(sheet)["sequence_strand_aggregates"]
    assert next(g for g in groups if g["strand"] == "-")["union_span_fraction"] == 1


def test_actual_native_format2_indices_are_local_to_query_list_and_ditto():
    sheet = populate([artifact("cmscan_fmt2")], program="cmscan")
    hits = sheet["hits"]
    assert hits[1]["anyidx"] == 1
    assert hits[1]["winidx"] == '"'
    assert hits[1]["anyfrct1"] == 1
    assert hits[1]["winfrct1"] == '"'
    assert hits[1]["overlap_references"]["win"]["ditto_of"] == "any"
    assert hits[1]["overlap_references"]["any"]["hit_id"] == hits[0]["hit_id"]
    assert hits[3]["overlap_references"]["any"]["hit_id"] == hits[2]["hit_id"]
    assert hits[3]["query_list_locator"] != hits[1]["query_list_locator"]
    assert hits[1]["clan"] is None and hits[1]["native_tokens"]["clan"] == "-"


@pytest.mark.parametrize("program", ["cmsearch", "cmscan"])
def test_actual_native_no_hits_are_available_not_missing(program):
    sheet = populate([artifact(program+"_no_hits")], program=program, supplied=False)
    assert sheet["status"] == "available"
    assert sheet["hits"] == []
    scores = calculate_infernal_search_scores(sheet)
    assert scores["status"] == "available"
    assert scores["hits"] == scores["sequence_strand_aggregates"] == []


def test_actual_hmm_algorithm_and_reporting_inclusion_are_not_confidence():
    hmm = populate([artifact("cmsearch_hmmonly")])
    assert all(h["algorithm"] == "hmm" and h["truncation"] == "-" for h in hmm["hits"])
    sheet = populate([artifact("cmsearch_mixed")])
    assert {h["inclusion"] for h in sheet["hits"]} == {"!", "?"}
    reported = calculate_infernal_search_scores(sheet)
    included = calculate_infernal_search_scores(sheet, parameters={"hit_scope":"included"})
    assert len(reported["hits"]) == len(included["hits"]) == len(sheet["hits"])
    assert sum(g["hit_count"] for g in included["sequence_strand_aggregates"]) == sum(h["inclusion"]=="!" for h in sheet["hits"])
    assert [h["components"] for h in included["hits"]] == [h["components"] for h in reported["hits"]]
    empty = calculate_infernal_search_scores(populate(), parameters={"hit_scope":"included"})
    assert all(g["hit_count"]==0 and g["union_numerator"]==0 and g["union_span_fraction"]==0 for g in empty["sequence_strand_aggregates"])


def test_missing_denominators_and_identity_preserve_native_measurements():
    sheet = populate([artifact("cmsearch_fmt1")], supplied=False)
    scores = calculate_infernal_search_scores(sheet)
    c = scores["hits"][0]["components"]
    assert c["bitscore"] == 71.4 and c["sequence_span_length"] == 72
    assert c["sequence_span_fraction"] is None and c["model_span_fraction"] is None
    assert scores["sequence_strand_aggregates"] == []
    assert len(scores["unresolved_aggregate_hit_ids"]) == 10
    assert "length_denominator_missing" in codes(sheet)


def test_native_fmt2_can_define_local_population_without_metadata_but_not_cross_files():
    a = artifact("cmscan_fmt2", artifact_id="a")
    b = artifact("cmscan_fmt2", artifact_id="b")
    scores = calculate_infernal_search_scores(populate([a,b], program="cmscan", supplied=False))
    assert len(scores["sequence_strand_aggregates"]) == 8
    assert all(g["sequence_identity"]["kind"]=="native_query_list" for g in scores["sequence_strand_aggregates"])
    assert all(g["union_span_fraction"] is not None for g in scores["sequence_strand_aggregates"])


def test_native_length_disagrees_with_supplied_does_not_erase_span_score():
    seq, _ = metadata()
    seq[0].pop("sequence")
    seq[0]["length"] = 80
    sheet = populate(sequence_metadata=seq)
    assert "native_supplied_length_conflict" in codes(sheet)
    row = calculate_infernal_search_scores(sheet)["hits"][0]
    assert row["components"]["sequence_span_length"] == 72
    assert row["components"]["sequence_span_fraction"] is None
    assert row["components"]["bitscore"] == 71.4
    assert sheet["hits"][0]["lengths"]["sequence"]["native"] == 72
    assert sheet["hits"][0]["lengths"]["sequence"]["supplied"] == 80


@pytest.mark.parametrize("case", ["duplicate", "invalid_sequence_length", "occurrence", "invalid_length"])
def test_metadata_ambiguity_and_occurrences_are_not_first_record_joins(case):
    seq, _ = metadata()
    if case == "duplicate":
        seq.append(deepcopy(seq[0]))
    elif case == "invalid_sequence_length":
        seq[0]["sequence"] += "A"
    elif case == "occurrence":
        seq[0]["occurrence"] = 1
    else:
        seq[0]["length"] = 0
    sheet = populate(sequence_metadata=seq)
    hit = sheet["hits"][0]
    assert hit["sequence_length"] is None
    assert hit["sequence"]["identity"] is None
    assert hit["sequence"]["metadata_join"]["status"] != "matched"
    assert hit["bitscore"] == 71.4
    assert sheet["sequence_metadata"] == seq


def test_wrong_accession_and_scoped_metadata_do_not_join():
    seq, _ = metadata()
    seq[0]["accession"] = "WRONG"
    text = replace_cell(artifact()["content"],0,1,"REAL")
    sheet = populate([artifact(content=text)], sequence_metadata=seq)
    assert sheet["hits"][0]["sequence"]["metadata_join"]["status"] == "identity_conflict"
    assert sheet["hits"][0]["sequence_length"] is None
    seq[0]["artifact_id"] = "another_artifact"
    sheet = populate([artifact(content=text)], sequence_metadata=seq)
    assert sheet["hits"][0]["sequence"]["metadata_join"]["status"] == "missing"


def test_false_same_name_query_record_association_is_not_resolved_by_visible_order():
    text = artifact("cmscan_fmt2")["content"].replace("native_reverse", "native_forward")
    sheet = populate([artifact("cmscan_fmt2",content=text)], program="cmscan")
    assert "native_record_association_ambiguous" in codes(sheet)
    assert sheet["hits"][0]["sequence"]["identity"] is None
    assert sheet["hits"][2]["sequence"]["identity"] is None
    assert sheet["hits"][0]["sequence"]["input_record_occurrence"] is None
    assert sheet["hits"][3]["overlap_references"]["any"]["hit_id"] == sheet["hits"][2]["hit_id"]


def test_invalid_native_cells_malformed_rows_and_zero_are_independent():
    text = replace_cell(artifact()["content"],0,12,"nan")
    text = replace_cell(text,0,15,"0")
    text = text.replace("#\n# Program:", "garbled two columns\n#\n# Program:")
    sheet = populate([artifact(content=text)])
    assert len(sheet["hits"]) == 10 and len(sheet["artifacts"][0]["rows"]) == 11
    assert "native_row_truncated_or_wrong_format" in codes(sheet)
    c = calculate_infernal_search_scores(sheet)["hits"][0]["components"]
    assert c["gc_fraction"] is None
    assert c["evalue"] == 0
    assert c["bitscore"] == 71.4 and c["sequence_span_fraction"] == 1
    assert "log_evalue" not in c
    json.dumps(sheet,allow_nan=False)
    aggregate=calculate_infernal_search_scores(sheet)["sequence_strand_aggregates"][0]
    assert aggregate["union_numerator"]==72
    assert aggregate["union_span_fraction"] is None
    assert aggregate["complete_for_selected_population"] is False


def test_unrepresentable_nonzero_evalue_never_becomes_native_zero():
    sheet=populate([artifact(content=replace_cell(artifact()["content"],0,15,"1e-999"))])
    assert sheet["hits"][0]["evalue"] is None
    assert sheet["hits"][0]["native_tokens"]["evalue"]=="1e-999"
    assert "native_cell_invalid" in codes(sheet)


def test_invalid_native_length_cannot_silently_fall_back_to_supplied_denominator():
    sheet=populate([artifact(content=replace_cell(artifact()["content"],0,18,"bad"))])
    assert sheet["hits"][0]["sequence_length"] is None
    assert sheet["hits"][0]["lengths"]["sequence"]["supplied"]==72
    assert sheet["hits"][0]["lengths"]["sequence"]["status"]=="invalid_native_length"


def test_one_supplied_name_cannot_bind_multiple_native_accessions():
    text=replace_cell(artifact()["content"],0,1,"ONE")
    text=replace_cell(text,6,1,"TWO")
    sheet=populate([artifact(content=text)])
    assert "native_record_association_ambiguous" in codes(sheet)
    assert sheet["hits"][0]["sequence"]["identity"] is None
    assert sheet["hits"][6]["sequence"]["identity"] is None


@pytest.mark.parametrize("cell,value", [(5,"72"),(7,"0"),(8,"999"),(9,"-")])
def test_invalid_coordinates_preserve_other_native_cells(cell,value):
    text = replace_cell(artifact()["content"],0,cell,value)
    if cell == 5:
        text = replace_cell(text,0,6,"1")
    sheet = populate([artifact(content=text)])
    c = calculate_infernal_search_scores(sheet)["hits"][0]["components"]
    assert c["bitscore"] == 71.4
    assert c["model_span_length" if cell==5 else "sequence_span_length"] is None


def test_single_base_coordinate_boundary_and_partial_union():
    text = replace_cell(artifact()["content"],0,7,"72")
    sheet = populate([artifact(content=text)])
    c = calculate_infernal_search_scores(sheet)["hits"][0]["components"]
    assert c["sequence_span_length"] == 1 and c["sequence_span_fraction"] == pytest.approx(1/72)
    text = replace_cell(text,6,8,"1000")
    scores = calculate_infernal_search_scores(populate([artifact(content=text)]))
    group = scores["sequence_strand_aggregates"][0]
    assert group["union_numerator"] == 1
    assert group["invalid_geometry_count"] == 1
    assert group["union_span_fraction"] is None


def test_native_length_conflict_between_hits_invalidates_all_matching_denominators():
    text = replace_cell(artifact()["content"],6,18,"73")
    sheet = populate([artifact(content=text)])
    assert "entity_native_lengths_conflict" in codes(sheet)
    assert all(h["sequence_length"] is None for h in sheet["hits"] if h["sequence"]["name"]=="native_forward")


@pytest.mark.parametrize("change,expected", [
    ("program","program_declaration_conflict"), ("version","version_declaration_conflict"),
    ("format","table_format_declaration_conflict"), ("complete","completion_declaration_conflict")])
def test_contradictory_declarations_are_exposed(change,expected):
    art = artifact()
    operation = {}
    if change=="program": operation["program"]="cmscan"
    if change=="version": operation["native_version"]="1.1.4"
    if change=="format": art["table_format"]=1
    if change=="complete": art["complete"]=False
    sheet = populate([art], **operation)
    assert expected in codes(sheet)
    assert len(sheet["hits"]) == 10
    assert sheet["status"] == "partial"


def test_unknown_settings_remain_absent_and_unknown_completion_is_not_no_hit():
    sheet = populate([artifact(content="",complete=None)], supplied=False,native_version=None)
    assert sheet["status"] == "missing"
    assert sheet["operation"]["settings"] == {}
    text = "\n".join(artifact()["content"].splitlines()[:12]) + "\n"
    partial = populate([artifact(content=text,complete=None)],native_version=None)
    assert partial["status"] == "partial"
    assert partial["artifacts"][0]["effective_complete"] is None
    assert "native_version_unknown" in codes(partial)
    assert len(partial["hits"]) == 10


def test_duplicate_artifact_identity_remains_distinct_and_unjoinable():
    sheet=populate([artifact(),artifact()])
    assert "artifact_id_ambiguous" in codes(sheet)
    assert len({h["hit_id"] for h in sheet["hits"]})==20
    assert calculate_infernal_search_scores(sheet)["sequence_strand_aggregates"]==[]


def test_duplicate_representations_across_explicit_shared_input_do_not_double_union():
    sheet=populate([artifact(artifact_id="a"),artifact(artifact_id="b")])
    scores=calculate_infernal_search_scores(sheet)
    group=scores["sequence_strand_aggregates"][0]
    assert group["hit_count"]==4 and group["union_numerator"]==72
    assert len(group["duplicate_representation_memberships"])==2
    assert all(len(m)==2 for m in group["duplicate_representation_memberships"])


@pytest.mark.parametrize("case",["wrong_index","wrong_fraction","wrong_strand","wrong_ditto"])
def test_format2_overlap_relationship_validation(case):
    text=artifact("cmscan_fmt2")["content"]
    cell,value={"wrong_index":(20,"99"),"wrong_fraction":(21,"0.100"),"wrong_strand":(11,"-"),"wrong_ditto":(24,"-")}[case]
    text=replace_cell(text,1,cell,value,fmt=2)
    sheet=populate([artifact("cmscan_fmt2",content=text)],program="cmscan")
    assert any(code.startswith("overlap_") for code in codes(sheet))
    assert sheet["hits"][1]["bitscore"]==69.2


def test_format2_omitted_reference_minus_one_is_not_missing_index_or_zero_fraction():
    text=artifact("cmscan_fmt2")["content"]
    for cell,value in [(19,"$"),(20,"-1"),(23,"-"),(24,"-"),(25,"-")]:
        text=replace_cell(text,1,cell,value,fmt=2)
    text=text.replace("--fmt 2", "--fmt 2 --oskip")
    sheet=populate([artifact("cmscan_fmt2",content=text)],program="cmscan")
    hit=sheet["hits"][1]
    assert hit["anyidx"]==-1 and hit["anyfrct1"]==1
    assert hit["overlap_references"]["any"]["status"]=="omitted_reference"
    assert "overlap_reference_missing_or_ambiguous" not in codes(sheet)


def test_header_qualified_legacy_format2_without_lengths_keeps_missing_denominators():
    original=artifact("cmscan_fmt2")["content"]
    lines=[]
    for line in original.splitlines():
        if line.startswith("#idx"):
            line=line.replace("mdl len seq len ","")
        elif line and not line.startswith("#"):
            fields=line.split(maxsplit=28)
            line=" ".join(fields[:26]+fields[28:])
        line=line.replace("1.1.5 (Sep 2023)","1.1.4 (Dec 2020)")
        lines.append(line)
    sheet=populate([artifact("cmscan_fmt2",content="\n".join(lines)+"\n")],program="cmscan",native_version="1.1.4",supplied=False)
    assert len(sheet["hits"])==10
    assert all(h["native_sequence_length"] is None and h["native_model_length"] is None for h in sheet["hits"])
    assert sheet["hits"][1]["overlap_references"]["any"]["status"]=="resolved"
    assert calculate_infernal_search_scores(sheet)["hits"][0]["components"]["sequence_span_fraction"] is None


def test_format2_missing_index_and_truncated_artifact_never_look_complete():
    text=replace_cell(artifact("cmscan_fmt2")["content"],1,0,"3",fmt=2)
    sheet=populate([artifact("cmscan_fmt2",content=text)],program="cmscan",supplied=False)
    assert "native_list_index_discontinuity" in codes(sheet)
    assert sheet["hits"][0]["sequence"]["identity"] is None
    text="\n".join(artifact()["content"].splitlines()[:12])+"\n"
    scored=calculate_infernal_search_scores(populate([artifact(content=text,complete=None)]))
    assert all(g["union_span_fraction"] is None and not g["complete_for_selected_population"] for g in scored["sequence_strand_aggregates"])


def test_wrong_native_header_program_and_version_do_not_silently_override():
    text=artifact()["content"].replace("# [ok]","# Program: cmscan\n# [ok]")
    sheet=populate([artifact(content=text)])
    assert "native_declaration_conflict" in codes(sheet)
    assert all(h["sequence"]["native_role"] is None for h in sheet["hits"])
    future=populate([artifact(content=artifact()["content"].replace("1.1.5 (Sep 2023)","9.0.0 (future)"))],native_version="9.0.0")
    assert "native_version_unverified" in codes(future)


def test_artifact_decode_and_format_errors_are_explicit():
    sheet=populate([artifact(content=artifact()["content"]+"# replacement \ufffd\n")])
    assert "native_text_possible_decode_loss" in codes(sheet)
    assert "data_after_native_completion_marker" in codes(sheet)
    invalid=populate([artifact(table_format=9)])
    assert invalid["status"]=="invalid"
    assert "artifact_contract_invalid" in codes(invalid)


def test_headerless_native_option_format_resolves_cells_and_exposes_wrong_declaration():
    text="\n".join(artifact()["content"].splitlines()[2:])+"\n"
    sheet=populate([artifact(content=text,table_format=1)],supplied=False)
    assert "native_option_table_format_conflict" in codes(sheet)
    assert sheet["artifacts"][0]["effective_table_format"]==3
    assert sheet["artifacts"][0]["table_format_basis"]=="native_options"
    assert sheet["hits"][0]["native_sequence_length"]==72


def test_format2_cannot_reassign_physical_roles_to_cmsearch():
    text=artifact("cmscan_fmt2")["content"].replace("# Program:         cmscan","# Program:         cmsearch")
    sheet=populate([artifact("cmscan_fmt2",content=text)])
    assert "format_2_requires_cmscan" in codes(sheet)
    assert sheet["hits"][0]["sequence"]["native_role"] is None
    assert sheet["hits"][0]["bitscore"]==71.4


def test_saved_sheet_recalculation_uses_no_native_text_parser_network_or_process(monkeypatch):
    sheet=json.loads(json.dumps(populate()))
    expected=calculate_infernal_search_scores(sheet)
    def forbidden(*args,**kwargs):
        raise AssertionError("parser/acquisition/execution forbidden during recalculation")
    monkeypatch.setattr(inputs,"populate_infernal_search_sheet",forbidden)
    monkeypatch.setattr(inputs,"_read_artifact",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr(subprocess,"run",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(Path,"read_text",forbidden)
    for art in sheet["artifacts"]:
        art["content"]="native text intentionally unavailable to calculator"
        art["rows"]=[]
    assert calculate_infernal_search_scores(sheet)==expected
    included=calculate_infernal_search_scores(sheet,parameters={"hit_scope":"included"})
    assert all(g["hit_count"]==0 for g in included["sequence_strand_aggregates"])


@pytest.mark.parametrize("parameters",[{"temperature":1},{"hit_scope":"best"},[],{"hit_scope":None}])
def test_unknown_parameters_are_rejected(parameters):
    with pytest.raises(ValueError,match="parameters_invalid"):
        calculate_infernal_search_scores(populate(),parameters=parameters)


def test_all_calculated_cell_definitions_have_meanings_and_native_fixture_hashes_match():
    scores=calculate_infernal_search_scores(populate())
    for definition in scores["definitions"].values():
        assert set(definition)=={"inputs","formula_or_native_source","units","population","denominator","kind","coordinate_convention","uncertainty","missing_behavior"}
    for row in json.loads((FIXTURES/"MANIFEST.json").read_text()):
        assert hashlib.sha256((FIXTURES/row["path"]).read_bytes()).hexdigest()==row["sha256"]


def test_no_input_mutation_and_finite_json_validation():
    arts=[artifact()]
    before=deepcopy(arts)
    sheet=populate(arts)
    saved=deepcopy(sheet)
    calculate_infernal_search_scores(sheet)
    assert arts==before and sheet==saved
    with pytest.raises(ValueError,match="finite_json"):
        populate(arts,settings={"value":float("nan")})
