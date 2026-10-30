"""Controlled caller/failure joins, not verification of native FCS decoding.

The stand-in decoder deliberately supplies values independent of the stub bytes.
Actual FlowIO writer output and retained upstream fixtures are tested separately
in test_fluorescence_fcs_native.py under the bounded runner.
"""

from copy import deepcopy
import hashlib
import io
from types import SimpleNamespace

import pytest

from gene_annotation_episode import fluorescence_fcs_reader as reader
from gene_annotation_episode.fluorescence_event_contracts import (
    FluorescenceContractError,
    validate_event_input_request,
    validate_event_parse_result,
    validate_snapshot_request,
)


def _file(raw):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha,
                size_bytes=len(raw), format="fcs")


def _case(values=None, *, count=2, total=None, data_size=None):
    """Handwritten structural stub plus controlled decoder state, not FCS data."""
    values = [11, 12, 21, 22] if values is None else values
    total = (len(values) + count - 1) // count if total is None else total
    data_size = len(values) * 4 if data_size is None else data_size
    stop = 64 + data_size - 1
    raw = (b"FCS3.1    " + b"".join(f"{n:8d}".encode() for n in
                                    (58, 63, 64, stop, 0, 0))
           + b"/stub/" + b"\0" * data_size)
    header = dict(version="3.1", text_start=58, text_stop=63,
                  data_start=64, data_stop=stop, analysis_start=0, analysis_stop=0)
    text = dict(par=str(count), tot=str(total), datatype="F", mode="L",
                nextdata="0", byteord="1,2,3,4", begindata="64", enddata=str(stop),
                beginanalysis="0", endanalysis="0")
    for position in range(1, count + 1):
        text.update({f"p{position}n": f"C{position}", f"p{position}b": "32",
                     f"p{position}r": "262144"})
    source = dict(key="input", file=_file(raw), dataset_position=0,
                  format_profile=reader.FORMAT_PROFILE, extent="partial",
                  native_event_count=9999, metadata=[dict(name="supplied", value="kept")])
    sample = dict(key="sample", primary_domain_key="encoded", label="supplied sample",
                  condition="supplied condition", biological_replicate="bio1",
                  technical_replicate="tech1", associations=[])
    preparation = dict(state="unknown", method=None, parameters_file=None)
    domain = dict(key="encoded", sample_key="sample", source_key="input",
                  parent_domain_key=None, state="available", scale_kind="encoded",
                  compensation=deepcopy(preparation), transformation=deepcopy(preparation),
                  correspondence=None, comparison_basis=None)
    channels = [dict(key=f"channel{position}", ordinal=position - 1,
                     native_name=None, label=None, unit=None, analyte=None,
                     measurement_origin="supplied_predicted")
                for position in range(1, count + 1)]
    kwargs = dict(source=source, sample=sample, channels=channels, domain=domain)
    state = dict(header=header, text=text, analysis={"comment": "native metadata"},
                 events=values)
    return raw, kwargs, state


class _ControlledNativeError(Exception):
    pass


def _decoder(monkeypatch, states, *, fail=None):
    calls = []

    class ControlledFlowData:
        def __init__(self, handle, *, only_text, nextdata_offset, **options):
            assert isinstance(handle, io.BytesIO)
            calls.append(dict(handle=handle, only_text=only_text,
                              offset=nextdata_offset, options=options))
            state = deepcopy(states[nextdata_offset])
            self.header = state["header"]
            self.text = state["text"]
            self.analysis = state["analysis"]
            if fail is not None:
                fail(only_text)
            self.events = None if only_text else state["events"]
            handle.close()

    decoder = SimpleNamespace(
        __version__="1.4.0", FlowData=ControlledFlowData,
        exceptions=SimpleNamespace(FCSParsingError=_ControlledNativeError,
                                   MultipleDataSetsError=_ControlledNativeError),
    )
    monkeypatch.setattr(reader, "_load_decoder", lambda: decoder)
    return calls


def _codes(result):
    return [problem["code"] for problem in result["issues"]]


def _assert_unavailable(result, code):
    assert result["events"] == []
    assert result["source"]["extent"] == "unavailable"
    assert result["domain"]["state"] in {"unavailable", "failed"}
    assert code in _codes(result)
    assert validate_event_parse_result(result) is result


