"""Exercise installed ComparativeSystems parsing, calculation and saved return codec.

Inputs retain synthetic qualified wrappers and source-executed tiny native
fixtures. This verifies installed code/data, not live service or host custody.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

installed, specimen_path, expected_path = map(lambda value: Path(value).resolve(), sys.argv[1:4])
expected_pin = sys.argv[4]
sys.path.insert(0, str(installed))
from gene_annotation_episode import bvbrc_comparative_systems_bundle_adapter as provider
from gene_annotation_episode import bvbrc_comparative_systems_bundle_resolution as resolution
from gene_annotation_episode import bvbrc_comparative_systems_native as native
from gene_annotation_episode import bvbrc_comparative_systems_sheet as builder
from gene_annotation_episode import bvbrc_comparative_systems_data_inputs as data
from gene_annotation_episode import bvbrc_comparative_systems_calculators as calculations
from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
from gene_annotation_episode.bvbrc_comparative_systems_publication import encode_comparative_publication_result
from gene_annotation_episode.bvbrc_proteome_bundle_adapter import implementation_sha256 as legacy_pin
from gene_annotation_episode.bvbrc_proteome_bundle_adapter_v2 import implementation_sha256 as directional_pin

assert Path(provider.__file__).resolve().is_relative_to(installed)
assert provider.implementation_sha256() == expected_pin
assert legacy_pin() == "4a38563301a75481c9fc8cfcde77e0a09b9d8e08f3c0562e9635c18692e44a20"
assert directional_pin() == "7dbdd8cfbc5193d149af6bfd314e0199ff074a1d671a39e1395a785b22b10ce9"
specimen = json.loads(specimen_path.read_text())
expected = json.loads(expected_path.read_text())
args = {key: value for key, value in specimen.items() if key not in {"byte_files", "classification"}}
raw = {}
for reference, binding in specimen["byte_files"].items():
    path = (specimen_path.parent / binding["path"]).resolve()
    assert path.is_relative_to(specimen_path.parent)
    value = path.read_bytes()
    assert hashlib.sha256(value).hexdigest() == binding["sha256"] and len(value) == binding["byte_count"]
    raw[reference] = value
args["artifact_bytes"] = raw
before = deepcopy(args)


def forbidden(*args, **kwargs):
    raise AssertionError("installed pure computation attempted acquisition, execution or scientific replay")


with patch("socket.socket", side_effect=forbidden), patch("socket.create_connection", side_effect=forbidden), \
        patch("subprocess.Popen", side_effect=forbidden), patch("urllib.request.urlopen", side_effect=forbidden):
    result = provider.consume_bundle(**args)
assert args == before and result == expected and result["status"] == "ok"
context = {"retained_requirements": [], "retained_diagnostics": [], "failure_status": None}
patches = [(resolution, name) for name in ("parse_comparative_systems_document", "build_comparative_systems_sheet",
    "extract_comparative_systems_data_inputs", "calculate_comparative_systems_components")]
patches += [(native, "parse_comparative_systems_document"), (builder, "build_comparative_systems_sheet"),
    (data, "extract_comparative_systems_data_inputs"), (calculations, "calculate_comparative_systems_components"),
    (Path, "read_bytes"), (Path, "read_text")]
with ExitStack() as stack:
    for owner, name in patches:
        stack.enter_context(patch.object(owner, name, forbidden))
    for name in ("socket.socket", "socket.create_connection", "subprocess.Popen", "urllib.request.urlopen"):
        stack.enter_context(patch(name, side_effect=forbidden))
    validate_saved_comparative_systems_projection(result["sheet"], result["components"],
        **{key: result[key] for key in ("facts", "status", "missing_requirements", "diagnostics")},
        requested_form=args["requested_form"], parameters=args["parameters"],
        original_task=args["bundle"]["original_task"], bundle=args["bundle"], failure_context=context)
    encoded = encode_comparative_publication_result(result, failure_context=context)
    assert encoded["components"]["calculations"] == result["components"]
    assert encoded["components"]["failure_context"] == context
value = lambda name: result["facts"][name]["values"][0]
assert value("native")["value"] == value("retained_ratio")["output"]["value"] == 75
assert (value("later_ratio")["numerator"]["value"], value("later_ratio")["denominator"]["value"]) == (4, 9)
assert value("native_reference")["output"]["value"] == 2 / 4
assert value("later_reference")["output"]["value"] == 3 / 4
assert value("active_genomes")["value"] == 0
modules = {}
for name, module in sorted(sys.modules.items()):
    if name == "gene_annotation_episode" or name.startswith("gene_annotation_episode."):
        location = getattr(module, "__file__", None)
        if location is not None:
            path = Path(location).resolve()
            assert path.is_relative_to(installed), (name, str(path))
            modules[name] = str(path.relative_to(installed))
print(json.dumps({"provider_sha256": expected_pin, "status": result["status"],
    "native_percent": 75, "later_percent": value("later_ratio")["output"]["value"],
    "later_operands": [4, 9], "native_reference_operands": [2, 4], "later_reference_operands": [3, 4],
    "active_genome_count": 0, "reference_release": result["sheet"]["reference_memberships"][0]["release"],
    "matches_retained_result": True, "saved_validation_without_scientific_replay": True,
    "imported_modules": modules, "live_service_execution_verified": False,
    "authenticated_publication_verified": False}))
