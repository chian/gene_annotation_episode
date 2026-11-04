"""Engineered native-boundary controls, not executed PyLiftover measurements.

Every converter below is a test double. These cases check input bytes, explicit
stream construction, call accounting and the handoff to the verified pure core.
They establish no native installation, conversion accuracy, custody or episode.
"""
from copy import deepcopy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
from types import ModuleType
import urllib.request

import pytest

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode import liftover_measurements as measurements


CHAIN = b"chain 9 literal.source 20 + 0 10 literal.target 20 - 0 10 1\n10\n"


def selected_input(tmp_path, *, format="ucsc_chain", filename="selected.input", content=None):
    directory = tmp_path / "owned"
    directory.mkdir()
    if content is None:
        content = gzip.compress(CHAIN, mtime=0) if format == "ucsc_chain_gzip" else CHAIN
    path = directory / filename
    path.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    request = dict(version=core.REQUEST_VERSION,
        chain=dict(file=dict(artifact_ref="artifact_" + sha, sha256=sha,
            size_bytes=len(content), format=format), source_ref="source_" + "a" * 24),
        point=dict(chromosome="literal.source", position_0based=0, strand="-"))
    return request, path, directory


def mock_native(monkeypatch, *, native=None, constructor_error=None, conversion_error=None):
    seen = dict(constructors=[], conversions=[], versions=[])
    class Converter:
        def convert_coordinate(self, *arguments):
            seen["conversions"].append(arguments)
            if conversion_error is not None:
                raise conversion_error
            return native
    def constructor(stream, **kwargs):
        entry = dict(stream=stream, kwargs=kwargs)
        seen["constructors"].append(entry)
        assert not isinstance(stream, (str, bytes, Path))
        entry["bytes"] = stream.read()
        if constructor_error is not None:
            raise constructor_error
        return Converter()
    module = ModuleType("pyliftover")
    module.LiftOver = constructor
    monkeypatch.setitem(sys.modules, "pyliftover", module)
    def version(name):
        seen["versions"].append(name)
        return "engineered-boundary-version"
    monkeypatch.setattr(measurements.metadata, "version", version)
    def no_network(*args, **kwargs):
        raise AssertionError("engineered producer boundary must not acquire a chain")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(urllib.request, "urlretrieve", no_network)
    return seen


def run(request, path, directory):
    return measurements.run_liftover_tool_request(request,
        chain_path=path, output_directory=directory)


def assert_failure(result, *, code, state, count):
    observation = result["sheet"]["observation"]
    assert result["version"] == measurements.RESULT_VERSION
    assert result["components"]["sheet"] == result["sheet"]
    assert observation["failure"]["code"] == code
    assert observation["failure"]["stage"] == core.FAILURES[code]
    assert observation["failure"]["exception_message"] is None
    assert observation["conversion_call_state"] == state
    assert observation["conversion_call_count"] == count
    assert observation["result_state"] == "unavailable" and observation["native_result"] is None
    population = result["components"]["population"]
    assert population["conversion_call_scope"] == core.CALL_SCOPE
    assert population["mapping_count"] is None and result["components"]["rows"] == []


@pytest.mark.parametrize("chromosome,position,strand", [
    ("unprefixed", 0, "-"), ("chr:literal", 7, "+"), ("scaffold.alt", 1099511627776, "-")])
def test_one_stream_constructor_and_one_exact_literal_point_call(tmp_path, monkeypatch, chromosome, position, strand):
    request, path, directory = selected_input(tmp_path)
    request["point"] = dict(chromosome=chromosome, position_0based=position, strand=strand)
    original, original_bytes, original_files = deepcopy(request), path.read_bytes(), set(directory.iterdir())
    native = [("target.literal", 0, "-", 0)]
    seen = mock_native(monkeypatch, native=native)
    result = run(request, path, directory)
    assert len(seen["constructors"]) == 1
    constructed = seen["constructors"][0]
    assert constructed["bytes"] == CHAIN and constructed["stream"].closed
    assert constructed["kwargs"] == dict(search_dir=None, cache_dir=None,
        use_web=False, write_cache=False, show_progress=False)
    assert seen["conversions"] == [(chromosome, position, strand)]
    assert seen["versions"] == ["pyliftover"]
    assert result["request"] == request == original
    assert result["sheet"]["observation"]["software"] == {
        "name": "pyliftover", "version": "engineered-boundary-version"}
    assert result["sheet"]["observation"]["native_result"] == [list(row) for row in native]
    assert result["components"]["sheet"] == result["sheet"]
    assert path.read_bytes() == original_bytes and set(directory.iterdir()) == original_files
    assert str(directory) not in json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("format,filename", [
    ("ucsc_chain", "plain_named.chain.gz"), ("ucsc_chain_gzip", "compressed_named.chain")])
