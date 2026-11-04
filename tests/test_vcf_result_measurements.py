"""Retained native VCF evidence and explicitly engineered reader controls.

The native fixture is upstream expected output, not execution of a current
variant caller. Engineered records below supply independent population and
grammar oracles; they do not claim biological or clinical interpretation.
"""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest

from gene_annotation_episode import vcf_result_measurements as core


FIXTURES = Path(__file__).parent / "fixtures" / "vcf_results"
NATIVE_NAME = "expected.testExposureOfSmithWatermanParameters.M2.gatk4.vcf"
NATIVE_SHA256 = "5a143a78f9a29c7f3abefecfcbbb97764a4517db6af7f7f1d7012c36f48f3ff0"
RESULT_SOURCE = "source_" + "a" * 24


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _file(raw):
    digest = _sha(raw)
    return dict(artifact_ref="artifact_" + digest, sha256=digest,
        size_bytes=len(raw), format="vcf")


def _input(raw, *, original=None, capture_state="complete", source_ref=None):
    original = raw if original is None else original
    return dict(input_id="supplied-vcf-occurrence", retained_file=_file(raw),
        original_file=_file(original), source_ref=source_ref, content=raw,
        capture=dict(state=capture_state, byte_start_0based=0,
            byte_end_0based_exclusive=len(raw), original_size_bytes=len(original)))


def _selection(**changes):
    value = dict(version="vcf_result_selection_v1", record_ordinals=None,
        sample_ordinals=None, info_keys=None, format_keys=None, offset=0, limit=1000)
    value.update(changes)
    return value


def _vcf(rows, *, samples=("S1", "S2"), definitions=(), metadata=()):
    """Literal engineered VCF bytes; no parser or caller generates the oracle."""
    lines = ["##fileformat=VCFv4.2", "##source=engineered_reader_test"]
    lines.extend(metadata)
    lines.extend(definitions)
    columns = "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
    if samples:
        columns += "\tFORMAT\t" + "\t".join(samples)
    lines.append(columns)
    lines.extend(rows)
    return ("\n".join(lines) + "\n").encode("ascii")


DEFINITIONS = (
    '##INFO=<ID=AC,Number=A,Type=Integer,Description="Native alternate counts">',
    '##INFO=<ID=AN,Number=1,Type=Integer,Description="Native allele number">',
    '##INFO=<ID=AF,Number=A,Type=Float,Description="Native allele fractions">',
    '##INFO=<ID=STR,Number=0,Type=Flag,Description="Literal flag">',
    '##INFO=<ID=SS,Number=1,Type=String,Description="Opaque string, with comma">',
    '##FORMAT=<ID=GT,Number=1,Type=String,Description="Native genotype">',
    '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Native allele depths">',
    '##FORMAT=<ID=AF,Number=A,Type=Float,Description="Native fractions">',
    '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Native depth">',
    '##FORMAT=<ID=PL,Number=G,Type=Integer,Description="Genotype likelihoods">',
    '##FILTER=<ID=q10,Description="Engineered named filter">',
)


def _population_bytes():
    # Independent oracle: two records, three ALT occurrences, four sample
    # cells, seven GT slots (two missing), five called allele slots. Native
    # INFO AN=99 and AF values deliberately are not derived from those slots.
    return _vcf([
        "1\t10\tdup\tA\tC,G\t.\t.\tAC=7,1;AN=99;AF=0.1,0.8;STR;SS=a|b"
        "\tGT:AD:AF:DP\t0/2:2,0,4:0.1,0.8:6\t./.:.,.,.:.,.:.",
        "1\t20\tdup\tC\tT\t0\tPASS\tAC=1;AN=3;AF=0.8"
        "\tGT:AD:AF:DP\t0/0:8,0:0:8\t1:0,2:1:2",
    ], definitions=DEFINITIONS)


def _field(record, key, *, sample=None, occurrence=0):
    rows = record["info"] if sample is None else record["samples"][sample]["fields"]
    matches = [row for row in rows if row["key"] == key]
    return matches[occurrence]


def _value_tokens(field):
    return [value["token"]["raw_token"] for value in field["values"]]


def _tokens(value):
    if type(value) is dict:
        if set(value) == {"raw_token", "raw_base64", "locator"}:
            yield value
        else:
            for child in value.values():
                yield from _tokens(child)
    elif type(value) is list:
        for child in value:
            yield from _tokens(child)