def test_common_request_extraction_keeps_snapshot_validation_and_inputs():
    _, kwargs, _ = _case()
    before = deepcopy(kwargs)
    assert validate_event_input_request(**kwargs) is None
    assert validate_snapshot_request(**kwargs) is None
    assert kwargs == before
    kwargs["channels"][0]["ordinal"] = 7
    for validator in (validate_event_input_request, validate_snapshot_request):
        with pytest.raises(FluorescenceContractError) as error:
            validator(**kwargs)
        assert error.value.code == "invalid_channel"


@pytest.mark.parametrize("bad_raw", ["FCS3.1", bytearray(b"FCS3.1"), memoryview(b"FCS3.1")])
def test_wrong_raw_types_are_caller_errors(bad_raw):
    _, kwargs, _ = _case()
    with pytest.raises(FluorescenceContractError) as error:
        reader.parse_fluorescence_fcs(bad_raw, **kwargs)
    assert error.value.code == "invalid_source"


@pytest.mark.parametrize("field,value,code", [
    ("profile", "fcs_unspecified", "invalid_source"),
    ("scale", "scaled", "invalid_domain"),
    ("origin", "guessed", "invalid_channel"),
    ("file", None, "invalid_source"),
    ("position", -1, "invalid_source"),
])
def test_malformed_requests_reject_before_decoder(field, value, code, monkeypatch):
    raw, kwargs, _ = _case()
    if field == "profile":
        kwargs["source"]["format_profile"] = value
    elif field == "scale":
        kwargs["domain"]["scale_kind"] = value
    elif field == "origin":
        kwargs["channels"][0]["measurement_origin"] = value
    elif field == "position":
        kwargs["source"]["dataset_position"] = value
    else:
        kwargs["source"].update(file=value, extent="unavailable")
    monkeypatch.setattr(reader, "_load_decoder", lambda: pytest.fail("decoder consulted"))
    with pytest.raises(FluorescenceContractError) as error:
        reader.parse_fluorescence_fcs(raw, **kwargs)
    assert error.value.code == code


def test_derived_domain_is_not_an_encoded_primary_input():
    raw, kwargs, _ = _case()
    kwargs["sample"]["primary_domain_key"] = "original"
    kwargs["domain"].update(parent_domain_key="original", correspondence=[])
    with pytest.raises(FluorescenceContractError) as error:
        reader.parse_fluorescence_fcs(raw, **kwargs)
    assert error.value.code == "invalid_domain"


@pytest.mark.parametrize("mutation", ["size", "sha"])
def test_artifact_identity_checked_before_decoder(mutation, monkeypatch):
    raw, kwargs, _ = _case()
    if mutation == "size":
        kwargs["source"]["file"]["size_bytes"] += 1
    else:
        kwargs["source"]["file"].update(sha256="0" * 64, artifact_ref="artifact_" + "0" * 64)
    monkeypatch.setattr(reader, "_load_decoder", lambda: pytest.fail("decoder consulted"))
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "retained_artifact_mismatch")
    assert result["source"]["native_event_count"] is None
    assert result["issues"][0]["stage"] == "input"


@pytest.mark.parametrize("state", ["unavailable", "failed"])
def test_requested_unavailable_domain_preserves_state(state, monkeypatch):
    raw, kwargs, _ = _case()
    kwargs["domain"]["state"] = state
    monkeypatch.setattr(reader, "_load_decoder", lambda: pytest.fail("decoder consulted"))
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "measurement_domain_unavailable")
    assert result["domain"]["state"] == state


@pytest.mark.parametrize("version", [None, "1.3.0", "1.4.1", "1.4.0+local"])
def test_wrong_decoder_version_is_not_used(version, monkeypatch):
    raw, kwargs, _ = _case()
    monkeypatch.setattr(reader.importlib, "import_module", lambda name: SimpleNamespace(__version__=version))
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "decoder_unavailable")


def test_absent_decoder_is_explicit(monkeypatch):
    raw, kwargs, _ = _case()

    def absent(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(reader.importlib, "import_module", absent)
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "decoder_unavailable")


def test_non_little_endian_host_is_not_silently_used(monkeypatch):
    raw, kwargs, state = _case()
    calls = _decoder(monkeypatch, {0: state})
    monkeypatch.setattr(reader.sys, "byteorder", "big")
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "native_format_mismatch")
    assert calls == []