def test_declared_compression_not_filename_selects_binary_decoding(tmp_path, monkeypatch, format, filename):
    request, path, directory = selected_input(tmp_path, format=format, filename=filename)
    seen = mock_native(monkeypatch, native=[])
    result = run(request, path, directory)
    assert seen["constructors"][0]["bytes"] == CHAIN
    assert result["request"]["chain"]["file"] == request["chain"]["file"]
    assert result["sheet"]["observation"]["native_result"] == []
    assert seen["conversions"] == [("literal.source", 0, "-")]


@pytest.mark.parametrize("changed", ["sha", "size", "tail", "decompressed_identity"])
def test_full_selected_raw_sha_and_size_precede_native_construction(tmp_path, monkeypatch, changed):
    request, path, directory = selected_input(tmp_path,
        format="ucsc_chain_gzip" if changed == "decompressed_identity" else "ucsc_chain")
    file = request["chain"]["file"]
    if changed == "sha":
        file.update(sha256="b" * 64, artifact_ref="artifact_" + "b" * 64)
    elif changed == "size":
        file["size_bytes"] += 1
    elif changed == "tail":
        path.write_bytes(path.read_bytes()[:-1] + b"X")
    else:
        sha = hashlib.sha256(CHAIN).hexdigest()
        file.update(sha256=sha, artifact_ref="artifact_" + sha, size_bytes=len(CHAIN))
    seen = mock_native(monkeypatch)
    result = run(request, path, directory)
    assert_failure(result, code="input_identity_conflict", state="not_started", count=0)
    assert seen["constructors"] == seen["conversions"] == seen["versions"] == []


@pytest.mark.parametrize("case", ["missing_chain", "missing_directory", "directory_as_chain", "outside", "outside_symlink"])
def test_unavailable_and_outside_owned_inputs_never_open_or_convert(tmp_path, monkeypatch, case):
    request, path, directory = selected_input(tmp_path)
    forbidden_path = None
    if case == "missing_chain":
        path.unlink()
    elif case == "missing_directory":
        directory = tmp_path / "missing-owned"
    elif case == "directory_as_chain":
        path = directory
    else:
        forbidden_path = tmp_path / "outside.chain"
        forbidden_path.write_bytes(CHAIN)
        if case == "outside":
            path = forbidden_path
        else:
            path.unlink()
            path.symlink_to(forbidden_path)
    seen = mock_native(monkeypatch)
    original_open = Path.open
    def guarded_open(self, *args, **kwargs):
        assert forbidden_path is None or self != forbidden_path, "outside payload must not be opened"
        return original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded_open)
    result = run(request, path, directory)
    assert_failure(result, code="input_identity_conflict" if case.startswith("outside") else "input_unavailable",
        state="not_started", count=0)
    assert seen["constructors"] == seen["conversions"] == []
    assert str(tmp_path) not in json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("phase,code", [("open", "input_unavailable"), ("read", "chain_read_failed"), ("seek", "chain_read_failed")])
def test_open_stream_and_rewind_failures_precede_constructor(tmp_path, monkeypatch, phase, code):
    request, path, directory = selected_input(tmp_path)
    seen = mock_native(monkeypatch)
    class BrokenStream(io.BytesIO):
        def read(self, *args):
            if phase == "read":
                raise OSError("engineered copied-chain read failure")
            return super().read(*args)
        def seek(self, *args):
            if phase == "seek":
                raise OSError("engineered copied-chain rewind failure")
            return super().seek(*args)
    original_open = Path.open
    def opened(self, *args, **kwargs):
        if self == path:
            if phase == "open":
                raise PermissionError("engineered copied-chain open failure")
            return BrokenStream(CHAIN)
        return original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    result = run(request, path, directory)
    assert_failure(result, code=code, state="not_started", count=0)
    assert seen["constructors"] == seen["conversions"] == []


@pytest.mark.parametrize("kind,code", [("parse", "chain_parse_failed"), ("io", "chain_read_failed"), ("eof", "chain_read_failed")])
def test_constructor_failures_have_zero_convert_calls_and_private_original_diagnostic(tmp_path, monkeypatch, capsys, kind, code):
    request, path, directory = selected_input(tmp_path)
    message = "engineered original diagnostic " + str(path)
    error = {"parse": ValueError, "io": OSError, "eof": EOFError}[kind](message)
    seen = mock_native(monkeypatch, constructor_error=error)
    result = run(request, path, directory)
    assert_failure(result, code=code, state="not_started", count=0)
    assert len(seen["constructors"]) == 1 and seen["conversions"] == []
    assert result["sheet"]["observation"]["failure"]["exception_type"] == type(error).__name__
    assert message in capsys.readouterr().err
    assert message not in json.dumps(result) and str(path) not in json.dumps(result)