def _no_io_or_parse(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("saved VCF operation reopened parsing, acquisition or process work")
    monkeypatch.setattr(core, "parse_vcf_sheet", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    return forbidden


@pytest.fixture
def native_raw():
    raw = (FIXTURES / NATIVE_NAME).read_bytes()
    assert len(raw) == 67702 and _sha(raw) == NATIVE_SHA256
    return raw


def test_required_native_fixture_has_exact_git_blob_and_self_contained_provenance(native_raw):
    provenance = json.loads((FIXTURES / "gatk_mutect_expected.provenance.json").read_bytes())
    assert provenance["file"] == NATIVE_NAME
    assert provenance["sha256"] == _sha(native_raw)
    assert provenance["size_bytes"] == len(native_raw)
    assert hashlib.sha1(b"blob 67702\0" + native_raw).hexdigest() == provenance["upstream"]["git_blob_sha1"]
    assert provenance["upstream"]["git_blob_sha1"] == "d4015319b6c8754734cf79665a4d46b5b9871f83"
    assert provenance["declared_metadata"]["reference_assembly"] is None
    assert provenance["declared_metadata"]["reference_fasta_identity"] is None
    assert provenance["declared_metadata"]["exact_caller_build"] is None
    assert provenance["application_native_execution_performed_for_this_fixture"] is False


def test_native_sheet_retains_exact_bytes_and_file_only_input_without_invented_source(native_raw):
    supplied = _input(native_raw)
    original = deepcopy(supplied)
    sheet = core.parse_vcf_sheet(supplied)
    assert sheet["version"] == "vcf_result_sheet_v1"
    assert sheet["input"] == {key: value for key, value in supplied.items() if key != "content"}
    assert sheet["input"]["source_ref"] is None
    assert sheet["raw_content"] == dict(encoding="base64", data=base64.b64encode(native_raw).decode("ascii"),
        sha256=NATIVE_SHA256, size_bytes=67702)
    assert core.validate_vcf_sheet(sheet) == sheet
    assert supplied == original


def test_native_record_and_sample_occurrences_are_not_deduplicated_or_renumbered(native_raw):
    sheet = core.parse_vcf_sheet(_input(native_raw))
    records = sheet["records"]
    assert len(records) == 295
    assert [row["record_ordinal_0based"] for row in records] == list(range(295))
    assert [records[index]["line_ordinal_0based"] for index in (0, 63, 279, 294)] == [44, 107, 323, 338]
    assert all(len(row["samples"]) == 1 for row in records)
    assert all(row["samples"][0]["sample_ordinal_0based"] == 0
        and row["samples"][0]["sample_name"] == "NA12878" for row in records)


def test_native_multiallelic_record_preserves_four_ordered_alternates_and_five_GT_slots(native_raw):
    record = core.parse_vcf_sheet(_input(native_raw))["records"][63]
    assert [(row["alt_ordinal_0based"], row["allele_index_1based"], row["token"]["raw_token"])
        for row in record["alts"]] == [
        (0, 1, "T"), (1, 2, "TAC"), (2, 3, "TACACACACAC"), (3, 4, "TAACACACACAC")]
    assert _field(record, "GT", sample=0)["token"]["raw_token"] == "0/1/2/3/4"
    assert _value_tokens(_field(record, "AD", sample=0)) == ["2", "3", "14", "5", "7"]
    assert _value_tokens(_field(record, "AF", sample=0)) == ["0.085", "0.326", "0.177", "0.306"]
    assert _value_tokens(_field(record, "AS_SB_TABLE")) == ["2,0|2,1|8,6|4,1|7,0"]
    genotype = record["samples"][0]["genotype"]
    assert genotype["ploidy"] == 5
    assert [row["allele_ordinal_0based"] for row in genotype["alleles"]] == [0, 1, 2, 3, 4]
    assert [row["allele_index"] for row in genotype["alleles"]] == [0, 1, 2, 3, 4]
    assert [row["value"] for row in genotype["separators"]] == ["/", "/", "/", "/"]


def test_native_phasing_and_distinct_AD_FAD_AF_are_retained_without_replacement(native_raw):
    record = core.parse_vcf_sheet(_input(native_raw))["records"][279]
    assert _field(record, "GT", sample=0)["token"]["raw_token"] == "0|1"
    assert _field(record, "PGT", sample=0)["token"]["raw_token"] == "0|1"
    assert _field(record, "PID", sample=0)["token"]["raw_token"] == "10099029_T_C"
    assert _value_tokens(_field(record, "AD", sample=0)) == ["19", "10"]
    assert _value_tokens(_field(record, "FAD", sample=0)) == ["25", "10"]
    assert _value_tokens(_field(record, "AF", sample=0)) == ["0.296"]
    assert _value_tokens(_field(record, "DP")) == ["30"]
    assert _value_tokens(_field(record, "DP", sample=0)) == ["29"]
    assert _value_tokens(_field(record, "POPAF")) == ["7.30"]
    assert _value_tokens(_field(record, "TLOD")) == ["35.13"]


def test_native_header_binds_INFO_and_FORMAT_namespaces_and_preserves_unknown_reference(native_raw):
    sheet = core.parse_vcf_sheet(_input(native_raw))
    header = sheet["header"]
    assert header["fileformat"] == "VCFv4.2" and header["decoder"] == "vcf4.2"
    assert header["state"] == "available"
    assert {row["key"] for row in header["meta_lines"]}.isdisjoint({"reference", "assembly", "GATKCommandLine"})
    metadata = {row["key"]: row["value"]["raw_token"] for row in header["meta_lines"]
        if row["key"] in {"MutectVersion", "tumor_sample", "filtering_status"}}
    assert metadata == dict(MutectVersion="2.2", tumor_sample="NA12878",
        filtering_status="Warning: unfiltered Mutect 2 calls.  Please run FilterMutectCalls to remove false positives.")
    record = sheet["records"][279]
    info, sample = _field(record, "DP"), _field(record, "DP", sample=0)
    assert info["definition_ordinals"] != sample["definition_ordinals"]
    for field, namespace in ((info, "INFO"), (sample, "FORMAT")):
        definition, = [header["definitions"][index] for index in field["definition_ordinals"]]
        assert (definition["namespace"], definition["id"], definition["number"], definition["type"]) == (
            namespace, "DP", "1", "Integer")


def test_all_native_token_witnesses_join_actual_original_bytes_and_File_identity(native_raw):
    sheet = core.parse_vcf_sheet(_input(native_raw))
    tokens = list(_tokens(sheet))
    assert tokens
    for token in tokens:
        location = token["locator"]
        assert location["input_id"] == "supplied-vcf-occurrence"
        assert location["artifact_ref"] == "artifact_" + NATIVE_SHA256
        assert location["sha256"] == NATIVE_SHA256
        assert location["line_start_1based"] == location["line_end_1based_inclusive"]
        start, end = location["byte_start_0based"], location["byte_end_0based_exclusive"]
        assert 0 <= start <= end <= len(native_raw)
        exact = native_raw[start:end]
        assert exact.decode("utf-8") == token["raw_token"]
        assert base64.b64decode(token["raw_base64"], validate=True) == exact
    assert sheet["records"][0]["locator"]["byte_start_0based"] == 4650
    assert sheet["records"][0]["locator"]["byte_end_0based_exclusive"] == 4847
    assert sheet["lines"][44]["locator"]["byte_end_0based_exclusive"] == 4848


def test_selection_preserves_caller_order_and_all_versus_empty_distinctions():
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    selections = [
        _selection(),
        _selection(record_ordinals=[1, 0], sample_ordinals=[1, 0],
            info_keys=["AN", "AC"], format_keys=["DP", "GT"], offset=1, limit=0),
        _selection(record_ordinals=[], sample_ordinals=[], info_keys=[], format_keys=[]),
    ]
    for selection in selections:
        original = deepcopy(selection)
        validated = core.validate_vcf_selection(selection, sheet=sheet)
        assert validated == original and selection == original
        assert validated is not selection


@pytest.mark.parametrize("changes", [
    dict(version="vcf_result_selection_unknown"),
    dict(record_ordinals=[0, 0]),
    dict(record_ordinals=[2]),
    dict(record_ordinals=[False]),
    dict(sample_ordinals=[1, 1]),
    dict(sample_ordinals=[2]),
    dict(info_keys=["AC", "AC"]),
    dict(format_keys="GT"),
    dict(offset=-1),
    dict(limit=True),
    dict(unrecognized=True),
])
def test_selection_is_closed_strict_and_rejects_outside_or_duplicate_original_ordinals(changes):
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    with pytest.raises(ValueError):
        core.validate_vcf_selection(_selection(**changes), sheet=sheet)


def test_duplicate_identifiers_positions_sample_names_and_INFO_keys_keep_original_occurrences():
    raw = _vcf([
        "1\t10\tdup\tA\tC\t.\t.\tAC=1;AC=2\tGT\t0/1\t0/0",
        "1\t10\tdup\tA\tC\t.\t.\tAC=3\tGT\t1\t.",
    ], samples=("same-name", "same-name"), definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    assert [row["record_ordinal_0based"] for row in sheet["records"]] == [0, 1]
    first = sheet["records"][0]
    assert [(sample["sample_ordinal_0based"], sample["sample_name"]) for sample in first["samples"]] == [
        (0, "same-name"), (1, "same-name")]
    assert _value_tokens(_field(first, "AC", occurrence=0)) == ["1"]
    assert _value_tokens(_field(first, "AC", occurrence=1)) == ["2"]
    assert _value_tokens(_field(sheet["records"][1], "AC")) == ["3"]
    assert first["issues"] or sheet["header"]["issues"] or sheet["issues"]


def test_malformed_record_keeps_its_slot_and_does_not_shift_later_original_ordinals():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tGT\t0/1\t0/0",
        "1\tnot-a-position\t.\tA\tC\t.\t.\t.\tGT\t0/1\t0/0",
        "1\t30\t.\tA\tG\t.\t.\t.\tGT\t1\t.",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    assert [row["record_ordinal_0based"] for row in sheet["records"]] == [0, 1, 2]
    assert sheet["records"][1]["pos_1based"] is None
    assert sheet["records"][1]["issues"]
    assert sheet["records"][2]["pos_1based"] == 30
    assert base64.b64decode(sheet["raw_content"]["data"], validate=True) == raw


def test_cardinality_conflicts_and_missing_values_retain_every_literal_value_token():
    raw = _vcf([
        "1\t10\t.\tA\tC,G\t.\t.\tAC=1;AF=0,.;STR"
        "\tGT:AD:DP\t0/2:0,.,3:0\t./.:.:.",
    ], definitions=DEFINITIONS)
    record = core.parse_vcf_sheet(_input(raw))["records"][0]
    assert _value_tokens(_field(record, "AC")) == ["1"]
    assert _field(record, "AC")["issues"]
    assert _value_tokens(_field(record, "AF")) == ["0", "."]
    assert _value_tokens(_field(record, "AD", sample=0)) == ["0", ".", "3"]
    assert _value_tokens(_field(record, "DP", sample=0)) == ["0"]
    assert _value_tokens(_field(record, "DP", sample=1)) == ["."]
    assert _field(record, "STR")["token"]["raw_token"] == "STR"


def test_symbolic_breakend_and_signed_SVLEN_values_remain_records_not_merged_events():
    definitions = DEFINITIONS + (
        '##INFO=<ID=END,Number=1,Type=Integer,Description="Native end">',
        '##INFO=<ID=SVLEN,Number=.,Type=Integer,Description="Native signed length">',
        '##INFO=<ID=MATEID,Number=.,Type=String,Description="Native mate labels">',
        '##INFO=<ID=EVENT,Number=1,Type=String,Description="Native event label">',
    )
    raw = _vcf([
        "1\t10\tdel\tN\t<DEL>\t.\t.\tEND=20;SVLEN=-10\tGT\t0/1\t0/0",
        "1\t30\tb1\tN\tN]2:40]\t.\tq10\tMATEID=b2;EVENT=e1\tGT\t0/1\t.",
        "2\t40\tb2\tN\t[1:30[N\t.\tq10\tMATEID=b1;EVENT=e1\tGT\t1\t.",
    ], definitions=definitions)
    records = core.parse_vcf_sheet(_input(raw))["records"]
    assert len(records) == 3
    assert [row["alts"][0]["token"]["raw_token"] for row in records] == ["<DEL>", "N]2:40]", "[1:30[N"]
    assert _value_tokens(_field(records[0], "END")) == ["20"]
    assert _value_tokens(_field(records[0], "SVLEN")) == ["-10"]
    assert _value_tokens(_field(records[1], "MATEID")) == ["b2"]
    assert _value_tokens(_field(records[2], "MATEID")) == ["b1"]
    assert _value_tokens(_field(records[1], "EVENT")) == _value_tokens(_field(records[2], "EVENT")) == ["e1"]


def test_unrepresentable_float_tokens_do_not_escape_as_nonfinite_JSON_numbers():
    raw = _vcf([
        "1\t10\t.\tA\tC,G\t.\t.\tAF=1e9999,1e-9999\tGT\t0/1\t.",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    field = _field(sheet["records"][0], "AF")
    assert _value_tokens(field) == ["1e9999", "1e-9999"]
    assert [row["decoded"] for row in field["values"]] == [
        dict(kind="overflow", value=None), dict(kind="underflow", value=None)]
    assert field["issues"]
    json.dumps(sheet, allow_nan=False)


def test_unfiltered_PASS_named_failure_and_native_zero_QUAL_are_distinct():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tGT\t0/1\t.",
        "1\t20\t.\tA\tC\t0\tPASS\t.\tGT\t0/1\t.",
        "1\t30\t.\tA\tC\t12\tq10\t.\tGT\t0/1\t.",
    ], definitions=DEFINITIONS)
    records = core.parse_vcf_sheet(_input(raw))["records"]
    assert [row["filter"]["state"] for row in records] == ["not_applied", "passed", "failed"]
    assert [row["filter"]["codes"] for row in records] == [[], [], ["q10"]]
    assert records[0]["qual"]["decoded"] == dict(kind="missing", value=None)
    assert records[1]["qual"]["decoded"] == dict(kind="Float", value=0.0)
    assert records[1]["qual"]["unit"] == "phred"


def test_duplicate_header_definitions_remain_ambiguous_without_first_match_selection():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\tAC=1\tGT\t0/1\t.",
    ], definitions=DEFINITIONS + (
        '##INFO=<ID=AC,Number=1,Type=String,Description="Conflicting engineered definition">',
    ))
    sheet = core.parse_vcf_sheet(_input(raw))
    field = _field(sheet["records"][0], "AC")
    assert len(field["definition_ordinals"]) == 2
    assert field["state"] == "ambiguous_definition"
    assert field["declared_type"] is field["declared_number"] is None
    assert _value_tokens(field) == ["1"]
    assert field["issues"] and sheet["header"]["issues"]


def test_Number_G_without_established_ploidy_keeps_values_indexed_and_unlabelled():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tPL\t0,10,20\t0,5,9",
        "1\t20\t.\tA\tC\t.\t.\t.\tGT:PL\t.:0,10,20\t./.:0,5,9",
    ], definitions=DEFINITIONS)
    records = core.parse_vcf_sheet(_input(raw))["records"]
    for record, sample in ((records[0], 0), (records[0], 1), (records[1], 0)):
        field = _field(record, "PL", sample=sample)
        assert field["cardinality"]["expected"] is None
        assert field["cardinality"]["ploidy"] is None
        assert [row["genotype_index_0based"] for row in field["values"]] == [0, 1, 2]
        assert all(row["genotype_allele_indices"] is None for row in field["values"])
    explicit = _field(records[1], "PL", sample=1)
    assert explicit["cardinality"]["ploidy"] == 2
    assert explicit["cardinality"]["ploidy_basis"] == "literal_GT_slots"
    assert [row["genotype_allele_indices"] for row in explicit["values"]] == [[0, 0], [0, 1], [1, 1]]


