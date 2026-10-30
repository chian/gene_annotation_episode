"""Synthetic format fixtures; these do not establish acquired assay results."""

from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.fluorescence_event_contracts import (
    FluorescenceContractError,
    PARSE_SCHEMA,
    TABLE_SCHEMA,
    validate_event_parse_result,
)
from gene_annotation_episode.fluorescence_event_readers import (
    parse_fluorescence_csv,
    parse_fluorescence_table_snapshot,
)
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet


def _identity(raw, format_name):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha,
                size_bytes=len(raw), format=format_name)


def event_request(raw, names, *, snapshot=False, header=True, source_key="source",
                  domain_key="domain", primary_domain_key="domain"):
    """Explicit synthetic input request, reusable by the bounded integration run."""
    source = dict(key=source_key, file=_identity(raw, "json" if snapshot else "csv"),
                  dataset_position=0, format_profile="synthetic_snapshot" if snapshot else "synthetic_csv",
                  extent="unavailable", native_event_count=919,
                  metadata=[dict(name="fixture_origin", value="synthetic format fixture"),
                            dict(name="native duplicate", value="first"),
                            dict(name="native duplicate", value="second")])
    sample = dict(key="sample", primary_domain_key=primary_domain_key, label="sample label",
                  condition=None, biological_replicate=None, technical_replicate=None,
                  associations=[])
    preparation = dict(state="not_applied", method=None, parameters_file=None)
    domain = dict(key=domain_key, sample_key="sample", source_key=source_key,
                  parent_domain_key=None, state="available", scale_kind="as_supplied",
                  compensation=deepcopy(preparation), transformation=deepcopy(preparation),
                  correspondence=None, comparison_basis=None)
    channels = [dict(key=f"{domain_key}_channel_{i}", ordinal=i, native_name=name,
                     label="duplicate label", unit="arbitrary_instrument_units", analyte=None,
                     measurement_origin="observed") for i, name in enumerate(names)]
    request = dict(source=source, sample=sample, channels=channels, domain=domain)
    if not snapshot:
        request["format_spec"] = dict(encoding="utf-8", delimiter=",", quotechar='"',
                                      escapechar=None, doublequote=True,
                                      header=header, missing_tokens=[])
    return request