def test_invalid_selected_gzip_is_read_failure_without_format_fallback(tmp_path, monkeypatch):
    request, path, directory = selected_input(tmp_path, format="ucsc_chain_gzip", content=CHAIN)
    seen = mock_native(monkeypatch)
    result = run(request, path, directory)
    assert_failure(result, code="chain_read_failed", state="not_started", count=0)
    assert len(seen["constructors"]) == 1 and seen["conversions"] == []


@pytest.mark.parametrize("native", [None, [], [("Z", 9, "+", -3), ("A", 0, "-", 99), ("Z", 9, "+", -3)]],
    ids=["unknown_contig", "empty_mapping", "all_native_order_and_duplicates"])
def test_complete_original_native_results_are_handed_to_one_core_unchanged(tmp_path, monkeypatch, native):
    request, path, directory = selected_input(tmp_path)
    original = deepcopy(native)
    seen = mock_native(monkeypatch, native=native)
    result = run(request, path, directory)
    observed = result["sheet"]["observation"]
    expected_json = None if native is None else [list(row) for row in native]
    assert observed["native_result"] == expected_json and native == original
    assert observed["conversion_call_state"] == "returned" and observed["conversion_call_count"] == 1
    assert observed["result_state"] == "captured" and observed["failure"] is None
    assert len(seen["constructors"]) == len(seen["conversions"]) == 1


@pytest.mark.parametrize("kind", ["value", "io"])
def test_thrown_conversion_is_one_call_not_an_empty_mapping(tmp_path, monkeypatch, capsys, kind):
    request, path, directory = selected_input(tmp_path)
    message = "engineered original conversion diagnostic " + str(path)
    error = (ValueError if kind == "value" else OSError)(message)
    seen = mock_native(monkeypatch, conversion_error=error)
    result = run(request, path, directory)
    assert_failure(result, code="coordinate_conversion_failed", state="raised", count=1)
    assert seen["conversions"] == [("literal.source", 0, "-")]
    assert message in capsys.readouterr().err and message not in json.dumps(result)


@pytest.mark.parametrize("kind", ["nonfinite", "unsupported"])
def test_capture_failure_preserves_known_returned_call_count(tmp_path, monkeypatch, kind):
    request, path, directory = selected_input(tmp_path)
    native = [["target", 0, "+", float("inf") if kind == "nonfinite" else object()]]
    seen = mock_native(monkeypatch, native=native)
    result = run(request, path, directory)
    assert_failure(result, code="native_result_capture_failed", state="returned", count=1)
    assert len(seen["conversions"]) == 1


def test_native_malformed_row_is_retained_not_a_dropped_or_fabricated_partial_execution(tmp_path, monkeypatch):
    request, path, directory = selected_input(tmp_path)
    native = [("left", 1, "+", 9), False, ("right", 2, "-", 8)]
    seen = mock_native(monkeypatch, native=native)
    result = run(request, path, directory)
    assert result["sheet"]["observation"]["native_result"] == [["left", 1, "+", 9], False, ["right", 2, "-", 8]]
    assert [row["ordinal"] for row in result["components"]["rows"]] == [0, 1, 2]
    assert result["sheet"]["parsing_state"] == "partial"
    assert result["sheet"]["observation"]["failure"] is None and len(seen["conversions"]) == 1


def test_missing_distribution_version_remains_unknown(tmp_path, monkeypatch):
    request, path, directory = selected_input(tmp_path)
    seen = mock_native(monkeypatch, native=[])
    def unavailable(name):
        assert name == "pyliftover"
        raise measurements.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(measurements.metadata, "version", unavailable)
    result = run(request, path, directory)
    assert result["sheet"]["observation"]["software"]["version"] is None
    assert len(seen["conversions"]) == 1


def test_missing_native_software_propagates_as_operational_failure(tmp_path, monkeypatch):
    request, path, directory = selected_input(tmp_path)
    seen = mock_native(monkeypatch)
    monkeypatch.setitem(sys.modules, "pyliftover", None)
    with pytest.raises(ModuleNotFoundError):
        run(request, path, directory)
    assert seen["constructors"] == seen["conversions"] == []