def test_polyploid_Number_G_preserves_observed_order_without_inventing_genotype_labels():
    raw = _vcf([
        "1\t10\t.\tA\tC,G\t.\t.\t.\tGT:PL\t0/1/2:0,1,2,3,4,5,6,7,8,9\t.:.",
    ], definitions=DEFINITIONS)
    field = _field(core.parse_vcf_sheet(_input(raw))["records"][0], "PL", sample=0)
    assert field["cardinality"] == dict(expected=10, observed=10, state="matched",
        ploidy=3, ploidy_basis="literal_GT_slots")
    assert _value_tokens(field) == ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    assert all(row["genotype_allele_indices"] is None for row in field["values"])
    assert field["issues"]


def test_flag_presence_and_malformed_flag_value_are_distinct_from_false_or_absent():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\tSTR\tGT\t0/1\t.",
        "1\t20\t.\tA\tC\t.\t.\tSTR=0\tGT\t0/1\t.",
        "1\t30\t.\tA\tC\t.\t.\t.\tGT\t0/1\t.",
    ], definitions=DEFINITIONS)
    records = core.parse_vcf_sheet(_input(raw))["records"]
    present, malformed = _field(records[0], "STR"), _field(records[1], "STR")
    assert present["flag"] is True and present["values"] == []
    assert present["has_equals"] is False and present["value_token"] is None
    assert malformed["state"] == "malformed" and malformed["issues"]
    assert malformed["has_equals"] is True and malformed["value_token"]["raw_token"] == "0"
    assert records[2]["info"] == []