def test_positional_values_metadata_associations_and_input_immutability(monkeypatch):
    raw, kwargs, state = _case()
    association = dict(namespace="supplied-map", identifier="gene7", file=_file(b"map"),
                       source_key=None, location=dict(record_ordinal=0, line_start=None,
                                                       line_end=None, byte_start=0, byte_end=3))
    kwargs["sample"]["associations"] = [association]
    kwargs["channels"][0]["analyte"] = deepcopy(association)
    kwargs["channels"][0]["unit"] = "explicit units"
    kwargs["channels"][1]["measurement_origin"] = "observed"
    state["text"].update(p1n="same", p2n="same", p1s="native alternate label")
    calls = _decoder(monkeypatch, {0: state})
    before = deepcopy(kwargs)
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert kwargs == before
    assert result["sample"] == kwargs["sample"]
    assert result["sample"] is not kwargs["sample"]
    assert result["source"]["file"] == kwargs["source"]["file"]
    assert result["source"]["native_event_count"] == 2
    assert result["source"]["extent"] == "complete"
    assert [c["native_name"] for c in result["channels"]] == ["same", "same"]
    assert [c["label"] for c in result["channels"]] == ["native alternate label", None]
    assert [c["analyte"] for c in result["channels"]] == [association, None]
    assert [c["unit"] for c in result["channels"]] == ["explicit units", None]
    assert result["source"]["metadata"][0] == dict(name="supplied", value="kept")
    metadata = {item["name"]: item["value"] for item in result["source"]["metadata"]}
    assert metadata["flowio.header.data_start"] == "64"
    assert metadata["flowio.text.tot"] == "2"
    assert metadata["flowio.analysis.comment"] == "native metadata"
    assert "flowio.text.p1e" not in metadata
    for ordinal, event in enumerate(result["events"]):
        assert event["source_ordinal"] == event["event_ordinal"] == ordinal
        assert event["location"] == dict(record_ordinal=ordinal, line_start=None,
                                          line_end=None, byte_start=None, byte_end=None)
        assert [cell["measurement"]["state"] for cell in event["values"]] == ["supplied_predicted", "observed"]
        assert all(type(cell["measurement"]["value"]) is int for cell in event["values"])
        assert all(cell["measurement"]["raw"] is None for cell in event["values"])
    assert [(call["only_text"], call["offset"]) for call in calls] == [(True, 0), (False, 0)]
    assert all(call["options"] == {} for call in calls)
    assert calls[0]["handle"] is not calls[1]["handle"]
    assert all(call["handle"].closed for call in calls)


def test_extra_native_column_is_a_binding_error(monkeypatch):
    raw, kwargs, state = _case()
    kwargs["channels"].pop()
    calls = _decoder(monkeypatch, {0: state})
    with pytest.raises(FluorescenceContractError) as error:
        reader.parse_fluorescence_fcs(raw, **kwargs)
    assert error.value.code == "invalid_channel"
    assert [call["only_text"] for call in calls] == [True]


def test_requested_extra_channel_is_unavailable_without_shifting(monkeypatch):
    raw, kwargs, state = _case()
    extra = deepcopy(kwargs["channels"][0])
    extra.update(key="channel3", ordinal=2, native_name="requested missing")
    kwargs["channels"].append(extra)
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert result["source"]["extent"] == "complete"
    assert [cell["measurement"]["value"] for cell in result["events"][0]["values"]] == [11, 12, None]
    assert result["events"][0]["values"][2]["measurement"]["state"] == "unavailable"
    assert any(p["code"] == "channel_missing" and p["channel_key"] == "channel3" for p in result["issues"])


def test_explicit_native_name_mismatch_never_rebinds(monkeypatch):
    raw, kwargs, state = _case()
    kwargs["channels"][0]["native_name"] = "C2"
    calls = _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "native_format_mismatch")
    assert result["issues"][0]["channel_key"] == "channel1"
    assert [call["only_text"] for call in calls] == [True]


def test_nonfinite_cells_preserve_rows_and_ordinals(monkeypatch):
    raw, kwargs, state = _case([1.0, float("nan"), float("inf"), 4.0, 5.0, 6.0])
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert [e["event_ordinal"] for e in result["events"]] == [0, 1, 2]
    assert result["events"][0]["values"][1]["measurement"] == dict(value=None, state="invalid", raw=None)
    assert result["events"][1]["values"][0]["measurement"] == dict(value=None, state="invalid", raw=None)
    assert result["events"][2]["values"][0]["measurement"]["value"] == 5.0
    assert [(p["channel_key"], p["event_ordinal"]) for p in result["issues"]] == [("channel2", 0), ("channel1", 1)]