def _snapshot(columns, rows):
    return json.dumps(dict(schema=TABLE_SCHEMA, columns=columns, rows=rows),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _measurements(result, channel=0):
    return [event["values"][channel]["measurement"] for event in result["events"]]


def _values(result, channel=0):
    return [measurement["value"] for measurement in _measurements(result, channel)]


def _codes(result):
    return [item["code"] for item in result["issues"]]


def complete_example_batch(*, snapshot=False):
    """Packet548 operands: inclusive100..250 should select ordinals1..5."""
    values = [90, 100, 125, 150, 200, 250, 300, 350]
    if snapshot:
        raw = _snapshot(["signal"], [[value] for value in values])
        return parse_fluorescence_table_snapshot(raw, **event_request(raw, ["signal"], snapshot=True))
    raw = b"signal\r\n90\r\n100\r\n125\r\n150\r\n200\r\n250\r\n300\r\n350\r\n"
    return parse_fluorescence_csv(raw, **event_request(raw, ["signal"]))


@pytest.mark.parametrize("snapshot", [False, True])
def test_complete_packet548_operands_keep_identity_metadata_and_unknown_native_count(snapshot):
    batch = complete_example_batch(snapshot=snapshot)
    assert validate_event_parse_result(batch) is batch
    assert batch["schema"] == PARSE_SCHEMA
    assert _values(batch) == [90, 100, 125, 150, 200, 250, 300, 350]
    assert batch["source"]["extent"] == "complete"
    assert batch["source"]["native_event_count"] is None
    assert [e["source_ordinal"] for e in batch["events"]] == list(range(8))
    assert [e["event_ordinal"] for e in batch["events"]] == list(range(8))
    assert batch["source"]["metadata"][1:] == [
        dict(name="native duplicate", value="first"),
        dict(name="native duplicate", value="second"),
    ]
    assert batch["issues"] == []


def test_csv_crlf_quoted_newline_bom_and_decoded_raw_have_exact_byte_locations():
    raw = b'\xef\xbb\xbfA,B\r\n"1\r\n",2\r\n3,"4""x"\r\n'
    request = event_request(raw, ["A", "B"])
    request["format_spec"]["encoding"] = "utf-8-sig"
    result = parse_fluorescence_csv(raw, **request)
    first, second = result["events"]
    assert first["location"] == dict(record_ordinal=0, line_start=2, line_end=3,
                                     byte_start=8, byte_end=17)
    assert second["location"] == dict(record_ordinal=1, line_start=4, line_end=4,
                                      byte_start=17, byte_end=len(raw))
    assert raw[first["location"]["byte_start"]:first["location"]["byte_end"]] == b'"1\r\n",2\r\n'
    assert _measurements(result)[0] == dict(value=1.0, state="observed", raw="1\r\n")
    assert _measurements(result, 1)[1] == dict(value=None, state="invalid", raw='4"x')
    assert result["issues"][0]["event_ordinal"] == 1
    assert result["issues"][0]["channel_key"] == "domain_channel_1"


def test_unicode_header_and_carriage_return_endings_keep_byte_offsets():
    raw = "α,B\r1,2\r3,4".encode("utf-8")
    result = parse_fluorescence_csv(raw, **event_request(raw, [None, "B"]))
    assert result["channels"][0]["native_name"] == "α"
    assert result["events"][0]["location"] == dict(
        record_ordinal=0, line_start=2, line_end=2, byte_start=5, byte_end=9)
    assert result["events"][1]["location"] == dict(
        record_ordinal=1, line_start=3, line_end=3, byte_start=9, byte_end=12)


def test_explicit_escapes_keep_decoded_tokens_and_multiline_record_locations():
    raw = b"A,B\n1\\,x,2\n3\\\n4,5\n"
    request = event_request(raw, ["A", "B"])
    request["format_spec"]["escapechar"] = "\\"
    result = parse_fluorescence_csv(raw, **request)
    assert [m["raw"] for m in _measurements(result)] == ["1,x", "3\n4"]
    assert _values(result) == [None, None]
    assert _values(result, 1) == [2.0, 5.0]
    assert result["events"][1]["location"] == dict(
        record_ordinal=1, line_start=3, line_end=4, byte_start=11, byte_end=len(raw))
    assert result["source"]["extent"] == "complete"


def test_exact_missing_tokens_and_finite_conversion_never_change_raw():
    raw = b"A,B\nNA,0\n, 2 \n NA,NaN\n-Inf,1e999\n 0 ,bad\n"
    request = event_request(raw, ["A", "B"])
    request["format_spec"]["missing_tokens"] = ["NA"]
    result = parse_fluorescence_csv(raw, **request)
    assert [m["state"] for m in _measurements(result)] == ["missing", "invalid", "invalid", "invalid", "observed"]
    assert [m["raw"] for m in _measurements(result)] == ["NA", "", " NA", "-Inf", " 0 "]
    assert _measurements(result, 1)[0] == dict(value=0.0, state="observed", raw="0")
    assert _measurements(result, 1)[1] == dict(value=2.0, state="observed", raw=" 2 ")
    assert _values(result, 1) == [0.0, 2.0, None, None, None]
    assert result["source"]["extent"] == "complete"


def test_empty_token_is_missing_only_when_declared_and_blank_rows_are_not_skipped():
    raw = b'A,B\n"",1\n\n2\n3,4,99\n5,6\n'
    request = event_request(raw, ["A", "B"])
    request["format_spec"]["missing_tokens"] = [""]
    result = parse_fluorescence_csv(raw, **request)
    assert [e["event_ordinal"] for e in result["events"]] == [0, 1, 2, 3, 4]
    assert _measurements(result)[0] == dict(value=None, state="missing", raw="")
    assert _measurements(result)[1] == dict(value=None, state="unavailable", raw=None)
    assert _values(result) == [None, None, 2.0, 3.0, 5.0]
    assert _values(result, 1) == [1.0, None, None, 4.0, 6.0]
    assert [i["event_ordinal"] for i in result["issues"] if i["code"] == "invalid_event_row"] == [1, 2, 3]
    assert result["source"]["extent"] == "complete"


def test_strict_quote_error_with_closed_record_preserves_unavailable_row_and_next_ordinal():
    raw = b'A,B\n1,2\n"3"x,4\n5,6\n'
    result = parse_fluorescence_csv(raw, **event_request(raw, ["A", "B"]))
    assert _values(result) == [1.0, None, 5.0]
    assert _values(result, 1) == [2.0, None, 6.0]
    assert result["events"][1]["location"] == dict(
        record_ordinal=1, line_start=3, line_end=3, byte_start=8, byte_end=15)
    assert result["events"][2]["event_ordinal"] == 2
    assert _codes(result) == ["invalid_event_row"]
    assert result["source"]["extent"] == "complete"


@pytest.mark.parametrize("suffix", [b'"3,4\n5,6\n', b'"3"x,"4\n5,6\n'])
def test_unrecoverable_quoting_preserves_only_confirmed_prefix_and_unknown_total(suffix):
    raw = b"A,B\r\n1,2\r\n" + suffix
    result = parse_fluorescence_csv(raw, **event_request(raw, ["A", "B"]))
    assert _values(result) == [1.0]
    assert result["source"]["extent"] == "partial"
    assert result["source"]["native_event_count"] is None
    assert _codes(result) == ["truncated_source"]
    assert result["issues"][0]["event_ordinal"] == 1
    assert result["events"][0]["location"]["byte_end"] == 10


def test_unrecoverable_first_data_record_keeps_a_valid_empty_prefix():
    raw = b'A\n"1\n'
    result = parse_fluorescence_csv(raw, **event_request(raw, ["A"]))
    assert result["events"] == []
    assert result["source"]["extent"] == "partial"
    assert result["domain"]["state"] == "available"
    assert result["issues"][0]["event_ordinal"] == 0


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_utf8_suffix_retains_complete_records_without_inventing_truncated_last_row(bom):
    raw = bom + b"A\r\n1\r\n2\xff\r\n3\r\n"
    request = event_request(raw, ["A"])
    request["format_spec"]["encoding"] = "utf-8-sig" if bom else "utf-8"
    result = parse_fluorescence_csv(raw, **request)
    assert _values(result) == [1.0]
    assert result["source"]["extent"] == "partial"
    assert "input_encoding_invalid" in _codes(result)
    assert result["events"][0]["location"]["byte_start"] == len(bom) + 3
    assert result["events"][0]["location"]["byte_end"] == len(bom) + 6
    assert result["issues"][-1]["event_ordinal"] == 1


@pytest.mark.parametrize("raw", [b"\xff\n1\n", b'"A\n\xff', b"A\xff\n1\n"])
def test_utf8_failure_in_header_is_unavailable(raw):
    result = parse_fluorescence_csv(raw, **event_request(raw, [None]))
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert "input_encoding_invalid" in _codes(result)


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("changed", ["digest", "size"])
def test_exact_byte_identity_is_required_before_admission(snapshot, changed):
    raw = _snapshot(["A"], [[1]]) if snapshot else b"A\n1\n"
    request = event_request(raw, ["A"], snapshot=snapshot)
    if changed == "digest":
        request["source"]["file"]["sha256"] = "0" * 64
        request["source"]["file"]["artifact_ref"] = "artifact_" + "0" * 64
    else:
        request["source"]["file"]["size_bytes"] += 1
    before = deepcopy(request)
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    result = parser(raw, **request)
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert _codes(result) == ["retained_artifact_mismatch"]
    assert result["source"]["file"] == before["source"]["file"]
    assert request == before


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("state", ["unavailable", "failed"])
def test_declared_unavailable_domain_is_not_made_available_by_readable_bytes(snapshot, state):
    raw = _snapshot(["A"], [[1]]) if snapshot else b"A\n1\n"
    request = event_request(raw, ["A"], snapshot=snapshot)
    request["domain"]["state"] = state
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    result = parser(raw, **request)
    assert result["events"] == []
    assert result["domain"]["state"] == state
    assert _codes(result) == ["measurement_domain_unavailable"]


def test_explicit_dialect_header_and_positional_duplicate_names_are_not_guessed(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dialect sniffing is not allowed")
    monkeypatch.setattr("csv.Sniffer.sniff", forbidden)
    raw = b"A;A\n'1';'2'\n'1';'2'\n"
    request = event_request(raw, [None, None])
    request["format_spec"].update(delimiter=";", quotechar="'", escapechar="\\", doublequote=False)
    result = parse_fluorescence_csv(raw, **request)
    assert [c["native_name"] for c in result["channels"]] == ["A", "A"]
    assert [c["ordinal"] for c in result["channels"]] == [0, 1]
    assert _values(result) == [1.0, 1.0]
    assert _values(result, 1) == [2.0, 2.0]
    assert [e["event_ordinal"] for e in result["events"]] == [0, 1]
    no_header = event_request(b"A\n1\n", [None], header=False)
    result = parse_fluorescence_csv(b"A\n1\n", **no_header)
    assert _values(result) == [None, 1.0]
    assert _measurements(result)[0]["raw"] == "A"


@pytest.mark.parametrize("snapshot", [False, True])
def test_complete_column_array_cannot_silently_drop_unbound_channels(snapshot):
    raw = _snapshot(["A", "B"], [[1, 2]]) if snapshot else b"A,B\n1,2\n"
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    with pytest.raises(FluorescenceContractError) as error:
        parser(raw, **event_request(raw, ["A"], snapshot=snapshot))
    assert error.value.code == "invalid_channel"


@pytest.mark.parametrize("snapshot", [False, True])
def test_nonmatching_positional_header_does_not_reassign_columns(snapshot):
    raw = _snapshot(["B", "A"], [[1, 2]]) if snapshot else b"B,A\n1,2\n"
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    result = parser(raw, **event_request(raw, ["A", "B"], snapshot=snapshot))
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert set(_codes(result)) == {"native_format_mismatch"}
    assert [c["native_name"] for c in result["channels"]] == ["A", "B"]


@pytest.mark.parametrize("snapshot", [False, True])
def test_short_header_preserves_bound_present_values_without_inventing_a_name(snapshot):
    raw = _snapshot(["A"], [[1], [2, 3]]) if snapshot else b"A\n1\n2,3\n"
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    request = event_request(raw, ["A", None], snapshot=snapshot)
    result = parser(raw, **request)
    assert result["channels"][1]["native_name"] is None
    assert _values(result) == [1, 2]
    assert _values(result, 1) == [None, 3]
    assert any(i["code"] == "channel_missing" and i["event_ordinal"] is None
               and i["channel_key"] == "domain_channel_1" for i in result["issues"])
    assert any(i["code"] == "invalid_event_row" and i["event_ordinal"] == 1
               for i in result["issues"])


def test_headerless_extra_fields_are_qualified_at_original_positions():
    raw = b"1,2\n3\n"
    result = parse_fluorescence_csv(raw, **event_request(raw, [None], header=False))
    assert _values(result) == [1.0, 3.0]
    assert _codes(result) == ["invalid_event_row"]
    assert result["issues"][0]["event_ordinal"] == 0


@pytest.mark.parametrize("header", [False, True])
def test_complete_empty_csv_does_not_invent_header_or_unknown_population(header):
    request = event_request(b"", [None], header=header)
    result = parse_fluorescence_csv(b"", **request)
    assert result["events"] == []
    assert result["source"]["extent"] == "complete"
    assert result["source"]["native_event_count"] is None
    assert result["domain"]["state"] == "available"
    assert result["channels"][0]["native_name"] is None
    assert result["issues"] == []


def test_snapshot_null_bad_cells_and_rows_preserve_original_ordinals():
    raw = _snapshot(["A", "B"], [[0, None], [True, "3"], None, [4], [5, 6, 7], [8, 9]])
    result = parse_fluorescence_table_snapshot(raw, **event_request(raw, ["A", "B"], snapshot=True))
    assert _values(result) == [0, None, None, 4, 5, 8]
    assert _values(result, 1) == [None, None, None, None, 6, 9]
    assert [m["state"] for m in _measurements(result)] == ["observed", "invalid", "unavailable", "observed", "observed", "observed"]
    assert _measurements(result, 1)[0]["state"] == "missing"
    assert [e["event_ordinal"] for e in result["events"]] == list(range(6))
    assert [i["event_ordinal"] for i in result["issues"] if i["code"] == "invalid_event_row"] == [2, 3, 4]
    assert all(m["raw"] is None for m in _measurements(result))
    assert result["events"][5]["location"] == dict(
        record_ordinal=5, line_start=None, line_end=None, byte_start=None, byte_end=None)


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity"])
def test_snapshot_nonstandard_json_constants_reject_the_document(token):
    raw = b'{"schema":"fluorescence_event_table_v1","columns":["A"],"rows":[[1],[' + token + b']]}'
    result = parse_fluorescence_table_snapshot(raw, **event_request(raw, ["A"], snapshot=True))
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert _codes(result) == ["native_format_mismatch"]


@pytest.mark.parametrize("raw", [
    b"not JSON", b'{"schema":"wrong","columns":[],"rows":[]}',
    b'{"schema":"fluorescence_event_table_v1","columns":[],"rows":[],"extra":1}',
    b'{"schema":"fluorescence_event_table_v1","columns":[],"rows":[],"rows":[[1]]}',
    b'{"schema":"fluorescence_event_table_v1","columns":[2],"rows":[]}',
    b'{"schema":"fluorescence_event_table_v1","columns":[],"rows":{}}',
])
def test_snapshot_schema_and_object_keys_are_explicit(raw):
    result = parse_fluorescence_table_snapshot(raw, **event_request(raw, [], snapshot=True))
    assert result["events"] == []
    assert _codes(result) == ["native_format_mismatch"]


def test_snapshot_numeric_overflow_is_an_invalid_cell_and_empty_snapshot_is_complete():
    raw = b'{"schema":"fluorescence_event_table_v1","columns":["A"],"rows":[[1e999],[0]]}'
    result = parse_fluorescence_table_snapshot(raw, **event_request(raw, ["A"], snapshot=True))
    assert _values(result) == [None, 0]
    assert _measurements(result)[0]["state"] == "invalid"
    empty = _snapshot([None], [])
    result = parse_fluorescence_table_snapshot(empty, **event_request(empty, [None], snapshot=True))
    assert result["source"]["extent"] == "complete"
    assert result["events"] == []
    assert result["issues"] == []


def test_snapshot_retains_integral_native_values_without_rounding_through_float():
    exact_integer = 1180591620717411303425
    raw = _snapshot(["A"], [[exact_integer]])
    result = parse_fluorescence_table_snapshot(raw, **event_request(raw, ["A"], snapshot=True))
    assert _values(result) == [exact_integer]
    assert type(_values(result)[0]) is int
    assert _measurements(result)[0]["raw"] is None


def test_analyte_associations_are_supplied_facts_not_native_label_inference():
    raw = b"CD4_IFN-IL-17\n1\n"
    request = event_request(raw, [None])
    unmapped = parse_fluorescence_csv(raw, **request)
    assert unmapped["channels"][0]["analyte"] is None
    assert unmapped["sample"]["associations"] == []
    mapping = b"fixture analyte assignment"
    association = dict(namespace="synthetic_namespace", identifier="synthetic_analyte",
                       file=_identity(mapping, "txt"), source_key="source",
                       location=dict(record_ordinal=0, line_start=1, line_end=1,
                                     byte_start=0, byte_end=len(mapping)))
    request["channels"][0]["analyte"] = association
    request["sample"]["associations"] = [association]
    result = parse_fluorescence_csv(raw, **request)
    assert result["channels"][0]["analyte"] == association
    assert result["sample"]["associations"] == [association]
    assert result["channels"][0]["analyte"] is not association


@pytest.mark.parametrize("snapshot", [False, True])
def test_explicit_prediction_origin_survives_and_inputs_outputs_do_not_alias(snapshot):
    raw = _snapshot(["A", "B"], [[1, 2]]) if snapshot else b"A,B\n1,2\n"
    request = event_request(raw, ["A", "B"], snapshot=snapshot)
    request["channels"][1]["measurement_origin"] = "supplied_predicted"
    before = deepcopy(request)
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    result = parser(raw, **request)
    assert _measurements(result)[0]["state"] == "observed"
    assert _measurements(result, 1)[0]["state"] == "supplied_predicted"
    assert all("measurement_origin" not in channel for channel in result["channels"])
    assert request == before
    result["source"]["metadata"][0]["value"] = "changed only in returned copy"
    result["domain"]["transformation"]["state"] = "unknown"
    result["sample"]["associations"].append({})
    assert request == before


def test_derived_correspondence_is_explicit_never_matched_from_equal_values():
    primary_raw = b"A\n5\n5\n5\n"
    primary = parse_fluorescence_csv(primary_raw, **event_request(primary_raw, ["A"]))
    prepared_raw = _snapshot(["A"], [[50], [51]])
    request = event_request(prepared_raw, ["A"], snapshot=True,
                            source_key="prepared_source", domain_key="prepared")
    request["domain"]["parent_domain_key"] = "domain"
    request["domain"]["correspondence"] = [dict(source_ordinal=0, event_ordinal=2),
                                           dict(source_ordinal=1, event_ordinal=0)]
    prepared = parse_fluorescence_table_snapshot(prepared_raw, **request)
    assert [e["event_ordinal"] for e in prepared["events"]] == [2, 0]
    assert [e["source_ordinal"] for e in prepared["events"]] == [0, 1]
    assert _values(prepared) == [50, 51]
    sheet = populate_fluorescence_sheet([primary, prepared], populations=[], gates=[],
                                        control_pairs=[], native_reports=[])
    assert [(e["domain_key"], e["event_ordinal"]) for e in sheet["events"]] == [
        ("domain", 0), ("domain", 1), ("domain", 2), ("prepared", 2), ("prepared", 0)]


def test_partial_derived_prefix_may_leave_mapped_rows_unobserved_but_not_invent_them():
    raw = b'A\n50\n"51\n'
    request = event_request(raw, ["A"], source_key="prepared_source", domain_key="prepared")
    request["domain"]["parent_domain_key"] = "domain"
    request["domain"]["correspondence"] = [dict(source_ordinal=0, event_ordinal=2),
                                           dict(source_ordinal=1, event_ordinal=0)]
    result = parse_fluorescence_csv(raw, **request)
    assert result["source"]["extent"] == "partial"
    assert [e["event_ordinal"] for e in result["events"]] == [2]
    assert result["issues"][0]["event_ordinal"] == 0
    assert result["events"][0]["location"]["record_ordinal"] == 0


@pytest.mark.parametrize("mapping", [[], [dict(source_ordinal=0, event_ordinal=2), dict(source_ordinal=1, event_ordinal=0)]])
def test_complete_derived_input_requires_exact_source_row_correspondence(mapping):
    raw = b"A\n50\n"
    request = event_request(raw, ["A"], source_key="prepared_source", domain_key="prepared")
    request["domain"]["parent_domain_key"] = "domain"
    request["domain"]["correspondence"] = mapping
    with pytest.raises(FluorescenceContractError) as error:
        parse_fluorescence_csv(raw, **request)
    assert error.value.code == "invalid_domain"


@pytest.mark.parametrize("snapshot", [False, True])
def test_parser_uses_shared_request_validation_and_rejects_nonbytes(snapshot):
    raw = _snapshot(["A"], [[1]]) if snapshot else b"A\n1\n"
    parser = parse_fluorescence_table_snapshot if snapshot else parse_fluorescence_csv
    request = event_request(raw, ["A"], snapshot=snapshot)
    del request["channels"][0]["measurement_origin"]
    with pytest.raises(FluorescenceContractError) as error:
        parser(raw, **request)
    assert error.value.code == "invalid_channel"
    request = event_request(raw, ["A"], snapshot=snapshot)
    with pytest.raises(FluorescenceContractError) as error:
        parser(bytearray(raw), **request)
    assert error.value.code == "invalid_source"


def test_reader_does_not_acquire_files_or_import_table_packages(monkeypatch):
    import builtins
    raw = _snapshot(["A"], [[1]])
    request = event_request(raw, ["A"], snapshot=True)
    original_import = builtins.__import__
    def guard_import(name, *args, **kwargs):
        if name.split(".")[0] in {"pandas", "numpy", "pickle", "subprocess", "socket", "requests"}:
            raise AssertionError("reader attempted acquisition or external conversion")
        return original_import(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("reader attempted file I/O")
    monkeypatch.setattr(builtins, "__import__", guard_import)
    monkeypatch.setattr(builtins, "open", forbidden)
    assert _values(parse_fluorescence_table_snapshot(raw, **request)) == [1]


def test_csv_and_snapshot_use_the_same_sheet_and_calculator_for_packet548():
    from gene_annotation_episode.fluorescence_event_calculations import calculate_fluorescence_sheet
    populations = [dict(key="all", sample_key="sample", kind="all", event_ordinals=None)]
    gates = [dict(key="selected", sample_key="sample", parent=dict(kind="population", key="all"),
                  kind="threshold", domain_key="domain", channel_key="domain_channel_0",
                  lower=dict(value=100, inclusive=True), upper=dict(value=250, inclusive=True))]
    parameters = dict(fraction_requests=[dict(gate_key="selected", denominator="parent")],
                      intensity_requests=[dict(gate_key="selected", domain_key="domain", channel_key="domain_channel_0")],
                      control_requests=[], native_comparison_requests=[])
    calculated = []
    for snapshot in (False, True):
        sheet = populate_fluorescence_sheet([complete_example_batch(snapshot=snapshot)],
                                            populations=populations, gates=gates,
                                            control_pairs=[], native_reports=[])
        calculated.append(calculate_fluorescence_sheet(sheet, parameters=parameters))
    assert calculated[0]["memberships"] == calculated[1]["memberships"]
    assert calculated[0]["cells"] == calculated[1]["cells"]
    values = {cell["request"]["metric"]: cell["value"] for cell in calculated[0]["cells"]}
    assert values["selected_event_count"] == 5
    assert values["parent_event_count"] == 8
    assert values["selected_fraction"] == 0.625
    assert values["selected_percent"] == 62.5
    assert values["selected_intensity_sum"] == 825
    assert values["selected_intensity_mean"] == 165
    assert values["selected_intensity_median"] == 150