def test_independent_record_allele_sample_and_GT_slot_denominators_do_not_replace_native_AN_AF():
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    value = core.calculate_vcf_components(sheet, _selection())["value"]
    population = value["population"]
    assert population["total_original_record_slots"] == 2
    assert population["retained_record_slots"] == population["selected_record_slots"] == 2
    assert population["selected_alt_tokens"] == 3
    assert population["selected_sample_cells"] == population["selected_observed_sample_cells"] == 4
    assert population["selected_genotype_slots"] == 7
    first, second = value["records"]
    assert [allele["state"] for allele in first["samples"][1]["genotype"]["alleles"]] == ["missing", "missing"]
    assert [sample["genotype"]["ploidy"] for sample in second["samples"]] == [2, 1]
    assert _value_tokens(_field(first, "AN")) == ["99"]
    assert _value_tokens(_field(first, "AF")) == ["0.1", "0.8"]
    assert _value_tokens(_field(first, "AF", sample=0)) == ["0.1", "0.8"]
    assert not {"calculated_AF", "calculated_AN", "calculated_AC"}.intersection(population)


def test_record_window_changes_returned_rows_without_changing_selected_denominators():
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    selected = _selection(record_ordinals=[1, 0], sample_ordinals=[1, 0])
    full = core.calculate_vcf_components(sheet, selected)["value"]
    page = core.calculate_vcf_components(sheet, dict(selected, offset=0, limit=1))["value"]
    empty_page = core.calculate_vcf_components(sheet, dict(selected, offset=99, limit=1))["value"]
    assert [row["record_ordinal_0based"] for row in full["records"]] == [1, 0]
    assert [row["record_ordinal_0based"] for row in page["records"]] == [1]
    assert [sample["sample_ordinal_0based"] for sample in page["records"][0]["samples"]] == [1, 0]
    for value in (full, page, empty_page):
        assert value["population"]["selected_record_slots"] == 2
        assert value["population"]["selected_alt_tokens"] == 3
        assert value["population"]["selected_sample_cells"] == 4
        assert value["population"]["selected_genotype_slots"] == 7
    assert page["population"]["returned_record_slots"] == 1
    assert page["population"]["returned_alt_tokens"] == 1
    assert page["population"]["returned_sample_cells"] == 2
    assert page["population"]["omitted_by_window_record_slots"] == 1
    assert page["population"]["has_more"] is True
    assert page["population"]["returned_record_fraction"] == dict(
        value=0.5, numerator=1, denominator=2, unit="fraction", missing_reason=None)
    assert empty_page["records"] == []
    assert empty_page["population"]["returned_record_slots"] == 0
    assert empty_page["population"]["has_more"] is False