def test_trailing_partial_row_retains_prefix_cells(monkeypatch):
    raw, kwargs, state = _case([1.0, 2.0, 3.0], total=2)
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert result["source"]["extent"] == "partial"
    assert result["source"]["native_event_count"] == 2
    assert len(result["events"]) == 2
    assert [c["measurement"]["value"] for c in result["events"][1]["values"]] == [3.0, None]
    assert {"truncated_source", "invalid_event_row"} <= set(_codes(result))
    assert all(p["event_ordinal"] == 1 for p in result["issues"])


def test_decoded_count_conflict_preserves_reported_count(monkeypatch):
    raw, kwargs, state = _case(total=17)
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert result["source"]["native_event_count"] == 17
    assert len(result["events"]) == 2
    assert result["source"]["extent"] == "partial"
    assert _codes(result) == ["native_count_conflict"]


def test_complete_empty_dataset_is_not_failed_measurement(monkeypatch):
    raw, kwargs, state = _case([], total=0)
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert result["source"]["extent"] == "complete"
    assert result["source"]["native_event_count"] == 0
    assert result["events"] == result["issues"] == []
    assert result["domain"]["state"] == "available"


def test_decoder_discarded_tail_is_qualified_without_reconstructed_values(monkeypatch):
    raw, kwargs, state = _case([1, 2], total=1, data_size=12)
    state["text"]["datatype"] = "I"
    _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert len(result["events"]) == 1
    assert result["source"]["extent"] == "partial"
    assert {"invalid_event_row", "truncated_source"} <= set(_codes(result))
    assert all(p["event_ordinal"] == 1 for p in result["issues"])


def test_no_retained_values_after_decoder_discards_tail_is_unavailable(monkeypatch):
    raw, kwargs, state = _case([], total=1, data_size=4)
    state["text"]["datatype"] = "I"
    _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "truncated_source")


@pytest.mark.parametrize("only_metadata", [True, False])
def test_strict_native_failure_keeps_established_metadata(only_metadata, monkeypatch):
    raw, kwargs, state = _case()

    def fail(only_text):
        if only_text == only_metadata:
            raise _ControlledNativeError("strict native failure")

    calls = _decoder(monkeypatch, {0: state}, fail=fail)
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "native_format_mismatch")
    assert result["source"]["native_event_count"] == 2
    assert dict(name="flowio.text.tot", value="2") in result["source"]["metadata"]
    assert all(call["handle"].closed for call in calls)


def test_established_native_error_precedes_post_decode_segment_check(monkeypatch):
    raw, kwargs, state = _case()
    # This controlled native failure represents a strict HEADER/TEXT discrepancy.
    # A later independent span check would instead classify ENDDATA as truncated.
    state["text"]["enddata"] = "9999"

    def fail(only_text):
        raise _ControlledNativeError("strict HEADER/TEXT DATA discrepancy")

    calls = _decoder(monkeypatch, {0: state}, fail=fail)
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "native_format_mismatch")
    assert "truncated_source" not in _codes(result)
    assert result["source"]["native_event_count"] == 2
    metadata = {item["name"]: item["value"] for item in result["source"]["metadata"]}
    assert metadata["flowio.header.data_stop"] == "79"
    assert metadata["flowio.text.enddata"] == "9999"
    assert [call["only_text"] for call in calls] == [True]
    assert calls[0]["handle"].closed


@pytest.mark.parametrize("exception_type", [MemoryError, OSError, KeyboardInterrupt, SystemExit])
def test_process_and_resource_exceptions_propagate(exception_type, monkeypatch):
    raw, kwargs, state = _case()

    def fail(only_text):
        raise exception_type("controlled process failure")

    calls = _decoder(monkeypatch, {0: state}, fail=fail)
    with pytest.raises(exception_type):
        reader.parse_fluorescence_fcs(raw, **kwargs)
    assert calls[0]["handle"].closed


@pytest.mark.parametrize("key,value", [
    ("mode", "C"), ("mode", "arbitrary"), ("datatype", "A"),
    ("byteord", "5,4,3,2,1"), ("par", "0"), ("par", "2000000000000"),
    ("p1b", "16"), ("p1r", "NaN"), ("p1r", "0"),
    ("p1n", None), ("p1b", None), ("p1r", None),
])
def test_unsupported_or_structurally_missing_native_fields_reject(key, value, monkeypatch):
    raw, kwargs, state = _case()
    if value is None:
        state["text"].pop(key)
    else:
        state["text"][key] = value
    calls = _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "native_format_mismatch")
    assert [call["only_text"] for call in calls] == [True]


