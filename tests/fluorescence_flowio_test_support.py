"""Frozen FlowIO source and retained FCS fixtures for bounded verification only.

This is test support, not a production installation or an acquisition adapter.
Every import, native write and fixture acquisition is guarded by the existing
529 runner's selected request and frozen source location.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import urllib.request


SOURCE_RELATIVE = Path(
    "verification/tool_graders_fluorescence_implementation_2026-10-28_557/flowio_source_1_4_0"
)
UPSTREAM_SOURCE_RELATIVE = Path(
    "verification/tool_graders_fluorescence_fcs_native_2026-10-28_563/upstream_source"
)
ARTIFACT_DIRECTORY = "fluorescence_fcs_native_563"
SOURCE_PINS = {
    "__init__.py": "bca46ee4a3d9480791f5a9f3846780cbf66512e0bd148e6ddfcb8b87deb0132c",
    "_version.py": "904aa13553c428109e7c1afb8c429579532cfff31e48987688389285adedf174",
    "create_fcs.py": "51286e599e17b15f6e50bd9031afd1a0542d74c1337a79405502bc2da70b0b95",
    "exceptions.py": "323103d8558d4e1c2df89e410208c00347cf033eaf40cd64bda62cff5857637a",
    "fcs_keywords.py": "f049f71df8597be5a8298f6219a96d57510ddd5dd21c51c18affeea8171bbfda",
    "flowdata.py": "a03c67d2dce94d0397df046a8b893f8c91bd2fb6092a6384e8c4a8cf5bf7dcd3",
    "utils.py": "e39d2706be637e119b6c64ef420f9308147ff4d85092f1298f3d168855e76677",
}
UPSTREAM_SOURCE_PINS = {
    "tests/test_flowdata.py": "48278e230f67a3a7ce5b9fb6b2f8810aa3e9df498711a2ac7fec17122876ddff",
    "tests/test_fcs_write.py": "3a168cced5ad458c2ca8db595c7f787caad85f571d3a42ca21667d3d2bccec40",
    "tests/test_read_multiple_datasets.py": "0daf298c5d150848fbc02d16c59c5e7cd777847042e56d13d566c9bd578ebf42",
    "LICENSE": "52bfc9d9ada20974b1c1db1376f8c9f7a6958d7a35a79889c062b5076d630bca",
}
FIXTURES = {
    "variable_int_example.fcs": {
        "size_bytes": 6189,
        "git_blob_sha1": "a39387da4514b1d65c10c7db30932f73037531e6",
    },
    "data_start_offset_discrepancy_example.fcs": {
        "size_bytes": 6263,
        "git_blob_sha1": "1aa1819291dc125cfcbbe1c69e56c6c413b06a45",
    },
    "data_stop_offset_discrepancy_example.fcs": {
        "size_bytes": 6263,
        "git_blob_sha1": "bb5527ace0764bbc56aa22ee89a0b5afb57d2c0d",
    },
}


def require_bounded_runtime():
    """Fail before application/scientific imports if invoked outside the runner."""
    supplied = os.environ.get("HMMER529_ATTEMPT")
    if not supplied:
        raise RuntimeError("FCS native verification requires the existing bounded529 runner")
    attempt = Path(supplied).resolve(strict=True)
    snapshot = attempt / "source_snapshot"
    if not Path(__file__).resolve(strict=True).is_relative_to(snapshot):
        raise RuntimeError("FCS test support must execute from the frozen source snapshot")
    selected = json.loads((attempt / "selected_request.json").read_text())
    if (selected["policy"] != {"memory_bytes": 21474836480,
                              "scratch_bytes": 4294967296, "wall_seconds": None}
            or selected["swap_bytes"] != 0):
        raise RuntimeError("FCS verification requires the selected 20GiB/4GiB/zero-swap policy")
    return attempt


def artifact_root():
    root = require_bounded_runtime() / "temporary" / ARTIFACT_DIRECTORY
    root.mkdir(exist_ok=True)
    return root


def file_identity(raw, format_name="fcs"):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha,
            "size_bytes": len(raw), "format": format_name}


def save_json(name, value):
    path = artifact_root() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return path


def _pin_source(root, expected):
    rows = []
    for relative, sha in expected.items():
        path = root / relative
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise AssertionError("frozen FlowIO source mismatch: " + relative)
        rows.append({"path": str(path), "sha256": sha, "size_bytes": len(raw)})
    return rows


@contextmanager
def source_flowio():
    """Load the actual pinned source package; restore the prior module table."""
    attempt = require_bounded_runtime()
    source = attempt / "source_snapshot" / SOURCE_RELATIVE
    pins = _pin_source(source, SOURCE_PINS)
    evidence = attempt / "source_snapshot" / UPSTREAM_SOURCE_RELATIVE
    evidence_pins = _pin_source(evidence, UPSTREAM_SOURCE_PINS)
    saved = {name: module for name, module in sys.modules.copy().items()
             if name == "flowio" or name.startswith("flowio.")}
    for name in saved:
        del sys.modules[name]
    try:
        spec = importlib.util.spec_from_file_location(
            "flowio", source / "__init__.py", submodule_search_locations=[str(source)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["flowio"] = module
        spec.loader.exec_module(module)
        assert module.__version__ == "1.4.0"
        assert sys.byteorder == "little", "The selected decoder profile is verified on little endian only"
        save_json("decoder_source_receipt.json", {
            "kind": "test_only_source_loading_not_production_installation",
            "version": module.__version__, "host_byteorder": sys.byteorder,
            "source_pins": pins, "upstream_evidence_pins": evidence_pins,
        })
        yield module
    finally:
        for name in list(sys.modules):
            if name == "flowio" or name.startswith("flowio."):
                del sys.modules[name]
        sys.modules.update(saved)


def upstream_source_path(relative):
    attempt = require_bounded_runtime()
    path = attempt / "source_snapshot" / UPSTREAM_SOURCE_RELATIVE / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == UPSTREAM_SOURCE_PINS[relative]
    return path


def _verify_upstream(raw, name):
    expected = FIXTURES[name]
    assert len(raw) == expected["size_bytes"], "unexpected upstream fixture byte size"
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert git_blob == expected["git_blob_sha1"], "upstream fixture differs from pinned Git blob"
    return dict(file_identity(raw), git_blob_sha1=git_blob)


def _staged_caches(attempt):
    """Only explicitly staged copies are reusable; never read other live runs."""
    request = json.loads((attempt / "selected_request.json").read_text())
    for relative in request.get("support_trees", []):
        selected = Path(relative)
        if selected.name == "upstream" and selected.parent.name == ARTIFACT_DIRECTORY:
            yield attempt / "source_snapshot" / selected


def acquire_upstream_fixture(name):
    """Acquire once inside the bounded run; retain original bytes and receipt."""
    attempt = require_bounded_runtime()
    expected = FIXTURES[name]
    url = "https://raw.githubusercontent.com/whitews/FlowIO/1.4.0/data/fcs_files/" + name
    root = artifact_root() / "upstream"
    root.mkdir(exist_ok=True)
    target = root / name
    receipt_path = root / (name + ".provenance.json")
    for cache in [root, *_staged_caches(attempt)]:
        cached = cache / name
        if not cached.exists():
            continue
        raw = cached.read_bytes()
        identity = _verify_upstream(raw, name)
        receipt = json.loads((cache / (name + ".provenance.json")).read_text())
        assert receipt["url"] == url
        assert receipt["git_blob_sha1"] == identity["git_blob_sha1"]
        assert receipt["sha256"] == identity["sha256"]
        assert receipt["size_bytes"] == identity["size_bytes"]
        if cache != root:
            target.write_bytes(raw)
            receipt_path.write_text(json.dumps({**receipt, "reused_from": str(cached)}, indent=2) + "\n")
        return raw, json.loads(receipt_path.read_text())
    # No host acquisition, retry, fallback fixture, generated substitute or
    # permissive decode. Network failure is a failed verification attempt.
    with urllib.request.urlopen(url) as response:
        raw = response.read(expected["size_bytes"] + 1)
        final_url = response.geturl()
    identity = _verify_upstream(raw, name)
    target.write_bytes(raw)
    receipt = {
        "kind": "unmodified_upstream_fixture", "repository": "whitews/FlowIO",
        "tag": "1.4.0", "repository_path": "data/fcs_files/" + name,
        "url": url, "resolved_url": final_url,
        "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
        "acquired_inside_attempt": str(attempt), "reused_from": None,
        **identity,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return raw, receipt


def retain_bytes(name, raw, *, kind, details):
    path = artifact_root() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, "refusing to overwrite a different retained fixture"
    else:
        path.write_bytes(raw)
    save_json(name + ".provenance.json", {"kind": kind, **file_identity(raw), **details})
    return raw


def writer_fixture(flowio, name, values, names, *, labels=None, metadata=None):
    require_bounded_runtime()
    stream = io.BytesIO()
    flowio.create_fcs(stream, values, names, opt_channel_names=labels, metadata_dict=metadata)
    return retain_bytes(name, stream.getvalue(), kind="native_writer_synthetic_values", details={
        "writer": "FlowIO.create_fcs", "version": "1.4.0",
        "source_sha256": SOURCE_PINS["create_fcs.py"],
        "event_data_tokens": [repr(value) for value in values],
        "channel_names": names, "optional_channel_names": labels, "metadata": metadata,
        "measurement_origin": "supplied_predicted", "assay_observation_claimed": False,
    })


def mutate_writer(raw, *, text_updates=None, data=None):
    """Rebuild a tiny writer fixture with declared changes, never upstream data.

    This intentionally simple test fixture editor accepts only the writer's
    slash-delimited, unescaped TEXT. It is not an alternative scientific parser.
    Offsets are recomputed to keep a selected malformed condition isolated.
    """
    require_bounded_runtime()
    text_start, text_stop, data_start, data_stop = [
        int(raw[start:start + 8]) for start in (10, 18, 26, 34)
    ]
    text = raw[text_start:text_stop + 1]
    assert text.startswith(b"/") and text.endswith(b"/") and b"//" not in text
    tokens = text[1:-1].decode("utf-8").split("/")
    assert len(tokens) % 2 == 0
    pairs = list(zip(tokens[::2], tokens[1::2]))
    updates = text_updates or {}
    assert set(updates) <= {key for key, _ in pairs}
    pairs = [(key, updates.get(key, value)) for key, value in pairs if updates.get(key, value) is not None]
    data = raw[data_start:data_stop + 1] if data is None else data
    while True:
        text = ("/" + "/".join(token for pair in pairs for token in pair) + "/").encode("utf-8")
        start = text_start + len(text)
        offsets = {"$BEGINDATA": str(start), "$ENDDATA": str(start + len(data) - 1)}
        rebuilt = [(key, offsets.get(key, value)) for key, value in pairs]
        if rebuilt == pairs:
            break
        pairs = rebuilt
    header = bytearray(raw[:text_start])
    for column, value in ((18, start - 1), (26, start), (34, start + len(data) - 1)):
        header[column:column + 8] = f"{value:>8}".encode("ascii")
    return bytes(header) + text + data


def mutation_fixture(name, raw, originals, changes):
    return retain_bytes(name, raw, kind="handcrafted_mutation_of_native_writer", details={
        "parent_files": [file_identity(parent) for parent in originals],
        "changes": changes, "measurement_origin": "supplied_predicted",
        "assay_observation_claimed": False,
    })