def test_explicit_empty_selection_is_available_zero_with_no_invented_fraction():
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    value = core.calculate_vcf_components(sheet, _selection(record_ordinals=[]))["value"]
    assert value["records"] == []
    population = value["population"]
    for name in ("selected_record_slots", "returned_record_slots", "selected_alt_tokens", "selected_sample_cells",
            "selected_observed_sample_cells", "selected_genotype_slots"):
        assert population[name] == 0
    fraction = population["returned_record_fraction"]
    assert fraction["numerator"] == fraction["denominator"] == 0
    assert fraction["value"] is None and fraction["missing_reason"]


def test_saved_recalculation_uses_only_sheet_and_explicit_field_scope(monkeypatch):
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    original = deepcopy(sheet)
    _no_io_or_parse(monkeypatch)
    first = core.calculate_vcf_components(sheet, _selection())
    selected = _selection(record_ordinals=[0], sample_ordinals=[0], info_keys=[], format_keys=["GT"])
    second = core.calculate_vcf_components(sheet, selected)
    assert first["sheet_sha256"] == second["sheet_sha256"]
    assert second["value"]["selection"] == selected
    population = second["value"]["population"]
    assert population["selected_record_slots"] == 1 and population["selected_alt_tokens"] == 2
    assert population["selected_sample_cells"] == 1 and population["selected_genotype_slots"] == 2
    record, = second["value"]["records"]
    assert record["info"] == []
    assert [row["key"] for row in record["format"]] == ["GT"]
    assert [row["key"] for row in record["samples"][0]["fields"]] == ["GT"]
    hidden = core.calculate_vcf_components(sheet, _selection(format_keys=["DP"]))["value"]
    assert hidden["population"]["selected_genotype_slots"] == 0
    assert all(sample["genotype"] is None for row in hidden["records"] for sample in row["samples"])
    no_fields = core.calculate_vcf_components(sheet, _selection(info_keys=[], format_keys=[]))["value"]
    assert no_fields["population"]["selected_observed_sample_cells"] == 4
    assert no_fields["population"]["selected_genotype_slots"] == 0
    assert all(sample["column_present"] is True and sample["fields"] == []
        for row in no_fields["records"] for sample in row["samples"])
    assert sheet == original