def test_extra_native_parameter_declaration_is_structural_failure(monkeypatch):
    raw, kwargs, state = _case()
    state["text"]["p3n"] = "undeclared third parameter"
    _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "native_format_mismatch")


@pytest.mark.parametrize("text_change,code", [
    ({"nextdata": "-1"}, "native_format_mismatch"),
    ({"nextdata": "8"}, "native_format_mismatch"),
    ({"nextdata": "9999"}, "truncated_source"),
    ({"begindata": "-1"}, "native_format_mismatch"),
    ({"enddata": "9999"}, "truncated_source"),
    ({"beginanalysis": "64", "endanalysis": "9999"}, "truncated_source"),
])
def test_invalid_links_and_absolute_segment_bounds_reject(text_change, code, monkeypatch):
    raw, kwargs, state = _case()
    state["text"].update(text_change)
    calls = _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), code)
    assert [call["only_text"] for call in calls] == [True]


def test_missing_requested_dataset_does_not_decode_other_events(monkeypatch):
    raw, kwargs, state = _case()
    kwargs["source"]["dataset_position"] = 1
    calls = _decoder(monkeypatch, {0: state})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, "source_unavailable")
    assert result["source"]["native_event_count"] is None
    assert result["source"]["metadata"] == kwargs["source"]["metadata"]
    assert [call["only_text"] for call in calls] == [True]


def test_multidataset_relative_navigation_only_decodes_selected(monkeypatch):
    first, kwargs, state0 = _case([1, 2])
    second, _, state1 = _case([3, 4, 5, 6])
    third, _, state2 = _case([7, 8])
    state0["text"]["nextdata"] = str(len(first))
    state1["text"]["nextdata"] = str(len(second))
    raw = first + second + third
    kwargs["source"].update(file=_file(raw), dataset_position=2)
    selected_offset = len(first) + len(second)
    calls = _decoder(monkeypatch, {0: state0, len(first): state1, selected_offset: state2})
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert [c["measurement"]["value"] for c in result["events"][0]["values"]] == [7, 8]
    assert result["source"]["dataset_position"] == 2
    assert result["source"]["native_event_count"] == 1
    assert [(c["only_text"], c["offset"]) for c in calls] == [
        (True, 0), (True, len(first)), (True, selected_offset), (False, selected_offset)]


def test_selected_data_cannot_extend_into_later_dataset(monkeypatch):
    first, kwargs, state = _case([1, 2])
    second, _, _ = _case([3, 4])
    state["text"].update(nextdata=str(len(first)), enddata=str(len(first) + 3))
    state["header"]["data_stop"] = len(first) + 3
    raw = first + second
    kwargs["source"]["file"] = _file(raw)
    calls = _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), "native_format_mismatch")
    assert [call["only_text"] for call in calls] == [True]


@pytest.mark.parametrize("raw,code", [(b"FCS3.1", "truncated_source"),
                                      (b"garbage" + b" " * 60, "native_format_mismatch")])
def test_wrong_or_truncated_native_bytes_prevent_decoder_reads(raw, code, monkeypatch):
    _, kwargs, state = _case()
    kwargs["source"]["file"] = _file(raw)
    calls = _decoder(monkeypatch, {0: state})
    _assert_unavailable(reader.parse_fluorescence_fcs(raw, **kwargs), code)
    assert calls == []


def _analysis_case(kind, *, selected_second):
    """Controlled ANALYSIS spans; values still come from the stand-in decoder."""
    selected, kwargs, state = _case([7, 8])
    start = len(selected)
    payload = b"|comment|valid|"
    if kind == "valid":
        stop = start + len(payload) - 1
        selected += payload
    elif kind == "eof":
        stop = start + len(payload) - 1
    else:
        stop = start + 5
        state["text"]["nextdata"] = str(len(selected))
    selected = (selected[:42] + f"{start:8d}{stop:8d}".encode()
                + selected[58:])
    state["header"].update(analysis_start=start, analysis_stop=stop)
    state["text"].update(beginanalysis=str(start), endanalysis=str(stop))
    trailing = _case([9, 10])[0] if kind == "next" else b""
    if selected_second:
        first, _, leading = _case([1, 2])
        leading["text"]["nextdata"] = str(len(first))
        states = {0: leading, len(first): state}
        raw = first + selected + trailing
        selected_offset = len(first)
        kwargs["source"]["dataset_position"] = 1
    else:
        states = {0: state}
        raw = selected + trailing
        selected_offset = 0
    kwargs["source"]["file"] = _file(raw)
    return raw, kwargs, states, selected_offset