def test_core_request_validation_occurs_before_any_native_or_file_work(tmp_path, monkeypatch):
    request, path, directory = selected_input(tmp_path)
    request["point"]["position_0based"] = True
    seen = mock_native(monkeypatch)
    def no_open(*args, **kwargs):
        raise AssertionError("invalid request must not open a chain")
    monkeypatch.setattr(Path, "open", no_open)
    with pytest.raises(ValueError):
        run(request, path, directory)
    assert seen["constructors"] == seen["conversions"] == seen["versions"] == []


def saved_envelope(native):
    """Engineered saved cells only; no native call, file or publication proof."""
    sha = hashlib.sha256(CHAIN).hexdigest()
    request = dict(version=core.REQUEST_VERSION,
        chain=dict(file=dict(artifact_ref="artifact_" + sha, sha256=sha,
            size_bytes=len(CHAIN), format="ucsc_chain"), source_ref=None),
        point=dict(chromosome="literal.source", position_0based=0, strand="-"))
    observation = dict(version=core.OBSERVATION_VERSION,
        request_sha256=core.liftover_request_sha256(request),
        chain_file=deepcopy(request["chain"]["file"]),
        software=dict(name="pyliftover", version=None), conversion_call_state="returned",
        conversion_call_count=1, result_state="captured", native_result=native, failure=None)
    sheet = core.populate_liftover_sheet(request, native_observation=observation)
    return dict(version=measurements.RESULT_VERSION, request=request,
        sheet=sheet, components=core.calculate_liftover_components(sheet))


def test_saved_envelope_roundtrip_uses_only_core_validation_without_native_or_io(monkeypatch):
    import builtins
    original = saved_envelope([("literal.target", 0, "-", -9)])
    serialized = json.dumps(original, sort_keys=True, separators=(",", ":"), allow_nan=False)
    restored = json.loads(serialized)
    original_import = builtins.__import__
    def no_converter(name, *args, **kwargs):
        assert not name.startswith("pyliftover"), "saved envelope must not import native software"
        return original_import(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved envelope validation must not perform native work or IO")
    monkeypatch.setattr(builtins, "__import__", no_converter)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib.request, "urlretrieve", forbidden)
    monkeypatch.setattr(measurements, "run_liftover_tool_request", forbidden)
    validated = measurements.validate_liftover_tool_result(restored)
    assert json.dumps(validated, sort_keys=True, separators=(",", ":"), allow_nan=False) == serialized
    assert json.dumps(restored, sort_keys=True, separators=(",", ":"), allow_nan=False) == serialized
    assert validated is not restored and validated["sheet"] is not restored["sheet"]


@pytest.mark.parametrize("changed", ["extra", "missing", "version", "request", "sheet"])
def test_saved_envelope_requires_closed_version_and_matching_independently_valid_copies(changed):
    value = saved_envelope([("target", 1, "+", 3)])
    if changed == "extra":
        value["control_path"] = "not-a-scientific-field"
    elif changed == "missing":
        del value["request"]
    elif changed == "version":
        value["version"] = "ordinary_liftover_result_unknown"
    elif changed == "request":
        value["request"]["point"]["strand"] = "+"
        core.validate_liftover_request(value["request"])
    else:
        value["sheet"] = saved_envelope([("other", 2, "-", 4)])["sheet"]
        core.validate_liftover_sheet(value["sheet"])
    with pytest.raises(ValueError, match="liftover_tool_result_"):
        measurements.validate_liftover_tool_result(value)


@pytest.mark.parametrize("other", [1.0, True], ids=["float_alias", "bool_alias"])
def test_saved_envelope_cross_copy_comparison_preserves_native_json_scalar_types(other):
    value = saved_envelope({"native_cell": 1})
    alternative = saved_envelope({"native_cell": other})
    assert value["sheet"] == alternative["sheet"]
    value["components"] = alternative["components"]
    core.validate_liftover_sheet(value["sheet"])
    core.validate_liftover_components(value["components"])
    with pytest.raises(ValueError, match="liftover_tool_result_identity_conflict"):
        measurements.validate_liftover_tool_result(value)


@pytest.mark.parametrize("changed", ["sheet", "components"])
def test_saved_envelope_delegates_internal_tamper_rejection_to_existing_core(changed):
    value = saved_envelope([("target", 1, "+", 3)])
    if changed == "sheet":
        value["sheet"]["rows"][0]["target_position_0based"] = 2
    else:
        value["components"]["population"]["mapping_count"] = 2
    with pytest.raises(ValueError, match="liftover_saved_"):
        measurements.validate_liftover_tool_result(value)