def test_validate_and_projection_do_not_call_calculator_parser_or_external_IO(monkeypatch):
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    components = core.calculate_vcf_components(sheet, _selection(record_ordinals=[1, 0]))
    original = deepcopy(components)
    forbidden = _no_io_or_parse(monkeypatch)
    monkeypatch.setattr(core, "calculate_vcf_components", forbidden)
    assert core.validate_vcf_sheet(sheet) == sheet
    assert core.validate_vcf_components(components) == components
    returned = core.project_vcf_return(components, source_ref=RESULT_SOURCE)
    assert returned == dict(version="vcf_result_return_v1", source_ref=RESULT_SOURCE, value=original["value"])
    assert core.validate_vcf_return(returned) == returned
    returned["value"]["records"].clear()
    assert components == original


def test_complete_header_only_missing_bytes_and_empty_bytes_do_not_share_a_population_state():
    valid_empty = _vcf([], samples=())
    header_only = core.parse_vcf_sheet(_input(valid_empty))
    missing_input = dict(input_id="supplied-vcf-occurrence", retained_file=None,
        original_file=_file(valid_empty), source_ref=None, content=None,
        capture=dict(state="missing", byte_start_0based=0,
            byte_end_0based_exclusive=0, original_size_bytes=len(valid_empty)))
    missing = core.parse_vcf_sheet(missing_input)
    empty_bytes = core.parse_vcf_sheet(_input(b""))
    assert header_only["header"]["state"] == "available"
    assert header_only["records"] == missing["records"] == empty_bytes["records"] == []
    assert missing["raw_content"] is None and missing["header"]["state"] == "missing"
    assert empty_bytes["raw_content"]["size_bytes"] == 0
    assert empty_bytes["header"]["state"] != "available"
    valid_population = core.calculate_vcf_components(header_only, _selection())["value"]["population"]
    missing_population = core.calculate_vcf_components(missing, _selection())["value"]["population"]
    assert valid_population["record_population_complete"] is True
    assert valid_population["total_original_record_slots"] == 0
    assert missing_population["record_population_complete"] is False
    assert missing_population["total_original_record_slots"] is None


def test_truncated_record_retains_original_slot_and_prefix_identity_without_claiming_full_total():
    full = _population_bytes()
    cut = full.index(b"1\t20\tdup") + len(b"1\t20\tdup")
    prefix = full[:cut]
    sheet = core.parse_vcf_sheet(_input(prefix, original=full, capture_state="truncated"))
    assert sheet["input"]["retained_file"]["sha256"] == _sha(prefix)
    assert sheet["input"]["original_file"]["sha256"] == _sha(full)
    assert [row["record_ordinal_0based"] for row in sheet["records"]] == [0, 1]
    assert sheet["records"][1]["state"] == "truncated"
    assert all(token["locator"]["sha256"] == _sha(prefix) for token in _tokens(sheet))
    population = core.calculate_vcf_components(sheet, _selection())["value"]["population"]
    assert population["record_population_complete"] is False
    assert population["total_original_record_slots"] is None
    assert population["retained_record_slots"] == population["selected_record_slots"] == 2
    assert population["selected_sample_cells"] == 4
    assert population["selected_observed_sample_cells"] == 2


def test_unknown_capture_extent_and_complete_last_line_without_newline_are_explicit():
    raw = _population_bytes().removesuffix(b"\n")
    complete = core.parse_vcf_sheet(_input(raw))
    supplied = _input(raw, capture_state="unknown")
    supplied["original_file"] = None
    supplied["capture"]["original_size_bytes"] = None
    unknown = core.parse_vcf_sheet(supplied)
    assert complete["records"][-1]["state"] == "decoded"
    assert unknown["records"][-1]["state"] == "truncated"
    population = core.calculate_vcf_components(unknown, _selection())["value"]["population"]
    assert population["capture_state"] == "unknown"
    assert population["record_population_complete"] is False
    assert population["total_original_record_slots"] is None