def _analysis_reading_decoder(monkeypatch, states, *, read_method):
    """Emulate the pinned constructor's HEADER -> TEXT -> ANALYSIS I/O order."""
    calls, attempted, completed = [], [], []

    class ControlledReadingFlowData:
        def __init__(self, handle, *, only_text, nextdata_offset, **options):
            assert isinstance(handle, io.BytesIO)
            assert options == {}
            calls.append(handle)
            state = deepcopy(states[nextdata_offset])
            handle.seek(nextdata_offset)
            assert len(handle.read(58)) == 58
            self.header = state["header"]
            handle.seek(nextdata_offset + self.header["text_start"])
            assert handle.read(self.header["text_stop"] - self.header["text_start"] + 1) == b"/stub/"
            self.text = state["text"]
            start = int(self.text["beginanalysis"])
            stop = int(self.text["endanalysis"])
            if start != stop:
                handle.seek(nextdata_offset + start)
                attempted.append(nextdata_offset)
                if read_method == "readinto":
                    buffer = bytearray(stop - start + 1)
                    size = handle.readinto(buffer)
                    payload = bytes(buffer[:size])
                else:
                    payload = getattr(handle, read_method)(stop - start + 1)
                completed.append(nextdata_offset)
                self.analysis = {"raw": payload.decode("ascii")}
            else:
                self.analysis = {}
            self.events = None if only_text else state["events"]
            handle.close()

    decoder = SimpleNamespace(
        __version__="1.4.0", FlowData=ControlledReadingFlowData,
        exceptions=SimpleNamespace(FCSParsingError=_ControlledNativeError,
                                   MultipleDataSetsError=_ControlledNativeError),
    )
    monkeypatch.setattr(reader, "_load_decoder", lambda: decoder)
    return calls, attempted, completed


@pytest.mark.parametrize("selected_second", [False, True])
@pytest.mark.parametrize("kind,code", [("eof", "truncated_source"),
                                       ("next", "native_format_mismatch")])
@pytest.mark.parametrize("read_method", ["read", "read1", "readinto"])
def test_invalid_analysis_read_is_prevented_before_facts_are_established(
        selected_second, kind, code, read_method, monkeypatch):
    raw, kwargs, states, offset = _analysis_case(kind, selected_second=selected_second)
    calls, attempted, completed = _analysis_reading_decoder(
        monkeypatch, states, read_method=read_method)
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    _assert_unavailable(result, code)
    assert attempted == [offset]
    assert completed == []
    assert all(handle.closed for handle in calls)
    metadata = {item["name"]: item["value"] for item in result["source"]["metadata"]}
    assert metadata["flowio.header.version"] == "3.1"
    assert metadata["flowio.text.tot"] == "1"
    assert result["source"]["native_event_count"] == 1
    assert not any(name.startswith("flowio.analysis.") for name in metadata)


@pytest.mark.parametrize("selected_second", [False, True])
@pytest.mark.parametrize("read_method", ["read", "read1", "readinto"])
def test_valid_analysis_and_selected_values_survive_guard(
        selected_second, read_method, monkeypatch):
    raw, kwargs, states, offset = _analysis_case("valid", selected_second=selected_second)
    calls, attempted, completed = _analysis_reading_decoder(
        monkeypatch, states, read_method=read_method)
    result = reader.parse_fluorescence_fcs(raw, **kwargs)
    assert result["source"]["extent"] == "complete"
    assert result["issues"] == []
    assert attempted == completed == [offset, offset]
    assert all(handle.closed for handle in calls)
    metadata = {item["name"]: item["value"] for item in result["source"]["metadata"]}
    assert metadata["flowio.analysis.raw"] == "|comment|valid|"
    assert [c["measurement"]["value"] for c in result["events"][0]["values"]] == [7, 8]


@pytest.mark.parametrize("exception_type", [MemoryError, OSError])
def test_guard_does_not_swallow_resource_failure(exception_type, monkeypatch):
    raw, kwargs, states, _ = _analysis_case("valid", selected_second=False)
    calls, attempted, completed = _analysis_reading_decoder(monkeypatch, states, read_method="read")

    def fail(native, offset, size):
        raise exception_type("controlled guard resource failure")

    monkeypatch.setattr(reader, "_segments", fail)
    with pytest.raises(exception_type):
        reader.parse_fluorescence_fcs(raw, **kwargs)
    assert attempted == [0]
    assert completed == []
    assert calls[0].closed
