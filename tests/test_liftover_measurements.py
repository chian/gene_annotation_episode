"""Engineered native-boundary controls, not executed PyLiftover measurements.

Every converter below is a test double. These cases check input bytes, explicit
stream construction, call accounting and the handoff to the verified pure core.
They establish no native installation, conversion accuracy, custody or episode.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import urllib.request

import pytest

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode import liftover_measurements as measurements


CHAIN = b"chain 9 literal.source 20 + 0 10 literal.target 20 - 0 10 1\n10\n"


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