def test_missing_sample_column_is_an_unobserved_slot_and_not_an_observed_missing_genotype():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tGT\t0/1",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    record, = sheet["records"]
    assert record["samples"][1]["sample_ordinal_0based"] == 1
    assert record["samples"][1]["column_present"] is False
    assert record["samples"][1]["token"] is record["samples"][1]["genotype"] is None
    assert _field(record, "GT", sample=1)["state"] == "omitted"
    population = core.calculate_vcf_components(sheet, _selection())["value"]["population"]
    assert population["selected_sample_cells"] == 2
    assert population["selected_observed_sample_cells"] == 1
    assert population["selected_genotype_slots"] == 2


@pytest.mark.parametrize("fault", ["retained_hash", "artifact_hash", "complete_original", "missing_with_bytes",
    "content_absent", "unknown_original_too_short"])
def test_declared_input_identity_and_capture_conflicts_are_rejected_before_any_decode(fault, monkeypatch):
    raw = _population_bytes()
    supplied = _input(raw)
    if fault == "retained_hash":
        supplied["retained_file"].update(sha256="0" * 64, artifact_ref="artifact_" + "0" * 64)
    elif fault == "artifact_hash":
        supplied["retained_file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif fault == "complete_original":
        supplied["original_file"] = _file(raw + b"x")
    elif fault == "missing_with_bytes":
        supplied["capture"]["state"] = "missing"
    elif fault == "content_absent":
        supplied["content"] = None
    else:
        supplied["capture"].update(state="unknown", original_size_bytes=None)
        supplied["original_file"] = _file(b"x")
    def forbidden(*args, **kwargs):
        raise AssertionError("contradictory input reached native token decoding")
    monkeypatch.setattr(core, "_meta", forbidden)
    monkeypatch.setattr(core, "_record", forbidden)
    with pytest.raises(ValueError):
        core.parse_vcf_sheet(supplied)


@pytest.mark.parametrize("target,path,bad", [
    ("components", ("value", "population", "selected_record_slots"), True),
    ("components", ("value", "population", "selected_record_slots"), 2.0),
    ("components", ("value", "records", 0, "record_ordinal_0based"), False),
    ("components", ("value", "records", 0, "samples", 0, "sample_ordinal_0based"), True),
    ("return", ("value", "population", "returned_alt_tokens"), 3.0),
    ("return", ("value", "population", "selected_genotype_slots"), True),
    ("return", ("value", "records", 0, "alts", 0, "allele_index_1based"), 1.0),
    ("return", ("value", "records", 0, "samples", 0, "genotype", "alleles", 0, "allele_index"), False),
])
def test_components_and_return_reject_bool_ordinals_and_noninteger_counts_without_recalculation(
        target, path, bad, monkeypatch):
    sheet = core.parse_vcf_sheet(_input(_population_bytes()))
    components = core.calculate_vcf_components(sheet, _selection())
    value = deepcopy(components if target == "components" else core.project_vcf_return(components, RESULT_SOURCE))
    node = value
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = bad
    forbidden = _no_io_or_parse(monkeypatch)
    monkeypatch.setattr(core, "calculate_vcf_components", forbidden)
    validator = core.validate_vcf_components if target == "components" else core.validate_vcf_return
    with pytest.raises(ValueError):
        validator(value)


@pytest.mark.parametrize("fault", ["raw_hash", "noncanonical_base64", "record_ordinal", "record_line", "sample_ordinal", "sample_presence",
    "definition_pointer", "token_span", "declared_number", "missing_state", "flag_state", "extra_key"])
def test_saved_sheet_crossfield_and_byte_witness_tampering_is_not_repaired(fault, monkeypatch):
    raw = (_vcf(["1\t10\t.\tA\tC\t.\t.\tSTR=0\tGT\t0/1\t."], definitions=DEFINITIONS)
        if fault == "flag_state" else _population_bytes())
    sheet = core.parse_vcf_sheet(_input(raw))
    if fault == "raw_hash":
        sheet["raw_content"]["sha256"] = "0" * 64
    elif fault == "noncanonical_base64":
        sheet["raw_content"]["data"] += "\n"
    elif fault == "record_ordinal":
        sheet["records"][0]["record_ordinal_0based"] = 1
    elif fault == "record_line":
        sheet["records"][0]["line_ordinal_0based"] = sheet["records"][1]["line_ordinal_0based"]
    elif fault == "sample_ordinal":
        sheet["records"][0]["samples"][0]["sample_ordinal_0based"] = 1
    elif fault == "sample_presence":
        sheet["records"][0]["samples"][0].update(column_present=False, token=None)
    elif fault == "definition_pointer":
        _field(sheet["records"][0], "AC")["definition_ordinals"] = [100000]
    elif fault == "token_span":
        _field(sheet["records"][0], "AC")["values"][0]["token"]["locator"]["byte_start_0based"] += 1
    elif fault == "declared_number":
        _field(sheet["records"][0], "AC")["declared_number"] = "R"
    elif fault == "missing_state":
        field = _field(sheet["records"][0], "DP", sample=1)
        assert field["value_token"]["raw_token"] == "."
        field["state"] = "available"
        field["cardinality"]["state"] = "matched"
    elif fault == "flag_state":
        field = _field(sheet["records"][0], "STR")
        assert field["value_token"]["raw_token"] == "0"
        field["state"] = "available"
    else:
        sheet["unrecognized"] = None
    forbidden = _no_io_or_parse(monkeypatch)
    monkeypatch.setattr(core, "calculate_vcf_components", forbidden)
    with pytest.raises(ValueError):
        core.validate_vcf_sheet(sheet)


@pytest.mark.parametrize("raw_gt,states", [
    ("0/9", ["called", "outside_alleles"]),
    ("0//1", ["called", "malformed", "called"]),
    ("-1/0", ["malformed", "called"]),
])
def test_malformed_or_outside_GT_allele_slots_remain_literal_and_unresolved(raw_gt, states):
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tGT\t" + raw_gt + "\t.",
    ], definitions=DEFINITIONS)
    record = core.parse_vcf_sheet(_input(raw))["records"][0]
    genotype = record["samples"][0]["genotype"]
    assert genotype["token"]["raw_token"] == raw_gt
    assert [row["state"] for row in genotype["alleles"]] == states
    assert genotype["state"] == "malformed" and genotype["ploidy"] is None
    assert record["issues"]


@pytest.mark.parametrize("encoding", [b"\x1f\x8bengineered-gzip-envelope", b"BCF\x02\x02engineered-binary-envelope"])
def test_unselected_binary_or_compressed_representation_is_retained_without_hidden_decoder(encoding):
    sheet = core.parse_vcf_sheet(_input(encoding))
    assert base64.b64decode(sheet["raw_content"]["data"], validate=True) == encoding
    assert sheet["header"]["state"] == "unsupported" and sheet["header"]["decoder"] == "unsupported"
    assert sheet["records"] == [] and sheet["issues"]


def test_dot_ALT_is_no_supplied_alternate_token_not_a_discarded_record():
    raw = _vcf([
        "1\t10\t.\tA\t.\t.\t.\t.\tGT\t0\t.",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    assert len(sheet["records"]) == 1 and sheet["records"][0]["alts"] == []
    value = core.calculate_vcf_components(sheet, _selection())["value"]
    assert value["population"]["selected_record_slots"] == 1
    assert value["population"]["selected_alt_tokens"] == 0
    assert value["population"]["selected_sample_cells"] == 2
    assert _field(value["records"][0], "GT", sample=1)["state"] == "missing"


def test_schema_copies_keep_only_the_public_result_Source_semantic_and_input_ids_opaque():
    schemas = {kind: core.vcf_result_schema(kind) for kind in ("Sheet", "Selection", "Components", "Value", "Return")}
    assert all(schema["$ref"] == "#/$defs/" + kind for kind, schema in schemas.items())
    definitions = schemas["Return"]["$defs"]
    top_source = definitions["Return"]["properties"]["source_ref"]
    assert top_source["format"] == "reference" and top_source["x-reference-namespace"] == "source"
    for field in (definitions["Input"]["properties"]["source_ref"],
            definitions["File"]["properties"]["artifact_ref"],
            definitions["Location"]["properties"]["artifact_ref"]):
        assert "format" not in field and "x-reference-namespace" not in field
    schemas["Return"]["$defs"]["Return"]["properties"].clear()
    assert core.vcf_result_schema("Return")["$defs"]["Return"]["properties"]


def test_return_requires_a_Source_reference_and_never_promotes_an_input_File_as_result():
    components = core.calculate_vcf_components(core.parse_vcf_sheet(_input(_population_bytes())), _selection())
    with pytest.raises(ValueError):
        core.project_vcf_return(components, source_ref=components["value"]["input"]["retained_file"]["artifact_ref"])


def test_saved_Sheet_cannot_invent_Number_G_ploidy_when_original_FORMAT_has_no_GT(monkeypatch):
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tPL\t0,10,20\t0,5,9",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    field = _field(sheet["records"][0], "PL", sample=0)
    assert field["cardinality"]["ploidy"] is None
    field["cardinality"].update(ploidy=2, ploidy_basis="literal_GT_slots", expected=3, state="matched")
    for value, label in zip(field["values"], [[0, 0], [0, 1], [1, 1]]):
        value["genotype_allele_indices"] = label
    _no_io_or_parse(monkeypatch)
    with pytest.raises(ValueError):
        core.validate_vcf_sheet(sheet)


def test_selected_PL_keeps_its_saved_GT_bound_ploidy_when_GT_is_not_returned():
    raw = _vcf([
        "1\t10\t.\tA\tC\t.\t.\t.\tGT:PL\t0/1:0,10,20\t1:5,0",
    ], definitions=DEFINITIONS)
    sheet = core.parse_vcf_sheet(_input(raw))
    components = core.calculate_vcf_components(sheet, _selection(info_keys=[], format_keys=["PL"]))
    assert components["value"]["population"]["selected_genotype_slots"] == 0
    samples = components["value"]["records"][0]["samples"]
    assert all(sample["genotype"] is None for sample in samples)
    assert [_field(components["value"]["records"][0], "PL", sample=index)["cardinality"]["ploidy"]
        for index in (0, 1)] == [2, 1]
    assert core.validate_vcf_components(components) == components
    returned = core.project_vcf_return(components, RESULT_SOURCE)
    assert core.validate_vcf_return(returned) == returned

